package main

import (
	"bytes"
	"context"
	"encoding/base64"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"net"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"time"
	"unicode/utf8"

	"github.com/Yankj/ferry-dock/internal/buildinfo"
	"github.com/Yankj/ferry-dock/internal/desktop"
	"github.com/Yankj/ferry-dock/internal/host"
	"github.com/Yankj/ferry-dock/internal/relay"
)

const maxResponseBytes = 128 << 10

type controlFile struct {
	SchemaVersion int    `json:"schemaVersion"`
	ServerURL     string `json:"serverUrl"`
	OwnerToken    string `json:"ownerToken"`
	InstanceID    string `json:"instanceId,omitempty"`
	PID           int    `json:"pid,omitempty"`
}

type requestHandle struct {
	SchemaVersion int    `json:"schemaVersion"`
	ServerURL     string `json:"serverUrl"`
	RequestID     string `json:"requestId"`
	ReaderToken   string `json:"readerToken"`
}

type commandError struct {
	code, message string
	exit          int
}

func (e *commandError) Error() string    { return e.message }
func problem(code, message string) error { return &commandError{code: code, message: message, exit: 1} }
func invalid(message string) error {
	return &commandError{code: "invalid_argument", message: message, exit: 2}
}

func runCLI(ctx context.Context, args []string, out, errOut io.Writer) int {
	if len(args) > 0 && (args[0] == "version" || args[0] == "--version") {
		if len(args) != 1 {
			fmt.Fprintln(errOut, "version takes no arguments")
			return 2
		}
		_ = json.NewEncoder(out).Encode(buildinfo.Current())
		return 0
	}
	if len(args) > 0 && args[0] == "desktop" {
		if err := desktop.Run(ctx, args[1:], out, errOut); err != nil {
			fmt.Fprintln(errOut, "Ferry Dock:", err)
			return 1
		}
		return 0
	}
	if len(args) == 0 || strings.HasPrefix(args[0], "-") || args[0] == "serve" {
		if len(args) > 0 && args[0] == "serve" {
			args = args[1:]
		}
		if err := serve(ctx, args, out, errOut); err != nil {
			fmt.Fprintln(errOut, "Ferry Dock:", err)
			return 1
		}
		return 0
	}
	if args[0] != "request" {
		fmt.Fprintln(errOut, "Usage: ferry-dock desktop [options] | version | [serve] [options] | request <create|status|wait|read|cancel> [options]")
		return 2
	}
	result, err := requestCommand(ctx, args[1:], errOut)
	if errors.Is(err, flag.ErrHelp) {
		return 0
	}
	if err != nil {
		var failure *commandError
		if !errors.As(err, &failure) {
			failure = &commandError{code: "internal", message: err.Error(), exit: 1}
		}
		_ = json.NewEncoder(out).Encode(map[string]any{"error": map[string]string{"code": failure.code, "message": failure.message}})
		return failure.exit
	}
	if err = json.NewEncoder(out).Encode(result); err != nil {
		fmt.Fprintln(errOut, "could not write JSON result:", err)
		return 1
	}
	return 0
}

func serve(ctx context.Context, args []string, out, errOut io.Writer) error {
	flags := flag.NewFlagSet("ferry-dock serve", flag.ContinueOnError)
	flags.SetOutput(errOut)
	listen := flags.String("listen", "127.0.0.1:8787", "HTTP listen address; phone access requires explicit LAN configuration")
	publicURL := flags.String("public-url", "", "phone-accessible HTTP origin, e.g. http://192.168.1.10:8787")
	ttl := flags.Duration("ttl", 15*time.Minute, "retention lifetime, greater than zero and at most 24h")
	controlPath := flags.String("control-file", "", "write private, temporary loopback control state to a new file")
	if err := flags.Parse(args); err != nil {
		if errors.Is(err, flag.ErrHelp) {
			return nil
		}
		return err
	}
	if flags.NArg() != 0 {
		return errors.New("unexpected positional arguments")
	}
	service, err := host.Start(host.Options{Listen: *listen, PublicURL: *publicURL, TTL: *ttl})
	if err != nil {
		return err
	}
	defer func() {
		shutdown, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		_ = service.Close(shutdown)
	}()
	if *controlPath != "" {
		if err = validateOrigin(service.LocalURL); err != nil {
			return fmt.Errorf("control file requires a loopback-reachable listener: %w", err)
		}
		state := controlFile{SchemaVersion: 1, ServerURL: service.LocalURL, OwnerToken: service.OwnerToken}
		written, err := writePrivateJSON(*controlPath, state)
		if err != nil {
			return fmt.Errorf("control file: %w", err)
		}
		defer func() {
			current, readErr := os.ReadFile(*controlPath)
			if readErr == nil && bytes.Equal(current, written) {
				_ = os.Remove(*controlPath)
			}
		}()
		fmt.Fprintln(errOut, "Private control file:", *controlPath)
	}
	fmt.Fprintf(out, "Ferry Dock · alpha\n\nOpen on this computer:\n%s/#owner=%s\n\n", service.LocalURL, url.QueryEscape(service.OwnerToken))
	if service.PublicURL == service.LocalURL {
		fmt.Fprintln(out, "Local-only mode. For phone access, restart with -listen 0.0.0.0:8787 -public-url http://YOUR_LAN_IP:8787")
	} else {
		fmt.Fprintf(out, "Phone origin: %s\nUse only on a trusted LAN: HTTP does not encrypt content or capabilities.\n", service.PublicURL)
	}
	fmt.Fprintln(out, "Content stays in memory. Ctrl+C ends every session and request.")
	select {
	case <-ctx.Done():
		return nil
	case err := <-service.Done():
		if errors.Is(err, http.ErrServerClosed) {
			return nil
		}
		return err
	}
}

func requestCommand(ctx context.Context, args []string, diagnostics io.Writer) (any, error) {
	if len(args) == 0 {
		return nil, invalid("choose create, status, wait, read, or cancel")
	}
	action := args[0]
	if action != "create" && action != "status" && action != "read" && action != "wait" && action != "cancel" {
		return nil, invalid("unknown request operation")
	}
	flags := flag.NewFlagSet("ferry-dock request "+action, flag.ContinueOnError)
	flags.SetOutput(diagnostics)
	handlePath := flags.String("handle", "", "private request handle path (new file for create)")
	var controlPath, taskID, prompt, qrPath *string
	var ttl, timeout *time.Duration
	var maxBytes *int
	if action == "create" {
		controlPath = flags.String("control", "", "private control file produced by serve --control-file")
		taskID = flags.String("task-id", "", "task correlation label; never grants authority")
		prompt = flags.String("prompt", "", "what text the phone user should provide")
		qrPath = flags.String("qr", "", "new QR PNG path; default is HANDLE.png")
		ttl = flags.Duration("ttl", 0, "optional request retention; whole seconds, at most 24h")
		maxBytes = flags.Int("max-bytes", 0, "optional text limit, at most 16384 bytes")
	}
	if action == "wait" {
		timeout = flags.Duration("timeout", 10*time.Second, "bounded wait, 0..10s; timeout does not cancel the request")
	}
	if err := flags.Parse(args[1:]); err != nil {
		if errors.Is(err, flag.ErrHelp) {
			return nil, err
		}
		return nil, invalid(err.Error())
	}
	if flags.NArg() != 0 {
		return nil, invalid("unexpected positional arguments")
	}
	if *handlePath == "" {
		return nil, invalid("--handle is required")
	}
	absoluteHandle, err := filepath.Abs(*handlePath)
	if err != nil {
		return nil, invalid("invalid handle path")
	}
	if action == "create" {
		if !utf8.ValidString(*prompt) || !utf8.ValidString(*taskID) {
			return nil, invalid("task label and prompt must be valid Unicode")
		}
		if *controlPath == "" || strings.TrimSpace(*prompt) == "" {
			return nil, invalid("--control and nonblank --prompt are required")
		}
		if *ttl < 0 || *ttl > 24*time.Hour || *ttl%time.Second != 0 {
			return nil, invalid("--ttl must be whole seconds between zero and 24h")
		}
		if err = ensureNew(absoluteHandle); err != nil {
			return nil, invalid(err.Error())
		}
		qrFile := *qrPath
		if qrFile == "" {
			qrFile = absoluteHandle + ".png"
		}
		qrFile, err = filepath.Abs(qrFile)
		if err != nil || qrFile == absoluteHandle {
			return nil, invalid("QR and handle require distinct valid paths")
		}
		if err = ensureNew(qrFile); err != nil {
			return nil, invalid(err.Error())
		}
		var control controlFile
		if err = readPrivateJSON(*controlPath, &control); err != nil {
			return nil, invalid("control file: " + err.Error())
		}
		if control.SchemaVersion != 1 || len(control.OwnerToken) < 32 {
			return nil, invalid("unsupported or invalid control file")
		}
		if err = validateOrigin(control.ServerURL); err != nil {
			return nil, invalid(err.Error())
		}
		body := relay.CreateRequestInput{TaskID: *taskID, Prompt: *prompt, TTLSeconds: int(*ttl / time.Second), MaxTextBytes: *maxBytes}
		var created relay.RequestCreated
		if err = fetchJSON(ctx, control.ServerURL, "/api/requests", control.OwnerToken, http.MethodPost, body, &created); err != nil {
			return nil, err
		}
		if created.Request.RequestID == "" || len(created.ReaderToken) < 32 {
			return nil, problem("invalid_response", "server returned an invalid request handle")
		}
		handle := requestHandle{SchemaVersion: 1, ServerURL: control.ServerURL, RequestID: created.Request.RequestID, ReaderToken: created.ReaderToken}
		if _, err = writePrivateJSON(absoluteHandle, handle); err != nil {
			// This was a new request; failure to retain its handle must not leave it accepting input.
			var canceled relay.RequestSnapshot
			cleanupErr := fetchJSON(context.Background(), control.ServerURL, "/api/requests/"+url.PathEscape(handle.RequestID), handle.ReaderToken, http.MethodDelete, nil, &canceled)
			if cleanupErr != nil {
				return nil, problem("local_write_failed", "handle could not be saved; request cancellation was unconfirmed and its TTL still applies")
			}
			return nil, problem("local_write_failed", "handle could not be saved; the new request was canceled")
		}
		response := map[string]any{"request": created.Request, "handlePath": absoluteHandle, "sendUrl": created.SendURL, "qrPath": qrFile}
		qr, decodeErr := base64.StdEncoding.DecodeString(strings.TrimPrefix(created.QRDataURL, "data:image/png;base64,"))
		if decodeErr != nil || len(qr) > 64<<10 || !bytes.HasPrefix(qr, []byte{137, 80, 78, 71, 13, 10, 26, 10}) {
			response["qrPath"] = nil
			response["warning"] = "QR was unavailable; the private sendUrl remains usable"
		} else if err = writePrivateBytes(qrFile, qr); err != nil {
			response["qrPath"] = nil
			response["warning"] = "QR file could not be saved; the request handle and private sendUrl remain usable"
		}
		return response, nil
	}
	var handle requestHandle
	if err = readPrivateJSON(absoluteHandle, &handle); err != nil {
		return nil, invalid("handle: " + err.Error())
	}
	if handle.SchemaVersion != 1 || handle.RequestID == "" || len(handle.ReaderToken) < 32 {
		return nil, invalid("unsupported or invalid request handle")
	}
	if err = validateOrigin(handle.ServerURL); err != nil {
		return nil, invalid(err.Error())
	}
	path := "/api/requests/" + url.PathEscape(handle.RequestID)
	switch action {
	case "status":
		var state relay.RequestSnapshot
		err = fetchJSON(ctx, handle.ServerURL, path, handle.ReaderToken, http.MethodGet, nil, &state)
		return state, err
	case "read":
		var result relay.RequestResult
		err = fetchJSON(ctx, handle.ServerURL, path+"/result", handle.ReaderToken, http.MethodGet, nil, &result)
		return result, err
	case "cancel":
		var state relay.RequestSnapshot
		err = fetchJSON(ctx, handle.ServerURL, path, handle.ReaderToken, http.MethodDelete, nil, &state)
		return state, err
	case "wait":
		if *timeout < 0 || *timeout > 10*time.Second {
			return nil, invalid("--timeout must be between 0 and 10s")
		}
		var result relay.RequestWaitResult
		err = fetchJSON(ctx, handle.ServerURL, fmt.Sprintf("%s/wait?timeoutMs=%d", path, timeout.Milliseconds()), handle.ReaderToken, http.MethodGet, nil, &result)
		if ctx.Err() != nil {
			return nil, &commandError{code: "wait_canceled", message: "wait interrupted; no request cancellation was sent", exit: 130}
		}
		return result, err
	}
	return nil, invalid("unknown operation")
}

func validateOrigin(raw string) error {
	u, err := url.Parse(raw)
	if err != nil || u.Scheme != "http" || u.Host == "" || u.User != nil || u.RawQuery != "" || u.ForceQuery || u.Fragment != "" || (u.Path != "" && u.Path != "/") || u.RawPath != "" {
		return errors.New("control origin must be a loopback HTTP origin")
	}
	ip := net.ParseIP(u.Hostname())
	if u.Hostname() != "localhost" && (ip == nil || !ip.IsLoopback()) {
		return errors.New("control origin must be loopback; phone LAN origin is separate")
	}
	return nil
}

func ensureNew(path string) error {
	if _, err := os.Lstat(path); !errors.Is(err, os.ErrNotExist) {
		return fmt.Errorf("destination must be a new file: %s", path)
	}
	info, err := os.Stat(filepath.Dir(path))
	if err != nil || !info.IsDir() {
		return errors.New("destination parent directory must already exist")
	}
	return nil
}

func writePrivateJSON(path string, value any) ([]byte, error) {
	data, err := json.Marshal(value)
	if err != nil {
		return nil, err
	}
	data = append(data, '\n')
	return data, writePrivateBytes(path, data)
}

func writePrivateBytes(path string, data []byte) error {
	file, err := os.OpenFile(path, os.O_CREATE|os.O_EXCL|os.O_WRONLY, 0600)
	if err != nil {
		return err
	}
	good := false
	defer func() {
		_ = file.Close()
		if !good {
			_ = os.Remove(path)
		}
	}()
	if _, err = file.Write(data); err != nil {
		return err
	}
	if err = file.Sync(); err != nil {
		return err
	}
	if err = file.Close(); err != nil {
		return err
	}
	good = true
	return nil
}

func readPrivateJSON(path string, target any) error {
	info, err := os.Lstat(path)
	if err != nil {
		return errors.New("file is unavailable")
	}
	if !info.Mode().IsRegular() || info.Size() > 4096 {
		return errors.New("expected a small regular file, not a symlink")
	}
	if runtime.GOOS != "windows" && info.Mode().Perm()&0077 != 0 {
		return errors.New("file must be private (mode 0600)")
	}
	file, err := os.Open(path)
	if err != nil {
		return errors.New("file is unavailable")
	}
	defer file.Close()
	opened, err := file.Stat()
	if err != nil || !os.SameFile(info, opened) {
		return errors.New("file changed while opening")
	}
	decoder := json.NewDecoder(io.LimitReader(file, 4097))
	decoder.DisallowUnknownFields()
	if err = decoder.Decode(target); err != nil || decoder.Decode(new(any)) != io.EOF {
		return errors.New("invalid runtime state JSON")
	}
	return nil
}

func fetchJSON(ctx context.Context, origin, path, token, method string, body, target any) error {
	var reader io.Reader
	if body != nil {
		data, err := json.Marshal(body)
		if err != nil {
			return err
		}
		reader = bytes.NewReader(data)
	}
	request, err := http.NewRequestWithContext(ctx, method, strings.TrimRight(origin, "/")+path, reader)
	if err != nil {
		return invalid("invalid control request")
	}
	request.Header.Set("Authorization", "Bearer "+token)
	if body != nil {
		request.Header.Set("Content-Type", "application/json")
	}
	transport := &http.Transport{Proxy: nil}
	defer transport.CloseIdleConnections()
	client := &http.Client{Transport: transport, Timeout: 15 * time.Second, CheckRedirect: func(r *http.Request, via []*http.Request) error { return http.ErrUseLastResponse }}
	response, err := client.Do(request)
	if err != nil {
		return transportProblem(ctx, method)
	}
	defer response.Body.Close()
	data, err := io.ReadAll(io.LimitReader(response.Body, maxResponseBytes+1))
	if err != nil {
		return transportProblem(ctx, method)
	}
	if len(data) > maxResponseBytes {
		return problem("result_too_large", "service response exceeded 128 KiB; no result was truncated")
	}
	if response.StatusCode < 200 || response.StatusCode >= 300 {
		var failure struct {
			Code  string `json:"code"`
			Error string `json:"error"`
		}
		if json.Unmarshal(data, &failure) != nil || failure.Code == "" {
			return problem("invalid_response", "service returned an invalid error response")
		}
		return problem(failure.Code, failure.Error)
	}
	if json.Unmarshal(data, target) != nil {
		return problem("invalid_response", "service returned invalid JSON")
	}
	return nil
}

// Mutations can commit before a response is lost. Never label them as a canceled
// wait or promise the business operation did not happen.
func transportProblem(ctx context.Context, method string) error {
	exit := 1
	if ctx.Err() != nil {
		exit = 130
	}
	if method == http.MethodPost {
		return &commandError{code: "outcome_unknown", message: "request creation outcome is unknown; no handle was saved; any unseen request still expires by its TTL", exit: exit}
	}
	if method == http.MethodDelete {
		return &commandError{code: "outcome_unknown", message: "cancellation outcome is unknown; inspect status with the same handle before retrying", exit: exit}
	}
	if ctx.Err() != nil {
		return &commandError{code: "operation_canceled", message: "read operation interrupted; no request cancellation was sent", exit: exit}
	}
	return problem("server_unavailable", "local service response was incomplete or unavailable; query again when it is reachable")
}
