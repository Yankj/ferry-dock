# Verification record

## App signature incident and alpha.3 correction

The supplied App-open screenshot led to a reproduced defect in the original
alpha.2 Mac App bundles. ZIP integrity, layout, modes and direct runtime checks
had passed, but complete arm64 bundle verification failed with
`code has no resources but signature indicates they must be present`; the
same binary outside the bundle verified successfully. The Intel App was unsigned.
This supersedes any interpretation of the earlier package-runtime passes as
complete App validity or downloaded first-launch acceptance. See the
[incident record](packaging-incident.md) for the actual diagnostics and boundary.

The alpha.3 source correction stages every resource before locally sealing the
complete new bundle, verifies it strictly, and archives those exact bytes.
Mac package checks now verify complete bundles reconstructed from ZIPs before
execution, with separate tamper-rejection regressions. Formal alpha.3 results
are recorded after the frozen build; the bundled documentation can therefore
predate those later evidence records. No Developer ID signing, notarization or
Gatekeeper pass is inferred from an ad-hoc resource seal.

Clean source `269af8e11e1b0099c6308d9d82887d31c58a4152` produced four macOS
archives: CLI and App for arm64 and amd64. The [artifact manifest](benchmarks/2026-10-29-alpha3-artifacts.json)
and [completed package check](benchmarks/2026-10-29-alpha3-native-validation.json)
record hashes/layout and both complete App strict-signature passes, followed by
the isolated Mac arm64 lifecycle/CLI/reuse/Quit/safety/cleanup pass. No browser
was opened. The [system-ditto regression](benchmarks/2026-10-29-alpha3-app-signature.json)
passed for the new arm64 App; altering Info.plist, a resource or the seal was
rejected, while the original alpha.2 comparison reproduced its signature error.
Two builds of the same source/toolchain produced [six identical outputs](benchmarks/2026-10-29-alpha3-reproducibility.json).
The arm64 App ZIP is 3,336,619 bytes, SHA-256
`654ab5a7e0b9aa585b2245b4b1b5cb0146e63c031ccb0ea63778562d95b5849f`.
It is a new private structural-test artifact, not a replacement public release.

A read-only signing-identity query listed zero valid code-signing identities;
no private key was used. Developer ID/notarization and normal downloaded-file
first-launch acceptance are still outstanding, so the test ZIP must not be
presented as a trusted ready-to-distribute application. No original archive,
user download, quarantine attribute or security setting was changed. Remote CI
for these local commits is NOT_RUN; no new public push was authorized.

## Local npm entry and fixed-tag Go install, 2026-10-29

The npm entry is implemented and locally tested, **not published to a registry**.
Candidate `ferry-dock@0.1.0-alpha.2` is not a reserved package name or ownership
claim. It contains the exact released Mac arm64 Go executable from `a351555`,
with a small Node 22+ entry that maps no arguments to `desktop`. Explicit
arguments retain the native interface. The [npm receipt](benchmarks/2026-10-29-npm-validation.json)
records **79 passing assertions** using existing Node 22.17.1 / npm 10.9.2 on
Mac arm64, without changing global tools or configuration:

- Offline local pack/install/exec with installation scripts disabled; private
  empty npm configuration, HOME, cache and installation prefix. Nine allowlisted
  files, executable modes and pinned binary hash matched; repacking preserved
  every packaged file byte. No install hook, dependency or runtime binary download.
- Literal Unicode, spaces, quotes and shell metacharacter arguments; JSON stdout
  and numeric exit codes. Missing, changed and unexecutable binaries failed clearly.
- Real SIGINT/SIGTERM to the known wrapper child and Ctrl+C through an owned
  controlling PTY ended request waiting with `wait_canceled` / 130 while leaving
  the collection pending. Ordinary text, request response, read, reuse warning,
  authenticated Quit, control cleanup and socket closure passed.
- No-argument `desktop` mapping and unsupported OS/CPU/old-Node rejection were
  VM checks. Actual default-browser opening, other-platform installation/signals,
  public registry `npx`, phone/LAN/QR and actual Codex host were not exercised.

The tested local tarball is **3,139,752 bytes**, SHA-256
`5a50504b7d726fa1fa80a31d9aae776db6e57c1b02a8daa635d1dfd6fedfc680`.
The wrapper's desktop notice does not detect a running backend's version:
current Go startup verifies instance authority and may reuse an older service.
It never automatically stops a shared service to upgrade it. npm publication
still needs a confirmed owner/namespace and authenticated publishing flow;
the selected environment's safe `npm whoami` returned `ENEEDAUTH`.

The [Go-install receipt](benchmarks/2026-10-29-go-install-validation.json) records
**31 passing assertions** after real
`go install github.com/Yankj/ferry-dock/cmd/ferry-dock@v0.1.0-alpha.2` with Go
1.27.3, fresh private GOBIN/module/build caches, the public Go proxy and checksum
service. `go version -m` and module origin establish tag `v0.1.0-alpha.2` and
source `a351555`. The command's own `version` reports `dev` / `unknown`, because
this source-install path omits the release packager's linker metadata.
Isolated `--no-open` startup/reuse, ordinary Unicode text, scoped request
create/wait/read/cancel, stable input ID, Quit and cleanup passed without
developer tools on the runtime PATH. The default build used CGO; a second
`CGO_ENABLED=0 CC=/nonexistent` install/version/help check passed without repeating
the full runtime suite. Cached source reinstall with `GOPROXY=off` attempted a
deprecation lookup and failed, so offline source installation is not promised.
Native Go 1.26, other OS/CPU source installation, GUI/phone/host acceptance remain
NOT_RUN. All services created by these checks were stopped.

## Published CLI download check, 2026-10-29

The [v0.1.0-alpha.2 prerelease](https://github.com/Yankj/ferry-dock/releases/tag/v0.1.0-alpha.2)
publishes only the Mac Apple Silicon CLI archive, a release-specific `SHA256SUMS`
and the original full-build `manifest.json`. The tag was read back as a commit
reference to `a351555ccd1615795bc2a6c10dd7e97a633a074f`; all three assets were
confirmed uploaded. App and other-platform packages remain unpublished.

All three public HTTPS asset URLs were downloaded without GitHub authentication
into a new private temporary directory. The [sanitized receipt](benchmarks/2026-10-29-public-download-validation.json)
records 21 assertions plus the existing 12 HTTP and 27 synthetic request checks
against that downloaded binary. Archive size/SHA, both entries of the release's
checksum list, original-manifest executable hash and `version` source/platform
identity matched. `serve` and all five request-operation help commands exited
zero. An isolated `desktop --no-open --state-dir PRIVATE --listen 127.0.0.1:0`
with private HOME and `PATH=/nonexistent` reached ready, reused its verified
instance, accepted synthetic sender text, returned the exact ordinary inbox
text and stopped with authenticated Quit, socket closure and control cleanup.

This was a command-line `curl` download and developer-machine execution, not a
browser-downloaded quarantine/Gatekeeper first-launch test. Observed archive and
binary xattr-name lists contained only `com.apple.provenance`, with no
`com.apple.quarantine` listed; no security attribute was removed. No GUI,
default-cache/browser automatic opening, OS clipboard, real phone/LAN/QR scan or
actual Codex host was exercised. Publication and successful command checks do
not accept those remaining paths. The binary and older bundled documentation
remain immutable at `a351555`; use the current online guides for availability.

## Repository usage-guide check, 2026-10-29

The English and Chinese [guides](usage.md) were added after the frozen alpha.2
package snapshot. They do not replace those archives or claim an executed Agent
host prompt. The [sanitized command receipt](benchmarks/2026-10-29-usage-validation.json)
records 30 local assertions against the existing Mac arm64 prebuilt CLI from
`a351555ccd1615795bc2a6c10dd7e97a633a074f`:

- Both guides' actual POSIX create/wait/status/read/cancel blocks executed. Only
  the established control path was replaced with this test's private path; the
  macOS `open` image-viewer command was omitted and remains NOT_RUN.
- Each language completed a real ten-second pending wait, then a synthetic HTTP
  phone submission, same-handle wait/read, exact Unicode and trust-marker checks,
  stable repeat-read ID, and explicit cancellation. The test's own desktop service
  ran with `--no-open --state-dir PRIVATE --listen 127.0.0.1:0`; authenticated Quit
  returned 202 and its control file was removed.
- All 21 repository Markdown documents passed 236 local image/link/anchor checks
  and all 29 POSIX shell blocks passed `sh -n`. Windows examples are syntax
  references, not a native execution pass. The scene illustration was inspected
  at full size and 320 px; it is not a browser screenshot.
- `go vet ./...`, `go test -race -cover ./...`, 12 HTTP, 27 synthetic request,
  11 VM and SCRIPT_HTTP checks passed locally. The first restricted-sandbox test
  could not bind its temporary listener; the authorized loopback run passed.
  A first tutorial harness expected an explicit null input for a pending read;
  the API omits that optional field, so the harness was corrected before passing.

No new GUI, Finder/default-browser, Gatekeeper, real phone/LAN/QR, Windows/Linux
native app, or actual Codex-host acceptance was performed. Those scopes remain
separate below. This repository's guides and illustration are newer than the
documentation bundled in the immutable alpha.2 preview.

## Current alpha.2 preview

Version `0.1.0-alpha.2` is a local preview frozen at clean source
`a351555ccd1615795bc2a6c10dd7e97a633a074f`, with black, white, and gray styling
and translucent UI layers. Transfer/request contracts and the one-Go-core
install form are unchanged. QR backgrounds and quiet zones remain opaque. The
implementation lead and package validator recorded these current-revision results:

| Alpha.2 check | Status and scope |
| --- | --- |
| Actual Safari desktop light | RECORDED_PASS: the black/white/gray desktop UI rendered; synthetic ordinary text sent through the UI appeared as one received item, and clicking Copy showed **Copied**. Actual OS paste was not repeated for this revision. |
| Local screenshot | An original CUA JPEG was saved at ignored `bin/previews/desktop-light.jpg`. It is a local evidence file, not a published image or package asset. The pictured QR was revoked by the later service shutdown. |
| Dark and phone-size GUI | BLOCKED at an interactive desktop authentication boundary. A read-only inventory recheck did not restore interactive access; GUI work remains paused without a retry or bypass. Neither rendering mode is recorded as passed. This is not a code or package failure. |
| Owned-service cleanup | RECORDED_PASS: API Quit returned 202, the socket closed, the control file was removed, and the owned QA files were cleaned. Private browser-window closure is deferred at the same GUI boundary. This was not the alpha.1 UI Quit case or zero-argument Finder acceptance. |
| Automated regression | RECORDED_PASS: Go tests, 12 compiled-program HTTP checks, 27 synthetic request checks, 11 UI VM checks, and SCRIPT_HTTP. These do not replace rendered mobile/dark UI or physical-phone/Agent-host acceptance. |
| Contrast | [Calculated source contrast](ui-contrast.md), not a pass for actual dark-mode browser rendering. |
| All eight final archives | RECORDED_PASS: archive/binary hashes, actual Mach-O/ELF/PE target headers, metadata, permissions and layouts. See the [manifest](benchmarks/2026-10-29-alpha2-artifacts.json) and [validation receipt](benchmarks/2026-10-29-alpha2-validation.json). |
| Mac arm64 packaged native lifecycle | RECORDED_PASS: app implicit flag dispatch without a `desktop` subcommand, Chinese/space path, private HOME and `PATH=/nonexistent`, readiness, CLI compatibility, reuse, Quit, stale recovery, occupied-port rejection, unknown-service/private-state preservation and owned cleanup. `smoke-package.py --require-all` exited zero; `--no-open --state-dir ... --listen 127.0.0.1:0` does not establish zero-argument Finder/default-cache or automatic browser opening. |
| Same-input rebuild and preservation | RECORDED_PASS: [two complete builds](benchmarks/2026-10-29-alpha2-reproducibility.json) from the same clean source/toolchain into different directories produced identical bytes for eight archives, manifest and checksums. All ten alpha.1 output hashes were unchanged. |

The Apple Silicon alpha.2 app ZIP is **3,290,056 bytes**, SHA-256
`5c872fa71f6376344397fbec91cf24d7f5e68c75a700a6227ee3ac8fc2c15051`.
Its manifest's `nativeValidation` fields are generation-time state; the separate
validation receipt records the later pass. Subsequent evidence-document commits
do not rebuild the artifacts or their bundled snapshot documentation.

No new alpha.2 startup timing is claimed; the 20-sample alpha.1 measurement below
belongs only to clean `3d6fca8`. Finder/default-cache discovery, default-browser
auto-opening, downloaded Gatekeeper acceptance, actual phone/LAN/QR, actual
Codex-host, and Intel Mac/Windows/Linux native execution remain **NOT_RUN**.
The blocked GUI checks were paused without a retry or bypass.

The complete alpha.1 Safari/system-copy-paste observations below remain historical
evidence for that revision, not a substitute for the unexecuted alpha.2 cases.

## Historical local packaging preview, 2026-10-29

Version `0.1.0-alpha.1` changes the user installation path to prebuilt macOS app
and native CLI archives; source builds are for contributors. It builds the same
`cmd/ferry-dock`, with desktop as the app's no-argument default, not another
backend. The immutable artifact source is clean commit
`3d6fca8c843281b9ab2806966fc2661e3cccbe52`; its final package checks passed.
This historical snapshot predates the next visual revision, which requires its
own acceptance. Actual Safari loopback acceptance is recorded separately below.
Alpha.1 has no GitHub Release or public artifact URL; the separate alpha.2 CLI
publication is recorded above.

The desktop contract is a short-lived launcher, one owned background Go service,
private owner/instance verification on reopen, browser opening, and explicit
**Quit Ferry Dock** from the local owner page. Closing the browser keeps the
service running. Default state is in the OS user cache under
`ferry-dock/runtime`; requests can reuse that private control file.

The [artifact manifest](benchmarks/2026-10-29-artifacts.json) identifies clean
source, all eight targets, embedded metadata, sizes, binary/archive hashes,
toolchain and signing state. Its `nativeValidation: NOT_RUN` fields were written
at generation time; the separate later
[desktop receipt](benchmarks/2026-10-29-desktop-preview.json) records completed
validation without rewriting that original manifest.

| Package check | Observed result at source `3d6fca8` |
| --- | --- |
| All eight archives | PASS: archive/binary hashes, Mach-O/ELF/PE target headers, metadata, permissions and layouts, including bundled docs/Skill. |
| Mac arm64 packaged executable | PASS: default-mode flag dispatch without a `desktop` subcommand, Chinese/space extraction path, private HOME and `PATH=/nonexistent`, version/readiness, CLI compatibility, reuse, Quit and stale recovery. Invocation used `--no-open --state-dir ... --listen 127.0.0.1:0`; this was not zero-argument Finder launch or default cache discovery. |
| Service safety and cleanup | PASS: an occupied explicit port was not taken over; unknown recorded service/private state remained untouched; verified owned processes stopped and private extracted/runtime files were removed. |
| Same-input rebuild | PASS: [two complete builds](benchmarks/2026-10-29-reproducibility.json) from the same clean source/toolchain into different directories produced identical bytes for all eight archives, `manifest.json`, and `SHA256SUMS`. No arbitrary cross-toolchain guarantee is inferred. |

The Apple Silicon app ZIP is **3,274,113 bytes**, SHA-256
`5fcec3986d47765b9a5b0c966c15be9723a58339160e6798a82f36afd6e746c0`.
Later evidence-document commits do not rebuild this snapshot.

The same receipt records **20 fresh process/private-state readiness samples**
on Apple M4 Pro, Darwin 27 arm64, 24 GiB RAM, Go 1.27.3: p50 **82.281 ms**,
p95 **85.225 ms**, maximum **98.025 ms**, zero recorded errors, unique instances
and successful Quit/cleanup for every sample. Timing begins immediately before
invoking the packaged app and ends after launcher exit-zero, private control
read, and authenticated HTTP instance validation. `--no-open`, an explicit
`127.0.0.1:0` listener, private HOME/state and `PATH=/nonexistent` were used.
OS/filesystem caches were not flushed; background desktop load was uncontrolled.
This excludes LAN discovery, browser opening/rendering, phone/QR, OS trust prompts
and Agent execution, and is not an OS cold-boot measurement or platform ranking.

Publisher signing, notarization, downloaded-file Gatekeeper, Finder/no-argument
default-cache launch, default-browser auto-opening, real-phone LAN/QR scan, and
actual Codex-host workflows remain **NOT_RUN**. A Safari page opened explicitly
for the tests below is not the default-browser launch chain.

See [distribution](distribution.md) and [packaging claims](claims-evidence.md).
The older results below are preserved with their source/binary identities. They
do not establish the packaged launch results above or a downloaded package's
first-use experience. The older core-startup baseline and this app-readiness
measurement have different definitions and must not be compared as one metric.

## Actual Safari loopback acceptance, 2026-10-29

The implementation lead exercised Safari 27.0.1 on the Mac through the supported
computer-use surface, in an independent private window and against an owned
loopback service. These are **RECORDED_PASS** observations, not a physical-phone,
Finder, or packaged-download test. No OS security protection or browser privacy
setting was lowered for this run.

| Case | Observed result |
| --- | --- |
| S1: ordinary transfer and system clipboard | Text sent and appeared in the receiver; Copy showed **Copied**. A real system Cmd+V pasted the original leading/trailing whitespace, newlines, Chinese, emoji, and literal HTML text. Clipboard was not merely a test double. |
| S2: request flow after bounded timeout | Task A's prompt displayed; submission changed the form to **Received**, disabled send, and made the textarea read-only. The initial CLI ten-second wait had timed out; a later wait/read through the same handle returned received state and exact text. Refresh kept the received form locked against another send. |
| S3: ended-page states | An expired request and invalid-token page displayed ended/disabled states while the textarea remained editable. These initial-page cases are not an in-flight failed-network/dropped-response test. |
| S4: layout sample | Safari Responsive Design Mode at 390×844 was visually inspected from an actual screenshot, without observed cropping or overlap. This is desktop Safari viewport emulation, not an iPhone/Android or software-keyboard test. |
| S5: UI Quit and owned cleanup | Clicking **Quit Ferry Dock** showed stopped status. The socket then refused connections and the owned control file was removed. The test's own files were cleaned and its private window closed. Normal Quit does not promise to remove the default cache directory or `startup.log`. |
| S6: same-tab invitation change, fresh binary | After fixing hash-change handling, a fresh compiled binary was retested in Safari. Replacing hash A with hash B in the same `/send` tab, without manually reloading, immediately showed B. Submission left A pending with no input; B alone received the intended text. The owned window/service/control/files were cleaned. |

The same-tab fix also passed the eleventh UI VM regression. The latest working
tree passed `go vet ./...`, `go test -race -cover ./...`, the 12-check ordinary
HTTP smoke, 27-check synthetic request scenario, and SCRIPT_HTTP integration.
Recorded unit coverage was relay 88.4%, CLI 41.3%, desktop 21.1%; these package
figures are not product or UI acceptance percentages. The final package record
above separately identifies its clean source and artifact identities.

Remaining UI/device gates include Finder/default-cache first launch, automatic
system-browser opening, physical-phone LAN/QR scan, other browsers, actual
in-flight network failure/retry, unexercised clipboard permission/fallback paths,
Gatekeeper/download trust, and actual Codex-host execution. None is inferred
from S1–S6 or a VM/SCRIPT_HTTP pass.

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
At that earlier freeze, browser, physical Android/iOS and actual Codex-host
acceptance were **NOT_RUN**; the later Safari-only evidence is recorded above.

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

At that follow-up audit, the Go/application sources remained at the `5d3caff`
freeze. It added integration evidence, not a runtime change or a new performance
baseline; the later desktop/packaging revision is recorded separately above. Faults
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

## Earlier blocked browser attempt

Before the later Safari run above, the supported
computer-use tool reported a locked desktop and no connected browser surface.
Installed browser applications and cached Chromium binaries were present;
the blocker was access through that tool/session, rather than missing browser
software.

That attempt required a manually unlocked Mac and a supported isolated test
tab/window. It did not perform rendered UI acceptance; SCRIPT_HTTP was not used
as a substitute. Actual Safari cases subsequently completed are listed above,
with their remaining limitations.

Real Android and iOS LAN acceptance is also **NOT_RUN**. Before claiming mobile
compatibility, verify QR scan, text submission, exact copy, fallback selection,
network retry without duplicate delivery, expiry, and separate-session isolation
on the devices named in [the performance plan](performance.md).
