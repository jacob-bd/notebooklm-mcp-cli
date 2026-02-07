// Package auth manages authentication state for the NotebookLM API.
//
// Cookies are the sole credential. They can be provided via:
//   - NOTEBOOKLM_COOKIES environment variable at container startup
//   - The save_auth_tokens MCP tool during a conversation
//
// CSRF token and session ID are automatically extracted from the
// NotebookLM page HTML on the first API call.
package auth

import (
	"context"
	"errors"
	"fmt"
	"io"
	"log/slog"
	"net/http"
	"regexp"
	"strings"
	"sync"
	"time"
)

var (
	// ErrNoCookies is returned when no cookies have been configured.
	ErrNoCookies = errors.New(
		"no authentication cookies configured — provide via NOTEBOOKLM_COOKIES " +
			"environment variable or the save_auth_tokens MCP tool during the conversation",
	)

	csrfRe    = regexp.MustCompile(`"SNlM0e":"([^"]+)"`)
	sessionRe = regexp.MustCompile(`"FdrFJe":"([^"]+)"`)
)

// Store is a thread-safe in-memory store for authentication credentials.
// It holds cookies, CSRF token, and session ID. Cookies must be provided
// externally; CSRF and session tokens are auto-extracted from the NotebookLM
// page when needed.
type Store struct {
	mu         sync.RWMutex
	cookies    string // Raw Cookie header value
	csrfToken  string // SNlM0e from page HTML
	sessionID  string // FdrFJe from page HTML
	httpClient *http.Client
}

// New creates a Store, optionally pre-loaded with cookies.
// Pass an empty string if cookies will be provided later via SetCookies.
func New(cookies string) *Store {
	return &Store{
		cookies:    strings.TrimSpace(cookies),
		httpClient: &http.Client{Timeout: 30 * time.Second},
	}
}

// SetCookies stores cookies provided at runtime (e.g. via save_auth_tokens).
// Clears cached CSRF/session tokens so they are re-extracted on next use.
func (s *Store) SetCookies(cookies string) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.cookies = strings.TrimSpace(cookies)
	s.csrfToken = ""
	s.sessionID = ""
	slog.Info("auth cookies updated", "cookie_len", len(s.cookies))
}

// SetTokens explicitly sets CSRF token and/or session ID.
// Non-empty values override the stored ones.
func (s *Store) SetTokens(csrf, sessionID string) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if csrf != "" {
		s.csrfToken = csrf
	}
	if sessionID != "" {
		s.sessionID = sessionID
	}
}

// HasCookies reports whether cookies have been configured.
func (s *Store) HasCookies() bool {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.cookies != ""
}

// Cookies returns the raw cookie header string.
func (s *Store) Cookies() string {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.cookies
}

// CSRFToken returns the current CSRF token.
func (s *Store) CSRFToken() string {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.csrfToken
}

// SessionID returns the current session ID.
func (s *Store) SessionID() string {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.sessionID
}

// EnsureTokens extracts CSRF token and session ID from the NotebookLM page
// if they haven't been extracted yet. Safe to call repeatedly — it's a no-op
// if tokens are already available.
func (s *Store) EnsureTokens(ctx context.Context) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	if s.cookies == "" {
		return ErrNoCookies
	}
	if s.csrfToken != "" {
		return nil
	}
	return s.extractTokensLocked(ctx)
}

// RefreshTokens forces re-extraction of CSRF and session tokens.
// Use after an auth error to get fresh tokens.
func (s *Store) RefreshTokens(ctx context.Context) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	if s.cookies == "" {
		return ErrNoCookies
	}
	s.csrfToken = ""
	s.sessionID = ""
	return s.extractTokensLocked(ctx)
}

// extractTokensLocked fetches the NotebookLM page and extracts tokens.
// Caller MUST hold s.mu write lock.
func (s *Store) extractTokensLocked(ctx context.Context) error {
	slog.Debug("extracting auth tokens from NotebookLM page")

	req, err := http.NewRequestWithContext(ctx, "GET", "https://notebooklm.google.com/", nil)
	if err != nil {
		return fmt.Errorf("building token extraction request: %w", err)
	}
	req.Header.Set("Cookie", s.cookies)
	req.Header.Set("User-Agent", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko)")

	resp, err := s.httpClient.Do(req)
	if err != nil {
		return fmt.Errorf("fetching NotebookLM page: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("NotebookLM returned HTTP %d — cookies may be expired or invalid", resp.StatusCode)
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return fmt.Errorf("reading NotebookLM page body: %w", err)
	}

	// Extract CSRF token (required)
	if m := csrfRe.FindSubmatch(body); len(m) > 1 {
		s.csrfToken = string(m[1])
	} else {
		return fmt.Errorf("CSRF token (SNlM0e) not found in page — cookies may be expired or for the wrong account")
	}

	// Extract session ID (optional, improves reliability)
	if m := sessionRe.FindSubmatch(body); len(m) > 1 {
		s.sessionID = string(m[1])
	}

	slog.Debug("auth tokens extracted",
		"csrf_len", len(s.csrfToken),
		"has_session", s.sessionID != "",
	)
	return nil
}

// Status returns a summary of the current auth state, useful for server_info.
func (s *Store) Status() string {
	s.mu.RLock()
	defer s.mu.RUnlock()

	if s.cookies == "" {
		return "no_cookies"
	}
	if s.csrfToken == "" {
		return "cookies_set_tokens_pending"
	}
	return "authenticated"
}
