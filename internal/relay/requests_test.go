package relay

import (
	"context"
	"net/http"
	"net/http/httptest"
	"net/url"
	"strings"
	"sync"
	"testing"
	"time"
)

// The context is a public wait dependency. Observing Done synchronizes the test
// with an admitted wait without inspecting the server's private semaphore.
type observedWaitContext struct {
	context.Context
	entered chan struct{}
	once    sync.Once
}

func (c *observedWaitContext) Done() <-chan struct{} {
	c.once.Do(func() { close(c.entered) })
	return c.Context.Done()
}

func startHTTPWait(t *testing.T, s *Server, created RequestCreated) (<-chan *httptest.ResponseRecorder, context.CancelFunc) {
	t.Helper()
	base, cancel := context.WithCancel(context.Background())
	observed := &observedWaitContext{Context: base, entered: make(chan struct{})}
	r := httptest.NewRequest(http.MethodGet, testOrigin+"/api/requests/"+created.Request.RequestID+"/wait?timeoutMs=10000", nil).WithContext(observed)
	r.Header.Set("Authorization", "Bearer "+created.ReaderToken)
	result := make(chan *httptest.ResponseRecorder, 1)
	go func() { w := httptest.NewRecorder(); s.ServeHTTP(w, r); result <- w }()
	t.Cleanup(cancel)
	select {
	case <-observed.entered:
	case w := <-result:
		cancel()
		t.Fatalf("wait ended before admission: %d %s", w.Code, w.Body)
	case <-time.After(3 * time.Second):
		cancel()
		t.Fatal("wait did not reach its context select")
	}
	return result, cancel
}

func receiveHTTPWait(t *testing.T, result <-chan *httptest.ResponseRecorder) *httptest.ResponseRecorder {
	t.Helper()
	select {
	case w := <-result:
		return w
	case <-time.After(3 * time.Second):
		t.Fatal("wait did not wake after its event")
		return nil
	}
}

func TestRequestWaitAdmissionLeavesOrdinaryTransferAvailable(t *testing.T) {
	s := testServer(t)
	created, _ := createCollection(t, s, "wait-admission")
	var waits []<-chan *httptest.ResponseRecorder
	for range 8 {
		result, _ := startHTTPWait(t, s, created)
		waits = append(waits, result)
	}
	w := request(s, http.MethodGet, "/api/requests/"+created.Request.RequestID+"/wait?timeoutMs=10000", created.ReaderToken, "", nil, nil)
	requireStatus(t, w, http.StatusTooManyRequests)
	if decode[map[string]any](t, w)["code"] != "capacity" {
		t.Fatal("ninth wait needs a capacity error")
	}
	ordinary := createSession(t, s)
	requireStatus(t, submitText(t, s, ordinary, "while-waits-open", "ordinary input remains available"), http.StatusCreated)
	if got := readInbox(t, s, ordinary, 0); len(got.Messages) != 1 {
		t.Fatal("waits starved ordinary transfer")
	}
	requireStatus(t, request(s, http.MethodDelete, "/api/requests/"+created.Request.RequestID, created.ReaderToken, "", nil, nil), http.StatusOK)
	for _, result := range waits {
		w = receiveHTTPWait(t, result)
		requireStatus(t, w, http.StatusOK)
		if got := decode[RequestWaitResult](t, w); got.TimedOut || got.Request.State != "canceled" {
			t.Fatalf("cancel did not wake wait: %+v", got)
		}
	}
	next, _ := createCollection(t, s, "after-waits")
	w = request(s, http.MethodGet, "/api/requests/"+next.Request.RequestID+"/wait?timeoutMs=1", next.ReaderToken, "", nil, nil)
	requireStatus(t, w, http.StatusOK)
}

func TestRequestWaitWakesOnDeliveryAndActiveContextInterruption(t *testing.T) {
	s := testServer(t)
	a, sender := createCollection(t, s, "arrival")
	result, _ := startHTTPWait(t, s, a)
	w := request(s, http.MethodPost, "/api/requests/"+a.Request.RequestID+"/input", sender, "application/json", jsonBody(t, map[string]string{"idempotencyKey": "wake-on-arrival", "text": "feedback"}), nil)
	requireStatus(t, w, http.StatusCreated)
	w = receiveHTTPWait(t, result)
	requireStatus(t, w, http.StatusOK)
	if got := decode[RequestWaitResult](t, w); got.TimedOut || got.Request.State != "received" {
		t.Fatalf("delivery did not wake wait: %+v", got)
	}
	b, _ := createCollection(t, s, "interrupt")
	result, cancel := startHTTPWait(t, s, b)
	cancel()
	w = receiveHTTPWait(t, result)
	requireStatus(t, w, http.StatusRequestTimeout)
	if decode[map[string]any](t, w)["code"] != "wait_canceled" {
		t.Fatal("active context interruption lost error code")
	}
	w = request(s, http.MethodGet, "/api/requests/"+b.Request.RequestID, b.ReaderToken, "", nil, nil)
	requireStatus(t, w, http.StatusOK)
	if decode[RequestSnapshot](t, w).State != "pending" {
		t.Fatal("interrupting an active wait canceled the request")
	}
}

func TestRequestWaitObservesExpiryWithoutBackgroundCleanup(t *testing.T) {
	s := testServer(t)
	w := request(s, http.MethodPost, "/api/requests", testOwner, "application/json", jsonBody(t, CreateRequestInput{Prompt: "short-lived input", TTLSeconds: 1}), nil)
	requireStatus(t, w, http.StatusCreated)
	created := decode[RequestCreated](t, w)
	w = request(s, http.MethodGet, "/api/requests/"+created.Request.RequestID+"/wait?timeoutMs=10000", created.ReaderToken, "", nil, nil)
	requireStatus(t, w, http.StatusOK)
	if got := decode[RequestWaitResult](t, w); got.TimedOut || got.Request.State != "expired" {
		t.Fatalf("wait must wake at request expiry: %+v", got)
	}
}

func TestRequestRetentionCapacityIsBoundedAndReclaimed(t *testing.T) {
	s := testServer(t)
	now := time.Date(2026, 10, 29, 11, 0, 0, 0, time.UTC)
	s.now = func() time.Time { return now }
	var first RequestCreated
	for i := 0; i < 64; i++ {
		created, _ := createCollection(t, s, "capacity")
		if i == 0 {
			first = created
		}
	}
	body := jsonBody(t, CreateRequestInput{Prompt: "one too many"})
	requireStatus(t, request(s, http.MethodPost, "/api/requests", testOwner, "application/json", body, nil), http.StatusTooManyRequests)
	requireStatus(t, request(s, http.MethodDelete, "/api/requests/"+first.Request.RequestID, first.ReaderToken, "", nil, nil), http.StatusOK)
	// Terminal metadata remains counted until its short retention window ends.
	requireStatus(t, request(s, http.MethodPost, "/api/requests", testOwner, "application/json", body, nil), http.StatusTooManyRequests)
	now = now.Add(2 * time.Minute)
	s.PurgeExpired()
	requireStatus(t, request(s, http.MethodPost, "/api/requests", testOwner, "application/json", body, nil), http.StatusCreated)
}

func TestRequestConcurrentRetriesKeepOneStableInput(t *testing.T) {
	s := testServer(t)
	created, sender := createCollection(t, s, "concurrent")
	body := jsonBody(t, map[string]string{"idempotencyKey": "same-attempt", "text": "one input"})
	const workers = 24
	start := make(chan struct{})
	results := make(chan *httptest.ResponseRecorder, workers)
	var group sync.WaitGroup
	for range workers {
		group.Add(1)
		go func() {
			defer group.Done()
			<-start
			results <- request(s, http.MethodPost, "/api/requests/"+created.Request.RequestID+"/input", sender, "application/json", body, nil)
		}()
	}
	close(start)
	group.Wait()
	close(results)
	var id any
	count := 0
	for w := range results {
		if w.Code == http.StatusCreated {
			count++
		} else {
			requireStatus(t, w, http.StatusOK)
		}
		receipt := decode[map[string]any](t, w)
		if id == nil {
			id = receipt["id"]
		} else if id != receipt["id"] {
			t.Fatal("concurrent retries changed receipt ID")
		}
	}
	if count != 1 {
		t.Fatalf("created %d inputs, want one", count)
	}
	read, err := s.ReadRequest(created.Request.RequestID, created.ReaderToken)
	if err != nil || read.Input == nil || read.Input.ID != id {
		t.Fatalf("public read disagrees with delivery receipt: %+v %v", read, err)
	}
	read.Input.Text = "consumer must not mutate stored input"
	again, err := s.ReadRequest(created.Request.RequestID, created.ReaderToken)
	if err != nil || again.Input == nil || again.Input.Text != "one input" {
		t.Fatal("public result aliased internal mutable input")
	}
}

func TestRequestRequiresBearerAuthorizationScheme(t *testing.T) {
	s := testServer(t)
	created, _ := createCollection(t, s, "authorization-format")
	r := httptest.NewRequest(http.MethodGet, testOrigin+"/api/requests/"+created.Request.RequestID, nil)
	r.Header.Set("Authorization", created.ReaderToken)
	w := httptest.NewRecorder()
	s.ServeHTTP(w, r)
	requireStatus(t, w, http.StatusUnauthorized)
}

func TestRequestWaitTimeoutAndInterruptionDoNotCancel(t *testing.T) {
	s := testServer(t)
	created, sender := createCollection(t, s, "waiting")
	path := "/api/requests/" + created.Request.RequestID
	w := request(s, http.MethodGet, path+"/wait?timeoutMs=20", created.ReaderToken, "", nil, nil)
	requireStatus(t, w, http.StatusOK)
	if result := decode[RequestWaitResult](t, w); !result.TimedOut || result.Request.State != "pending" {
		t.Fatalf("wait timeout must preserve pending: %+v", result)
	}
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	r := httptest.NewRequest(http.MethodGet, testOrigin+path+"/wait?timeoutMs=10000", nil).WithContext(ctx)
	r.Header.Set("Authorization", "Bearer "+created.ReaderToken)
	w = httptest.NewRecorder()
	s.ServeHTTP(w, r)
	requireStatus(t, w, http.StatusRequestTimeout)
	if decode[map[string]any](t, w)["code"] != "wait_canceled" {
		t.Fatal("context interruption needs a stable error code")
	}
	w = request(s, http.MethodGet, path, created.ReaderToken, "", nil, nil)
	requireStatus(t, w, http.StatusOK)
	if decode[RequestSnapshot](t, w).State != "pending" {
		t.Fatal("interrupting a wait canceled the request")
	}
	for _, timeout := range []string{"-1", "10001", "nope"} {
		w = request(s, http.MethodGet, path+"/wait?timeoutMs="+timeout, created.ReaderToken, "", nil, nil)
		requireStatus(t, w, http.StatusBadRequest)
		if decode[map[string]any](t, w)["code"] != "invalid_argument" {
			t.Fatal("invalid wait duration needs a stable code")
		}
	}
	w = request(s, http.MethodPost, path+"/input", sender, "application/json", jsonBody(t, map[string]string{"idempotencyKey": "after-interrupt", "text": "still accepted"}), nil)
	requireStatus(t, w, http.StatusCreated)
	w = request(s, http.MethodGet, path+"/wait?timeoutMs=10000", created.ReaderToken, "", nil, nil)
	requireStatus(t, w, http.StatusOK)
	if result := decode[RequestWaitResult](t, w); result.TimedOut || result.Request.State != "received" {
		t.Fatalf("received wait did not return immediately: %+v", result)
	}
}

func TestRequestRejectsInvalidUnicodeAndHonorsTextByteLimit(t *testing.T) {
	s := testServer(t)
	w := request(s, http.MethodPost, "/api/requests", testOwner, "application/json", []byte(`{"taskId":"unicode","prompt":"\ud800"}`), nil)
	requireStatus(t, w, http.StatusBadRequest)
	if decode[map[string]any](t, w)["code"] != "invalid_argument" {
		t.Fatal("missing invalid_argument code")
	}
	for _, input := range []CreateRequestInput{
		{Prompt: " "}, {Prompt: strings.Repeat("x", 1025)}, {Prompt: "ok", TaskID: strings.Repeat("界", 43)},
		{Prompt: "ok", TTLSeconds: -1}, {Prompt: "ok", TTLSeconds: 86401}, {Prompt: "ok", MaxTextBytes: -1}, {Prompt: "ok", MaxTextBytes: 16385},
	} {
		w = request(s, http.MethodPost, "/api/requests", testOwner, "application/json", jsonBody(t, input), nil)
		requireStatus(t, w, http.StatusBadRequest)
	}
	w = request(s, http.MethodPost, "/api/requests", testOwner, "application/json", jsonBody(t, CreateRequestInput{Prompt: "valid Unicode\uFFFD", MaxTextBytes: 4}), nil)
	requireStatus(t, w, http.StatusCreated)
	created := decode[RequestCreated](t, w)
	u, _ := url.Parse(created.SendURL)
	fragment, _ := url.ParseQuery(u.Fragment)
	path, sender := "/api/requests/"+created.Request.RequestID, fragment.Get("key")
	for _, body := range [][]byte{
		[]byte(`{"idempotencyKey":"valid-key","text":"\udc00"}`),
		[]byte(`{"idempotencyKey":"valid-key","text":"\ud800x"}`),
		[]byte(`{"idempotencyKey":"valid-key","text":"ok","extra":1}`),
		jsonBody(t, map[string]string{"idempotencyKey": "valid-key", "text": " \t\n"}),
	} {
		w = request(s, http.MethodPost, path+"/input", sender, "application/json", body, nil)
		requireStatus(t, w, http.StatusBadRequest)
	}
	w = request(s, http.MethodPost, path+"/input", sender, "application/json", jsonBody(t, map[string]string{"idempotencyKey": "oversized-key", "text": "界界"}), nil)
	requireStatus(t, w, http.StatusRequestEntityTooLarge)
	w = request(s, http.MethodGet, path+"/result", created.ReaderToken, "", nil, nil)
	requireStatus(t, w, http.StatusOK)
	if result := decode[RequestResult](t, w); result.Request.State != "pending" || result.Input != nil {
		t.Fatal("rejected input changed request or was silently truncated")
	}
	w = request(s, http.MethodPost, path+"/input", sender, "application/json", []byte(`{"idempotencyKey":"unicode-pair","text":"\ud83d\udc4b"}`), nil)
	requireStatus(t, w, http.StatusCreated)
	w = request(s, http.MethodGet, path+"/result", created.ReaderToken, "", nil, nil)
	requireStatus(t, w, http.StatusOK)
	if result := decode[RequestResult](t, w); result.Input == nil || result.Input.Text != "👋" {
		t.Fatal("valid surrogate pair must decode without truncation")
	}
}

func TestRequestCancellationAndExpiryRemoveInput(t *testing.T) {
	s := testServer(t)
	now := time.Date(2026, 10, 29, 10, 0, 0, 0, time.UTC)
	s.now = func() time.Time { return now }
	a, senderA := createCollection(t, s, "cancel-A")
	b, senderB := createCollection(t, s, "expire-B")
	pathA, pathB := "/api/requests/"+a.Request.RequestID, "/api/requests/"+b.Request.RequestID
	body := jsonBody(t, map[string]string{"idempotencyKey": "submitted-input", "text": "erase this feedback"})
	for _, item := range []struct{ path, token string }{{pathA, senderA}, {pathB, senderB}} {
		requireStatus(t, request(s, http.MethodPost, item.path+"/input", item.token, "application/json", body, nil), http.StatusCreated)
	}
	requireStatus(t, request(s, http.MethodDelete, pathA, senderA, "", nil, nil), http.StatusUnauthorized)
	w := request(s, http.MethodDelete, pathA, a.ReaderToken, "", nil, nil)
	requireStatus(t, w, http.StatusOK)
	canceled := decode[RequestSnapshot](t, w)
	if canceled.State != "canceled" {
		t.Fatalf("cancel did not change state: %+v", canceled)
	}
	w = request(s, http.MethodDelete, pathA, a.ReaderToken, "", nil, nil)
	requireStatus(t, w, http.StatusOK)
	if decode[RequestSnapshot](t, w) != canceled {
		t.Fatal("repeated cancellation changed metadata")
	}
	w = request(s, http.MethodGet, pathA+"/result", a.ReaderToken, "", nil, nil)
	requireStatus(t, w, http.StatusOK)
	if result := decode[RequestResult](t, w); result.Input != nil || result.Request.State != "canceled" {
		t.Fatalf("cancellation retained text: %+v", result)
	}
	requireStatus(t, request(s, http.MethodGet, pathA+"/info", senderA, "", nil, nil), http.StatusGone)
	requireStatus(t, request(s, http.MethodPost, pathA+"/input", senderA, "application/json", body, nil), http.StatusGone)
	now = b.Request.ExpiresAt
	s.PurgeExpired()
	w = request(s, http.MethodGet, pathB+"/result", b.ReaderToken, "", nil, nil)
	requireStatus(t, w, http.StatusOK)
	if result := decode[RequestResult](t, w); result.Input != nil || result.Request.State != "expired" {
		t.Fatalf("expiry retained text: %+v", result)
	}
	requireStatus(t, request(s, http.MethodGet, pathB+"/info", senderB, "", nil, nil), http.StatusGone)
	requireStatus(t, request(s, http.MethodPost, pathB+"/input", senderB, "application/json", body, nil), http.StatusGone)
	now = now.Add(2 * time.Minute)
	s.PurgeExpired()
	for _, item := range []struct{ path, reader string }{{pathA, a.ReaderToken}, {pathB, b.ReaderToken}, {"/api/requests/unknown", a.ReaderToken}} {
		w = request(s, http.MethodGet, item.path+"/result", item.reader, "", nil, nil)
		requireStatus(t, w, http.StatusGone)
		if decode[map[string]any](t, w)["code"] != "gone" {
			t.Fatal("missing gone error code")
		}
	}
}

func createCollection(t testing.TB, s *Server, label string) (RequestCreated, string) {
	t.Helper()
	w := request(s, http.MethodPost, "/api/requests", testOwner, "application/json", jsonBody(t, CreateRequestInput{TaskID: label, Prompt: "Send phone feedback"}), nil)
	requireStatus(t, w, http.StatusCreated)
	created := decode[RequestCreated](t, w)
	u, err := url.Parse(created.SendURL)
	if err != nil {
		t.Fatal(err)
	}
	fragment, err := url.ParseQuery(u.Fragment)
	if err != nil {
		t.Fatal(err)
	}
	return created, fragment.Get("key")
}

func TestRequestDeliveryIsScopedAndReadsAreRepeatable(t *testing.T) {
	s := testServer(t)
	a, senderA := createCollection(t, s, "same-label")
	b, senderB := createCollection(t, s, "same-label")
	path := "/api/requests/" + a.Request.RequestID
	text := " \tPhone feedback\n中文 👋 <script>data</script>\r\n "
	body := jsonBody(t, map[string]string{"idempotencyKey": "feedback-one", "text": text})
	w := request(s, http.MethodGet, path+"/info", senderA, "", nil, nil)
	requireStatus(t, w, http.StatusOK)
	if decode[RequestSnapshot](t, w).Prompt != "Send phone feedback" || strings.Contains(w.Body.String(), "readerToken") {
		t.Fatalf("sender info leaks capabilities or omits prompt: %s", w.Body)
	}
	w = request(s, http.MethodPost, path+"/input", senderA, "application/json", body, nil)
	requireStatus(t, w, http.StatusCreated)
	receipt := decode[map[string]any](t, w)
	if receipt["id"] == "" || receipt["requestId"] != a.Request.RequestID || receipt["state"] != "received" || receipt["text"] != nil {
		t.Fatalf("invalid metadata-only receipt: %s", w.Body)
	}
	w = request(s, http.MethodPost, path+"/input", senderA, "application/json", body, nil)
	requireStatus(t, w, http.StatusOK)
	if decode[map[string]any](t, w)["id"] != receipt["id"] {
		t.Fatal("retry changed stable receipt ID")
	}
	for _, delivery := range []map[string]string{{"idempotencyKey": "feedback-one", "text": "changed"}, {"idempotencyKey": "feedback-two", "text": text}} {
		w = request(s, http.MethodPost, path+"/input", senderA, "application/json", jsonBody(t, delivery), nil)
		requireStatus(t, w, http.StatusConflict)
		if decode[map[string]any](t, w)["code"] != "conflict" {
			t.Fatal("missing conflict code")
		}
	}
	w = request(s, http.MethodGet, path, a.ReaderToken, "", nil, nil)
	requireStatus(t, w, http.StatusOK)
	if decode[RequestSnapshot](t, w).State != "received" || strings.Contains(w.Body.String(), "Phone feedback") {
		t.Fatalf("status includes input or wrong state: %s", w.Body)
	}
	var original RequestInput
	for i := 0; i < 2; i++ {
		w = request(s, http.MethodGet, path+"/result", a.ReaderToken, "", nil, nil)
		requireStatus(t, w, http.StatusOK)
		result := decode[RequestResult](t, w)
		if result.Input == nil || result.Input.Text != text || result.Input.Trust != "untrusted_user_input" || result.Input.ID != receipt["id"] {
			t.Fatalf("lost exact untrusted input: %s", w.Body)
		}
		if i == 0 {
			original = *result.Input
		} else if original != *result.Input {
			t.Fatal("repeat reads must return identical input and metadata")
		}
	}
	for _, token := range []string{senderA, senderB, b.ReaderToken, testOwner, "same-label", ""} {
		w = request(s, http.MethodGet, path+"/result", token, "", nil, nil)
		requireStatus(t, w, http.StatusUnauthorized)
	}
	w = request(s, http.MethodPost, "/api/requests/"+b.Request.RequestID+"/input", senderA, "application/json", body, nil)
	requireStatus(t, w, http.StatusUnauthorized)
	w = request(s, http.MethodGet, "/api/requests/"+b.Request.RequestID+"/result", b.ReaderToken, "", nil, nil)
	requireStatus(t, w, http.StatusOK)
	if result := decode[RequestResult](t, w); result.Input != nil || result.Request.State != "pending" {
		t.Fatalf("request A contaminated request B: %+v", result)
	}
}

func TestRequestCreateSeparatesCapabilitiesAndMetadata(t *testing.T) {
	s := testServer(t)
	body := jsonBody(t, map[string]any{"taskId": "review-A", "prompt": "Send the issue shown on your phone", "ttlSeconds": 120, "maxTextBytes": 2048})
	w := request(s, http.MethodPost, "/api/requests", testOwner, "application/json", body, nil)
	requireStatus(t, w, http.StatusCreated)
	got := decode[struct {
		Request struct {
			RequestID    string `json:"requestId"`
			TaskID       string `json:"taskId"`
			Prompt       string `json:"prompt"`
			State        string `json:"state"`
			MaxTextBytes int    `json:"maxTextBytes"`
		} `json:"request"`
		ReaderToken string `json:"readerToken"`
		SendURL     string `json:"sendUrl"`
		QRDataURL   string `json:"qrDataUrl"`
	}](t, w)
	u, err := url.Parse(got.SendURL)
	if err != nil {
		t.Fatal(err)
	}
	fragment, err := url.ParseQuery(u.Fragment)
	if err != nil {
		t.Fatal(err)
	}
	sender := fragment.Get("key")
	if got.Request.RequestID == "" || fragment.Get("request") != got.Request.RequestID || u.Scheme+"://"+u.Host != testPublic || u.Path != "/send" || u.RawQuery != "" {
		t.Fatalf("invalid request invitation: %s", w.Body)
	}
	if got.Request.TaskID != "review-A" || got.Request.Prompt != "Send the issue shown on your phone" || got.Request.State != "pending" || got.Request.MaxTextBytes != 2048 {
		t.Fatalf("request metadata mismatch: %s", w.Body)
	}
	if sender == "" || got.ReaderToken == "" || sender == got.ReaderToken || sender == testOwner || got.ReaderToken == testOwner || strings.Contains(w.Body.String(), testOwner) || !strings.HasPrefix(got.QRDataURL, "data:image/png;base64,") {
		t.Fatalf("request capabilities are not isolated: %s", w.Body)
	}
	for _, token := range []string{"", sender, got.ReaderToken} {
		denied := request(s, http.MethodPost, "/api/requests", token, "application/json", body, nil)
		requireStatus(t, denied, http.StatusUnauthorized)
		if decode[map[string]any](t, denied)["code"] != "unauthorized" {
			t.Fatal("missing stable authorization error code")
		}
	}
	denied := request(s, http.MethodPost, "/api/requests", testOwner, "application/json", body, map[string]string{"Origin": "https://other.example"})
	requireStatus(t, denied, http.StatusForbidden)
}
