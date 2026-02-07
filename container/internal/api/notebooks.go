package api

import (
	"context"
	"encoding/json"
	"fmt"
)

// Notebook represents a NotebookLM notebook.
type Notebook struct {
	ID    string `json:"id"`
	Title string `json:"title"`
}

// ListNotebooks returns all notebooks for the authenticated user.
func (c *Client) ListNotebooks(ctx context.Context, maxResults int) ([]Notebook, error) {
	// RPC params: [null, 1, null, [2]]
	params := []any{nil, 1, nil, []any{2}}

	raw, err := c.Execute(ctx, RPCListNotebooks, params, "")
	if err != nil {
		return nil, fmt.Errorf("listing notebooks: %w", err)
	}

	nbs, err := parseNotebookList(raw)
	if err != nil {
		return nil, err
	}
	if maxResults > 0 && len(nbs) > maxResults {
		nbs = nbs[:maxResults]
	}
	return nbs, nil
}

// GetNotebook returns notebook details including sources.
func (c *Client) GetNotebook(ctx context.Context, notebookID string) (map[string]any, error) {
	// RPC params: [notebook_id, null, [2], null, 0]
	params := []any{notebookID, nil, []any{2}, nil, 0}
	sourcePath := NotebookPath(notebookID)

	raw, err := c.Execute(ctx, RPCGetNotebook, params, sourcePath)
	if err != nil {
		return nil, fmt.Errorf("getting notebook: %w", err)
	}

	return parseNotebookDetails(raw, notebookID)
}

// CreateNotebook creates a new notebook with the given title.
func (c *Client) CreateNotebook(ctx context.Context, title string) (map[string]any, error) {
	// RPC params: [title, null, null, [2], [1,null,null,null,null,null,null,null,null,null,[1]]]
	settings := []any{1, nil, nil, nil, nil, nil, nil, nil, nil, nil, []any{1}}
	params := []any{title, nil, nil, []any{2}, settings}

	raw, err := c.Execute(ctx, RPCCreateNotebook, params, "")
	if err != nil {
		return nil, fmt.Errorf("creating notebook: %w", err)
	}

	// Parse response to extract notebook ID
	arr, err := ParseRawArray(raw)
	if err != nil {
		return nil, fmt.Errorf("parsing create response: %w", err)
	}

	result := map[string]any{
		"title": title,
	}

	// The notebook ID is typically at position 2 in the response array
	if len(arr) > 2 {
		result["id"] = GetString(arr[2])
	}
	if len(arr) > 4 {
		result["title"] = GetString(arr[4])
	}

	return result, nil
}

// DeleteNotebook permanently deletes a notebook.
func (c *Client) DeleteNotebook(ctx context.Context, notebookID string) error {
	// RPC params: [[notebook_id], [2]]
	params := []any{[]any{notebookID}, []any{2}}

	_, err := c.Execute(ctx, RPCDeleteNotebook, params, "")
	if err != nil {
		return fmt.Errorf("deleting notebook: %w", err)
	}
	return nil
}

// RenameNotebook changes a notebook's title.
func (c *Client) RenameNotebook(ctx context.Context, notebookID, newTitle string) error {
	// RPC params: [notebook_id, [[null, null, null, [null, "New Title"]]]]
	params := []any{notebookID, []any{[]any{nil, nil, nil, []any{nil, newTitle}}}}
	sourcePath := NotebookPath(notebookID)

	_, err := c.Execute(ctx, RPCUpdateNotebook, params, sourcePath)
	if err != nil {
		return fmt.Errorf("renaming notebook: %w", err)
	}
	return nil
}

// parseNotebookList extracts notebooks from the list response.
func parseNotebookList(raw json.RawMessage) ([]Notebook, error) {
	// Response structure: [null, [[notebook_data], [notebook_data], ...], ...]
	// or possibly: [[null, [[notebook_data], ...]], ...]
	outer, err := ParseRawArray(raw)
	if err != nil {
		return nil, fmt.Errorf("parsing notebook list outer: %w", err)
	}

	var notebooks []Notebook

	// Navigate the nested structure to find the array of notebook entries.
	// The exact nesting can vary; we look for arrays containing notebook data.
	entries := findNotebookEntries(outer)
	for _, entry := range entries {
		nb := parseOneNotebook(entry)
		if nb.ID != "" {
			notebooks = append(notebooks, nb)
		}
	}

	return notebooks, nil
}

// findNotebookEntries locates the array of notebook entries in the response.
func findNotebookEntries(outer []json.RawMessage) []json.RawMessage {
	// Response: [[nb1, nb2, ...], ...] — entries are at outer[0]
	if len(outer) > 0 {
		arr, err := ParseRawArray(outer[0])
		if err == nil && len(arr) > 0 {
			return arr
		}
	}
	return nil
}

// parseOneNotebook extracts a Notebook from a single entry in the list.
// Entry structure: [title, [sources], notebook_id, emoji, null, [metadata]]
func parseOneNotebook(data json.RawMessage) Notebook {
	arr, err := ParseRawArray(data)
	if err != nil || len(arr) < 3 {
		return Notebook{}
	}

	return Notebook{
		Title: GetString(arr[0]), // position 0 = title
		ID:    GetString(arr[2]), // position 2 = notebook UUID
	}
}

// parseNotebookDetails parses the full notebook response including sources.
func parseNotebookDetails(raw json.RawMessage, notebookID string) (map[string]any, error) {
	outer, err := ParseRawArray(raw)
	if err != nil {
		return nil, fmt.Errorf("parsing notebook details: %w", err)
	}

	result := map[string]any{
		"id": notebookID,
	}

	// Response structure: [[title, [sources...], ...], ...]
	if len(outer) > 0 {
		nbData, err := ParseRawArray(outer[0])
		if err == nil {
			if len(nbData) > 0 {
				result["title"] = GetString(nbData[0])
			}
			if len(nbData) > 1 {
				entries := ParseSourceEntries(nbData[1])
				// Strip internal _raw field before returning to clients
				for _, e := range entries {
					delete(e, "_raw")
				}
				result["sources"] = entries
			}
		}
	}
	if _, ok := result["sources"]; !ok {
		result["sources"] = []map[string]any{}
	}

	return result, nil
}

// ParseSourceEntries extracts source ID/title pairs from a notebook response
// sources array. Shared by GetNotebook, GetNotebookSourcesWithTypes, and
// getNotebookSourceIDs to avoid duplicating the nested array traversal.
func ParseSourceEntries(data json.RawMessage) []map[string]any {
	srcArr, err := ParseRawArray(data)
	if err != nil {
		return nil
	}
	var sources []map[string]any
	for _, s := range srcArr {
		arr, err := ParseRawArray(s)
		if err != nil || len(arr) < 2 {
			continue
		}
		idArr, _ := ParseRawArray(arr[0])
		if len(idArr) == 0 {
			continue
		}
		id := GetString(idArr[0])
		if id == "" {
			continue
		}
		sources = append(sources, map[string]any{
			"id":    id,
			"title": GetString(arr[1]),
			"_raw":  arr, // carry raw for callers needing metadata
		})
	}
	return sources
}
