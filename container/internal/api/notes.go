package api

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"
)

// CreateNote creates a new note in a notebook.
func (c *Client) CreateNote(ctx context.Context, notebookID, title string) (map[string]any, error) {
	params := []any{notebookID, "", []any{1}, nil, title}
	sourcePath := NotebookPath(notebookID)

	raw, err := c.Execute(ctx, RPCSaveMindMap, params, sourcePath) // CYK0Xb
	if err != nil {
		return nil, fmt.Errorf("creating note: %w", err)
	}

	outer, _ := ParseRawArray(raw)
	noteID := ""
	if len(outer) > 0 {
		inner, _ := ParseRawArray(outer[0])
		if len(inner) > 0 {
			noteID = GetString(inner[0])
		}
	}

	return map[string]any{
		"note_id": noteID,
		"title":   title,
	}, nil
}

// ListNotes returns all notes (and mind maps) for a notebook.
func (c *Client) ListNotes(ctx context.Context, notebookID string) ([]map[string]any, error) {
	params := []any{notebookID}
	sourcePath := NotebookPath(notebookID)

	raw, err := c.Execute(ctx, RPCListMindMaps, params, sourcePath) // cFji9
	if err != nil {
		return nil, fmt.Errorf("listing notes: %w", err)
	}

	outer, _ := ParseRawArray(raw)
	var notes []map[string]any

	if len(outer) > 0 {
		items, _ := ParseRawArray(outer[0])
		for _, item := range items {
			note := parseNoteItem(item)
			if note != nil {
				notes = append(notes, note)
			}
		}
	}

	return notes, nil
}

func parseNoteItem(data json.RawMessage) map[string]any {
	arr, err := ParseRawArray(data)
	if err != nil || len(arr) < 2 {
		return nil
	}

	noteID := GetString(arr[0])
	if noteID == "" {
		return nil
	}

	// Check if deleted (status=2 at position 2, or data=null at position 1)
	if len(arr) > 2 && GetInt(arr[2]) == 2 {
		return nil
	}

	var isNull interface{}
	if json.Unmarshal(arr[1], &isNull) == nil && isNull == nil {
		return nil // deleted
	}

	// Parse inner data: [id, content, metadata, null, title]
	inner, err := ParseRawArray(arr[1])
	if err != nil || len(inner) < 2 {
		return nil
	}

	content := GetString(inner[1])
	title := ""
	if len(inner) > 4 {
		title = GetString(inner[4])
	}

	// Distinguish notes from mind maps by content format
	isMindMap := false
	if content != "" {
		content = strings.TrimSpace(content)
		if strings.HasPrefix(content, "{") {
			var parsed map[string]any
			if json.Unmarshal([]byte(content), &parsed) == nil {
				if _, hasChildren := parsed["children"]; hasChildren {
					isMindMap = true
				}
				if _, hasNodes := parsed["nodes"]; hasNodes {
					isMindMap = true
				}
			}
		}
	}

	itemType := "note"
	if isMindMap {
		itemType = "mind_map"
	}

	return map[string]any{
		"note_id": noteID,
		"title":   title,
		"content": content,
		"type":    itemType,
	}
}

// UpdateNote updates a note's content and/or title.
func (c *Client) UpdateNote(ctx context.Context, notebookID, noteID, content, title string) error {
	params := []any{
		notebookID,
		noteID,
		[]any{[]any{[]any{content, title, []any{}, 0}}},
	}
	sourcePath := NotebookPath(notebookID)

	_, err := c.Execute(ctx, RPCUpdateNote, params, sourcePath)
	if err != nil {
		return fmt.Errorf("updating note: %w", err)
	}
	return nil
}

// DeleteNote soft-deletes a note.
func (c *Client) DeleteNote(ctx context.Context, notebookID, noteID string) error {
	params := []any{notebookID, nil, []any{noteID}}
	sourcePath := NotebookPath(notebookID)

	_, err := c.Execute(ctx, RPCDeleteMindMap, params, sourcePath) // AH0mwd
	if err != nil {
		return fmt.Errorf("deleting note: %w", err)
	}
	return nil
}
