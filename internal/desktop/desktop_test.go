package desktop

import (
	"context"
	"encoding/json"
	"io"
	"net"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"testing"
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
