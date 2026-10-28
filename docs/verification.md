# Verification record

## Collection-request slice, 2026-10-28

The request core and JSON CLI were frozen at local source revision
`5d3caff0833ff52e805a4a874e7f07d82e39c624`. On macOS arm64 with Go 1.27.3:

- `go vet ./...` and `go test -race -cover ./...` passed. Core package coverage
  was 88.9%; CLI unit coverage was 42.8%. These are package numbers, not total
  product acceptance percentages.
- The compiled program passed 12 ordinary-transfer HTTP checks and 27 synthetic
  task-collection checks. The proposal scenario verifies request isolation,
  bounded/repeatable waiting, stable input IDs, a sample consumer's duplicate
  edit prevention, explicit cancellation and expiry. It is not an LLM run.
- Ten dependency-free Node VM checks passed for request/ordinary sender UI
  logic. A fake DOM is not a rendered browser or clipboard permission test.
- Final CLI regression tests distinguish interrupted waits, interrupted reads,
  unknown mutation outcomes, and oversized result rejection.
- Windows amd64 and Linux amd64 binaries built with `CGO_ENABLED=0`. They were
  cross-compiled, not executed on those platforms for this slice.

See [claims and evidence](claims-evidence.md) for command-level audit and
[the measured baseline](performance-baseline.md) for machine, raw data and limits.
The CI workflow includes the new scenarios, but the earlier remote CI run below
belongs to the prior text alpha and is not evidence for this local revision.
Browser, physical Android/iOS and actual Codex-host acceptance remain **NOT_RUN**.

## Follow-up use-path audit, 2026-10-28

An independent macOS arm64 / Go 1.27.3 cached build at local revision `2c3d695`
passed 37 README/Skill command checks in two private, independently owned
loopback services. These included the exact `15m`/16384-byte request flags, a real
ten-second pending wait followed by an empty read, later submission and stable
input reads, explicit cancellation, normal process exit, and control-file cleanup.
After clarifying the examples, all 14 POSIX shell blocks across both READMEs and
the Skill passed `sh -n`. The documentation now names its shell prerequisites,
Windows `.exe` output, fresh handle/PNG paths, service restart condition, and the
QR/submission step before reading. A Windows cross-build confirmed that an
explicit extensionless `-o` path produces a PE file without appending `.exe`;
Windows native execution was not performed.

`node scripts/smoke-ui.cjs --binary bin/ferry-dock` passed in two local runs
(2.634 and 2.728 seconds), with independent static review. This **SCRIPT_HTTP**
check obtains HTML and `app.js`
from the compiled service, verifies that the served script matches the working
source, and executes it with a narrow DOM adapter. It covers:

- CLI create → script prompt/input → real HTTP → CLI wait/read, A/B authority
  isolation, exact untrusted input, repeat reads, and received-form locking.
- Real accepted/deduplicated responses (201 then 200 with the same receipt)
  after dropping the first response inside the adapter; offline info/send
  injection and retry; real 401/410 responses retaining drafts.
- Ordinary computer-script session creation, two phone-script submissions,
  polling failure/recovery, incremental cursor, reload from retained history,
  and session closure. Copy checks the argument passed to a clipboard test
  double only.
- Normal completion stopped the test's processes and removed its private
  runtime files. The harness bounds its own failures/deadline; it does not promise
  cleanup after an uncatchable external kill.

The Go/application sources remain at the `5d3caff` freeze. This adds integration
evidence, not a product runtime change or a new performance baseline. Faults
are explicitly injected before a request or after its real HTTP response;
an actual network outage is not claimed. This is **not** rendered-browser,
OS-clipboard, physical-phone/LAN, QR-scan, or actual Codex-host acceptance.

Both READMEs put the Banner directly below the title. The light/dark SVG paths
exist in the local Git tree; 320×100 renders were visually inspected with clear
text and no clipping. This is a vector-render check, not a GitHub page or mobile
browser screenshot. The public branch still pointed to `13e5b27` during this
audit; a fresh public clone of this new slice and its remote CI remain unverified
until publication.

## Earlier ordinary-transfer slice

The transfer alpha has automated HTTP coverage and a compiled-program loopback
smoke test. These checks do not establish phone-browser or real-device behaviour.

## Local checks

Environment: macOS arm64, Go 1.27.3. The runtime toolchain and optional brand
renderer were installed under `/tmp`; no system runtime or network setting was
changed.

- `gofmt`, `go vet ./...`, `go test ./...`, and `go test -race -cover ./...`.
- `go build -trimpath -o bin/ferry-dock ./cmd/ferry-dock`.
- `node --check internal/relay/web/app.js`.
- `python3 scripts/smoke-http.py --binary bin/ferry-dock`: the compiled program
  starts on an ephemeral loopback port, then exercises creation, text fidelity,
  retry deduplication, owner retrieval, sender read/close denial, cross-origin
  rejection, closure, and expiry. It always terminates its own process.
- Embedded brand routes return SVGs; missing, nested, and HTML brand paths are
  rejected. The same canonical sources feed the binary and brand preview.

The brand PNG was rendered from SVG sources with resvg 2.6.2 and visually checked.
It contains no QR code or capability and is not a screenshot of the running UI.
Palette contrast calculations are recorded in [brand specifications](../brand/README.md).

## Windows formatting diagnosis

The [diagnostic CI run](https://github.com/Yankj/ferry-dock/actions/runs/40684823352)
prints the actual `gofmt -d` differences on both Windows versions. All three Go
files were reported; Linux and macOS passed. The removed and added source text
matched, which motivated a byte-level check rather than a source-format rewrite.

A separate checkout of the initial commit with repository-local
`core.autocrlf=true` produced `i/lf w/crlf` for those files. The original Git blobs
were already gofmt-clean. Formatting the CRLF copies produced output byte-for-byte
equal to those original blobs: the only differences removed CR bytes (97, 374,
and 501 respectively). For example, with line endings made visible:

```text
-package main\r\n
+package main\n
```

In a second independent checkout, keeping `core.autocrlf=true` and adding
`* text=auto eol=lf` produced `i/lf w/lf`; the formatting check passed. The project
now carries that `.gitattributes` rule. CI prints actual index/worktree line-ending
information and any future formatting diff instead of hiding the reason for a
failure. See the latest Actions run for the result on a real Windows runner.

## Browser and device acceptance

**NOT_RUN for the Ferry Dock revision.** During this audit, the supported
computer-use tool reported a locked desktop and no connected browser surface.
Installed browser applications and cached Chromium binaries were present;
the blocker was access through that tool/session, rather than missing browser
software.

The minimum condition for resuming UI acceptance is a manually unlocked Mac
and a supported isolated test tab/window through the computer-use tool. The
complete rendered receive/copy/paste loop, permission prompts, and phone-page
responsive layout remain unverified. The SCRIPT_HTTP result above does not
satisfy that gate.

Real Android and iOS LAN acceptance is also **NOT_RUN**. Before claiming mobile
compatibility, verify QR scan, text submission, exact copy, fallback selection,
network retry without duplicate delivery, expiry, and separate-session isolation
on the devices named in [the performance plan](performance.md).
