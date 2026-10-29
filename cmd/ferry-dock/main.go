// Ferry Dock runs one local text service with ordinary and task-bound inputs.
package main

import (
	"context"
	"os"
	"os/signal"
	"strings"
	"syscall"

	"github.com/Yankj/ferry-dock/internal/buildinfo"
)

func main() {
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()
	args := os.Args[1:]
	if buildinfo.DefaultMode == "desktop" && (len(args) == 0 || (strings.HasPrefix(args[0], "-") && args[0] != "--version")) {
		args = append([]string{"desktop"}, args...)
	}
	os.Exit(runCLI(ctx, args, os.Stdout, os.Stderr))
}
