package api

import (
	"encoding/json"
	"fmt"
	"strings"
)

// ParseBatchResponse extracts the response payload for a given RPC ID
// from a NotebookLM batchexecute response body.
//
// The response format is:
//
//	)]}'                          ← anti-XSSI prefix (must strip)
//	<byte_count>
//	[["wrb.fr","RPCID","<json_payload_string>",null,...]]
//	<byte_count>
//	[["di",<number>]]
//	...
//
// The payload at index 2 of the "wrb.fr" entry is a JSON string that
// must be parsed again (double-encoded).
func ParseBatchResponse(body []byte, rpcID string) (json.RawMessage, error) {
	text := string(body)

	// Strip anti-XSSI prefix: )]}' followed by optional whitespace/newline
	if idx := strings.Index(text, "\n"); idx >= 0 && idx < 10 {
		text = text[idx+1:]
	}

	if strings.TrimSpace(text) == "" {
		return nil, fmt.Errorf("empty response body for RPC %s", rpcID)
	}

	// Check if response is HTML (auth failure)
	trimmed := strings.TrimSpace(text)
	if strings.HasPrefix(trimmed, "<!") || strings.HasPrefix(trimmed, "<html") {
		return nil, fmt.Errorf("received HTML instead of API response — cookies may be expired")
	}

	// Scan lines looking for JSON arrays containing our RPC data
	for _, line := range strings.Split(text, "\n") {
		line = strings.TrimSpace(line)
		if line == "" || line[0] != '[' {
			continue // skip byte-count lines and empty lines
		}

		payload, found := extractRPCPayload([]byte(line), rpcID)
		if found {
			return payload, nil
		}
	}

	return nil, fmt.Errorf("no response found for RPC %s in batch response", rpcID)
}

// extractRPCPayload looks for a "wrb.fr" entry matching rpcID in a JSON line.
// Returns the decoded payload and true if found.
func extractRPCPayload(line []byte, rpcID string) (json.RawMessage, bool) {
	// Parse the line as an array of arrays
	var outer []json.RawMessage
	if err := json.Unmarshal(line, &outer); err != nil {
		return nil, false
	}

	for _, item := range outer {
		var inner []json.RawMessage
		if err := json.Unmarshal(item, &inner); err != nil {
			continue
		}
		if len(inner) < 3 {
			continue
		}

		// Check for ["wrb.fr", "<rpcID>", "<payload>", ...]
		var marker, id string
		if err := json.Unmarshal(inner[0], &marker); err != nil || marker != "wrb.fr" {
			continue
		}
		if err := json.Unmarshal(inner[1], &id); err != nil || id != rpcID {
			continue
		}

		// inner[2] is the payload — a JSON string containing the actual data
		var payloadStr string
		if err := json.Unmarshal(inner[2], &payloadStr); err != nil {
			// Might be null for RPCs that return null on success
			var isNull interface{}
			if json.Unmarshal(inner[2], &isNull) == nil && isNull == nil {
				return json.RawMessage("null"), true
			}
			continue
		}

		return json.RawMessage(payloadStr), true
	}

	return nil, false
}

// ParseRawArray is a helper to unmarshal a JSON array where elements
// can be of any type. Useful for navigating the deeply nested response
// structures returned by the NotebookLM API.
func ParseRawArray(data json.RawMessage) ([]json.RawMessage, error) {
	var arr []json.RawMessage
	if err := json.Unmarshal(data, &arr); err != nil {
		return nil, fmt.Errorf("parsing as array: %w", err)
	}
	return arr, nil
}

// GetString extracts a string from a json.RawMessage, returning "" if null or not a string.
func GetString(data json.RawMessage) string {
	var s string
	if json.Unmarshal(data, &s) == nil {
		return s
	}
	return ""
}

// GetInt extracts an int from a json.RawMessage, returning 0 if null or not a number.
func GetInt(data json.RawMessage) int {
	var n int
	if json.Unmarshal(data, &n) == nil {
		return n
	}
	return 0
}
