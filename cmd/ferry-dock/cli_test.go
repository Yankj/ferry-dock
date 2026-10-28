package main

import (
	"bytes"
	"context"
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
)

func TestRequestCreateMissingOptionsIsJSONFailure(t *testing.T) {
	var out, diagnostics bytes.Buffer
	code := runCLI(context.Background(), []string{"request", "create"}, &out, &diagnostics)
	if code == 0 {
		t.Fatal("missing control and handle must fail")
	}
	var failure struct {
		Error struct {
			Code string `json:"code"`
		} `json:"error"`
	}
	if err := json.Unmarshal(out.Bytes(), &failure); err != nil {
		t.Fatalf("request failures must be JSON: %v; output=%q", err, out.String())
	}
	if failure.Error.Code != "invalid_argument" {
		t.Fatalf("code=%q", failure.Error.Code)
	}
}

func TestRequestHandleCannotTargetNonLoopbackService(t *testing.T) {
	path := filepath.Join(t.TempDir(), "request.json")
	_, err := writePrivateJSON(path, requestHandle{SchemaVersion: 1, ServerURL: "http://example.invalid:8787", RequestID: "test-request", ReaderToken: strings.Repeat("r", 43)})
	if err != nil {
		t.Fatal(err)
	}
	var out, diagnostics bytes.Buffer
	code := runCLI(context.Background(), []string{"request", "status", "--handle", path}, &out, &diagnostics)
	if code == 0 || !strings.Contains(out.String(), `"code":"invalid_argument"`) {
		t.Fatalf("nonloopback handle: exit=%d output=%s", code, out.String())
	}
}

func TestPrivateFilesAreNeverOverwritten(t *testing.T) {
	path := filepath.Join(t.TempDir(), "private.json")
	if err := writePrivateBytes(path, []byte("original")); err != nil {
		t.Fatal(err)
	}
	if err := writePrivateBytes(path, []byte("replacement")); err == nil {
		t.Fatal("existing runtime state was overwritten")
	}
	got, err := os.ReadFile(path)
	if err != nil || string(got) != "original" {
		t.Fatalf("existing state changed: %q %v", got, err)
	}
	if runtime.GOOS != "windows" {
		if err := os.Chmod(path, 0644); err != nil {
			t.Fatal(err)
		}
		var state controlFile
		if err := readPrivateJSON(path, &state); err == nil {
			t.Fatal("world-readable control state accepted")
		}
	}
}

func TestRequestReadNeverTruncatesOversizedResult(t *testing.T) {
	service := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_, _ = io.WriteString(w, `{"input":{"text":"`+strings.Repeat("s", maxResponseBytes)+`"}}`)
	}))
	defer service.Close()
	path := filepath.Join(t.TempDir(), "request.json")
	if _, err := writePrivateJSON(path, requestHandle{SchemaVersion: 1, ServerURL: service.URL, RequestID: "test-request", ReaderToken: strings.Repeat("r", 43)}); err != nil {
		t.Fatal(err)
	}
	var out, diagnostics bytes.Buffer
	code := runCLI(context.Background(), []string{"request", "read", "--handle", path}, &out, &diagnostics)
	if code == 0 || !strings.Contains(out.String(), `"code":"result_too_large"`) {
		t.Fatalf("expected explicit size error: exit=%d %s", code, out.String())
	}
	if out.Len() > 512 {
		t.Fatal("partial result text leaked into error output")
	}
}

func TestInterruptedCancelReportsUnknownMutationOutcome(t *testing.T) {
	committed := make(chan struct{})
	service := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		close(committed)
		<-r.Context().Done()
	}))
	defer service.Close()
	path := filepath.Join(t.TempDir(), "request.json")
	if _, err := writePrivateJSON(path, requestHandle{SchemaVersion: 1, ServerURL: service.URL, RequestID: "test-request", ReaderToken: strings.Repeat("r", 43)}); err != nil {
		t.Fatal(err)
	}
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	var out, diagnostics bytes.Buffer
	done := make(chan int, 1)
	go func() { done <- runCLI(ctx, []string{"request", "cancel", "--handle", path}, &out, &diagnostics) }()
	<-committed
	cancel()
	if code := <-done; code != 130 || !strings.Contains(out.String(), `"code":"outcome_unknown"`) {
		t.Fatalf("mutation may have committed; exit=%d output=%s", code, out.String())
	}
}

func TestWaitInterruptedDuringResponseBodyIsStillWaitCanceled(t *testing.T) {
	headersSent := make(chan struct{})
	service := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_, _ = io.WriteString(w, "{")
		w.(http.Flusher).Flush()
		close(headersSent)
		<-r.Context().Done()
	}))
	defer service.Close()
	path := filepath.Join(t.TempDir(), "request.json")
	if _, err := writePrivateJSON(path, requestHandle{SchemaVersion: 1, ServerURL: service.URL, RequestID: "test-request", ReaderToken: strings.Repeat("r", 43)}); err != nil {
		t.Fatal(err)
	}
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	var out, diagnostics bytes.Buffer
	done := make(chan int, 1)
	go func() { done <- runCLI(ctx, []string{"request", "wait", "--handle", path}, &out, &diagnostics) }()
	<-headersSent
	cancel()
	if code := <-done; code != 130 || !strings.Contains(out.String(), `"code":"wait_canceled"`) {
		t.Fatalf("body interruption must preserve wait semantics; exit=%d output=%s", code, out.String())
	}
}
