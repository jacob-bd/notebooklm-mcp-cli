package api

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"

	"notebooklm-mcp/internal/constants"
)

// --- Source Add operations ---

// AddURLSource adds a website or YouTube URL as a source.
func (c *Client) AddURLSource(ctx context.Context, notebookID, url string) (map[string]any, error) {
	isYouTube := strings.Contains(strings.ToLower(url), "youtube.com") ||
		strings.Contains(strings.ToLower(url), "youtu.be")

	var sourceData []any
	if isYouTube {
		// YouTube: URL at position 7
		sourceData = []any{nil, nil, nil, nil, nil, nil, nil, []any{url}, nil, nil, 1}
	} else {
		// Regular website: URL at position 2
		sourceData = []any{nil, nil, []any{url}, nil, nil, nil, nil, nil, nil, nil, 1}
	}

	settings := []any{1, nil, nil, nil, nil, nil, nil, nil, nil, nil, []any{1}}
	params := []any{[]any{sourceData}, notebookID, []any{2}, settings}
	sourcePath := NotebookPath(notebookID)

	raw, err := c.Execute(ctx, RPCAddSource, params, sourcePath)
	if err != nil {
		return nil, fmt.Errorf("adding URL source: %w", err)
	}
	return parseAddSourceResult(raw)
}

// AddTextSource adds pasted text as a source.
func (c *Client) AddTextSource(ctx context.Context, notebookID, text, title string) (map[string]any, error) {
	if title == "" {
		title = "Pasted Text"
	}

	sourceData := []any{nil, []any{title, text}, nil, 2, nil, nil, nil, nil, nil, nil, 1}
	settings := []any{1, nil, nil, nil, nil, nil, nil, nil, nil, nil, []any{1}}
	params := []any{[]any{sourceData}, notebookID, []any{2}, settings}
	sourcePath := NotebookPath(notebookID)

	raw, err := c.Execute(ctx, RPCAddSource, params, sourcePath)
	if err != nil {
		return nil, fmt.Errorf("adding text source: %w", err)
	}
	return parseAddSourceResult(raw)
}

// AddDriveSource adds a Google Drive document as a source.
func (c *Client) AddDriveSource(ctx context.Context, notebookID, documentID, title, docType string) (map[string]any, error) {
	mimeTypes := map[string]string{
		"doc":    "application/vnd.google-apps.document",
		"slides": "application/vnd.google-apps.presentation",
		"sheets": "application/vnd.google-apps.spreadsheet",
		"pdf":    "application/pdf",
	}
	mimeType := mimeTypes[docType]
	if mimeType == "" {
		mimeType = mimeTypes["doc"]
	}

	sourceData := []any{
		[]any{documentID, mimeType, 1, title},
		nil, nil, nil, nil, nil, nil, nil, nil, nil, 1,
	}
	settings := []any{1, nil, nil, nil, nil, nil, nil, nil, nil, nil, []any{1}}
	params := []any{[]any{sourceData}, notebookID, []any{2}, settings}
	sourcePath := NotebookPath(notebookID)

	raw, err := c.Execute(ctx, RPCAddSource, params, sourcePath)
	if err != nil {
		return nil, fmt.Errorf("adding drive source: %w", err)
	}
	return parseAddSourceResult(raw)
}

func parseAddSourceResult(raw json.RawMessage) (map[string]any, error) {
	outer, err := ParseRawArray(raw)
	if err != nil {
		return nil, fmt.Errorf("parsing add source response: %w", err)
	}
	// Response: [[source_data]] where source_data = [[id], title, ...]
	if len(outer) > 0 {
		list, _ := ParseRawArray(outer[0])
		if len(list) > 0 {
			entry, _ := ParseRawArray(list[0])
			if len(entry) >= 2 {
				idArr, _ := ParseRawArray(entry[0])
				id := ""
				if len(idArr) > 0 {
					id = GetString(idArr[0])
				}
				return map[string]any{
					"id":    id,
					"title": GetString(entry[1]),
				}, nil
			}
		}
	}
	return map[string]any{"status": "added"}, nil
}

// --- Source Delete ---

// DeleteSource permanently deletes a source.
func (c *Client) DeleteSource(ctx context.Context, sourceID string) error {
	params := []any{[]any{[]any{sourceID}}, []any{2}}
	_, err := c.Execute(ctx, RPCDeleteSource, params, "")
	if err != nil {
		return fmt.Errorf("deleting source: %w", err)
	}
	return nil
}

// --- Source Freshness & Sync ---

// SyncDriveSource syncs a Drive source with the latest content.
func (c *Client) SyncDriveSource(ctx context.Context, sourceID string) (map[string]any, error) {
	params := []any{nil, []any{sourceID}, []any{2}}
	raw, err := c.Execute(ctx, RPCSyncSource, params, "")
	if err != nil {
		return nil, fmt.Errorf("syncing source: %w", err)
	}

	outer, _ := ParseRawArray(raw)
	if len(outer) > 0 {
		entry, _ := ParseRawArray(outer[0])
		if len(entry) >= 2 {
			idArr, _ := ParseRawArray(entry[0])
			id := ""
			if len(idArr) > 0 {
				id = GetString(idArr[0])
			}
			return map[string]any{
				"id":    id,
				"title": GetString(entry[1]),
			}, nil
		}
	}
	return map[string]any{"id": sourceID, "status": "synced"}, nil
}

// --- Source Content & Guide ---

// GetSourceGuide returns an AI-generated summary and keywords for a source.
func (c *Client) GetSourceGuide(ctx context.Context, sourceID string) (map[string]any, error) {
	params := []any{[]any{[]any{[]any{sourceID}}}}
	raw, err := c.Execute(ctx, RPCSourceGuide, params, "/")
	if err != nil {
		return nil, fmt.Errorf("getting source guide: %w", err)
	}

	summary := ""
	var keywords []string

	outer, _ := ParseRawArray(raw)
	if len(outer) > 0 {
		l1, _ := ParseRawArray(outer[0])
		if len(l1) > 0 {
			l2, _ := ParseRawArray(l1[0])
			// Summary at [1][0]
			if len(l2) > 1 {
				sumArr, _ := ParseRawArray(l2[1])
				if len(sumArr) > 0 {
					summary = GetString(sumArr[0])
				}
			}
			// Keywords at [2][0]
			if len(l2) > 2 {
				kwOuter, _ := ParseRawArray(l2[2])
				if len(kwOuter) > 0 {
					kwArr, _ := ParseRawArray(kwOuter[0])
					for _, kw := range kwArr {
						if s := GetString(kw); s != "" {
							keywords = append(keywords, s)
						}
					}
				}
			}
		}
	}

	return map[string]any{
		"summary":  summary,
		"keywords": keywords,
	}, nil
}

// GetSourceContent returns the raw text content of a source.
func (c *Client) GetSourceContent(ctx context.Context, sourceID string) (map[string]any, error) {
	params := []any{[]any{sourceID}, []any{2}, []any{2}}
	raw, err := c.Execute(ctx, RPCGetSource, params, "/")
	if err != nil {
		return nil, fmt.Errorf("getting source content: %w", err)
	}

	title := ""
	sourceType := ""
	content := ""
	var sourceURL *string

	outer, _ := ParseRawArray(raw)

	// Extract metadata from outer[0]
	if len(outer) > 0 {
		meta, _ := ParseRawArray(outer[0])
		if len(meta) > 1 {
			title = GetString(meta[1])
		}
		if len(meta) > 2 {
			metaArr, _ := ParseRawArray(meta[2])
			if len(metaArr) > 4 {
				sourceType = sourceTypeName(GetInt(metaArr[4]))
			}
			if len(metaArr) > 7 {
				urlInfo, _ := ParseRawArray(metaArr[7])
				if len(urlInfo) > 0 {
					u := GetString(urlInfo[0])
					if u != "" {
						sourceURL = &u
					}
				}
			}
		}
	}

	// Extract content from outer[3][0] — array of content blocks
	if len(outer) > 3 {
		wrapper, _ := ParseRawArray(outer[3])
		if len(wrapper) > 0 {
			blocks, _ := ParseRawArray(wrapper[0])
			var parts []string
			for _, block := range blocks {
				parts = append(parts, extractAllText(block)...)
			}
			content = strings.Join(parts, "\n\n")
		}
	}

	result := map[string]any{
		"content":     content,
		"title":       title,
		"source_type": sourceType,
		"char_count":  len(content),
	}
	if sourceURL != nil {
		result["url"] = *sourceURL
	}
	return result, nil
}

// GetNotebookSourcesWithTypes returns sources with type info for source_list_drive.
func (c *Client) GetNotebookSourcesWithTypes(ctx context.Context, notebookID string) ([]map[string]any, error) {
	params := []any{notebookID, nil, []any{2}, nil, 0}
	sourcePath := NotebookPath(notebookID)

	raw, err := c.Execute(ctx, RPCGetNotebook, params, sourcePath)
	if err != nil {
		return nil, fmt.Errorf("getting notebook for sources: %w", err)
	}

	outer, _ := ParseRawArray(raw)
	var sources []map[string]any

	// Sources are at outer[0][1] in the notebook response
	if len(outer) > 0 {
		nbData, _ := ParseRawArray(outer[0])
		if len(nbData) > 1 {
			entries := ParseSourceEntries(nbData[1])
			for _, entry := range entries {
				src := enrichSourceWithType(entry)
				sources = append(sources, src)
			}
		}
	}

	return sources, nil
}

// enrichSourceWithType adds type metadata from the raw array carried by ParseSourceEntries.
func enrichSourceWithType(entry map[string]any) map[string]any {
	result := map[string]any{
		"id":    entry["id"],
		"title": entry["title"],
	}

	rawArr, ok := entry["_raw"].([]json.RawMessage)
	if !ok || len(rawArr) < 3 {
		result["source_type"] = 0
		result["source_type_name"] = "unknown_0"
		result["can_sync"] = false
		return result
	}

	metadata, _ := ParseRawArray(rawArr[2])
	sourceType := 0
	canSync := false

	if len(metadata) > 4 {
		sourceType = GetInt(metadata[4])
	}
	if len(metadata) > 0 {
		driveInfo, _ := ParseRawArray(metadata[0])
		if len(driveInfo) > 0 {
			d := GetString(driveInfo[0])
			if d != "" {
				result["drive_doc_id"] = d
				if sourceType == 1 || sourceType == 2 {
					canSync = true
				}
			}
		}
	}

	result["source_type"] = sourceType
	result["source_type_name"] = sourceTypeName(sourceType)
	result["can_sync"] = canSync
	return result
}

func sourceTypeName(code int) string {
	if name, ok := constants.SourceTypes.Name(code); ok {
		return name
	}
	return fmt.Sprintf("unknown_%d", code)
}

// extractAllText recursively extracts all text strings from nested JSON arrays.
func extractAllText(data json.RawMessage) []string {
	var s string
	if json.Unmarshal(data, &s) == nil && s != "" {
		return []string{s}
	}

	arr, err := ParseRawArray(data)
	if err != nil {
		return nil
	}

	var texts []string
	for _, item := range arr {
		texts = append(texts, extractAllText(item)...)
	}
	return texts
}
