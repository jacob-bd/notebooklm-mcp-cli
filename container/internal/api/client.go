package api

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log/slog"
	"net/http"
	"net/url"
	"strings"
	"sync/atomic"
	"time"

	"notebooklm-mcp/internal/auth"
)

// Client is the HTTP client for the NotebookLM batchexecute API.
type Client struct {
	auth       *auth.Store
	httpClient *http.Client
	buildLabel string
	reqID      atomic.Int64
}

// NewClient creates a Client backed by the given auth store.
func NewClient(authStore *auth.Store, buildLabel string) *Client {
	if buildLabel == "" {
		buildLabel = DefaultBuildLabel
	}
	return &Client{
		auth:       authStore,
		httpClient: &http.Client{Timeout: 120 * time.Second},
		buildLabel: buildLabel,
	}
}

// Execute sends an RPC request via the batchexecute endpoint and returns
// the parsed response payload for the given RPC ID.
//
// The params value is marshalled to JSON, then placed as a string inside
// the f.req envelope (double-encoded). sourcePath is the page context
// (e.g. "/notebook/<id>") and can be empty for global operations.
func (c *Client) Execute(ctx context.Context, rpcID string, params any, sourcePath string) (json.RawMessage, error) {
	if err := c.auth.EnsureTokens(ctx); err != nil {
		return nil, err
	}

	// Marshal params to JSON string (this becomes double-encoded in f.req)
	paramsJSON, err := json.Marshal(params)
	if err != nil {
		return nil, fmt.Errorf("marshaling RPC params: %w", err)
	}

	// Build the f.req envelope:
	// [[["RPC_ID", "<params_json_string>", null, "generic"]]]
	fReqInner := []any{rpcID, string(paramsJSON), nil, "generic"}
	fReqOuter := []any{[]any{fReqInner}}
	fReqJSON, err := json.Marshal(fReqOuter)
	if err != nil {
		return nil, fmt.Errorf("marshaling f.req: %w", err)
	}

	// Form body
	form := url.Values{
		"f.req": {string(fReqJSON)},
		"at":    {c.auth.CSRFToken()},
	}

	// URL query parameters
	query := url.Values{
		"rpcids": {rpcID},
		"bl":     {c.buildLabel},
		"hl":     {"en"},
		"rt":     {"c"},
	}
	if sourcePath != "" {
		query.Set("source-path", sourcePath)
	}
	if sid := c.auth.SessionID(); sid != "" {
		query.Set("f.sid", sid)
	}
	reqID := c.reqID.Add(100000)
	query.Set("_reqid", fmt.Sprintf("%d", reqID))

	fullURL := BaseURL + BatchExecutePath + "?" + query.Encode()

	// Build HTTP request
	req, err := http.NewRequestWithContext(ctx, "POST", fullURL, strings.NewReader(form.Encode()))
	if err != nil {
		return nil, fmt.Errorf("creating HTTP request: %w", err)
	}
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded;charset=UTF-8")
	req.Header.Set("Cookie", c.auth.Cookies())
	req.Header.Set("Origin", BaseURL)
	req.Header.Set("Referer", BaseURL+"/")
	req.Header.Set("X-Same-Domain", "1")

	slog.Debug("executing RPC", "rpc_id", rpcID, "source_path", sourcePath)

	// Send request
	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("HTTP request failed: %w", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("reading response body: %w", err)
	}

	// Handle auth errors with automatic token refresh
	if resp.StatusCode == http.StatusUnauthorized || resp.StatusCode == http.StatusForbidden {
		slog.Warn("auth error from API, attempting token refresh", "status", resp.StatusCode)
		if refreshErr := c.auth.RefreshTokens(ctx); refreshErr != nil {
			return nil, fmt.Errorf("API returned %d and token refresh failed: %w", resp.StatusCode, refreshErr)
		}
		return nil, fmt.Errorf("API returned %d — tokens refreshed, please retry the operation", resp.StatusCode)
	}

	if resp.StatusCode != http.StatusOK {
		preview := string(body)
		if len(preview) > 500 {
			preview = preview[:500] + "..."
		}
		return nil, fmt.Errorf("API returned HTTP %d: %s", resp.StatusCode, preview)
	}

	// Parse the batchexecute response to extract our RPC's payload
	return ParseBatchResponse(body, rpcID)
}
