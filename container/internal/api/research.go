package api

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"
)

// StartResearch initiates a research session (web or drive search).
func (c *Client) StartResearch(ctx context.Context, notebookID, query, source, mode string) (map[string]any, error) {
	sourceType := 1 // web
	if strings.ToLower(source) == "drive" {
		sourceType = 2
	}

	var rpcID string
	var params []any

	if strings.ToLower(mode) == "deep" {
		if sourceType == 2 {
			return nil, fmt.Errorf("deep research only supports web sources, not drive")
		}
		rpcID = RPCStartDeepResearch
		params = []any{nil, []any{1}, []any{query, sourceType}, 5, notebookID}
	} else {
		rpcID = RPCStartFastResearch
		params = []any{[]any{query, sourceType}, nil, 1, notebookID}
	}

	sourcePath := NotebookPath(notebookID)
	raw, err := c.Execute(ctx, rpcID, params, sourcePath)
	if err != nil {
		return nil, fmt.Errorf("starting research: %w", err)
	}

	outer, _ := ParseRawArray(raw)
	taskID := ""
	if len(outer) > 0 {
		taskID = GetString(outer[0])
	}

	return map[string]any{
		"task_id":     taskID,
		"notebook_id": notebookID,
		"query":       query,
		"source":      strings.ToLower(source),
		"mode":        strings.ToLower(mode),
	}, nil
}

// PollResearch polls for research results.
func (c *Client) PollResearch(ctx context.Context, notebookID string, targetTaskID string) (map[string]any, error) {
	params := []any{nil, nil, notebookID}
	sourcePath := NotebookPath(notebookID)

	raw, err := c.Execute(ctx, RPCPollResearch, params, sourcePath)
	if err != nil {
		return nil, fmt.Errorf("polling research: %w", err)
	}

	outer, _ := ParseRawArray(raw)
	if len(outer) == 0 {
		return map[string]any{"status": "no_research", "message": "No active research found"}, nil
	}

	// Unwrap to find research tasks
	tasks := unwrapResearchTasks(outer)
	if len(tasks) == 0 {
		return map[string]any{"status": "no_research"}, nil
	}

	// Find target task or return first
	for _, task := range tasks {
		if targetTaskID == "" || task["task_id"] == targetTaskID {
			return task, nil
		}
	}

	return tasks[0], nil
}

func unwrapResearchTasks(outer []json.RawMessage) []map[string]any {
	// Try to unwrap nested arrays to find task data
	data := outer
	if len(data) > 0 {
		inner, err := ParseRawArray(data[0])
		if err == nil && len(inner) > 0 {
			// Check if this is a further nested array
			test, err2 := ParseRawArray(inner[0])
			if err2 == nil && len(test) > 0 {
				data = inner
			}
		}
	}

	var tasks []map[string]any
	for _, item := range data {
		arr, err := ParseRawArray(item)
		if err != nil || len(arr) < 2 {
			continue
		}

		taskID := GetString(arr[0])
		if taskID == "" {
			continue
		}

		taskInfo, err := ParseRawArray(arr[1])
		if err != nil || len(taskInfo) == 0 {
			continue
		}

		queryText := ""
		sourceType := "web"
		researchMode := "fast"
		var sources []map[string]any
		summary := ""
		status := "in_progress"

		// Parse query info at taskInfo[1]
		if len(taskInfo) > 1 {
			qi, _ := ParseRawArray(taskInfo[1])
			if len(qi) > 0 {
				queryText = GetString(qi[0])
			}
			if len(qi) > 1 && GetInt(qi[1]) == 2 {
				sourceType = "drive"
			}
		}
		// Research mode at taskInfo[2]
		if len(taskInfo) > 2 && GetInt(taskInfo[2]) == 5 {
			researchMode = "deep"
		}
		// Sources and summary at taskInfo[3]
		if len(taskInfo) > 3 {
			sa, _ := ParseRawArray(taskInfo[3])
			if len(sa) > 0 {
				srcArr, _ := ParseRawArray(sa[0])
				sources = parseResearchSources(srcArr)
			}
			if len(sa) > 1 {
				summary = GetString(sa[1])
			}
		}
		// Status at taskInfo[4]: 1=in_progress, 2=completed, 6=imported
		if len(taskInfo) > 4 {
			code := GetInt(taskInfo[4])
			if code == 2 || code == 6 {
				status = "completed"
			}
		}

		tasks = append(tasks, map[string]any{
			"task_id":      taskID,
			"status":       status,
			"query":        queryText,
			"source_type":  sourceType,
			"mode":         researchMode,
			"sources":      sources,
			"source_count": len(sources),
			"summary":      summary,
		})
	}
	return tasks
}

func parseResearchSources(data []json.RawMessage) []map[string]any {
	var sources []map[string]any
	for idx, item := range data {
		arr, err := ParseRawArray(item)
		if err != nil || len(arr) < 2 {
			continue
		}

		url := GetString(arr[0])
		title := ""
		desc := ""
		resultType := 1

		if len(arr) > 1 {
			title = GetString(arr[1])
		}
		if len(arr) > 2 {
			desc = GetString(arr[2])
		}
		if len(arr) > 3 {
			resultType = GetInt(arr[3])
		}

		sources = append(sources, map[string]any{
			"index":       idx,
			"url":         url,
			"title":       title,
			"description": desc,
			"result_type": resultType,
		})
	}
	return sources
}

// ImportResearchSources imports selected sources from research into the notebook.
func (c *Client) ImportResearchSources(ctx context.Context, notebookID, taskID string, sources []map[string]any) ([]map[string]any, error) {
	if len(sources) == 0 {
		return nil, fmt.Errorf("no sources to import")
	}

	var sourceArray []any
	for _, src := range sources {
		url, _ := src["url"].(string)
		title, _ := src["title"].(string)
		resultType := 1
		if rt, ok := src["result_type"].(float64); ok {
			resultType = int(rt)
		} else if rt, ok := src["result_type"].(int); ok {
			resultType = rt
		}

		if resultType == 5 || url == "" {
			continue // skip reports and empty URLs
		}

		if resultType == 1 {
			// Web source
			sourceArray = append(sourceArray,
				[]any{nil, nil, []any{url, title}, nil, nil, nil, nil, nil, nil, nil, 2})
		} else {
			// Drive source — extract doc ID from URL
			docID := extractDocID(url)
			if docID != "" {
				mimeType := "application/vnd.google-apps.document"
				sourceArray = append(sourceArray,
					[]any{[]any{docID, mimeType, 1, title}, nil, nil, nil, nil, nil, nil, nil, nil, nil, 2})
			} else {
				sourceArray = append(sourceArray,
					[]any{nil, nil, []any{url, title}, nil, nil, nil, nil, nil, nil, nil, 2})
			}
		}
	}

	params := []any{nil, []any{1}, taskID, notebookID, sourceArray}
	sourcePath := NotebookPath(notebookID)

	raw, err := c.Execute(ctx, RPCImportSources, params, sourcePath)
	if err != nil {
		return nil, fmt.Errorf("importing sources: %w", err)
	}

	outer, _ := ParseRawArray(raw)
	var imported []map[string]any

	// Unwrap: response is [[source1, source2, ...]]
	resultArr := outer
	if len(outer) > 0 {
		inner, err := ParseRawArray(outer[0])
		if err == nil && len(inner) > 0 {
			test, _ := ParseRawArray(inner[0])
			if len(test) > 0 {
				resultArr = inner
			}
		}
	}

	for _, item := range resultArr {
		arr, err := ParseRawArray(item)
		if err != nil || len(arr) < 2 {
			continue
		}
		idArr, _ := ParseRawArray(arr[0])
		if len(idArr) > 0 {
			id := GetString(idArr[0])
			if id != "" {
				imported = append(imported, map[string]any{
					"id":    id,
					"title": GetString(arr[1]),
				})
			}
		}
	}

	return imported, nil
}

func extractDocID(url string) string {
	if idx := strings.Index(url, "id="); idx >= 0 {
		rest := url[idx+3:]
		if amp := strings.Index(rest, "&"); amp >= 0 {
			return rest[:amp]
		}
		return rest
	}
	return ""
}
