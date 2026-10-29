package relay

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/Yankj/ferry-dock/internal/buildinfo"
)

func TestDesktopBuildIdentityRequiresLocalOwnerAndDoesNotLeakCapabilities(t *testing.T) {
	config := Config{OwnerToken: strings.Repeat("o", 43), LocalURL: "http://127.0.0.1:8787", PublicURL: "http://192.168.1.20:8787", TTL: time.Minute, Desktop: &DesktopConfig{InstanceID: "test-instance", Quit: func() {}}}
	app, err := New(config)
	if err != nil {
		t.Fatal(err)
	}
	for _, row := range []struct {
		remote, host, token string
		want                int
	}{
		{"127.0.0.1:1234", "127.0.0.1:8787", "", 401},
		{"127.0.0.1:1234", "127.0.0.1:8787", "sender-capability", 401},
		{"192.168.1.2:1234", "127.0.0.1:8787", config.OwnerToken, 403},
		{"127.0.0.1:1234", "192.168.1.20:8787", config.OwnerToken, 403},
		{"127.0.0.1:1234", "127.0.0.1:8787", config.OwnerToken, 200},
	} {
		request := httptest.NewRequest(http.MethodGet, "http://"+row.host+"/api/desktop", nil)
		request.RemoteAddr = row.remote
		request.Header.Set("Authorization", "Bearer "+row.token)
		response := httptest.NewRecorder()
		app.ServeHTTP(response, request)
		if response.Code != row.want {
			t.Fatalf("status %d want %d", response.Code, row.want)
		}
		if strings.Contains(response.Body.String(), config.OwnerToken) || strings.Contains(response.Body.String(), "sender-capability") {
			t.Fatal("desktop status exposed a capability")
		}
		if row.want == http.StatusOK {
			var status struct {
				Version string `json:"version"`
				Commit  string `json:"commit"`
			}
			build := buildinfo.Current()
			if json.Unmarshal(response.Body.Bytes(), &status) != nil || status.Version != build.Version || status.Commit != build.Commit {
				t.Fatal("desktop status did not identify its actual build")
			}
		} else if strings.Contains(response.Body.String(), "test-instance") {
			t.Fatal("unauthorized caller inspected desktop instance")
		}
	}
}

func TestDesktopQuitRequiresLocalComputerAndDoesNotExistInServe(t *testing.T) {
	quit := 0
	config := Config{OwnerToken: strings.Repeat("o", 43), LocalURL: "http://127.0.0.1:8787", PublicURL: "http://192.168.1.20:8787", TTL: time.Minute, Desktop: &DesktopConfig{InstanceID: "instance", Quit: func() { quit++ }}}
	app, err := New(config)
	if err != nil {
		t.Fatal(err)
	}
	for _, row := range []struct {
		remote, host, token string
		want                int
	}{{"127.0.0.1:1234", "127.0.0.1:8787", "wrong", 401}, {"192.168.1.2:1234", "127.0.0.1:8787", config.OwnerToken, 403}, {"127.0.0.1:1234", "192.168.1.20:8787", config.OwnerToken, 403}, {"127.0.0.1:1234", "127.0.0.1:8787", config.OwnerToken, 202}} {
		request := httptest.NewRequest(http.MethodPost, "http://"+row.host+"/api/desktop/quit", strings.NewReader("{}"))
		request.RemoteAddr = row.remote
		request.Header.Set("Authorization", "Bearer "+row.token)
		request.Header.Set("Content-Type", "application/json")
		response := httptest.NewRecorder()
		app.ServeHTTP(response, request)
		if response.Code != row.want {
			t.Fatalf("status %d want %d", response.Code, row.want)
		}
	}
	if quit != 1 {
		t.Fatal("unauthorized quit called")
	}
	config.Desktop = nil
	plain, _ := New(config)
	request := httptest.NewRequest(http.MethodPost, config.LocalURL+"/api/desktop/quit", strings.NewReader("{}"))
	response := httptest.NewRecorder()
	plain.ServeHTTP(response, request)
	if response.Code == 202 {
		t.Fatal("plain serve exposed quit")
	}
}
