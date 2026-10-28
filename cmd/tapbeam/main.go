// Tapbeam runs a local, ephemeral text inbox.
package main

import (
	"context"
	"flag"
	"fmt"
	"log"
	"net"
	"net/http"
	"net/url"
	"os"
	"os/signal"
	"strings"
	"syscall"
	"time"

	"github.com/Yankj/tapbeam/internal/relay"
)

func main() {
	if err := run(); err != nil {
		log.Fatal(err)
	}
}

func run() error {
	listen := flag.String("listen", "127.0.0.1:8787", "HTTP listen address (LAN access must be enabled explicitly)")
	publicURL := flag.String("public-url", "", "phone-accessible HTTP origin, e.g. http://192.168.1.10:8787")
	ttl := flag.Duration("ttl", 15*time.Minute, "session lifetime (maximum 24h)")
	flag.Parse()
	host, _, err := net.SplitHostPort(*listen)
	if err != nil {
		return fmt.Errorf("invalid listen address: %w", err)
	}
	ip := net.ParseIP(host)
	loopback := ip != nil && ip.IsLoopback()
	if host == "localhost" {
		loopback = true
	}
	if !loopback && *publicURL == "" {
		return fmt.Errorf("LAN listeners require -public-url with the address your phone can reach")
	}
	if *ttl <= 0 || *ttl > 24*time.Hour {
		return fmt.Errorf("ttl must be greater than zero and at most 24h")
	}
	owner, err := relay.NewToken()
	if err != nil {
		return err
	}
	listener, err := net.Listen("tcp", *listen)
	if err != nil {
		return err
	}
	defer listener.Close()
	_, port, _ := net.SplitHostPort(listener.Addr().String())
	localURL := "http://" + net.JoinHostPort("127.0.0.1", port)
	if addr, ok := listener.Addr().(*net.TCPAddr); ok && !addr.IP.IsUnspecified() {
		localURL = "http://" + net.JoinHostPort(addr.IP.String(), port)
	}
	if *publicURL == "" {
		*publicURL = localURL
	}
	app, err := relay.New(relay.Config{OwnerToken: owner, LocalURL: localURL, PublicURL: *publicURL, TTL: *ttl})
	if err != nil {
		return err
	}
	server := &http.Server{Handler: app, ReadHeaderTimeout: 5 * time.Second, ReadTimeout: 15 * time.Second, WriteTimeout: 15 * time.Second, IdleTimeout: 30 * time.Second, MaxHeaderBytes: 16 << 10}
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()
	done := make(chan error, 1)
	go func() { done <- server.Serve(listener) }()
	fmt.Printf("Tapbeam · alpha\n\nOpen on this computer:\n%s/#owner=%s\n\n", localURL, url.QueryEscape(owner))
	if loopback {
		fmt.Println("Local-only mode. For phone access, restart with -listen 0.0.0.0:8787 -public-url http://YOUR_LAN_IP:8787")
	} else {
		fmt.Printf("Phone origin: %s\nUse only on a trusted LAN: HTTP does not encrypt content or capabilities.\n", strings.TrimRight(*publicURL, "/"))
	}
	fmt.Println("Content stays in memory. Ctrl+C ends every session.")
	ticker := time.NewTicker(30 * time.Second)
	defer ticker.Stop()
	for {
		select {
		case <-ticker.C:
			app.PurgeExpired()
		case err := <-done:
			if err != http.ErrServerClosed {
				return err
			}
			return nil
		case <-ctx.Done():
			shutdown, cancel := context.WithTimeout(context.Background(), 5*time.Second)
			defer cancel()
			return server.Shutdown(shutdown)
		}
	}
}
