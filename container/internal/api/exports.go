package api

import (
	"context"
	"fmt"
)

// ExportArtifact exports a studio artifact to Google Docs or Sheets.
func (c *Client) ExportArtifact(ctx context.Context, notebookID, artifactID, title, exportType string) (map[string]any, error) {
	exportTypeCode := 1 // docs
	if exportType == "sheets" {
		exportTypeCode = 2
	}

	params := []any{nil, artifactID, nil, title, exportTypeCode}
	sourcePath := NotebookPath(notebookID)

	raw, err := c.Execute(ctx, RPCExport, params, sourcePath)
	if err != nil {
		return nil, fmt.Errorf("exporting artifact: %w", err)
	}

	// Try to extract URL from response
	docURL := ""
	outer, _ := ParseRawArray(raw)

	// Try multiple patterns: [[[url]]], [[url]], [url]
	if len(outer) > 0 {
		l1, _ := ParseRawArray(outer[0])
		if len(l1) > 0 {
			l2, _ := ParseRawArray(l1[0])
			if len(l2) > 0 {
				docURL = GetString(l2[0])
			}
			if docURL == "" {
				docURL = GetString(l1[0])
			}
		}
		if docURL == "" {
			docURL = GetString(outer[0])
		}
	}

	if docURL != "" {
		label := "Google Docs"
		if exportType == "sheets" {
			label = "Google Sheets"
		}
		return map[string]any{
			"status":  "success",
			"url":     docURL,
			"message": fmt.Sprintf("Exported to %s: %s", label, docURL),
		}, nil
	}

	return map[string]any{
		"status":  "failed",
		"message": "Export failed — no document URL returned",
	}, nil
}
