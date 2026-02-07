package api

import (
	"context"
	"encoding/json"
	"fmt"

	"notebooklm-mcp/internal/constants"
)

// CreateStudioContent creates audio, video, report, or other studio artifacts.
func (c *Client) CreateStudioContent(ctx context.Context, notebookID string, opts StudioOptions) (map[string]any, error) {
	// Build source IDs arrays
	nestedSources := make([]any, len(opts.SourceIDs))
	simpleSources := make([]any, len(opts.SourceIDs))
	for i, sid := range opts.SourceIDs {
		nestedSources[i] = []any{[]any{sid}}
		simpleSources[i] = []any{sid}
	}

	var content []any

	switch opts.TypeCode {
	case 1: // Audio
		content = []any{
			nil, nil, 1, nestedSources, nil, nil,
			[]any{nil, []any{
				opts.FocusPrompt, opts.LengthCode, nil,
				simpleSources, opts.Language, nil, opts.FormatCode,
			}},
		}
	case 3: // Video
		content = []any{
			nil, nil, 3, nestedSources, nil, nil, nil, nil,
			[]any{nil, nil, []any{
				simpleSources, opts.Language, opts.FocusPrompt,
				nil, opts.FormatCode, opts.StyleCode,
			}},
		}
	case 2: // Report
		content = []any{
			nil, nil, 2, nestedSources, nil, nil, nil,
			[]any{nil, []any{
				opts.ReportTitle, opts.ReportDesc, nil,
				simpleSources, opts.Language, opts.ReportPrompt, nil, true,
			}},
		}
	case 7: // Infographic
		pad := make([]any, 10) // 10 nils for positions 4-13
		content = append([]any{nil, nil, 7, nestedSources}, pad...)
		content = append(content, []any{[]any{
			opts.FocusPrompt, opts.Language, nil,
			opts.OrientationCode, opts.DetailCode,
		}})
	case 8: // Slide deck
		pad := make([]any, 12) // 12 nils for positions 4-15
		content = append([]any{nil, nil, 8, nestedSources}, pad...)
		content = append(content, []any{[]any{
			opts.FocusPrompt, opts.Language, opts.FormatCode, opts.LengthCode,
		}})
	case 4: // Flashcards/Quiz
		variantCode := 1 // flashcards
		if opts.IsQuiz {
			variantCode = 2
		}
		content = []any{
			nil, nil, 4, nestedSources, nil, nil, nil, nil, nil,
			[]any{nil, []any{
				variantCode, nil, nil, nil, nil, nil,
				[]any{opts.DifficultyCode, opts.CardCount},
			}},
		}
	case 9: // Data table
		pad := make([]any, 14)
		content = append([]any{nil, nil, 9, nestedSources}, pad...)
		content = append(content, []any{nil, []any{opts.Description, opts.Language}})
	default:
		return nil, fmt.Errorf("unsupported studio type code: %d", opts.TypeCode)
	}

	params := []any{[]any{2}, notebookID, content}
	sourcePath := NotebookPath(notebookID)

	_, err := c.Execute(ctx, RPCCreateStudio, params, sourcePath)
	if err != nil {
		return nil, fmt.Errorf("creating studio content: %w", err)
	}

	// The create RPC returns null on success — no artifact ID in the response.
	// We do an immediate poll to try to find the newly created artifact.
	artifactID := ""
	if arts, pollErr := c.PollStudioStatus(ctx, notebookID); pollErr == nil {
		for _, a := range arts {
			if status, _ := a["status"].(string); status == "in_progress" {
				if id, _ := a["artifact_id"].(string); id != "" {
					artifactID = id
					break
				}
			}
		}
	}

	return map[string]any{
		"artifact_id": artifactID,
		"status":      "in_progress",
		"notebook_id": notebookID,
		"message":     "Generation started. Use studio_status to check progress.",
	}, nil
}

// StudioOptions holds parameters for studio content creation.
type StudioOptions struct {
	TypeCode        int
	SourceIDs       []string
	FormatCode      int
	LengthCode      int
	StyleCode       int
	Language        string
	FocusPrompt     string
	OrientationCode int
	DetailCode      int
	DifficultyCode  int
	CardCount       int
	IsQuiz          bool
	Description     string
	ReportTitle     string
	ReportDesc      string
	ReportPrompt    string
}

// PollStudioStatus checks the status of studio artifacts.
func (c *Client) PollStudioStatus(ctx context.Context, notebookID string) ([]map[string]any, error) {
	params := []any{
		[]any{2},
		notebookID,
		`NOT artifact.status = "ARTIFACT_STATUS_SUGGESTED"`,
	}
	sourcePath := NotebookPath(notebookID)

	raw, err := c.Execute(ctx, RPCPollStudio, params, sourcePath)
	if err != nil {
		return nil, fmt.Errorf("polling studio status: %w", err)
	}

	outer, _ := ParseRawArray(raw)
	var artifacts []map[string]any

	// Artifacts are in the first element
	if len(outer) > 0 {
		artArr, _ := ParseRawArray(outer[0])
		for _, a := range artArr {
			art := parseArtifact(a)
			if art != nil {
				artifacts = append(artifacts, art)
			}
		}
	}

	return artifacts, nil
}

func parseArtifact(data json.RawMessage) map[string]any {
	arr, err := ParseRawArray(data)
	if err != nil || len(arr) < 5 {
		return nil
	}

	id := GetString(arr[0])
	if id == "" {
		return nil
	}

	title := GetString(arr[1])
	typeCode := GetInt(arr[2])
	statusCode := GetInt(arr[4]) // position 4 is the status code

	typeName, ok := constants.StudioTypes.Name(typeCode)
	if !ok {
		typeName = fmt.Sprintf("type_%d", typeCode)
	}

	// Map status codes: 1 = in_progress, 2 = completed (alternate), 3 = completed
	status := "unknown"
	switch statusCode {
	case 1:
		status = "in_progress"
	case 2, 3:
		status = "completed"
	}

	result := map[string]any{
		"artifact_id": id,
		"title":       title,
		"type":        typeName,
		"type_code":   typeCode,
		"status":      status,
	}

	// Extract audio URL from position 6
	if typeCode == 1 && len(arr) > 6 {
		audioOpts, _ := ParseRawArray(arr[6])
		if len(audioOpts) > 3 {
			if url := GetString(audioOpts[3]); url != "" {
				result["audio_url"] = url
			}
		}
	}

	// Extract video URL from position 8
	if typeCode == 3 && len(arr) > 8 {
		videoOpts, _ := ParseRawArray(arr[8])
		if len(videoOpts) > 3 {
			if url := GetString(videoOpts[3]); url != "" {
				result["video_url"] = url
			}
		}
	}

	return result
}

// DeleteStudioContent permanently deletes a studio artifact.
func (c *Client) DeleteStudioContent(ctx context.Context, artifactID string) error {
	params := []any{[]any{2}, artifactID}
	_, err := c.Execute(ctx, RPCDeleteStudio, params, "")
	if err != nil {
		return fmt.Errorf("deleting studio content: %w", err)
	}
	return nil
}

// RenameStudioArtifact renames a studio artifact.
func (c *Client) RenameStudioArtifact(ctx context.Context, artifactID, newTitle string) error {
	params := []any{[]any{artifactID, newTitle}, []any{[]any{"title"}}}
	_, err := c.Execute(ctx, RPCRenameStudio, params, "")
	if err != nil {
		return fmt.Errorf("renaming artifact: %w", err)
	}
	return nil
}
