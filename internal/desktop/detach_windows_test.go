package desktop

import (
	"os/exec"
	"syscall"
	"testing"
)

func TestDetachedRelayDoesNotInheritConsoleCancellation(t *testing.T) {
	command := exec.Command("not-executed.exe")
	detach(command)
	const detachedProcess = 0x00000008
	if command.SysProcAttr == nil || command.SysProcAttr.CreationFlags != detachedProcess|syscall.CREATE_NEW_PROCESS_GROUP {
		t.Fatal("background relay would inherit launcher console or process group")
	}
}
