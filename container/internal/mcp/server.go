package mcp

import (
	"context"
	"encoding/json"
	"fmt"
	"log/slog"
	"sync"
)

const (
	// ProtocolVersion is the MCP protocol version we support.
	ProtocolVersion = "2024-11-05"
	// ServerName identifies this server.
	ServerName = "notebooklm-mcp-go"
	// ServerVersion is the current version of this server.
	ServerVersion = "0.1.0"
)

// HandlerFunc is the signature for MCP tool handlers.
// It receives parsed arguments and returns a result or error.
type HandlerFunc func(ctx context.Context, params map[string]any) (*ToolCallResult, error)

// registeredTool pairs a tool definition with its handler.
type registeredTool struct {
	def     ToolDef
	handler HandlerFunc
}

// Server is the MCP JSON-RPC server. It handles initialize, tools/list,
// and tools/call methods, dispatching tool calls to registered handlers.
type Server struct {
	mu    sync.RWMutex
	tools []registeredTool
	index map[string]int // name -> index in tools slice

	initialized bool
}

// NewServer creates an MCP server with no tools registered.
func NewServer() *Server {
	return &Server{
		index: make(map[string]int),
	}
}

// AddTool registers a tool with the server. Call before starting the transport.
func (s *Server) AddTool(def ToolDef, handler HandlerFunc) {
	s.mu.Lock()
	defer s.mu.Unlock()
	idx := len(s.tools)
	s.tools = append(s.tools, registeredTool{def: def, handler: handler})
	s.index[def.Name] = idx
}

// HandleMessage processes a single JSON-RPC message and returns the response.
// Returns nil for notifications (messages without an ID).
func (s *Server) HandleMessage(ctx context.Context, msg []byte) []byte {
	var req Request
	if err := json.Unmarshal(msg, &req); err != nil {
		return mustMarshal(Response{
			JSONRPC: "2.0",
			Error:   &Error{Code: ErrCodeParse, Message: "parse error: " + err.Error()},
		})
	}

	slog.Debug("received JSON-RPC", "method", req.Method, "id", req.ID)

	// Notifications have no ID and don't get a response
	if req.ID == nil {
		s.handleNotification(req)
		return nil
	}

	resp := s.dispatch(ctx, req)
	return mustMarshal(resp)
}

// dispatch routes a request to the appropriate handler.
func (s *Server) dispatch(ctx context.Context, req Request) Response {
	switch req.Method {
	case "initialize":
		return s.handleInitialize(req)
	case "tools/list":
		return s.handleToolsList(req)
	case "tools/call":
		return s.handleToolsCall(ctx, req)
	case "ping":
		return Response{JSONRPC: "2.0", ID: req.ID, Result: map[string]any{}}
	default:
		return Response{
			JSONRPC: "2.0",
			ID:      req.ID,
			Error:   &Error{Code: ErrCodeMethodNotFound, Message: "method not found: " + req.Method},
		}
	}
}

// handleNotification processes notifications (no response expected).
func (s *Server) handleNotification(req Request) {
	switch req.Method {
	case "notifications/initialized":
		s.initialized = true
		slog.Info("client initialized")
	default:
		slog.Debug("unhandled notification", "method", req.Method)
	}
}

// handleInitialize responds to the MCP initialize handshake.
func (s *Server) handleInitialize(req Request) Response {
	result := InitializeResult{
		ProtocolVersion: ProtocolVersion,
		ServerInfo: ServerInfo{
			Name:    ServerName,
			Version: ServerVersion,
		},
		Capabilities: Capabilities{
			Tools: &ToolsCapability{ListChanged: false},
		},
	}
	return Response{JSONRPC: "2.0", ID: req.ID, Result: result}
}

// handleToolsList returns all registered tool definitions.
func (s *Server) handleToolsList(req Request) Response {
	s.mu.RLock()
	defer s.mu.RUnlock()

	defs := make([]ToolDef, len(s.tools))
	for i, t := range s.tools {
		defs[i] = t.def
	}
	return Response{JSONRPC: "2.0", ID: req.ID, Result: ToolsListResult{Tools: defs}}
}

// handleToolsCall dispatches a tool call to the registered handler.
func (s *Server) handleToolsCall(ctx context.Context, req Request) Response {
	var callParams ToolCallParams
	if req.Params != nil {
		if err := json.Unmarshal(req.Params, &callParams); err != nil {
			return Response{
				JSONRPC: "2.0",
				ID:      req.ID,
				Error:   &Error{Code: ErrCodeInvalidParams, Message: "invalid params: " + err.Error()},
			}
		}
	}

	s.mu.RLock()
	idx, ok := s.index[callParams.Name]
	var handler HandlerFunc
	if ok {
		handler = s.tools[idx].handler
	}
	s.mu.RUnlock()

	if !ok {
		return Response{
			JSONRPC: "2.0",
			ID:      req.ID,
			Result:  ErrorResult(fmt.Sprintf("unknown tool: %s", callParams.Name)),
		}
	}

	args := callParams.Arguments
	if args == nil {
		args = make(map[string]any)
	}

	slog.Debug("calling tool", "name", callParams.Name)
	result, err := handler(ctx, args)
	if err != nil {
		slog.Error("tool call failed", "name", callParams.Name, "error", err)
		return Response{
			JSONRPC: "2.0",
			ID:      req.ID,
			Result:  ErrorResult(err.Error()),
		}
	}

	return Response{JSONRPC: "2.0", ID: req.ID, Result: result}
}

// ToolNames returns the names of all registered tools.
func (s *Server) ToolNames() []string {
	s.mu.RLock()
	defer s.mu.RUnlock()
	names := make([]string, len(s.tools))
	for i, t := range s.tools {
		names[i] = t.def.Name
	}
	return names
}

func mustMarshal(v any) []byte {
	data, err := json.Marshal(v)
	if err != nil {
		panic("mcp: failed to marshal response: " + err.Error())
	}
	return data
}
