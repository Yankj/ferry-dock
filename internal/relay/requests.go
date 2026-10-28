package relay

import (
	"context"
	"crypto/subtle"
	"encoding/base64"
	"net/http"
	"net/url"
	"strconv"
	"strings"
	"time"
	"unicode/utf8"

	qrcode "github.com/skip2/go-qrcode"
)

const (
	MaxRequestTextBytes = 16 << 10
	MaxRequests         = 64
)

type CreateRequestInput struct {
	TaskID       string `json:"taskId"`
	Prompt       string `json:"prompt"`
	TTLSeconds   int    `json:"ttlSeconds"`
	MaxTextBytes int    `json:"maxTextBytes"`
}

type RequestSnapshot struct {
	RequestID    string    `json:"requestId"`
	TaskID       string    `json:"taskId"`
	Prompt       string    `json:"prompt"`
	State        string    `json:"state"`
	CreatedAt    time.Time `json:"createdAt"`
	ExpiresAt    time.Time `json:"expiresAt"`
	MaxTextBytes int       `json:"maxTextBytes"`
}

type RequestCreated struct {
	Request     RequestSnapshot `json:"request"`
	ReaderToken string          `json:"readerToken"`
	SendURL     string          `json:"sendUrl"`
	QRDataURL   string          `json:"qrDataUrl"`
}

type RequestInput struct {
	ID         string    `json:"id"`
	Text       string    `json:"text"`
	Trust      string    `json:"trust"`
	ReceivedAt time.Time `json:"receivedAt"`
}

type RequestResult struct {
	Request RequestSnapshot `json:"request"`
	Input   *RequestInput   `json:"input,omitempty"`
}

type RequestWaitResult struct {
	Request  RequestSnapshot `json:"request"`
	TimedOut bool            `json:"timedOut"`
}

type RequestError struct {
	Code    string `json:"code"`
	Message string `json:"error"`
}

func (e *RequestError) Error() string { return e.Message }

type requestRecord struct {
	snapshot    RequestSnapshot
	reader      string
	sender      string
	input       *RequestInput
	deliveryKey string
	terminalAt  time.Time
	changed     chan struct{}
}

// WaitRequest only waits for state. A timeout or interrupted context never
// cancels the underlying collection request. Call ReadRequest for input data.
func (s *Server) WaitRequest(ctx context.Context, id, reader string, timeout time.Duration) (RequestWaitResult, error) {
	if timeout < 0 || timeout > 10*time.Second {
		return RequestWaitResult{}, &RequestError{Code: "invalid_argument", Message: "wait timeout must be 0..10s"}
	}
	snapshot, err := s.RequestStatus(id, reader)
	if err != nil {
		return RequestWaitResult{}, err
	}
	if ctx.Err() != nil {
		return RequestWaitResult{}, &RequestError{Code: "wait_canceled", Message: "wait context was interrupted"}
	}
	if snapshot.State != "pending" {
		return RequestWaitResult{Request: snapshot}, nil
	}
	if timeout == 0 {
		return RequestWaitResult{Request: snapshot, TimedOut: true}, nil
	}
	select {
	case s.waitSlots <- struct{}{}:
		defer func() { <-s.waitSlots }()
	default:
		return RequestWaitResult{}, &RequestError{Code: "capacity", Message: "at most eight outstanding waits are allowed"}
	}
	deadline := time.NewTimer(timeout)
	defer deadline.Stop()
	for {
		s.mu.Lock()
		record, err := s.readerRequestLocked(id, reader)
		if err != nil {
			s.mu.Unlock()
			return RequestWaitResult{}, err
		}
		snapshot, changed, untilExpiry := record.snapshot, record.changed, record.snapshot.ExpiresAt.Sub(s.now())
		s.mu.Unlock()
		if snapshot.State != "pending" {
			return RequestWaitResult{Request: snapshot}, nil
		}
		expiry := time.NewTimer(max(untilExpiry, 0))
		select {
		case <-ctx.Done():
			expiry.Stop()
			return RequestWaitResult{}, &RequestError{Code: "wait_canceled", Message: "wait context was interrupted"}
		case <-changed:
			expiry.Stop()
		case <-expiry.C:
		case <-deadline.C:
			expiry.Stop()
			snapshot, err := s.RequestStatus(id, reader)
			if err != nil {
				return RequestWaitResult{}, err
			}
			return RequestWaitResult{Request: snapshot, TimedOut: snapshot.State == "pending"}, nil
		}
	}
}

func notifyRequestLocked(record *requestRecord) {
	close(record.changed)
	record.changed = make(chan struct{})
}

func (s *Server) waitRequestHTTP(w http.ResponseWriter, r *http.Request) {
	timeout := 10000
	if value := r.URL.Query().Get("timeoutMs"); value != "" {
		parsed, err := strconv.Atoi(value)
		if err != nil || parsed < 0 || parsed > 10000 {
			requestFailure(w, &RequestError{Code: "invalid_argument", Message: "timeoutMs must be 0..10000"})
			return
		}
		timeout = parsed
	}
	result, err := s.WaitRequest(r.Context(), r.PathValue("id"), requestToken(r), time.Duration(timeout)*time.Millisecond)
	if err != nil {
		requestFailure(w, err)
		return
	}
	writeJSON(w, http.StatusOK, result)
}

// CancelRequest revokes delivery and removes received text. Readers may still
// inspect terminal metadata until its bounded retention window ends.
func (s *Server) CancelRequest(id, reader string) (RequestSnapshot, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	record, err := s.readerRequestLocked(id, reader)
	if err != nil {
		return RequestSnapshot{}, err
	}
	if record.snapshot.State == "pending" || record.snapshot.State == "received" {
		record.snapshot.State = "canceled"
		record.input = nil
		record.deliveryKey = ""
		record.terminalAt = s.now()
		notifyRequestLocked(record)
	}
	return record.snapshot, nil
}

func (s *Server) purgeRequestsLocked() {
	now := s.now()
	for id, record := range s.requests {
		if (record.snapshot.State == "pending" || record.snapshot.State == "received") && !now.Before(record.snapshot.ExpiresAt) {
			record.snapshot.State = "expired"
			record.input = nil
			record.deliveryKey = ""
			record.terminalAt = record.snapshot.ExpiresAt
			notifyRequestLocked(record)
		}
		if !record.terminalAt.IsZero() && !now.Before(record.terminalAt.Add(2*time.Minute)) {
			delete(s.requests, id)
		}
	}
}

func (s *Server) cancelRequestHTTP(w http.ResponseWriter, r *http.Request) {
	snapshot, err := s.CancelRequest(r.PathValue("id"), requestToken(r))
	if err != nil {
		requestFailure(w, err)
		return
	}
	writeJSON(w, http.StatusOK, snapshot)
}

// RequestStatus returns metadata only. Request labels never grant authority.
func (s *Server) RequestStatus(id, reader string) (RequestSnapshot, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	record, err := s.readerRequestLocked(id, reader)
	if err != nil {
		return RequestSnapshot{}, err
	}
	return record.snapshot, nil
}

// ReadRequest is repeatable and does not acknowledge or consume input.
func (s *Server) ReadRequest(id, reader string) (RequestResult, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	record, err := s.readerRequestLocked(id, reader)
	if err != nil {
		return RequestResult{}, err
	}
	result := RequestResult{Request: record.snapshot}
	if record.input != nil {
		value := *record.input
		result.Input = &value
	}
	return result, nil
}

func (s *Server) readerRequestLocked(id, reader string) (*requestRecord, error) {
	s.purgeLocked()
	record := s.requests[id]
	if record == nil {
		return nil, &RequestError{Code: "gone", Message: "request is unknown or no longer retained"}
	}
	if subtle.ConstantTimeCompare([]byte(reader), []byte(record.reader)) != 1 {
		return nil, &RequestError{Code: "unauthorized", Message: "request reader capability required"}
	}
	return record, nil
}

func (s *Server) senderRequestLocked(id, sender string) (*requestRecord, error) {
	s.purgeLocked()
	record := s.requests[id]
	if record == nil || record.snapshot.State == "expired" || record.snapshot.State == "canceled" {
		return nil, &RequestError{Code: "gone", Message: "request closed or expired"}
	}
	if subtle.ConstantTimeCompare([]byte(sender), []byte(record.sender)) != 1 {
		return nil, &RequestError{Code: "unauthorized", Message: "request sender capability required"}
	}
	return record, nil
}

func requestToken(r *http.Request) string {
	value, ok := strings.CutPrefix(r.Header.Get("Authorization"), "Bearer ")
	if !ok {
		return ""
	}
	return value
}

func (s *Server) requestStatusHTTP(w http.ResponseWriter, r *http.Request) {
	value, err := s.RequestStatus(r.PathValue("id"), requestToken(r))
	if err != nil {
		requestFailure(w, err)
		return
	}
	writeJSON(w, http.StatusOK, value)
}

func (s *Server) readRequestHTTP(w http.ResponseWriter, r *http.Request) {
	value, err := s.ReadRequest(r.PathValue("id"), requestToken(r))
	if err != nil {
		requestFailure(w, err)
		return
	}
	writeJSON(w, http.StatusOK, value)
}

func (s *Server) requestInfoHTTP(w http.ResponseWriter, r *http.Request) {
	s.mu.Lock()
	record, err := s.senderRequestLocked(r.PathValue("id"), requestToken(r))
	var snapshot RequestSnapshot
	if err == nil {
		snapshot = record.snapshot
	}
	s.mu.Unlock()
	if err != nil {
		requestFailure(w, err)
		return
	}
	writeJSON(w, http.StatusOK, snapshot)
}

type requestReceipt struct {
	ID         string    `json:"id"`
	RequestID  string    `json:"requestId"`
	State      string    `json:"state"`
	ReceivedAt time.Time `json:"receivedAt"`
}

func (s *Server) submitRequestHTTP(w http.ResponseWriter, r *http.Request) {
	id, sender := r.PathValue("id"), requestToken(r)
	s.mu.Lock()
	_, err := s.senderRequestLocked(id, sender)
	s.mu.Unlock()
	if err != nil {
		requestFailure(w, err)
		return
	}
	var body struct {
		Key  string `json:"idempotencyKey"`
		Text string `json:"text"`
	}
	if !readJSON(w, r, &body) {
		return
	}
	if !validKey(body.Key) || !utf8.ValidString(body.Text) || strings.TrimSpace(body.Text) == "" {
		fail(w, http.StatusBadRequest, "nonblank valid Unicode text and an 8–128 character idempotencyKey are required")
		return
	}
	inputID, err := NewToken()
	if err != nil {
		requestFailure(w, &RequestError{Code: "internal", Message: "could not generate input receipt"})
		return
	}
	s.mu.Lock()
	record, err := s.senderRequestLocked(id, sender)
	if err != nil {
		s.mu.Unlock()
		requestFailure(w, err)
		return
	}
	if len(body.Text) > record.snapshot.MaxTextBytes {
		s.mu.Unlock()
		fail(w, http.StatusRequestEntityTooLarge, "text exceeds this request's byte limit")
		return
	}
	status := http.StatusCreated
	if record.input != nil {
		if record.deliveryKey != body.Key || record.input.Text != body.Text {
			s.mu.Unlock()
			requestFailure(w, &RequestError{Code: "conflict", Message: "this request already received another delivery"})
			return
		}
		status = http.StatusOK
	} else {
		record.input = &RequestInput{ID: inputID, Text: body.Text, Trust: "untrusted_user_input", ReceivedAt: s.now()}
		record.deliveryKey = body.Key
		record.snapshot.State = "received"
		notifyRequestLocked(record)
	}
	receipt := requestReceipt{ID: record.input.ID, RequestID: id, State: record.snapshot.State, ReceivedAt: record.input.ReceivedAt}
	s.mu.Unlock()
	writeJSON(w, status, receipt)
}

// CreateRequest allocates independent reader and sender capabilities. Its caller
// is trusted local code; the HTTP seam additionally requires computer authority.
func (s *Server) CreateRequest(input CreateRequestInput) (RequestCreated, error) {
	if !utf8.ValidString(input.TaskID) || len(input.TaskID) > 128 || !utf8.ValidString(input.Prompt) || strings.TrimSpace(input.Prompt) == "" || len(input.Prompt) > 1024 {
		return RequestCreated{}, &RequestError{Code: "invalid_argument", Message: "taskId must fit 128 UTF-8 bytes and a nonblank prompt must fit 1024 bytes"}
	}
	if input.TTLSeconds < 0 || input.TTLSeconds > 86400 || input.MaxTextBytes < 0 || input.MaxTextBytes > MaxRequestTextBytes {
		return RequestCreated{}, &RequestError{Code: "invalid_argument", Message: "ttlSeconds must be 0..86400 and maxTextBytes must be 0..16384; zero selects the default"}
	}
	ttl := s.config.TTL
	if input.TTLSeconds != 0 {
		ttl = time.Duration(input.TTLSeconds) * time.Second
	}
	limit := input.MaxTextBytes
	if limit == 0 {
		limit = MaxRequestTextBytes
	}
	id, err := NewToken()
	if err != nil {
		return RequestCreated{}, &RequestError{Code: "internal", Message: "could not generate request"}
	}
	reader, err := NewToken()
	if err != nil {
		return RequestCreated{}, &RequestError{Code: "internal", Message: "could not generate reader capability"}
	}
	sender, err := NewToken()
	if err != nil {
		return RequestCreated{}, &RequestError{Code: "internal", Message: "could not generate sender capability"}
	}
	sendURL := s.config.PublicURL + "/send#" + url.Values{"request": {id}, "key": {sender}}.Encode()
	png, err := qrcode.Encode(sendURL, qrcode.Medium, 280)
	if err != nil {
		return RequestCreated{}, &RequestError{Code: "internal", Message: "could not generate QR code"}
	}
	s.mu.Lock()
	s.purgeLocked()
	if len(s.requests) >= MaxRequests {
		s.mu.Unlock()
		return RequestCreated{}, &RequestError{Code: "capacity", Message: "too many retained requests; wait for terminal cleanup"}
	}
	now := s.now()
	snapshot := RequestSnapshot{RequestID: id, TaskID: input.TaskID, Prompt: input.Prompt, State: "pending", CreatedAt: now, ExpiresAt: now.Add(ttl), MaxTextBytes: limit}
	s.requests[id] = &requestRecord{snapshot: snapshot, reader: reader, sender: sender, changed: make(chan struct{})}
	s.mu.Unlock()
	return RequestCreated{Request: snapshot, ReaderToken: reader, SendURL: sendURL, QRDataURL: "data:image/png;base64," + base64.StdEncoding.EncodeToString(png)}, nil
}

func (s *Server) createRequestHTTP(w http.ResponseWriter, r *http.Request) {
	if !s.owner(w, r) {
		return
	}
	var input CreateRequestInput
	if !readJSON(w, r, &input) {
		return
	}
	created, err := s.CreateRequest(input)
	if err != nil {
		requestFailure(w, err)
		return
	}
	writeJSON(w, http.StatusCreated, created)
}

func requestFailure(w http.ResponseWriter, err error) {
	failure, ok := err.(*RequestError)
	if !ok {
		failure = &RequestError{Code: "internal", Message: "request operation failed"}
	}
	status := map[string]int{"invalid_argument": http.StatusBadRequest, "unauthorized": http.StatusUnauthorized, "gone": http.StatusGone, "conflict": http.StatusConflict, "capacity": http.StatusTooManyRequests, "wait_canceled": http.StatusRequestTimeout, "internal": http.StatusInternalServerError}[failure.Code]
	if status == 0 {
		status = http.StatusInternalServerError
	}
	writeJSON(w, status, failure)
}
