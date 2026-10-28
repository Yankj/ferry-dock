// Package brand embeds the canonical Ferry Dock vector assets.
package brand

import "embed"

//go:embed logo-*.svg wordmark-*.svg favicon.svg
var Assets embed.FS
