// Package buildinfo describes the exact packaged executable without network access.
package buildinfo

import "runtime"

var Version = "dev"
var Commit = "unknown"
var DefaultMode = "serve"

type Info struct {
	Version     string `json:"version"`
	Commit      string `json:"commit"`
	OS          string `json:"os"`
	Arch        string `json:"arch"`
	DefaultMode string `json:"defaultMode"`
}

func Current() Info { return Info{Version, Commit, runtime.GOOS, runtime.GOARCH, DefaultMode} }
