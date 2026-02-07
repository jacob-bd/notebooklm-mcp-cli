// Command notebooklm-mcp runs the NotebookLM MCP server.
//
// It supports two transports:
//   - stdio (default): JSON-RPC over stdin/stdout, for desktop MCP clients
//   - http: JSON-RPC over HTTP POST, for container deployments
//
// Authentication cookies can be provided via the NOTEBOOKLM_COOKIES
// environment variable, or injected at runtime through the
// save_auth_tokens MCP tool during a conversation with the AI.
package main

import (
	"context"
	"flag"
	"fmt"
	"log/slog"
	"os"

	"notebooklm-mcp/internal/api"
	"notebooklm-mcp/internal/auth"
	"notebooklm-mcp/internal/mcp"
)

func main() {
	// CLI flags (with env var fallbacks)
	transport := flag.String("transport", envOrDefault("NOTEBOOKLM_MCP_TRANSPORT", "stdio"), "Transport: stdio or http")
	host := flag.String("host", envOrDefault("NOTEBOOKLM_MCP_HOST", "0.0.0.0"), "HTTP host to bind")
	port := flag.Int("port", envOrDefaultInt("NOTEBOOKLM_MCP_PORT", 8000), "HTTP port to bind")
	path := flag.String("path", envOrDefault("NOTEBOOKLM_MCP_PATH", "/mcp"), "HTTP endpoint path")
	debug := flag.Bool("debug", envOrDefault("NOTEBOOKLM_MCP_DEBUG", "") != "", "Enable debug logging")
	flag.Parse()

	// Configure logging
	logLevel := slog.LevelInfo
	if *debug {
		logLevel = slog.LevelDebug
	}
	logger := slog.New(slog.NewTextHandler(os.Stderr, &slog.HandlerOptions{Level: logLevel}))
	slog.SetDefault(logger)

	slog.Info("starting notebooklm-mcp",
		"version", mcp.ServerVersion,
		"transport", *transport,
	)

	// Initialize auth store from environment (cookies may be empty —
	// they can be provided later via the save_auth_tokens tool)
	cookies := os.Getenv("NOTEBOOKLM_COOKIES")
	authStore := auth.New(cookies)

	if cookies == "" {
		slog.Warn("NOTEBOOKLM_COOKIES not set — use the save_auth_tokens tool to provide cookies during the conversation")
	} else {
		slog.Info("cookies loaded from environment", "cookie_len", len(cookies))
	}

	// If CSRF token or session ID are explicitly provided, use them
	if csrf := os.Getenv("NOTEBOOKLM_CSRF_TOKEN"); csrf != "" {
		authStore.SetTokens(csrf, "")
	}
	if sid := os.Getenv("NOTEBOOKLM_SESSION_ID"); sid != "" {
		authStore.SetTokens("", sid)
	}

	// Create API client
	buildLabel := os.Getenv("NOTEBOOKLM_BL")
	client := api.NewClient(authStore, buildLabel)

	// Create MCP server and register tools
	server := mcp.NewServer()
	mcp.RegisterAllTools(server, client, authStore)

	slog.Info("registered MCP tools", "count", len(server.ToolNames()))

	// Select and start transport
	ctx := context.Background()
	var t mcp.Transport

	switch *transport {
	case "stdio":
		t = &mcp.StdioTransport{}
	case "http":
		t = &mcp.HTTPTransport{
			Host: *host,
			Port: *port,
			Path: *path,
		}
	default:
		fmt.Fprintf(os.Stderr, "unknown transport: %s (use stdio or http)\n", *transport)
		os.Exit(1)
	}

	if err := t.Start(ctx, server); err != nil {
		slog.Error("server stopped with error", "error", err)
		os.Exit(1)
	}
}

// envOrDefault returns the environment variable value, or the default if empty.
func envOrDefault(key, def string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return def
}

// envOrDefaultInt returns the environment variable as int, or the default.
func envOrDefaultInt(key string, def int) int {
	v := os.Getenv(key)
	if v == "" {
		return def
	}
	var n int
	if _, err := fmt.Sscanf(v, "%d", &n); err == nil {
		return n
	}
	return def
}
