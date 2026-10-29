package desktop

import (
	"os/exec"
	"syscall"
)

func detach(command *exec.Cmd) {
	// DETACHED_PROCESS gives the relay no inherited console. A new process
	// group keeps console cancellation of the launcher from targeting the relay.
	// This does not override a caller's Windows Job Object policy.
	const detachedProcess = 0x00000008
	command.SysProcAttr = &syscall.SysProcAttr{CreationFlags: detachedProcess | syscall.CREATE_NEW_PROCESS_GROUP}
}
