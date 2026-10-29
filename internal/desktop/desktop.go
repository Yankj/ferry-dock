// Package desktop is a short-lived launcher for the same Go relay. It installs
// no service: its owned background process is stopped by the local Quit button.
package desktop

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"net"
	"net/http"
	"net/url"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strconv"
	"strings"
	"syscall"
	"time"

	"github.com/Yankj/ferry-dock/internal/buildinfo"
	"github.com/Yankj/ferry-dock/internal/host"
	"github.com/Yankj/ferry-dock/internal/relay"
)

type state struct {
	SchemaVersion int    `json:"schemaVersion"`
	ServerURL     string `json:"serverUrl"`
	OwnerToken    string `json:"ownerToken"`
	InstanceID    string `json:"instanceId"`
	PID           int    `json:"pid"`
}

// Run launches or reopens one verified per-user desktop instance. --no-open is
// useful to test lifecycle without controlling the user's browser.
func Run(ctx context.Context, args []string, out, errOut io.Writer) error {
	f := flag.NewFlagSet("ferry-dock desktop", flag.ContinueOnError)
	f.SetOutput(errOut)
	directory := f.String("state-dir", "", "private per-user runtime directory (default: user cache/ferry-dock/runtime)")
	listen := f.String("listen", "0.0.0.0:0", "listen address; default selects a free port")
	public := f.String("public-url", "", "explicit phone-reachable HTTP origin")
	noOpen := f.Bool("no-open", false, "start/reopen without launching the system browser")
	background := f.Bool("background-service", false, "internal: run the owned relay process")
	if err := f.Parse(args); err != nil {
		if errors.Is(err, flag.ErrHelp) {
			return nil
		}
		return err
	}
	if f.NArg() != 0 {
		return errors.New("unexpected desktop arguments")
	}
	bindHost, bindPort, bindErr := net.SplitHostPort(*listen)
	port, portErr := strconv.Atoi(bindPort)
	if bindErr != nil || portErr != nil || port < 0 || port > 65535 || (bindHost != "127.0.0.1" && bindHost != "0.0.0.0") {
		return errors.New("desktop --listen requires 127.0.0.1 or 0.0.0.0 and a numeric port; use serve for other listener configurations")
	}
	if *directory == "" {
		cache, err := os.UserCacheDir()
		if err != nil {
			return errors.New("cannot locate user cache; specify --state-dir")
		}
		*directory = filepath.Join(cache, "ferry-dock", "runtime")
	}
	dir, err := filepath.Abs(*directory)
	if err != nil {
		return errors.New("invalid state directory")
	}
	if err = privateDirectory(dir); err != nil {
		return err
	}
	if *background {
		return runService(ctx, dir, *listen, *public)
	}
	control := filepath.Join(dir, "control.json")
	lock := filepath.Join(dir, "launch.lock")
	deadline := time.Now().Add(8 * time.Second)
	for {
		err = os.Mkdir(lock, 0700)
		if err == nil {
			break
		}
		if !os.IsExist(err) {
			return errors.New("cannot acquire private startup lock")
		}
		if time.Now().After(deadline) {
			return errors.New("desktop startup is busy or a previous startup was interrupted; inspect the private launch.lock directory before retrying")
		}
		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-time.After(40 * time.Millisecond):
		}
	}
	defer os.Remove(lock)
	s, reuse, err := existing(ctx, control)
	if err != nil {
		return err
	}
	if !reuse {
		executable, err := os.Executable()
		if err != nil {
			return errors.New("cannot locate packaged executable")
		}
		logPath := filepath.Join(dir, "startup.log")
		if info, e := os.Lstat(logPath); e == nil {
			if !info.Mode().IsRegular() || (runtime.GOOS != "windows" && info.Mode().Perm()&0077 != 0) {
				return errors.New("startup log is not a private regular file")
			}
			if os.Remove(logPath) != nil {
				return errors.New("cannot replace private startup log")
			}
		} else if !os.IsNotExist(e) {
			return errors.New("cannot inspect private startup log")
		}
		log, err := os.OpenFile(logPath, os.O_CREATE|os.O_EXCL|os.O_WRONLY, 0600)
		if err != nil {
			return errors.New("cannot create private startup log")
		}
		child := exec.Command(executable, "desktop", "--background-service", "--state-dir", dir, "--listen", *listen)
		if *public != "" {
			child.Args = append(child.Args, "--public-url", *public)
		}
		child.Stdout = log
		child.Stderr = log
		detach(child)
		if err = child.Start(); err != nil {
			log.Close()
			return errors.New("cannot start bundled relay")
		}
		log.Close()
		exited := make(chan error, 1)
		go func() { exited <- child.Wait() }()
		ready := false
		defer func() {
			if !ready {
				_ = child.Process.Kill()
				select {
				case <-exited:
				case <-time.After(time.Second):
				}
			}
		}()
		for !ready {
			select {
			case <-ctx.Done():
				return ctx.Err()
			case <-exited:
				return errors.New("bundled relay could not start; check the private startup.log (the selected port may be occupied)")
			case <-time.After(30 * time.Millisecond):
			}
			if time.Now().After(deadline) {
				return errors.New("bundled relay did not become ready within eight seconds")
			}
			s, err = readState(control)
			if os.IsNotExist(err) {
				continue
			}
			if err != nil {
				return err
			}
			if s.PID != child.Process.Pid {
				return errors.New("startup state belongs to an unexpected process")
			}
			ready, err = verify(ctx, s)
			if err != nil {
				return err
			}
		}
	}
	if !*noOpen {
		if err = openBrowser(ctx, s.ServerURL+"/#owner="+url.QueryEscape(s.OwnerToken)); err != nil {
			return errors.New("relay is running but the system browser could not open; retry desktop or use the private control file")
		}
	}
	build := buildinfo.Current()
	return json.NewEncoder(out).Encode(map[string]any{"state": "ready", "reused": reuse, "controlPath": control, "version": build.Version, "commit": build.Commit})
}

func privateDirectory(dir string) error {
	if err := os.MkdirAll(dir, 0700); err != nil {
		return errors.New("cannot create private runtime directory")
	}
	info, err := os.Lstat(dir)
	if err != nil || !info.IsDir() || info.Mode()&os.ModeSymlink != 0 {
		return errors.New("runtime directory must be a real directory")
	}
	if runtime.GOOS != "windows" && info.Mode().Perm()&0077 != 0 {
		return errors.New("runtime directory must be private to the current user")
	}
	return nil
}

func readState(path string) (state, error) {
	var s state
	info, err := os.Lstat(path)
	if err != nil {
		return s, err
	}
	if !info.Mode().IsRegular() || info.Size() > 4096 || (runtime.GOOS != "windows" && info.Mode().Perm()&0077 != 0) {
		return s, errors.New("invalid or non-private desktop control file")
	}
	file, err := os.Open(path)
	if err != nil {
		return s, err
	}
	defer file.Close()
	opened, err := file.Stat()
	if err != nil || !os.SameFile(info, opened) {
		return s, errors.New("desktop control file changed during open")
	}
	data, err := io.ReadAll(io.LimitReader(file, 4097))
	if err != nil {
		return s, err
	}
	if json.Unmarshal(data, &s) != nil || s.SchemaVersion != 1 || len(s.OwnerToken) < 32 || len(s.InstanceID) < 32 || s.PID < 1 {
		return s, errors.New("invalid desktop control state")
	}
	u, err := url.Parse(s.ServerURL)
	if err != nil || u.Scheme != "http" || u.Hostname() != "127.0.0.1" || u.Port() == "" || u.User != nil || u.Path != "" || u.RawQuery != "" || u.Fragment != "" {
		return s, errors.New("desktop control origin must be numeric loopback")
	}
	return s, nil
}

func verify(ctx context.Context, s state) (bool, error) {
	request, _ := http.NewRequestWithContext(ctx, http.MethodGet, s.ServerURL+"/api/desktop", nil)
	request.Header.Set("Authorization", "Bearer "+s.OwnerToken)
	transport := &http.Transport{Proxy: nil}
	defer transport.CloseIdleConnections()
	client := http.Client{Transport: transport, Timeout: 800 * time.Millisecond, CheckRedirect: func(*http.Request, []*http.Request) error { return http.ErrUseLastResponse }}
	response, err := client.Do(request)
	if err != nil {
		if connectionRefused(err) {
			return false, nil
		}
		return false, errors.New("desktop service identity could not be verified; no existing process was changed")
	}
	defer response.Body.Close()
	var status struct {
		Desktop    bool   `json:"desktop"`
		InstanceID string `json:"instanceId"`
		Version    string `json:"version"`
		Commit     string `json:"commit"`
	}
	data, err := io.ReadAll(io.LimitReader(response.Body, 4097))
	if err != nil || len(data) > 4096 || response.StatusCode != 200 || json.Unmarshal(data, &status) != nil || !status.Desktop || status.InstanceID != s.InstanceID {
		return false, errors.New("an unknown service occupies the recorded address; no existing process was changed")
	}
	build := buildinfo.Current()
	if status.Version != build.Version || status.Commit != build.Commit {
		return false, errors.New("the running Ferry Dock has a different or unknown version/commit; finish its tasks and use Quit Ferry Dock before retrying, or choose a different --state-dir; no existing process was changed")
	}
	return true, nil
}

func connectionRefused(err error) bool {
	// Winsock preserves WSAECONNREFUSED (10061); it is not Go's emulated
	// Windows syscall.ECONNREFUSED. No other dial error proves stale state.
	return errors.Is(err, syscall.ECONNREFUSED) || (runtime.GOOS == "windows" && errors.Is(err, syscall.Errno(10061)))
}

func existing(ctx context.Context, path string) (state, bool, error) {
	s, err := readState(path)
	if os.IsNotExist(err) {
		return s, false, nil
	}
	if err != nil {
		return s, false, err
	}
	valid, err := verify(ctx, s)
	if err != nil || valid {
		return s, valid, err
	}
	if err = os.Remove(path); err != nil {
		return s, false, errors.New("cannot remove stale private desktop state")
	}
	return s, false, nil
}

func runService(parent context.Context, dir, listen, public string) error {
	ctx, cancel := context.WithCancel(parent)
	defer cancel()
	instance, err := relay.NewToken()
	if err != nil {
		return err
	}
	publicHost := ""
	if public == "" {
		name, port, splitErr := net.SplitHostPort(listen)
		if splitErr != nil {
			return splitErr
		}
		ip := net.ParseIP(name)
		if name != "localhost" && (ip == nil || !ip.IsLoopback()) {
			publicHost = lanAddress()
			if publicHost == "" {
				listen = net.JoinHostPort("127.0.0.1", port)
			}
		}
	}
	service, err := host.Start(host.Options{Listen: listen, PublicURL: public, PublicHost: publicHost, TTL: 15 * time.Minute, Desktop: &relay.DesktopConfig{InstanceID: instance, Quit: cancel}})
	if err != nil {
		return fmt.Errorf("desktop listener: %w", err)
	}
	defer func() {
		shutdown, stop := context.WithTimeout(context.Background(), 3*time.Second)
		defer stop()
		_ = service.Close(shutdown)
	}()
	s := state{1, service.LocalURL, service.OwnerToken, instance, os.Getpid()}
	data, _ := json.Marshal(s)
	path := filepath.Join(dir, "control.json")
	temporary := path + "." + instance
	file, err := os.OpenFile(temporary, os.O_CREATE|os.O_EXCL|os.O_WRONLY, 0600)
	if err != nil {
		return errors.New("cannot create new private desktop control file")
	}
	defer os.Remove(temporary)
	_, writeErr := file.Write(data)
	closeErr := file.Close()
	if writeErr != nil || closeErr != nil {
		return errors.New("cannot save desktop control file")
	}
	if os.Link(temporary, path) != nil {
		return errors.New("cannot publish new private desktop control file")
	}
	defer func() {
		current, e := os.ReadFile(path)
		if e == nil && bytes.Equal(current, data) {
			_ = os.Remove(path)
		}
	}()
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

func lanAddress() string {
	preferred := primaryInterface()
	interfaces, err := net.Interfaces()
	if err != nil {
		return ""
	}
	var candidates []string
	for _, iface := range interfaces {
		if iface.Flags&net.FlagUp == 0 || iface.Flags&net.FlagLoopback != 0 || iface.Flags&net.FlagPointToPoint != 0 {
			continue
		}
		addresses, _ := iface.Addrs()
		for _, address := range addresses {
			ip, _, err := net.ParseCIDR(address.String())
			if err != nil || ip.To4() == nil || !ip.IsPrivate() {
				continue
			}
			if iface.Name == preferred {
				return ip.String()
			}
			candidates = append(candidates, ip.String())
		}
	}
	if len(candidates) == 1 {
		return candidates[0]
	}
	return ""
}

func primaryInterface() string {
	if runtime.GOOS != "darwin" {
		return ""
	}
	ctx, cancel := context.WithTimeout(context.Background(), time.Second)
	defer cancel()
	data, err := exec.CommandContext(ctx, "/sbin/route", "-n", "get", "default").Output()
	if err != nil {
		return ""
	}
	for _, line := range strings.Split(string(data), "\n") {
		fields := strings.Fields(line)
		if len(fields) == 2 && fields[0] == "interface:" {
			return fields[1]
		}
	}
	return ""
}

func openBrowser(ctx context.Context, address string) error {
	var command *exec.Cmd
	switch runtime.GOOS {
	case "darwin":
		command = exec.CommandContext(ctx, "/usr/bin/open", address)
	case "windows":
		command = exec.CommandContext(ctx, "rundll32.exe", "url.dll,FileProtocolHandler", address)
	default:
		command = exec.CommandContext(ctx, "xdg-open", address)
	}
	command.Stdout = io.Discard
	command.Stderr = io.Discard
	return command.Run()
}
