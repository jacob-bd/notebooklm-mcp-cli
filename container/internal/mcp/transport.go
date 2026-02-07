package mcp

import (
	"bufio"
	"context"
	"fmt"
	"io"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"
)

// Transport defines how the MCP server communicates with clients.
type Transport interface {
	// Start begins processing messages. It blocks until the transport
	// closes or the context is cancelled.
	Start(ctx context.Context, server *Server) error
}

// --- stdio transport ---

// StdioTransport reads JSON-RPC messages from stdin and writes
// responses to stdout, one message per line.
type StdioTransport struct{}

func (t *StdioTransport) Start(ctx context.Context, server *Server) error {
	slog.Info("starting stdio transport")

	scanner := bufio.NewScanner(os.Stdin)
	// Allow messages up to 10 MB
	scanner.Buffer(make([]byte, 0, 64*1024), 10*1024*1024)

	for scanner.Scan() {
		select {
		case <-ctx.Done():
			return ctx.Err()
		default:
		}

		line := scanner.Bytes()
		if len(line) == 0 {
			continue
		}

		resp := server.HandleMessage(ctx, line)
		if resp == nil {
			continue // notification, no response
		}

		// Write response followed by newline
		if _, err := os.Stdout.Write(resp); err != nil {
			return fmt.Errorf("writing to stdout: %w", err)
		}
		if _, err := os.Stdout.Write([]byte("\n")); err != nil {
			return fmt.Errorf("writing newline to stdout: %w", err)
		}
	}

	if err := scanner.Err(); err != nil {
		return fmt.Errorf("reading from stdin: %w", err)
	}
	return nil // stdin closed
}

// --- HTTP transport (streamable-http) ---

// HTTPTransport serves JSON-RPC over HTTP POST requests.
type HTTPTransport struct {
	Host string
	Port int
	Path string // MCP endpoint path, default "/mcp"
}

func (t *HTTPTransport) Start(ctx context.Context, server *Server) error {
	if t.Path == "" {
		t.Path = "/mcp"
	}

	mux := http.NewServeMux()

	// MCP endpoint — accepts JSON-RPC POST requests
	mux.HandleFunc(t.Path, func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}

		body, err := io.ReadAll(r.Body)
		if err != nil {
			http.Error(w, "failed to read body", http.StatusBadRequest)
			return
		}

		resp := server.HandleMessage(r.Context(), body)
		if resp == nil {
			w.WriteHeader(http.StatusAccepted)
			return
		}

		w.Header().Set("Content-Type", "application/json")
		w.Write(resp)
	})

	// Health check for container orchestration
	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		w.Write([]byte(`{"status":"ok"}`))
	})

	addr := fmt.Sprintf("%s:%d", t.Host, t.Port)
	httpServer := &http.Server{
		Addr:         addr,
		Handler:      mux,
		ReadTimeout:  30 * time.Second,
		WriteTimeout: 120 * time.Second,
		IdleTimeout:  60 * time.Second,
	}

	// Graceful shutdown on context cancellation or signal
	ctx, stop := signal.NotifyContext(ctx, syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	go func() {
		<-ctx.Done()
		slog.Info("shutting down HTTP server")
		shutdownCtx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		httpServer.Shutdown(shutdownCtx)
	}()

	slog.Info("starting HTTP transport", "addr", addr, "path", t.Path)
	if err := httpServer.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		return fmt.Errorf("HTTP server error: %w", err)
	}
	return nil
}
