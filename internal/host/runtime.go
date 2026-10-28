// Package host owns the single HTTP process shared by the ordinary and task flows.
package host

import (
	"context"
	"fmt"
	"net"
	"net/http"
	"sync"
	"time"

	"github.com/Yankj/ferry-dock/internal/relay"
)

type Options struct {
	Listen, PublicURL string
	TTL               time.Duration
}

type Runtime struct {
	App                             *relay.Server
	LocalURL, PublicURL, OwnerToken string
	server                          *http.Server
	listener                        net.Listener
	cancel                          context.CancelFunc
	done                            chan error
	once                            sync.Once
}

func Start(options Options) (*Runtime, error) {
	if options.Listen == "" {
		options.Listen = "127.0.0.1:8787"
	}
	host, _, err := net.SplitHostPort(options.Listen)
	if err != nil {
		return nil, fmt.Errorf("invalid listen address: %w", err)
	}
	ip := net.ParseIP(host)
	loopback := host == "localhost" || (ip != nil && ip.IsLoopback())
	if !loopback && options.PublicURL == "" {
		return nil, fmt.Errorf("LAN listeners require -public-url with the address your phone can reach")
	}
	if options.TTL <= 0 || options.TTL > 24*time.Hour {
		return nil, fmt.Errorf("ttl must be greater than zero and at most 24h")
	}
	owner, err := relay.NewToken()
	if err != nil {
		return nil, err
	}
	listener, err := net.Listen("tcp", options.Listen)
	if err != nil {
		return nil, err
	}
	closeOnError := true
	defer func() {
		if closeOnError {
			_ = listener.Close()
		}
	}()
	addr := listener.Addr().(*net.TCPAddr)
	localIP := addr.IP
	if localIP.IsUnspecified() {
		localIP = net.ParseIP("127.0.0.1")
	}
	localURL := "http://" + net.JoinHostPort(localIP.String(), fmt.Sprint(addr.Port))
	if options.PublicURL == "" {
		options.PublicURL = localURL
	}
	app, err := relay.New(relay.Config{OwnerToken: owner, LocalURL: localURL, PublicURL: options.PublicURL, TTL: options.TTL})
	if err != nil {
		return nil, err
	}
	ctx, cancel := context.WithCancel(context.Background())
	runtime := &Runtime{App: app, LocalURL: localURL, PublicURL: options.PublicURL, OwnerToken: owner, listener: listener, cancel: cancel, done: make(chan error, 1)}
	runtime.server = &http.Server{Handler: app, ReadHeaderTimeout: 5 * time.Second, ReadTimeout: 15 * time.Second, WriteTimeout: 15 * time.Second, IdleTimeout: 30 * time.Second, MaxHeaderBytes: 16 << 10}
	go func() { runtime.done <- runtime.server.Serve(listener) }()
	go func() {
		ticker := time.NewTicker(30 * time.Second)
		defer ticker.Stop()
		for {
			select {
			case <-ticker.C:
				app.PurgeExpired()
			case <-ctx.Done():
				return
			}
		}
	}()
	closeOnError = false
	return runtime, nil
}

func (r *Runtime) Done() <-chan error { return r.done }

func (r *Runtime) Close(ctx context.Context) error {
	var err error
	r.once.Do(func() { r.cancel(); err = r.server.Shutdown(ctx); _ = r.listener.Close() })
	return err
}
