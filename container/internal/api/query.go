package api

import (
	"context"
	crand "crypto/rand"
	"encoding/json"
	"fmt"
	"io"
	"log/slog"
	"net/http"
	"net/url"
	"strings"
	"time"
)

// Query sends a question to the notebook's AI and returns the answer.
// It uses the streaming GenerateFreeFormStreamed endpoint (not batchexecute).
func (c *Client) Query(
	ctx context.Context,
	notebookID string,
	queryText string,
	sourceIDs []string,
	conversationID string,
	timeout time.Duration,
) (map[string]any, error) {
	if err := c.auth.EnsureTokens(ctx); err != nil {
		return nil, err
	}
	if timeout == 0 {
		timeout = 120 * time.Second
	}

	// If no sourceIDs provided, get all from notebook
	if sourceIDs == nil {
		ids, err := c.getNotebookSourceIDs(ctx, notebookID)
		if err != nil {
			return nil, fmt.Errorf("getting source IDs: %w", err)
		}
		sourceIDs = ids
	}

	isNewConversation := conversationID == ""
	if isNewConversation {
		conversationID = generateUUID()
	}

	// Build sources array: [[sid]] for each source
	sourcesArray := make([]any, len(sourceIDs))
	for i, sid := range sourceIDs {
		sourcesArray[i] = []any{[]any{sid}}
	}

	// Build params: [sources, query, history, config, conversation_id]
	params := []any{
		sourcesArray,
		queryText,
		nil, // conversation history (nil for new)
		[]any{2, nil, []any{1}},
		conversationID,
	}

	paramsJSON, _ := json.Marshal(params)
	fReq := []any{nil, string(paramsJSON)}
	fReqJSON, _ := json.Marshal(fReq)

	// Build form body (trailing & to match NotebookLM format)
	body := "f.req=" + url.QueryEscape(string(fReqJSON))
	if csrf := c.auth.CSRFToken(); csrf != "" {
		body += "&at=" + url.QueryEscape(csrf)
	}
	body += "&"

	// Build URL
	reqID := c.reqID.Add(100000)
	queryParams := url.Values{
		"bl":     {c.buildLabel},
		"hl":     {"en"},
		"_reqid": {fmt.Sprintf("%d", reqID)},
		"rt":     {"c"},
	}
	if sid := c.auth.SessionID(); sid != "" {
		queryParams.Set("f.sid", sid)
	}

	fullURL := BaseURL + StreamQueryPath + "?" + queryParams.Encode()

	req, err := http.NewRequestWithContext(ctx, "POST", fullURL, strings.NewReader(body))
	if err != nil {
		return nil, fmt.Errorf("creating query request: %w", err)
	}
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded;charset=UTF-8")
	req.Header.Set("Cookie", c.auth.Cookies())
	req.Header.Set("Origin", BaseURL)
	req.Header.Set("Referer", BaseURL+"/")
	req.Header.Set("X-Same-Domain", "1")

	slog.Debug("sending query", "notebook", notebookID, "query_len", len(queryText))

	// Use a per-request context timeout instead of creating a new http.Client
	queryCtx, cancel := context.WithTimeout(ctx, timeout)
	defer cancel()
	req = req.WithContext(queryCtx)

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("query request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("query returned HTTP %d", resp.StatusCode)
	}

	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("reading query response: %w", err)
	}

	answer := parseQueryResponse(string(respBody))

	return map[string]any{
		"answer":          answer,
		"conversation_id": conversationID,
		"is_follow_up":    !isNewConversation,
	}, nil
}

// parseQueryResponse extracts the answer text from the streaming response.
// Strategy: find the longest chunk marked as type 1 (answer) vs type 2 (thinking).
func parseQueryResponse(text string) string {
	// Strip anti-XSSI prefix
	if strings.HasPrefix(text, ")]}'") {
		text = text[4:]
	}

	lines := strings.Split(strings.TrimSpace(text), "\n")
	longestAnswer := ""
	longestThinking := ""

	i := 0
	for i < len(lines) {
		line := strings.TrimSpace(lines[i])
		if line == "" {
			i++
			continue
		}

		// Check if line is a byte count (number)
		isNumber := true
		for _, ch := range line {
			if ch < '0' || ch > '9' {
				isNumber = false
				break
			}
		}

		if isNumber && i+1 < len(lines) {
			i++
			answerText, isAnswer := extractAnswerFromChunk(lines[i])
			if answerText != "" {
				if isAnswer && len(answerText) > len(longestAnswer) {
					longestAnswer = answerText
				} else if !isAnswer && len(answerText) > len(longestThinking) {
					longestThinking = answerText
				}
			}
		} else {
			answerText, isAnswer := extractAnswerFromChunk(line)
			if answerText != "" {
				if isAnswer && len(answerText) > len(longestAnswer) {
					longestAnswer = answerText
				} else if !isAnswer && len(answerText) > len(longestThinking) {
					longestThinking = answerText
				}
			}
		}
		i++
	}

	if longestAnswer != "" {
		return longestAnswer
	}
	return longestThinking
}

// extractAnswerFromChunk parses a single JSON chunk for answer text.
func extractAnswerFromChunk(jsonStr string) (string, bool) {
	var data []json.RawMessage
	if err := json.Unmarshal([]byte(jsonStr), &data); err != nil {
		return "", false
	}

	for _, item := range data {
		var inner []json.RawMessage
		if json.Unmarshal(item, &inner) != nil || len(inner) < 3 {
			continue
		}
		var marker string
		if json.Unmarshal(inner[0], &marker) != nil || marker != "wrb.fr" {
			continue
		}

		var payloadStr string
		if json.Unmarshal(inner[2], &payloadStr) != nil {
			continue
		}

		var innerData []json.RawMessage
		if json.Unmarshal([]byte(payloadStr), &innerData) != nil || len(innerData) == 0 {
			continue
		}

		firstElem, _ := ParseRawArray(innerData[0])
		if len(firstElem) > 0 {
			text := GetString(firstElem[0])
			if len(text) > 20 {
				// Check type indicator at firstElem[4][-1]: 1=answer, 2=thinking
				isAnswer := false
				if len(firstElem) > 4 {
					typeInfo, _ := ParseRawArray(firstElem[4])
					if len(typeInfo) > 0 {
						lastVal := GetInt(typeInfo[len(typeInfo)-1])
						isAnswer = lastVal == 1
					}
				}
				return text, isAnswer
			}
		}
	}

	return "", false
}

// getNotebookSourceIDs extracts all source IDs from a notebook.
func (c *Client) getNotebookSourceIDs(ctx context.Context, notebookID string) ([]string, error) {
	params := []any{notebookID, nil, []any{2}, nil, 0}
	raw, err := c.Execute(ctx, RPCGetNotebook, params, NotebookPath(notebookID))
	if err != nil {
		return nil, err
	}

	outer, _ := ParseRawArray(raw)
	var ids []string
	if len(outer) > 0 {
		nbData, _ := ParseRawArray(outer[0])
		if len(nbData) > 1 {
			for _, entry := range ParseSourceEntries(nbData[1]) {
				if id, ok := entry["id"].(string); ok && id != "" {
					ids = append(ids, id)
				}
			}
		}
	}
	return ids, nil
}

// generateUUID creates a UUID v4 using crypto/rand.
func generateUUID() string {
	b := make([]byte, 16)
	crand.Read(b)
	b[6] = (b[6] & 0x0f) | 0x40
	b[8] = (b[8] & 0x3f) | 0x80
	return fmt.Sprintf("%08x-%04x-%04x-%04x-%012x",
		b[0:4], b[4:6], b[6:8], b[8:10], b[10:16])
}
