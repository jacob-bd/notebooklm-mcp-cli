package api

import (
	"context"
	"fmt"
)

// NotebookDescribe returns an AI-generated summary and suggested topics.
func (c *Client) NotebookDescribe(ctx context.Context, notebookID string) (map[string]any, error) {
	params := []any{notebookID, []any{2}}
	sourcePath := NotebookPath(notebookID)

	raw, err := c.Execute(ctx, RPCNotebookSummary, params, sourcePath)
	if err != nil {
		return nil, fmt.Errorf("getting notebook description: %w", err)
	}

	summary := ""
	var suggestedTopics []string

	outer, _ := ParseRawArray(raw)

	// Response structure: [[[summary_text], ...], [[topic1_arr], [topic2_arr], ...]]
	if len(outer) > 0 {
		level1, _ := ParseRawArray(outer[0])
		if len(level1) > 0 {
			// Summary may be directly a string or nested one more level
			s := GetString(level1[0])
			if s != "" {
				summary = s
			} else {
				// Try one deeper: level1[0] is an array containing the string
				level2, _ := ParseRawArray(level1[0])
				if len(level2) > 0 {
					summary = GetString(level2[0])
				}
			}
		}
	}

	// Suggested topics at outer[1]
	if len(outer) > 1 {
		topicsOuter, _ := ParseRawArray(outer[1])
		for _, t := range topicsOuter {
			tArr, _ := ParseRawArray(t)
			if len(tArr) > 0 {
				topic := GetString(tArr[0])
				if topic != "" {
					suggestedTopics = append(suggestedTopics, topic)
				}
			}
		}
	}

	return map[string]any{
		"summary":          summary,
		"suggested_topics": suggestedTopics,
	}, nil
}
