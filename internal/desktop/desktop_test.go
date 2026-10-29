package desktop

import (
	"bytes"
	"context"
	"encoding/json"
	"io"
	"net"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"sync/atomic"
	"testing"

	"github.com/Yankj/ferry-dock/internal/buildinfo"
)

func TestUnsupportedDesktopListenersDoNotStartOrCreateState(t *testing.T) {
	for _, listen := range []string{"[::1]:0", "localhost:0", "192.168.1.2:8787", "127.0.0.1:-1", "0.0.0.0:65536"} {
		dir := filepath.Join(t.TempDir(), "unused")
		if err := Run(context.Background(), []string{"--no-open", "--listen", listen, "--state-dir", dir}, io.Discard, io.Discard); err == nil {
			t.Fatalf("accepted unsupported listener %s", listen)
		}
		if _, err := os.Stat(dir); !os.IsNotExist(err) {
			t.Fatal("invalid listener created runtime state")
		}
	}
}

func TestExistingBuildIdentityAndUpgradeDoNotStopOldService(t *testing.T) {
	build := buildinfo.Current()
	for _, row := range []struct {
		name, version, commit string
		compatible            bool
	}{
		{"same build", build.Version, build.Commit, true},
		{"different version", build.Version + "/other", build.Commit, false},
		{"different commit", build.Version, build.Commit + "/other", false},
		{"legacy service without build identity", "", "", false},
	} {
		t.Run(row.name, func(t *testing.T) {
			s := state{SchemaVersion: 1, OwnerToken: strings.Repeat("o", 43), InstanceID: strings.Repeat("i", 43), PID: 1}
			var requests atomic.Int32
			service := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
				requests.Add(1)
				if r.Method != http.MethodGet || r.URL.Path != "/api/desktop" || r.Header.Get("Authorization") != "Bearer "+s.OwnerToken {
					t.Error("launcher tried an operation other than authenticated identity inspection")
					w.WriteHeader(http.StatusForbidden)
					return
				}
				_ = json.NewEncoder(w).Encode(map[string]any{"desktop": true, "instanceId": s.InstanceID, "version": row.version, "commit": row.commit})
			}))
			defer service.Close()
			s.ServerURL = service.URL
			dir := t.TempDir()
			if err := os.Chmod(dir, 0700); err != nil {
				t.Fatal(err)
			}
			path := filepath.Join(dir, "control.json")
			data, _ := json.Marshal(s)
			if err := os.WriteFile(path, data, 0600); err != nil {
				t.Fatal(err)
			}
			var out bytes.Buffer
			args := []string{"--state-dir", dir}
			if row.compatible {
				args = append(args, "--no-open")
			}
			// An incompatible service must fail before attempting to open a
			// browser even without --no-open, and must not stop the old relay.
			err := Run(context.Background(), args, &out, io.Discard)
			if row.compatible {
				var ready struct {
					Reused  bool   `json:"reused"`
					Version string `json:"version"`
					Commit  string `json:"commit"`
				}
				if err != nil || json.Unmarshal(out.Bytes(), &ready) != nil || !ready.Reused || ready.Version != build.Version || ready.Commit != build.Commit {
					t.Fatalf("same build not reused: %v %s", err, out.String())
				}
			} else if err == nil || !strings.Contains(err.Error(), "Quit Ferry Dock") || !strings.Contains(err.Error(), "--state-dir") || out.Len() != 0 {
				t.Fatalf("incompatible build did not fail safely: %v %s", err, out.String())
			}
			retained, err := os.ReadFile(path)
			if err != nil || !bytes.Equal(data, retained) || requests.Load() != 1 {
				t.Fatal("inspection changed state or performed additional operations")
			}
			if _, err := os.Stat(filepath.Join(dir, "startup.log")); !os.IsNotExist(err) {
				t.Fatal("existing build inspection started a new relay")
			}
		})
	}
}

func TestStateRefusesSymlinkAndForeignService(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "control.json")
	s := state{SchemaVersion: 1, OwnerToken: "1234567890123456789012345678901234567890", InstanceID: "1234567890123456789012345678901234567890", PID: 1}
	foreign := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		_ = json.NewEncoder(w).Encode(map[string]any{"desktop": true, "instanceId": "someone-else"})
	}))
	defer foreign.Close()
	s.ServerURL = foreign.URL
	data, _ := json.Marshal(s)
	if err := os.WriteFile(path, data, 0600); err != nil {
		t.Fatal(err)
	}
	if _, _, err := existing(context.Background(), path); err == nil {
		t.Fatal("foreign service accepted")
	}
	if _, err := os.Stat(path); err != nil {
		t.Fatal("foreign state was removed")
	}
	alias := filepath.Join(dir, "alias.json")
	if err := os.Symlink(path, alias); err == nil {
		if _, err = readState(alias); err == nil {
			t.Fatal("symlink accepted")
		}
	}
}

func TestStaleStateRequiresConnectionRefusal(t *testing.T) {
	listener, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	origin := "http://" + listener.Addr().String()
	listener.Close()
	path := filepath.Join(t.TempDir(), "control.json")
	s := state{SchemaVersion: 1, ServerURL: origin, OwnerToken: "1234567890123456789012345678901234567890", InstanceID: "1234567890123456789012345678901234567890", PID: 1}
	data, _ := json.Marshal(s)
	os.WriteFile(path, data, 0600)
	_, valid, err := existing(context.Background(), path)
	if err != nil || valid {
		t.Fatalf("stale: %v %v", valid, err)
	}
	if _, err := os.Stat(path); !os.IsNotExist(err) {
		t.Fatal("stale state retained")
	}
}
