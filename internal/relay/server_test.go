package relay

import (
	"bytes"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"image/png"
	"net/http"
	"net/http/httptest"
	"net/url"
	"strings"
	"sync"
	"testing"
	"time"
)

const (
	testOwner  = "computer-capability-for-tests-0123456789"
	testOrigin = "http://127.0.0.1:8787"
	testPublic = "http://192.0.2.10:8787"
)

type invitation struct {
	ID           string    `json:"id"`
	ExpiresAt    time.Time `json:"expiresAt"`
	SendURL      string    `json:"sendUrl"`
	QRDataURL    string    `json:"qrDataUrl"`
	MaxTextBytes int       `json:"maxTextBytes"`
	key          string
}

type inbox struct {
	ID         string    `json:"id"`
	ExpiresAt  time.Time `json:"expiresAt"`
	Messages   []Message `json:"messages"`
	NextCursor uint64    `json:"nextCursor"`
}

func testServer(t testing.TB) *Server {
	t.Helper()
	s, err := New(Config{OwnerToken: testOwner, LocalURL: testOrigin, PublicURL: testPublic, TTL: 15 * time.Minute})
	if err != nil {
		t.Fatal(err)
	}
	return s
}

// request exercises HTTP parsing, routing, authorization, and response encoding
// without requiring a real listener or changing the host's network settings.
func request(s http.Handler, method, path, token, contentType string, body []byte, headers map[string]string) *httptest.ResponseRecorder {
	r := httptest.NewRequest(method, testOrigin+path, bytes.NewReader(body))
	if token != "" {
		r.Header.Set("Authorization", "Bearer "+token)
	}
	if contentType != "" {
		r.Header.Set("Content-Type", contentType)
	}
	for key, value := range headers {
		if key == "Host" {
			r.Host = value
		} else {
			r.Header.Set(key, value)
		}
	}
	w := httptest.NewRecorder()
	s.ServeHTTP(w, r)
	return w
}

func jsonBody(t testing.TB, value any) []byte {
	t.Helper()
	body, err := json.Marshal(value)
	if err != nil {
		t.Fatal(err)
	}
	return body
}

func requireStatus(t testing.TB, w *httptest.ResponseRecorder, status int) {
	t.Helper()
	if w.Code != status {
		t.Fatalf("status = %d, want %d; body: %s", w.Code, status, w.Body)
	}
}

func decode[T any](t testing.TB, w *httptest.ResponseRecorder) T {
	t.Helper()
	var value T
	if err := json.Unmarshal(w.Body.Bytes(), &value); err != nil {
		t.Fatalf("decode response: %v; body: %s", err, w.Body)
	}
	return value
}

func createSession(t testing.TB, s *Server) invitation {
	t.Helper()
	w := request(s, http.MethodPost, "/api/sessions", testOwner, "application/json", []byte("{}"), nil)
	requireStatus(t, w, http.StatusCreated)
	result := decode[invitation](t, w)
	u, err := url.Parse(result.SendURL)
	if err != nil {
		t.Fatal(err)
	}
	fragment, err := url.ParseQuery(u.Fragment)
	if err != nil {
		t.Fatal(err)
	}
	result.key = fragment.Get("key")
	if result.ID == "" || fragment.Get("session") != result.ID || result.key == "" {
		t.Fatalf("invalid invitation: %s", w.Body)
	}
	return result
}

func submitText(t testing.TB, s *Server, invite invitation, key, text string) *httptest.ResponseRecorder {
	t.Helper()
	body := jsonBody(t, map[string]string{"idempotencyKey": key, "text": text})
	return request(s, http.MethodPost, "/api/sessions/"+invite.ID+"/messages", invite.key, "application/json", body, nil)
}

func readInbox(t testing.TB, s *Server, invite invitation, after uint64) inbox {
	t.Helper()
	w := request(s, http.MethodGet, fmt.Sprintf("/api/sessions/%s?after=%d", invite.ID, after), testOwner, "", nil, nil)
	requireStatus(t, w, http.StatusOK)
	return decode[inbox](t, w)
}

func TestSessionTextRoundTrip(t *testing.T) {
	s := testServer(t)
	invite := createSession(t, s)
	u, err := url.Parse(invite.SendURL)
	if err != nil {
		t.Fatal(err)
	}
	if u.Scheme+"://"+u.Host != testPublic || u.Path != "/send" || u.RawQuery != "" {
		t.Fatalf("invitation must use the advertised phone origin and fragment-only capabilities: %s", invite.SendURL)
	}
	if strings.Contains(invite.SendURL, testOwner) || invite.key == testOwner || invite.key == invite.ID {
		t.Fatal("phone invitation must have its own capability")
	}
	if invite.MaxTextBytes != MaxTextBytes || !invite.ExpiresAt.After(time.Now()) {
		t.Fatalf("invalid session metadata: %+v", invite)
	}
	qr, err := base64.StdEncoding.DecodeString(strings.TrimPrefix(invite.QRDataURL, "data:image/png;base64,"))
	if err != nil {
		t.Fatalf("decode QR data: %v", err)
	}
	image, err := png.DecodeConfig(bytes.NewReader(qr))
	if err != nil || image.Width < 200 || image.Height != image.Width {
		t.Fatalf("invalid locally generated QR PNG: config=%+v, error=%v", image, err)
	}
	empty := readInbox(t, s, invite, 0)
	if empty.Messages == nil || len(empty.Messages) != 0 || empty.NextCursor != 0 {
		t.Fatalf("new session must have an empty array and cursor zero: %+v", empty)
	}
	text := "  first line\n\t中文 👋 café\r\n<script>alert('plain text')</script>\n  "
	w := submitText(t, s, invite, "request-one", text)
	requireStatus(t, w, http.StatusCreated)
	first := decode[Message](t, w)
	if first.ID == "" || first.Sequence != 1 || first.Text != text || first.ReceivedAt.IsZero() {
		t.Fatalf("receipt did not preserve text or metadata: %+v", first)
	}
	got := readInbox(t, s, invite, 0)
	if got.ID != invite.ID || !got.ExpiresAt.Equal(invite.ExpiresAt) || got.NextCursor != 1 || len(got.Messages) != 1 || got.Messages[0] != first {
		t.Fatalf("inbox does not match the receipt: %+v", got)
	}
}

func TestIdempotencyAndCursorRecovery(t *testing.T) {
	s := testServer(t)
	invite := createSession(t, s)
	first := submitText(t, s, invite, "retry-key-1", "original")
	requireStatus(t, first, http.StatusCreated)
	retry := submitText(t, s, invite, "retry-key-1", "original")
	requireStatus(t, retry, http.StatusOK)
	if decode[Message](t, first) != decode[Message](t, retry) {
		t.Fatal("a retry must return the original receipt, including ID and timestamp")
	}
	requireStatus(t, submitText(t, s, invite, "retry-key-1", "changed"), http.StatusConflict)
	requireStatus(t, submitText(t, s, invite, "retry-key-2", "received while computer was offline"), http.StatusCreated)
	requireStatus(t, submitText(t, s, invite, "retry-key-3", "another message"), http.StatusCreated)
	got := readInbox(t, s, invite, 1)
	if got.NextCursor != 3 || len(got.Messages) != 2 || got.Messages[0].Sequence != 2 || got.Messages[1].Sequence != 3 {
		t.Fatalf("cursor must replay all later messages in order: %+v", got)
	}
	replayed := readInbox(t, s, invite, 1)
	if replayed.NextCursor != got.NextCursor || len(replayed.Messages) != len(got.Messages) || replayed.Messages[0] != got.Messages[0] {
		t.Fatal("repeating a cursor query must not consume messages")
	}
	atEnd := readInbox(t, s, invite, 3)
	if len(atEnd.Messages) != 0 || atEnd.NextCursor != 3 {
		t.Fatalf("end cursor returned unexpected messages: %+v", atEnd)
	}
	for _, cursor := range []string{"-1", "text", "4", "18446744073709551616"} {
		t.Run("invalid_cursor_"+cursor, func(t *testing.T) {
			w := request(s, http.MethodGet, "/api/sessions/"+invite.ID+"?after="+cursor, testOwner, "", nil, nil)
			requireStatus(t, w, http.StatusBadRequest)
		})
	}
}

func TestCapabilitiesAreScoped(t *testing.T) {
	s := testServer(t)
	a, b := createSession(t, s), createSession(t, s)
	if a.ID == b.ID || a.key == b.key {
		t.Fatal("sessions must have independent IDs and capabilities")
	}
	body := jsonBody(t, map[string]string{"idempotencyKey": "scoped-key", "text": "private"})
	for _, tc := range []struct {
		name, method, path, token string
		body                      []byte
	}{
		{"anonymous_create", http.MethodPost, "/api/sessions", "", []byte("{}")},
		{"sender_create", http.MethodPost, "/api/sessions", a.key, []byte("{}")},
		{"sender_read", http.MethodGet, "/api/sessions/" + a.ID, a.key, nil},
		{"sender_close", http.MethodDelete, "/api/sessions/" + a.ID, a.key, nil},
		{"anonymous_read", http.MethodGet, "/api/sessions/" + a.ID, "", nil},
		{"other_session_send", http.MethodPost, "/api/sessions/" + b.ID + "/messages", a.key, body},
		{"owner_cannot_send", http.MethodPost, "/api/sessions/" + a.ID + "/messages", testOwner, body},
		{"query_token_not_authorization", http.MethodGet, "/api/sessions/" + a.ID + "?token=" + testOwner, "", nil},
	} {
		t.Run(tc.name, func(t *testing.T) {
			w := request(s, tc.method, tc.path, tc.token, "application/json", tc.body, nil)
			requireStatus(t, w, http.StatusUnauthorized)
		})
	}
	// An idempotency key belongs to a session, not to the entire server.
	requireStatus(t, submitText(t, s, a, "same-user-key", "first session"), http.StatusCreated)
	requireStatus(t, submitText(t, s, b, "same-user-key", "second session"), http.StatusCreated)
	if got := readInbox(t, s, b, 0); len(got.Messages) != 1 || got.Messages[0].Text != "second session" {
		t.Fatalf("messages leaked between sessions: %+v", got)
	}
}

func TestHostOriginAndSecurityHeaders(t *testing.T) {
	s := testServer(t)
	for _, tc := range []struct {
		name    string
		headers map[string]string
		status  int
	}{
		{"same_origin", map[string]string{"Origin": testOrigin}, http.StatusOK},
		{"phone_origin", map[string]string{"Host": "192.0.2.10:8787", "Origin": testPublic}, http.StatusOK},
		{"non_browser_client", nil, http.StatusOK},
		{"unconfigured_host", map[string]string{"Host": "attacker.example:8787"}, http.StatusForbidden},
		{"cross_origin", map[string]string{"Origin": "https://attacker.example"}, http.StatusForbidden},
		{"opaque_origin", map[string]string{"Origin": "null"}, http.StatusForbidden},
		{"wrong_port", map[string]string{"Host": "127.0.0.1:9999"}, http.StatusForbidden},
	} {
		t.Run(tc.name, func(t *testing.T) {
			w := request(s, http.MethodGet, "/healthz", "", "", nil, tc.headers)
			requireStatus(t, w, tc.status)
			for key, value := range map[string]string{"Cache-Control": "no-store", "Referrer-Policy": "no-referrer", "X-Content-Type-Options": "nosniff"} {
				if w.Header().Get(key) != value {
					t.Errorf("%s = %q, want %q", key, w.Header().Get(key), value)
				}
			}
			if !strings.Contains(w.Header().Get("Content-Security-Policy"), "frame-ancestors 'none'") || w.Header().Get("Access-Control-Allow-Origin") != "" {
				t.Fatal("response must prevent framing and must not grant cross-origin access")
			}
		})
	}
}

func TestCloseAndExpiryRevokeContent(t *testing.T) {
	s := testServer(t)
	now := time.Date(2026, 10, 28, 12, 0, 0, 0, time.UTC)
	s.now = func() time.Time { return now }
	a, b := createSession(t, s), createSession(t, s)
	requireStatus(t, submitText(t, s, a, "before-close", "temporary"), http.StatusCreated)
	requireStatus(t, request(s, http.MethodDelete, "/api/sessions/"+a.ID, testOwner, "", nil, nil), http.StatusNoContent)
	requireStatus(t, request(s, http.MethodGet, "/api/sessions/"+a.ID, testOwner, "", nil, nil), http.StatusGone)
	requireStatus(t, submitText(t, s, a, "after-close", "cannot return"), http.StatusGone)
	// Closing twice is safe and does not affect another active session.
	requireStatus(t, request(s, http.MethodDelete, "/api/sessions/"+a.ID, testOwner, "", nil, nil), http.StatusNoContent)
	requireStatus(t, submitText(t, s, b, "still-active", "independent"), http.StatusCreated)
	now = b.ExpiresAt
	requireStatus(t, submitText(t, s, b, "at-the-limit", "must expire exactly at deadline"), http.StatusGone)
	requireStatus(t, request(s, http.MethodGet, "/api/sessions/"+b.ID, testOwner, "", nil, nil), http.StatusGone)
	if len(s.sessions) != 0 {
		t.Fatal("closed and expired content must be released from the session map")
	}
	c := createSession(t, s)
	now = c.ExpiresAt
	s.PurgeExpired()
	if len(s.sessions) != 0 {
		t.Fatal("background cleanup entry point must release expired sessions even without a request")
	}
}

func TestRejectsMalformedAndOversizedInput(t *testing.T) {
	s := testServer(t)
	invite := createSession(t, s)
	path := "/api/sessions/" + invite.ID + "/messages"
	for _, tc := range []struct {
		name, contentType string
		body              []byte
		status            int
	}{
		{"wrong_type", "text/plain", []byte("hello"), http.StatusUnsupportedMediaType},
		{"missing_type", "", []byte("{}"), http.StatusUnsupportedMediaType},
		{"empty_body", "application/json", nil, http.StatusBadRequest},
		{"syntax", "application/json", []byte("{"), http.StatusBadRequest},
		{"array", "application/json", []byte("[]"), http.StatusBadRequest},
		{"null", "application/json", []byte("null"), http.StatusBadRequest},
		{"trailing_value", "application/json", []byte(`{"idempotencyKey":"valid-key","text":"hello"} {}`), http.StatusBadRequest},
		{"unknown_field", "application/json", []byte(`{"idempotencyKey":"valid-key","text":"hello","extra":true}`), http.StatusBadRequest},
		{"invalid_utf8", "application/json", append([]byte(`{"idempotencyKey":"valid-key","text":"`), 0xff, '"', '}'), http.StatusBadRequest},
		{"blank", "application/json", jsonBody(t, map[string]string{"idempotencyKey": "valid-key", "text": " \t\n\u2003"}), http.StatusBadRequest},
		{"missing_key", "application/json", []byte(`{"text":"hello"}`), http.StatusBadRequest},
		{"short_key", "application/json", []byte(`{"idempotencyKey":"short","text":"hello"}`), http.StatusBadRequest},
		{"unsafe_key", "application/json", []byte(`{"idempotencyKey":"path/key","text":"hello"}`), http.StatusBadRequest},
		{"long_key", "application/json", jsonBody(t, map[string]string{"idempotencyKey": strings.Repeat("x", 129), "text": "hello"}), http.StatusBadRequest},
		{"text_limit", "application/json", jsonBody(t, map[string]string{"idempotencyKey": "valid-key", "text": strings.Repeat("x", MaxTextBytes+1)}), http.StatusRequestEntityTooLarge},
		{"raw_body_limit", "application/json", bytes.Repeat([]byte(" "), maxJSONBytes+1), http.StatusRequestEntityTooLarge},
	} {
		t.Run(tc.name, func(t *testing.T) {
			w := request(s, http.MethodPost, path, invite.key, tc.contentType, tc.body, nil)
			requireStatus(t, w, tc.status)
		})
	}
	if got := readInbox(t, s, invite, 0); len(got.Messages) != 0 {
		t.Fatalf("invalid requests must not create messages: %+v", got)
	}
	// The byte limit applies to decoded UTF-8 text, not character count or JSON escapes.
	text := strings.Repeat("界", MaxTextBytes/3) + "x"
	if len(text) != MaxTextBytes {
		t.Fatal("invalid boundary fixture")
	}
	requireStatus(t, submitText(t, s, invite, "exact-byte-limit", text), http.StatusCreated)
	if got := readInbox(t, s, invite, 0); got.Messages[0].Text != text {
		t.Fatal("accepted boundary text changed during encoding")
	}
}

func TestSessionResourceLimits(t *testing.T) {
	t.Run("message_count", func(t *testing.T) {
		s := testServer(t)
		invite := createSession(t, s)
		for i := 0; i < MaxMessages; i++ {
			requireStatus(t, submitText(t, s, invite, fmt.Sprintf("message-%08d", i), "x"), http.StatusCreated)
		}
		requireStatus(t, submitText(t, s, invite, "one-too-many", "x"), http.StatusConflict)
		requireStatus(t, submitText(t, s, invite, "message-00000000", "x"), http.StatusOK)
		if got := readInbox(t, s, invite, 0); len(got.Messages) != MaxMessages || got.NextCursor != MaxMessages {
			t.Fatalf("message limit changed the accepted history: %+v", got)
		}
	})
	t.Run("text_bytes", func(t *testing.T) {
		s := testServer(t)
		invite := createSession(t, s)
		text := strings.Repeat("x", MaxTextBytes)
		for i := 0; i < MaxSessionBytes/MaxTextBytes; i++ {
			requireStatus(t, submitText(t, s, invite, fmt.Sprintf("payload-%08d", i), text), http.StatusCreated)
		}
		requireStatus(t, submitText(t, s, invite, "beyond-byte-limit", "x"), http.StatusConflict)
		requireStatus(t, submitText(t, s, invite, "payload-00000000", text), http.StatusOK)
	})
	t.Run("active_sessions", func(t *testing.T) {
		s := testServer(t)
		var first invitation
		for i := 0; i < MaxSessions; i++ {
			invite := createSession(t, s)
			if i == 0 {
				first = invite
			}
		}
		requireStatus(t, request(s, http.MethodPost, "/api/sessions", testOwner, "application/json", []byte("{}"), nil), http.StatusConflict)
		requireStatus(t, request(s, http.MethodDelete, "/api/sessions/"+first.ID, testOwner, "", nil, nil), http.StatusNoContent)
		createSession(t, s)
	})
}

func TestConcurrentRetriesProduceOneReceipt(t *testing.T) {
	s := testServer(t)
	invite := createSession(t, s)
	body := jsonBody(t, map[string]string{"idempotencyKey": "concurrent-retry", "text": "one logical send"})
	const workers = 24 // Keep below the documented 32-request admission limit.
	results := make(chan *httptest.ResponseRecorder, workers)
	start := make(chan struct{})
	var group sync.WaitGroup
	for range workers {
		group.Add(1)
		go func() {
			defer group.Done()
			<-start
			results <- request(s, http.MethodPost, "/api/sessions/"+invite.ID+"/messages", invite.key, "application/json", body, nil)
		}()
	}
	close(start)
	group.Wait()
	close(results)
	created := 0
	var original Message
	for result := range results {
		if result.Code == http.StatusCreated {
			created++
		} else {
			requireStatus(t, result, http.StatusOK)
		}
		message := decode[Message](t, result)
		if original.ID == "" {
			original = message
		} else if original != message {
			t.Fatal("concurrent retries returned different receipts")
		}
	}
	if created != 1 {
		t.Fatalf("created receipts = %d, want exactly one", created)
	}
	if got := readInbox(t, s, invite, 0); len(got.Messages) != 1 || got.Messages[0] != original || got.NextCursor != 1 {
		t.Fatalf("concurrent retries duplicated history: %+v", got)
	}
}

func TestConcurrentDistinctMessagesHaveContiguousCursors(t *testing.T) {
	s := testServer(t)
	invite := createSession(t, s)
	const workers = 24
	results := make(chan *httptest.ResponseRecorder, workers)
	start := make(chan struct{})
	var group sync.WaitGroup
	for i := range workers {
		body := jsonBody(t, map[string]string{"idempotencyKey": fmt.Sprintf("parallel-%08d", i), "text": fmt.Sprintf("message %d", i)})
		group.Add(1)
		go func() {
			defer group.Done()
			<-start
			results <- request(s, http.MethodPost, "/api/sessions/"+invite.ID+"/messages", invite.key, "application/json", body, nil)
		}()
	}
	close(start)
	group.Wait()
	close(results)
	for result := range results {
		requireStatus(t, result, http.StatusCreated)
	}
	got := readInbox(t, s, invite, 0)
	if len(got.Messages) != workers || got.NextCursor != workers {
		t.Fatalf("lost concurrent messages: count=%d, cursor=%d", len(got.Messages), got.NextCursor)
	}
	seen := make(map[string]bool)
	for i, message := range got.Messages {
		if message.Sequence != uint64(i+1) || seen[message.ID] {
			t.Fatalf("history has a gap or duplicate: %+v", message)
		}
		seen[message.ID] = true
	}
}

func TestNewRejectsUnsafeConfiguration(t *testing.T) {
	valid := Config{OwnerToken: testOwner, LocalURL: testOrigin, PublicURL: testPublic, TTL: time.Minute}
	for _, tc := range []struct {
		name string
		edit func(*Config)
	}{
		{"short_owner_capability", func(c *Config) { c.OwnerToken = "short" }},
		{"zero_ttl", func(c *Config) { c.TTL = 0 }},
		{"negative_ttl", func(c *Config) { c.TTL = -time.Second }},
		{"excessive_ttl", func(c *Config) { c.TTL = 25 * time.Hour }},
		{"empty_local_origin", func(c *Config) { c.LocalURL = "" }},
		{"userinfo", func(c *Config) { c.PublicURL = "http://user:password@192.0.2.10:8787" }},
		{"path", func(c *Config) { c.PublicURL += "/unexpected" }},
		{"query", func(c *Config) { c.PublicURL += "?token=unexpected" }},
		{"fragment", func(c *Config) { c.PublicURL += "#unexpected" }},
		{"unsupported_scheme", func(c *Config) { c.PublicURL = "file:///tmp/inbox" }},
	} {
		t.Run(tc.name, func(t *testing.T) {
			config := valid
			tc.edit(&config)
			if _, err := New(config); err == nil {
				t.Fatal("unsafe configuration was accepted")
			}
		})
	}
}

// BenchmarkListText measures the in-process HTTP handler (including request and
// JSON response allocations), not LAN throughput, browser rendering, or uploads.
// A stable inbox keeps every iteration on the successful path without bypassing
// production resource limits or benchmarking a full-session rejection.
func BenchmarkListText(b *testing.B) {
	for _, size := range []int{1024, MaxTextBytes} {
		b.Run(fmt.Sprintf("%d_bytes", size), func(b *testing.B) {
			s := testServer(b)
			invite := createSession(b, s)
			requireStatus(b, submitText(b, s, invite, "benchmark-text", strings.Repeat("x", size)), http.StatusCreated)
			path := "/api/sessions/" + invite.ID + "?after=0"
			b.SetBytes(int64(size))
			b.ReportAllocs()
			b.ResetTimer()
			for b.Loop() {
				result := request(s, http.MethodGet, path, testOwner, "", nil, nil)
				if result.Code != http.StatusOK {
					b.Fatalf("list failed: %d: %s", result.Code, result.Body)
				}
			}
		})
	}
}
