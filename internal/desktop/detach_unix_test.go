//go:build !windows

package desktop

import (
	"os/exec"
	"testing"
)

func TestDetachedRelayUsesOwnSession(t *testing.T) {
	command := exec.Command("not-executed")
	detach(command)
	if command.SysProcAttr == nil || !command.SysProcAttr.Setsid {
		t.Fatal("background relay would inherit the launcher's session")
	}
}
