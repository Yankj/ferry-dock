// Package relay provides a bounded, ephemeral text inbox over HTTP.
package relay

import (
	"bytes"
	"crypto/rand"
	"crypto/subtle"
	"embed"
	"encoding/base64"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net"
	"net/http"
	"net/url"
	"strconv"
	"strings"
	"sync"
	"time"
	"unicode/utf8"

	"github.com/Yankj/ferry-dock/brand"
	qrcode "github.com/skip2/go-qrcode"
)

const (
	MaxTextBytes    = 64 << 10
	MaxSessionBytes = 1 << 20
	MaxMessages     = 128
	MaxSessions     = 16
	maxJSONBytes    = 6*MaxTextBytes + 2048
)

//go:embed web/*
var assets embed.FS

// Config keeps deployment choices outside the in-memory relay.
type Config struct {
	OwnerToken string
	LocalURL   string
	PublicURL  string
	TTL        time.Duration
	Desktop    *DesktopConfig
}

// DesktopConfig exists only in the packaged local launcher mode.
type DesktopConfig struct {
	InstanceID string
	Quit       func()
}

type Message struct {
	ID         string    `json:"id"`
	Sequence   uint64    `json:"sequence"`
	Text       string    `json:"text"`
	ReceivedAt time.Time `json:"receivedAt"`
}

type session struct {
	id        string
	key       string
	expiresAt time.Time
	messages  []Message
	keys      map[string]int
	bytes     int
}

// Server has no disk storage, background workers, or external service dependency.
type Server struct {
	mu        sync.Mutex
	sessions  map[string]*session
	requests  map[string]*requestRecord
	waitSlots chan struct{}
	config    Config
	hosts     map[string]bool
	now       func() time.Time
	slots     chan struct{}
	handler   http.Handler
}

// New validates the advertised origins. The caller owns the listener and lifecycle.
func New(config Config) (*Server, error) {
	if len(config.OwnerToken) < 32 {
		return nil, errors.New("owner token must contain at least 32 characters")
	}
	if config.TTL <= 0 || config.TTL > 24*time.Hour {
		return nil, errors.New("session TTL must be greater than zero and at most 24h")
	}
	s := &Server{config: config, sessions: make(map[string]*session), requests: make(map[string]*requestRecord), waitSlots: make(chan struct{}, 8), hosts: make(map[string]bool), now: time.Now, slots: make(chan struct{}, 32)}
	for _, raw := range []string{config.LocalURL, config.PublicURL} {
		u, err := url.Parse(raw)
		if err != nil || u.Scheme != "http" || u.Host == "" || u.User != nil || (u.Path != "" && u.Path != "/") || u.RawQuery != "" || u.ForceQuery || u.RawPath != "" || u.Fragment != "" {
			return nil, fmt.Errorf("expected an HTTP origin, got %q", raw)
		}
		s.hosts[strings.ToLower(u.Host)] = true
	}
	s.config.PublicURL = strings.TrimRight(config.PublicURL, "/")
	mux := http.NewServeMux()
	mux.HandleFunc("GET /healthz", func(w http.ResponseWriter, r *http.Request) {
		writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
	})
	if config.Desktop != nil {
		if config.Desktop.InstanceID == "" || config.Desktop.Quit == nil {
			return nil, errors.New("invalid desktop lifecycle configuration")
		}
		mux.HandleFunc("GET /api/desktop", s.desktopStatus)
		mux.HandleFunc("POST /api/desktop/quit", s.desktopQuit)
	}
	mux.HandleFunc("POST /api/sessions", s.create)
	mux.HandleFunc("GET /api/sessions/{id}", s.list)
	mux.HandleFunc("DELETE /api/sessions/{id}", s.close)
	mux.HandleFunc("POST /api/sessions/{id}/messages", s.submit)
	mux.HandleFunc("POST /api/requests", s.createRequestHTTP)
	mux.HandleFunc("GET /api/requests/{id}", s.requestStatusHTTP)
	mux.HandleFunc("GET /api/requests/{id}/result", s.readRequestHTTP)
	mux.HandleFunc("GET /api/requests/{id}/info", s.requestInfoHTTP)
	mux.HandleFunc("POST /api/requests/{id}/input", s.submitRequestHTTP)
	mux.HandleFunc("DELETE /api/requests/{id}", s.cancelRequestHTTP)
	mux.HandleFunc("GET /api/requests/{id}/wait", s.waitRequestHTTP)
	mux.HandleFunc("GET /", s.static)
	s.handler = mux
	return s, nil
}

// NewToken returns a 256-bit URL-safe capability.
func NewToken() (string, error) {
	b := make([]byte, 32)
	if _, err := rand.Read(b); err != nil {
		return "", err
	}
	return base64.RawURLEncoding.EncodeToString(b), nil
}

func (s *Server) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Cache-Control", "no-store")
	w.Header().Set("Referrer-Policy", "no-referrer")
	w.Header().Set("X-Content-Type-Options", "nosniff")
	w.Header().Set("Content-Security-Policy", "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'")
	if !s.hosts[strings.ToLower(r.Host)] {
		fail(w, http.StatusForbidden, "host is not configured")
		return
	}
	if origin := r.Header.Get("Origin"); origin != "" && origin != "http://"+r.Host {
		fail(w, http.StatusForbidden, "cross-origin requests are not allowed")
		return
	}
	select {
	case s.slots <- struct{}{}:
		defer func() { <-s.slots }()
	default:
		w.Header().Set("Retry-After", "1")
		fail(w, http.StatusTooManyRequests, "server is busy; try again")
		return
	}
	s.handler.ServeHTTP(w, r)
}

func (s *Server) owner(w http.ResponseWriter, r *http.Request) bool {
	if !validToken(r, s.config.OwnerToken) {
		fail(w, http.StatusUnauthorized, "computer capability required")
		return false
	}
	return true
}

func (s *Server) desktopOwner(w http.ResponseWriter, r *http.Request) bool {
	host, _, err := net.SplitHostPort(r.RemoteAddr)
	ip := net.ParseIP(host)
	local, _ := url.Parse(s.config.LocalURL)
	if err != nil || ip == nil || !ip.IsLoopback() || r.Host != local.Host {
		fail(w, http.StatusForbidden, "desktop control requires the local computer")
		return false
	}
	return s.owner(w, r)
}

func (s *Server) desktopStatus(w http.ResponseWriter, r *http.Request) {
	if !s.desktopOwner(w, r) {
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"desktop": true, "instanceId": s.config.Desktop.InstanceID, "publicUrl": s.config.PublicURL, "localOnly": s.config.PublicURL == s.config.LocalURL})
}

func (s *Server) desktopQuit(w http.ResponseWriter, r *http.Request) {
	if !s.desktopOwner(w, r) {
		return
	}
	var body struct{}
	if !readJSON(w, r, &body) {
		return
	}
	writeJSON(w, http.StatusAccepted, map[string]string{"state": "stopping"})
	s.config.Desktop.Quit()
}

func validToken(r *http.Request, expected string) bool {
	provided, ok := strings.CutPrefix(r.Header.Get("Authorization"), "Bearer ")
	return ok && subtle.ConstantTimeCompare([]byte(provided), []byte(expected)) == 1
}

func (s *Server) create(w http.ResponseWriter, r *http.Request) {
	if !s.owner(w, r) {
		return
	}
	var body struct{}
	if !readJSON(w, r, &body) {
		return
	}
	id, err := NewToken()
	if err != nil {
		fail(w, http.StatusInternalServerError, "could not generate session")
		return
	}
	key, err := NewToken()
	if err != nil {
		fail(w, http.StatusInternalServerError, "could not generate capability")
		return
	}
	fragment := url.Values{"session": {id}, "key": {key}}.Encode()
	sendURL := s.config.PublicURL + "/send#" + fragment
	png, err := qrcode.Encode(sendURL, qrcode.Medium, 280)
	if err != nil {
		fail(w, http.StatusInternalServerError, "could not generate QR code")
		return
	}
	s.mu.Lock()
	s.purgeLocked()
	if len(s.sessions) >= MaxSessions {
		s.mu.Unlock()
		fail(w, http.StatusConflict, "too many active sessions; close one first")
		return
	}
	expiresAt := s.now().Add(s.config.TTL)
	s.sessions[id] = &session{id: id, key: key, expiresAt: expiresAt, keys: make(map[string]int)}
	s.mu.Unlock()
	writeJSON(w, http.StatusCreated, map[string]any{"id": id, "expiresAt": expiresAt, "sendUrl": sendURL, "qrDataUrl": "data:image/png;base64," + base64.StdEncoding.EncodeToString(png), "maxTextBytes": MaxTextBytes})
}

func (s *Server) list(w http.ResponseWriter, r *http.Request) {
	if !s.owner(w, r) {
		return
	}
	after, err := strconv.ParseUint(r.URL.Query().Get("after"), 10, 64)
	if r.URL.Query().Get("after") == "" {
		after, err = 0, nil
	}
	if err != nil {
		fail(w, http.StatusBadRequest, "invalid cursor")
		return
	}
	s.mu.Lock()
	s.purgeLocked()
	item := s.sessions[r.PathValue("id")]
	if item == nil {
		s.mu.Unlock()
		fail(w, http.StatusGone, "session closed or expired")
		return
	}
	if after > uint64(len(item.messages)) {
		s.mu.Unlock()
		fail(w, http.StatusBadRequest, "cursor exceeds session history")
		return
	}
	messages := append([]Message{}, item.messages[after:]...)
	cursor, expiresAt := len(item.messages), item.expiresAt
	s.mu.Unlock()
	writeJSON(w, http.StatusOK, map[string]any{"id": r.PathValue("id"), "expiresAt": expiresAt, "messages": messages, "nextCursor": cursor})
}

func (s *Server) submit(w http.ResponseWriter, r *http.Request) {
	// Check capabilities before parsing a potentially large request body.
	s.mu.Lock()
	s.purgeLocked()
	item := s.sessions[r.PathValue("id")]
	if item == nil {
		s.mu.Unlock()
		fail(w, http.StatusGone, "session closed or expired")
		return
	}
	key := item.key
	s.mu.Unlock()
	if !validToken(r, key) {
		fail(w, http.StatusUnauthorized, "send capability required")
		return
	}
	var body struct {
		Key  string `json:"idempotencyKey"`
		Text string `json:"text"`
	}
	if !readJSON(w, r, &body) {
		return
	}
	if !validKey(body.Key) || strings.TrimSpace(body.Text) == "" {
		fail(w, http.StatusBadRequest, "nonblank text and an 8–128 character idempotencyKey are required")
		return
	}
	if len(body.Text) > MaxTextBytes {
		fail(w, http.StatusRequestEntityTooLarge, "text exceeds 64 KiB")
		return
	}
	id, err := NewToken()
	if err != nil {
		fail(w, http.StatusInternalServerError, "could not generate receipt")
		return
	}
	s.mu.Lock()
	s.purgeLocked()
	item = s.sessions[r.PathValue("id")]
	if item == nil {
		s.mu.Unlock()
		fail(w, http.StatusGone, "session closed or expired")
		return
	}
	if index, exists := item.keys[body.Key]; exists {
		message := item.messages[index]
		s.mu.Unlock()
		if message.Text != body.Text {
			fail(w, http.StatusConflict, "idempotencyKey was used with different text")
			return
		}
		writeJSON(w, http.StatusOK, message)
		return
	}
	if len(item.messages) >= MaxMessages || item.bytes+len(body.Text) > MaxSessionBytes {
		s.mu.Unlock()
		fail(w, http.StatusConflict, "session is full; start a new session on the computer")
		return
	}
	message := Message{ID: id, Sequence: uint64(len(item.messages) + 1), Text: body.Text, ReceivedAt: s.now()}
	item.keys[body.Key] = len(item.messages)
	item.messages = append(item.messages, message)
	item.bytes += len(body.Text)
	s.mu.Unlock()
	writeJSON(w, http.StatusCreated, message)
}

func validKey(key string) bool {
	if len(key) < 8 || len(key) > 128 {
		return false
	}
	for _, c := range key {
		if !((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') || c == '-' || c == '_') {
			return false
		}
	}
	return true
}

func (s *Server) close(w http.ResponseWriter, r *http.Request) {
	if !s.owner(w, r) {
		return
	}
	s.mu.Lock()
	delete(s.sessions, r.PathValue("id"))
	s.mu.Unlock()
	w.WriteHeader(http.StatusNoContent)
}

// PurgeExpired releases expired content; handlers also enforce expiry synchronously.
func (s *Server) PurgeExpired() {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.purgeLocked()
}

func (s *Server) purgeLocked() {
	for id, item := range s.sessions {
		if !s.now().Before(item.expiresAt) {
			delete(s.sessions, id)
		}
	}
	s.purgeRequestsLocked()
}

func readJSON(w http.ResponseWriter, r *http.Request, target any) bool {
	if strings.TrimSpace(strings.Split(r.Header.Get("Content-Type"), ";")[0]) != "application/json" {
		fail(w, http.StatusUnsupportedMediaType, "application/json required")
		return false
	}
	r.Body = http.MaxBytesReader(w, r.Body, maxJSONBytes)
	data, err := io.ReadAll(r.Body)
	if err != nil {
		var large *http.MaxBytesError
		if errors.As(err, &large) {
			fail(w, http.StatusRequestEntityTooLarge, "request body is too large")
		} else {
			fail(w, http.StatusBadRequest, "could not read request body")
		}
		return false
	}
	if !utf8.Valid(data) || !validJSONUnicode(data) {
		fail(w, http.StatusBadRequest, "UTF-8 JSON required")
		return false
	}
	decoder := json.NewDecoder(bytes.NewReader(data))
	decoder.DisallowUnknownFields()
	if decoder.Decode(target) != nil || decoder.Decode(new(any)) != io.EOF {
		fail(w, http.StatusBadRequest, "invalid JSON object")
		return false
	}
	return true
}

// encoding/json replaces unpaired escaped surrogates with U+FFFD. Reject them
// before decoding so accepted input is never silently repaired or truncated.
func validJSONUnicode(data []byte) bool {
	for i := 0; i < len(data); i++ {
		if data[i] != '\\' {
			continue
		}
		i++
		if i >= len(data) {
			return false
		}
		if data[i] != 'u' {
			continue
		}
		if i+4 >= len(data) {
			return false
		}
		value, err := strconv.ParseUint(string(data[i+1:i+5]), 16, 16)
		if err != nil {
			return false
		}
		i += 4
		if value >= 0xD800 && value <= 0xDBFF {
			if i+6 >= len(data) || data[i+1] != '\\' || data[i+2] != 'u' {
				return false
			}
			low, err := strconv.ParseUint(string(data[i+3:i+7]), 16, 16)
			if err != nil || low < 0xDC00 || low > 0xDFFF {
				return false
			}
			i += 6
		} else if value >= 0xDC00 && value <= 0xDFFF {
			return false
		}
	}
	return true
}

func (s *Server) static(w http.ResponseWriter, r *http.Request) {
	if strings.HasPrefix(r.URL.Path, "/brand/") {
		file := strings.TrimPrefix(r.URL.Path, "/brand/")
		if strings.Contains(file, "/") || !strings.HasSuffix(file, ".svg") {
			http.NotFound(w, r)
			return
		}
		data, err := brand.Assets.ReadFile(file)
		if err != nil {
			http.NotFound(w, r)
			return
		}
		w.Header().Set("Content-Type", "image/svg+xml")
		_, _ = w.Write(data)
		return
	}
	file := map[string]string{"/": "index.html", "/send": "index.html", "/app.js": "app.js", "/style.css": "style.css"}[r.URL.Path]
	if file == "" {
		http.NotFound(w, r)
		return
	}
	data, err := assets.ReadFile("web/" + file)
	if err != nil {
		fail(w, http.StatusInternalServerError, "asset unavailable")
		return
	}
	kinds := map[string]string{"index.html": "text/html; charset=utf-8", "app.js": "text/javascript; charset=utf-8", "style.css": "text/css; charset=utf-8"}
	w.Header().Set("Content-Type", kinds[file])
	w.WriteHeader(http.StatusOK)
	_, _ = w.Write(data)
}

func writeJSON(w http.ResponseWriter, status int, value any) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(value)
}

func fail(w http.ResponseWriter, status int, message string) {
	code := "invalid_argument"
	switch status {
	case http.StatusUnauthorized, http.StatusForbidden:
		code = "unauthorized"
	case http.StatusNotFound, http.StatusGone:
		code = "gone"
	case http.StatusConflict:
		code = "conflict"
	case http.StatusTooManyRequests:
		code = "capacity"
	case http.StatusInternalServerError:
		code = "internal"
	}
	writeJSON(w, status, map[string]string{"error": message, "code": code})
}
