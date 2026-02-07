package mcp

import (
	"context"
	"fmt"
	"strings"
	"time"

	"notebooklm-mcp/internal/api"
	"notebooklm-mcp/internal/auth"
	"notebooklm-mcp/internal/constants"
)

// RegisterAllTools registers all MCP tools with the server.
func RegisterAllTools(s *Server, client *api.Client, authStore *auth.Store) {
	registerAuthTools(s, client, authStore)
	registerNotebookTools(s, client)
	registerSourceTools(s, client)
	registerChatTools(s, client)
	registerResearchTools(s, client)
	registerStudioTools(s, client)
	registerSharingTools(s, client)
	registerNoteTools(s, client)
	registerDownloadExportTools(s, client)
	registerServerTools(s, authStore)
}

// ============================================================================
// Auth tools
// ============================================================================

func registerAuthTools(s *Server, client *api.Client, authStore *auth.Store) {
	s.AddTool(ToolDef{
		Name:        "save_auth_tokens",
		Description: "Save authentication cookies for NotebookLM. Cookies can be extracted from Chrome DevTools (Network tab → any request to notebooklm.google.com → Cookie header).",
		InputSchema: schema(props{
			"cookies":      prop("string", "Full Cookie header value from Chrome DevTools (required)"),
			"csrf_token":   prop("string", "CSRF token (optional — auto-extracted)"),
			"session_id":   prop("string", "Session ID (optional — auto-extracted)"),
			"request_body": prop("string", "Request body from a batchexecute request (optional — extracts CSRF)"),
			"request_url":  prop("string", "Request URL from a batchexecute request (optional — extracts session ID)"),
		}, "cookies"),
	}, func(ctx context.Context, p map[string]any) (*ToolCallResult, error) {
		cookies, _ := p["cookies"].(string)
		if cookies == "" {
			return ErrorResult("cookies parameter is required"), nil
		}
		authStore.SetCookies(cookies)
		csrf, _ := p["csrf_token"].(string)
		sid, _ := p["session_id"].(string)
		if csrf == "" {
			if body, ok := p["request_body"].(string); ok {
				csrf = extractParam(body, "at")
			}
		}
		if sid == "" {
			if url, ok := p["request_url"].(string); ok {
				sid = extractParam(url, "f.sid")
			}
		}
		if csrf != "" || sid != "" {
			authStore.SetTokens(csrf, sid)
		}
		return TextResult("Authentication cookies saved. CSRF/session tokens will be auto-extracted on next API call."), nil
	})

	s.AddTool(ToolDef{
		Name:        "refresh_auth",
		Description: "Reload auth tokens by fetching NotebookLM page with current cookies.",
		InputSchema: schema(props{}, ""),
	}, func(ctx context.Context, p map[string]any) (*ToolCallResult, error) {
		if !authStore.HasCookies() {
			return ErrorResult("No cookies configured. Use save_auth_tokens first."), nil
		}
		if err := authStore.RefreshTokens(ctx); err != nil {
			return ErrorResult(fmt.Sprintf("Refresh failed: %v", err)), nil
		}
		return TextResult("Auth tokens refreshed."), nil
	})
}

// ============================================================================
// Notebook tools
// ============================================================================

func registerNotebookTools(s *Server, client *api.Client) {
	s.AddTool(ToolDef{
		Name: "notebook_list", Description: "List all notebooks.",
		InputSchema: schema(props{"max_results": propDefault("integer", "Max notebooks to return", 100)}, ""),
	}, func(ctx context.Context, p map[string]any) (*ToolCallResult, error) {
		nbs, err := client.ListNotebooks(ctx, intVal(p, "max_results", 100))
		if err != nil {
			return nil, err
		}
		return JSONResult(nbs)
	})

	s.AddTool(ToolDef{
		Name: "notebook_get", Description: "Get notebook details with sources.",
		InputSchema: schema(props{"notebook_id": prop("string", "Notebook UUID")}, "notebook_id"),
	}, func(ctx context.Context, p map[string]any) (*ToolCallResult, error) {
		id := str(p, "notebook_id")
		if id == "" {
			return ErrorResult("notebook_id is required"), nil
		}
		r, err := client.GetNotebook(ctx, id)
		if err != nil {
			return nil, err
		}
		return JSONResult(r)
	})

	s.AddTool(ToolDef{
		Name: "notebook_create", Description: "Create a new notebook.",
		InputSchema: schema(props{"title": propDefault("string", "Notebook title", "")}, ""),
	}, func(ctx context.Context, p map[string]any) (*ToolCallResult, error) {
		r, err := client.CreateNotebook(ctx, str(p, "title"))
		if err != nil {
			return nil, err
		}
		return JSONResult(r)
	})

	s.AddTool(ToolDef{
		Name: "notebook_describe", Description: "Get AI-generated notebook summary with suggested topics.",
		InputSchema: schema(props{"notebook_id": prop("string", "Notebook UUID")}, "notebook_id"),
	}, func(ctx context.Context, p map[string]any) (*ToolCallResult, error) {
		r, err := client.NotebookDescribe(ctx, str(p, "notebook_id"))
		if err != nil {
			return nil, err
		}
		return JSONResult(r)
	})

	s.AddTool(ToolDef{
		Name: "notebook_rename", Description: "Rename a notebook.",
		InputSchema: schema(props{
			"notebook_id": prop("string", "Notebook UUID"),
			"new_title":   prop("string", "New title"),
		}, "notebook_id", "new_title"),
	}, func(ctx context.Context, p map[string]any) (*ToolCallResult, error) {
		id, title := str(p, "notebook_id"), str(p, "new_title")
		if id == "" || title == "" {
			return ErrorResult("notebook_id and new_title required"), nil
		}
		if err := client.RenameNotebook(ctx, id, title); err != nil {
			return nil, err
		}
		return TextResult(fmt.Sprintf("Renamed to %q", title)), nil
	})

	s.AddTool(ToolDef{
		Name: "notebook_delete", Description: "Delete notebook permanently. IRREVERSIBLE. Requires confirm=true.",
		InputSchema: schema(props{
			"notebook_id": prop("string", "Notebook UUID"),
			"confirm":     prop("boolean", "Must be true to confirm"),
		}, "notebook_id"),
	}, func(ctx context.Context, p map[string]any) (*ToolCallResult, error) {
		if !boolean(p, "confirm") {
			return ErrorResult("Set confirm=true to delete. This is IRREVERSIBLE."), nil
		}
		if err := client.DeleteNotebook(ctx, str(p, "notebook_id")); err != nil {
			return nil, err
		}
		return TextResult("Notebook deleted."), nil
	})
}

// ============================================================================
// Source tools
// ============================================================================

func registerSourceTools(s *Server, client *api.Client) {
	s.AddTool(ToolDef{
		Name: "source_add", Description: "Add a source to a notebook. Supports url, text, drive source types.",
		InputSchema: schema(props{
			"notebook_id": prop("string", "Notebook UUID"),
			"source_type": propEnum("string", "Source type", "url", "text", "drive"),
			"url":         prop("string", "URL for url/youtube sources"),
			"text":        prop("string", "Text content for text sources"),
			"title":       prop("string", "Title for text/drive sources"),
			"document_id": prop("string", "Google Drive document ID"),
			"doc_type":    propEnum("string", "Drive doc type", "doc", "slides", "sheets", "pdf"),
		}, "notebook_id", "source_type"),
	}, func(ctx context.Context, p map[string]any) (*ToolCallResult, error) {
		nbID := str(p, "notebook_id")
		srcType := str(p, "source_type")
		switch srcType {
		case "url":
			u := str(p, "url")
			if u == "" {
				return ErrorResult("url is required for source_type=url"), nil
			}
			r, err := client.AddURLSource(ctx, nbID, u)
			if err != nil {
				return nil, err
			}
			return JSONResult(r)
		case "text":
			t := str(p, "text")
			if t == "" {
				return ErrorResult("text is required for source_type=text"), nil
			}
			r, err := client.AddTextSource(ctx, nbID, t, str(p, "title"))
			if err != nil {
				return nil, err
			}
			return JSONResult(r)
		case "drive":
			docID := str(p, "document_id")
			if docID == "" {
				return ErrorResult("document_id required for source_type=drive"), nil
			}
			dt := str(p, "doc_type")
			if dt == "" {
				dt = "doc"
			}
			r, err := client.AddDriveSource(ctx, nbID, docID, str(p, "title"), dt)
			if err != nil {
				return nil, err
			}
			return JSONResult(r)
		default:
			return ErrorResult(fmt.Sprintf("unsupported source_type: %s", srcType)), nil
		}
	})

	s.AddTool(ToolDef{
		Name: "source_describe", Description: "Get AI-generated summary and keywords for a source.",
		InputSchema: schema(props{"source_id": prop("string", "Source UUID")}, "source_id"),
	}, func(ctx context.Context, p map[string]any) (*ToolCallResult, error) {
		r, err := client.GetSourceGuide(ctx, str(p, "source_id"))
		if err != nil {
			return nil, err
		}
		return JSONResult(r)
	})

	s.AddTool(ToolDef{
		Name: "source_get_content", Description: "Get raw text content of a source (no AI processing).",
		InputSchema: schema(props{"source_id": prop("string", "Source UUID")}, "source_id"),
	}, func(ctx context.Context, p map[string]any) (*ToolCallResult, error) {
		r, err := client.GetSourceContent(ctx, str(p, "source_id"))
		if err != nil {
			return nil, err
		}
		return JSONResult(r)
	})

	s.AddTool(ToolDef{
		Name: "source_list_drive", Description: "List sources with types and Drive freshness status.",
		InputSchema: schema(props{"notebook_id": prop("string", "Notebook UUID")}, "notebook_id"),
	}, func(ctx context.Context, p map[string]any) (*ToolCallResult, error) {
		r, err := client.GetNotebookSourcesWithTypes(ctx, str(p, "notebook_id"))
		if err != nil {
			return nil, err
		}
		return JSONResult(r)
	})

	s.AddTool(ToolDef{
		Name: "source_sync_drive", Description: "Sync stale Drive sources. Requires confirm=true.",
		InputSchema: schema(props{
			"source_ids": propArray("string", "Source UUIDs to sync"),
			"confirm":    prop("boolean", "Must be true"),
		}, "source_ids"),
	}, func(ctx context.Context, p map[string]any) (*ToolCallResult, error) {
		if !boolean(p, "confirm") {
			return ErrorResult("Set confirm=true to sync."), nil
		}
		ids := strSlice(p, "source_ids")
		var results []map[string]any
		for _, id := range ids {
			r, err := client.SyncDriveSource(ctx, id)
			if err != nil {
				results = append(results, map[string]any{"id": id, "error": err.Error()})
			} else {
				results = append(results, r)
			}
		}
		return JSONResult(results)
	})

	s.AddTool(ToolDef{
		Name: "source_delete", Description: "Delete source permanently. IRREVERSIBLE. Requires confirm=true.",
		InputSchema: schema(props{
			"source_id": prop("string", "Source UUID"),
			"confirm":   prop("boolean", "Must be true"),
		}, "source_id"),
	}, func(ctx context.Context, p map[string]any) (*ToolCallResult, error) {
		if !boolean(p, "confirm") {
			return ErrorResult("Set confirm=true. IRREVERSIBLE."), nil
		}
		if err := client.DeleteSource(ctx, str(p, "source_id")); err != nil {
			return nil, err
		}
		return TextResult("Source deleted."), nil
	})
}

// ============================================================================
// Chat tools
// ============================================================================

func registerChatTools(s *Server, client *api.Client) {
	s.AddTool(ToolDef{
		Name: "notebook_query", Description: "Ask AI about existing sources in a notebook.",
		InputSchema: schema(props{
			"notebook_id":     prop("string", "Notebook UUID"),
			"query":           prop("string", "Question to ask"),
			"source_ids":      propArray("string", "Source IDs to query (default: all)"),
			"conversation_id": prop("string", "For follow-up questions"),
			"timeout":         prop("number", "Timeout seconds (default: 120)"),
		}, "notebook_id", "query"),
	}, func(ctx context.Context, p map[string]any) (*ToolCallResult, error) {
		nbID := str(p, "notebook_id")
		query := str(p, "query")
		if nbID == "" || query == "" {
			return ErrorResult("notebook_id and query required"), nil
		}
		srcIDs := strSlice(p, "source_ids")
		convID := str(p, "conversation_id")
		timeout := time.Duration(number(p, "timeout")) * time.Second

		r, err := client.Query(ctx, nbID, query, srcIDs, convID, timeout)
		if err != nil {
			return nil, err
		}
		return JSONResult(r)
	})

	s.AddTool(ToolDef{
		Name: "chat_configure", Description: "Configure notebook chat goal/style and response length.",
		InputSchema: schema(props{
			"notebook_id":     prop("string", "Notebook UUID"),
			"goal":            propEnum("string", "Chat goal", "default", "custom", "learning_guide"),
			"custom_prompt":   prop("string", "Custom prompt (for goal=custom)"),
			"response_length": propEnum("string", "Response length", "default", "longer", "shorter"),
		}, "notebook_id"),
	}, func(ctx context.Context, p map[string]any) (*ToolCallResult, error) {
		nbID := str(p, "notebook_id")
		goalStr := str(p, "goal")
		if goalStr == "" {
			goalStr = "default"
		}
		respLen := str(p, "response_length")
		if respLen == "" {
			respLen = "default"
		}

		goalCode, _ := constants.ChatGoals.Code(goalStr)
		lenCode, _ := constants.ResponseLengths.Code(respLen)

		goalArr := []any{goalCode}
		if goalStr == "custom" {
			goalArr = append(goalArr, str(p, "custom_prompt"))
		}

		chatSettings := []any{goalArr, []any{lenCode}}
		updateArr := []any{nil, nil, nil, nil, nil, nil, nil, chatSettings}
		params := []any{nbID, []any{updateArr}}

		_, err := client.Execute(ctx, api.RPCUpdateNotebook, params, fmt.Sprintf("/notebook/%s", nbID))
		if err != nil {
			return nil, err
		}
		return TextResult(fmt.Sprintf("Chat configured: goal=%s, length=%s", goalStr, respLen)), nil
	})
}

// ============================================================================
// Research tools
// ============================================================================

func registerResearchTools(s *Server, client *api.Client) {
	s.AddTool(ToolDef{
		Name: "research_start", Description: "Start web or Drive research to discover sources.",
		InputSchema: schema(props{
			"query":       prop("string", "Search query"),
			"source":      propEnum("string", "Search source", "web", "drive"),
			"mode":        propEnum("string", "Depth", "fast", "deep"),
			"notebook_id": prop("string", "Existing notebook (creates new if omitted)"),
			"title":       prop("string", "Title for new notebook"),
		}, "query"),
	}, func(ctx context.Context, p map[string]any) (*ToolCallResult, error) {
		nbID := str(p, "notebook_id")
		if nbID == "" {
			title := str(p, "title")
			if title == "" {
				title = str(p, "query")
			}
			nb, err := client.CreateNotebook(ctx, title)
			if err != nil {
				return nil, fmt.Errorf("creating notebook for research: %w", err)
			}
			nbID, _ = nb["id"].(string)
		}
		source := str(p, "source")
		if source == "" {
			source = "web"
		}
		mode := str(p, "mode")
		if mode == "" {
			mode = "fast"
		}
		r, err := client.StartResearch(ctx, nbID, str(p, "query"), source, mode)
		if err != nil {
			return nil, err
		}
		return JSONResult(r)
	})

	s.AddTool(ToolDef{
		Name: "research_status", Description: "Poll research progress.",
		InputSchema: schema(props{
			"notebook_id":   prop("string", "Notebook UUID"),
			"poll_interval": propDefault("integer", "Seconds between polls", 30),
			"max_wait":      propDefault("integer", "Max wait seconds", 300),
			"compact":       propDefault("boolean", "Truncate to save tokens", true),
			"task_id":       prop("string", "Specific task ID"),
		}, "notebook_id"),
	}, func(ctx context.Context, p map[string]any) (*ToolCallResult, error) {
		nbID := str(p, "notebook_id")
		taskID := str(p, "task_id")
		maxWait := intVal(p, "max_wait", 300)
		interval := intVal(p, "poll_interval", 30)

		deadline := time.Now().Add(time.Duration(maxWait) * time.Second)
		for {
			r, err := client.PollResearch(ctx, nbID, taskID)
			if err != nil {
				return nil, err
			}
			status, _ := r["status"].(string)
			if status == "completed" || status == "no_research" || time.Now().After(deadline) {
				if boolean(p, "compact") {
					if summary, ok := r["summary"].(string); ok && len(summary) > 500 {
						r["summary"] = summary[:500] + "..."
					}
				}
				return JSONResult(r)
			}
			select {
			case <-ctx.Done():
				return nil, ctx.Err()
			case <-time.After(time.Duration(interval) * time.Second):
			}
		}
	})

	s.AddTool(ToolDef{
		Name: "research_import", Description: "Import discovered sources into notebook.",
		InputSchema: schema(props{
			"notebook_id":    prop("string", "Notebook UUID"),
			"task_id":        prop("string", "Research task ID"),
			"source_indices": propArray("integer", "Indices to import (default: all)"),
		}, "notebook_id", "task_id"),
	}, func(ctx context.Context, p map[string]any) (*ToolCallResult, error) {
		nbID := str(p, "notebook_id")
		taskID := str(p, "task_id")

		// First poll to get source list
		research, err := client.PollResearch(ctx, nbID, taskID)
		if err != nil {
			return nil, err
		}
		allSources, _ := research["sources"].([]map[string]any)

		// Filter by indices if provided
		indices := intSlice(p, "source_indices")
		var toImport []map[string]any
		if len(indices) > 0 {
			for _, idx := range indices {
				if idx >= 0 && idx < len(allSources) {
					toImport = append(toImport, allSources[idx])
				}
			}
		} else {
			toImport = allSources
		}

		imported, err := client.ImportResearchSources(ctx, nbID, taskID, toImport)
		if err != nil {
			return nil, err
		}
		return JSONResult(map[string]any{
			"imported_count": len(imported),
			"sources":        imported,
		})
	})
}

// ============================================================================
// Studio tools
// ============================================================================

func registerStudioTools(s *Server, client *api.Client) {
	s.AddTool(ToolDef{
		Name: "studio_create", Description: "Create studio content (audio/video/report/etc). Requires confirm=true.",
		InputSchema: schema(props{
			"notebook_id":   prop("string", "Notebook UUID"),
			"artifact_type": propEnum("string", "Type", "audio", "video", "report", "flashcards", "quiz", "infographic", "slide_deck", "data_table", "mind_map"),
			"source_ids":    propArray("string", "Source IDs (default: all)"),
			"confirm":       prop("boolean", "Must be true"),
			"format":        prop("string", "Format variant"),
			"length":        prop("string", "Length variant"),
			"language":      propDefault("string", "BCP-47 code", "en"),
			"focus_prompt":  prop("string", "Focus text"),
			"visual_style":  prop("string", "Video style"),
			"orientation":   prop("string", "Infographic orientation"),
			"detail_level":  prop("string", "Infographic detail"),
			"difficulty":    prop("string", "Flashcard/quiz difficulty"),
			"description":   prop("string", "Data table description"),
		}, "notebook_id", "artifact_type"),
	}, func(ctx context.Context, p map[string]any) (*ToolCallResult, error) {
		if !boolean(p, "confirm") {
			return ErrorResult("Set confirm=true to create."), nil
		}
		nbID := str(p, "notebook_id")
		artType := str(p, "artifact_type")

		srcIDs := strSlice(p, "source_ids")
		if len(srcIDs) == 0 {
			// Get all source IDs from notebook
			sources, err := client.GetNotebookSourcesWithTypes(ctx, nbID)
			if err == nil {
				for _, s := range sources {
					if id, ok := s["id"].(string); ok {
						srcIDs = append(srcIDs, id)
					}
				}
			}
		}

		lang := str(p, "language")
		if lang == "" {
			lang = "en"
		}

		opts := api.StudioOptions{
			SourceIDs:   srcIDs,
			Language:    lang,
			FocusPrompt: str(p, "focus_prompt"),
			Description: str(p, "description"),
		}

		switch artType {
		case "audio":
			opts.TypeCode = 1
			opts.FormatCode, _ = constants.AudioFormats.Code(strOr(p, "format", "deep_dive"))
			opts.LengthCode, _ = constants.AudioLengths.Code(strOr(p, "length", "default"))
		case "video":
			opts.TypeCode = 3
			opts.FormatCode, _ = constants.VideoFormats.Code(strOr(p, "format", "explainer"))
			opts.StyleCode, _ = constants.VideoStyles.Code(strOr(p, "visual_style", "auto_select"))
		case "report":
			opts.TypeCode = 2
			opts.ReportTitle = strOr(p, "format", "Briefing Doc")
			opts.ReportDesc = "Key insights"
			opts.ReportPrompt = str(p, "focus_prompt")
		case "infographic":
			opts.TypeCode = 7
			opts.OrientationCode, _ = constants.InfographicOrientations.Code(strOr(p, "orientation", "landscape"))
			opts.DetailCode, _ = constants.InfographicDetails.Code(strOr(p, "detail_level", "standard"))
		case "slide_deck":
			opts.TypeCode = 8
			opts.FormatCode, _ = constants.SlideDeckFormats.Code(strOr(p, "format", "detailed_deck"))
			opts.LengthCode, _ = constants.SlideDeckLengths.Code(strOr(p, "length", "default"))
		case "flashcards":
			opts.TypeCode = 4
			opts.DifficultyCode, _ = constants.FlashcardDifficulties.Code(strOr(p, "difficulty", "medium"))
		case "quiz":
			opts.TypeCode = 4
			opts.IsQuiz = true
			opts.DifficultyCode, _ = constants.FlashcardDifficulties.Code(strOr(p, "difficulty", "medium"))
		case "data_table":
			opts.TypeCode = 9
		case "mind_map":
			return ErrorResult("Mind map uses a separate two-step RPC flow — not yet wired."), nil
		default:
			return ErrorResult("Unknown artifact_type: " + artType), nil
		}

		r, err := client.CreateStudioContent(ctx, nbID, opts)
		if err != nil {
			return nil, err
		}
		return JSONResult(r)
	})

	s.AddTool(ToolDef{
		Name: "studio_status", Description: "Check studio artifact status or rename.",
		InputSchema: schema(props{
			"notebook_id": prop("string", "Notebook UUID"),
			"action":      propEnum("string", "Action", "status", "rename"),
			"artifact_id": prop("string", "Artifact ID (for rename)"),
			"new_title":   prop("string", "New title (for rename)"),
		}, "notebook_id"),
	}, func(ctx context.Context, p map[string]any) (*ToolCallResult, error) {
		action := strOr(p, "action", "status")
		if action == "rename" {
			aid := str(p, "artifact_id")
			title := str(p, "new_title")
			if aid == "" || title == "" {
				return ErrorResult("artifact_id and new_title required for rename"), nil
			}
			if err := client.RenameStudioArtifact(ctx, aid, title); err != nil {
				return nil, err
			}
			return TextResult(fmt.Sprintf("Renamed to %q", title)), nil
		}
		arts, err := client.PollStudioStatus(ctx, str(p, "notebook_id"))
		if err != nil {
			return nil, err
		}
		return JSONResult(map[string]any{"artifacts": arts})
	})

	s.AddTool(ToolDef{
		Name: "studio_delete", Description: "Delete studio artifact. IRREVERSIBLE. Requires confirm=true.",
		InputSchema: schema(props{
			"notebook_id": prop("string", "Notebook UUID"),
			"artifact_id": prop("string", "Artifact UUID"),
			"confirm":     prop("boolean", "Must be true"),
		}, "notebook_id", "artifact_id"),
	}, func(ctx context.Context, p map[string]any) (*ToolCallResult, error) {
		if !boolean(p, "confirm") {
			return ErrorResult("Set confirm=true. IRREVERSIBLE."), nil
		}
		if err := client.DeleteStudioContent(ctx, str(p, "artifact_id")); err != nil {
			return nil, err
		}
		return TextResult("Artifact deleted."), nil
	})
}

// ============================================================================
// Sharing tools
// ============================================================================

func registerSharingTools(s *Server, client *api.Client) {
	s.AddTool(ToolDef{
		Name: "notebook_share_status", Description: "Get sharing settings and collaborators.",
		InputSchema: schema(props{"notebook_id": prop("string", "Notebook UUID")}, "notebook_id"),
	}, func(ctx context.Context, p map[string]any) (*ToolCallResult, error) {
		r, err := client.GetShareStatus(ctx, str(p, "notebook_id"))
		if err != nil {
			return nil, err
		}
		return JSONResult(r)
	})

	s.AddTool(ToolDef{
		Name: "notebook_share_public", Description: "Enable/disable public link access.",
		InputSchema: schema(props{
			"notebook_id": prop("string", "Notebook UUID"),
			"is_public":   propDefault("boolean", "Enable public link", true),
		}, "notebook_id"),
	}, func(ctx context.Context, p map[string]any) (*ToolCallResult, error) {
		isPublic := true
		if v, ok := p["is_public"].(bool); ok {
			isPublic = v
		}
		if err := client.SetSharePublic(ctx, str(p, "notebook_id"), isPublic); err != nil {
			return nil, err
		}
		state := "enabled"
		if !isPublic {
			state = "disabled"
		}
		return TextResult("Public link " + state + "."), nil
	})

	s.AddTool(ToolDef{
		Name: "notebook_share_invite", Description: "Invite collaborator by email.",
		InputSchema: schema(props{
			"notebook_id": prop("string", "Notebook UUID"),
			"email":       prop("string", "Email address"),
			"role":        propEnum("string", "Role", "viewer", "editor"),
		}, "notebook_id", "email"),
	}, func(ctx context.Context, p map[string]any) (*ToolCallResult, error) {
		email := str(p, "email")
		role := strOr(p, "role", "viewer")
		if err := client.InviteCollaborator(ctx, str(p, "notebook_id"), email, role); err != nil {
			return nil, err
		}
		return TextResult(fmt.Sprintf("Invited %s as %s.", email, role)), nil
	})
}

// ============================================================================
// Note tools
// ============================================================================

func registerNoteTools(s *Server, client *api.Client) {
	s.AddTool(ToolDef{
		Name: "note", Description: "Manage notes: create, list, update, or delete.",
		InputSchema: schema(props{
			"notebook_id": prop("string", "Notebook UUID"),
			"action":      propEnum("string", "Action", "create", "list", "update", "delete"),
			"note_id":     prop("string", "Note ID (update/delete)"),
			"content":     prop("string", "Note content (create/update)"),
			"title":       prop("string", "Note title (create/update)"),
			"confirm":     prop("boolean", "Required for delete"),
		}, "notebook_id", "action"),
	}, func(ctx context.Context, p map[string]any) (*ToolCallResult, error) {
		nbID := str(p, "notebook_id")
		switch str(p, "action") {
		case "create":
			r, err := client.CreateNote(ctx, nbID, str(p, "title"))
			if err != nil {
				return nil, err
			}
			// Update content if provided
			if content := str(p, "content"); content != "" {
				if noteID, ok := r["note_id"].(string); ok && noteID != "" {
					if err := client.UpdateNote(ctx, nbID, noteID, content, str(p, "title")); err != nil {
						return nil, fmt.Errorf("note created (id=%s) but content update failed: %w", noteID, err)
					}
				}
			}
			return JSONResult(r)
		case "list":
			notes, err := client.ListNotes(ctx, nbID)
			if err != nil {
				return nil, err
			}
			return JSONResult(notes)
		case "update":
			noteID := str(p, "note_id")
			if noteID == "" {
				return ErrorResult("note_id required for update"), nil
			}
			if err := client.UpdateNote(ctx, nbID, noteID, str(p, "content"), str(p, "title")); err != nil {
				return nil, err
			}
			return TextResult("Note updated."), nil
		case "delete":
			if !boolean(p, "confirm") {
				return ErrorResult("Set confirm=true. IRREVERSIBLE."), nil
			}
			if err := client.DeleteNote(ctx, nbID, str(p, "note_id")); err != nil {
				return nil, err
			}
			return TextResult("Note deleted."), nil
		default:
			return ErrorResult("Unknown action. Use: create, list, update, delete"), nil
		}
	})
}

// ============================================================================
// Download & Export tools
// ============================================================================

func registerDownloadExportTools(s *Server, client *api.Client) {
	s.AddTool(ToolDef{
		Name: "download_artifact", Description: "Download studio artifact (audio, video, pdf, etc).",
		InputSchema: schema(props{
			"notebook_id":   prop("string", "Notebook UUID"),
			"artifact_type": prop("string", "Artifact type"),
			"output_path":   prop("string", "Path to save file"),
			"artifact_id":   prop("string", "Specific artifact ID"),
			"output_format": propEnum("string", "Format", "json", "markdown"),
		}, "notebook_id", "artifact_type", "output_path"),
	}, func(ctx context.Context, p map[string]any) (*ToolCallResult, error) {
		// In container mode, downloads require volume mounts.
		// We get the URL from studio_status and return it.
		arts, err := client.PollStudioStatus(ctx, str(p, "notebook_id"))
		if err != nil {
			return nil, err
		}
		artType := str(p, "artifact_type")
		artID := str(p, "artifact_id")
		for _, a := range arts {
			if artID != "" && a["artifact_id"] != artID {
				continue
			}
			if t, ok := a["type"].(string); ok && t == artType {
				return JSONResult(a) // includes URLs
			}
		}
		return ErrorResult(fmt.Sprintf("No %s artifact found. Check studio_status first.", artType)), nil
	})

	s.AddTool(ToolDef{
		Name: "export_artifact", Description: "Export artifact to Google Docs or Sheets.",
		InputSchema: schema(props{
			"notebook_id": prop("string", "Notebook UUID"),
			"artifact_id": prop("string", "Artifact UUID"),
			"export_type": propEnum("string", "Destination", "docs", "sheets"),
			"title":       prop("string", "Document title"),
		}, "notebook_id", "artifact_id", "export_type"),
	}, func(ctx context.Context, p map[string]any) (*ToolCallResult, error) {
		title := strOr(p, "title", "NotebookLM Export")
		r, err := client.ExportArtifact(ctx, str(p, "notebook_id"), str(p, "artifact_id"), title, str(p, "export_type"))
		if err != nil {
			return nil, err
		}
		return JSONResult(r)
	})
}

// ============================================================================
// Server info
// ============================================================================

func registerServerTools(s *Server, authStore *auth.Store) {
	s.AddTool(ToolDef{
		Name: "server_info", Description: "Get server version, transport, and auth status.",
		InputSchema: schema(props{}, ""),
	}, func(ctx context.Context, p map[string]any) (*ToolCallResult, error) {
		return JSONResult(map[string]any{
			"name": ServerName, "version": ServerVersion,
			"runtime": "go", "auth_status": authStore.Status(),
		})
	})
}

// ============================================================================
// Schema builder helpers
// ============================================================================

type props = map[string]map[string]any

func schema(properties props, required ...string) map[string]any {
	s := map[string]any{"type": "object", "properties": properties}
	var req []string
	for _, r := range required {
		if r != "" {
			req = append(req, r)
		}
	}
	if len(req) > 0 {
		s["required"] = req
	}
	return s
}

func prop(typ, desc string) map[string]any {
	return map[string]any{"type": typ, "description": desc}
}

func propDefault(typ, desc string, def any) map[string]any {
	return map[string]any{"type": typ, "description": desc, "default": def}
}

func propEnum(typ, desc string, values ...string) map[string]any {
	return map[string]any{"type": typ, "description": desc, "enum": values}
}

func propArray(itemType, desc string) map[string]any {
	return map[string]any{"type": "array", "description": desc, "items": map[string]any{"type": itemType}}
}

// ============================================================================
// Parameter extraction helpers
// ============================================================================

func str(p map[string]any, key string) string {
	v, _ := p[key].(string)
	return v
}

func strOr(p map[string]any, key, def string) string {
	if v := str(p, key); v != "" {
		return v
	}
	return def
}

func boolean(p map[string]any, key string) bool {
	v, _ := p[key].(bool)
	return v
}

func number(p map[string]any, key string) float64 {
	v, _ := p[key].(float64)
	return v
}

func intVal(p map[string]any, key string, def int) int {
	if v, ok := p[key].(float64); ok {
		return int(v)
	}
	return def
}

func strSlice(p map[string]any, key string) []string {
	raw, ok := p[key]
	if !ok {
		return nil
	}
	switch v := raw.(type) {
	case []any:
		var out []string
		for _, item := range v {
			if s, ok := item.(string); ok {
				out = append(out, s)
			}
		}
		return out
	case []string:
		return v
	}
	return nil
}

func intSlice(p map[string]any, key string) []int {
	raw, ok := p[key]
	if !ok {
		return nil
	}
	if v, ok := raw.([]any); ok {
		var out []int
		for _, item := range v {
			if n, ok := item.(float64); ok {
				out = append(out, int(n))
			}
		}
		return out
	}
	return nil
}

func extractParam(s, key string) string {
	prefix := key + "="
	for i := 0; i <= len(s)-len(prefix); i++ {
		if s[i:i+len(prefix)] == prefix && (i == 0 || s[i-1] == '&' || s[i-1] == '?') {
			val := s[i+len(prefix):]
			if amp := strings.Index(val, "&"); amp >= 0 {
				return val[:amp]
			}
			return val
		}
	}
	return ""
}
