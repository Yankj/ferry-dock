# Claims and evidence

## Current usage instructions

The [English](usage.md) and [Chinese](usage.zh-CN.md) guides and README scenario
illustration describe current executable operations, while preserving the frozen
alpha.2 archive/documentation snapshot. See the [usage audit](verification.md#repository-usage-guide-check-2026-10-29)
and its [30-check receipt](benchmarks/2026-10-29-usage-validation.json).

| Instruction | Implementation / evidence | Status and boundary |
| --- | --- | --- |
| Fresh computer page creates the ordinary QR without an initial New session click. | Final `present()` and `create.click()` in [app.js](../internal/relay/web/app.js); existing served-script/HTTP checks. | SOURCE_REVIEWED and existing SCRIPT_HTTP pass. This does not establish Finder/default-browser launch or physical scanning. |
| Task creation writes a separate PNG; the user/Agent must display it. | `qrPath` output in [cli.go](../cmd/ferry-dock/cli.go); guide command audit. | PASS_LOCAL for saved PNG and request commands; image-viewer `open` is NOT_RUN. No automatic QR display or ordinary-inbox delivery is implied. |
| The documented request can time out, then receive/read through the same handle. | Both guide POSIX blocks against frozen `a351555` native CLI; usage receipt. | PASS_LOCAL: two real ten-second pending waits, synthetic HTTP submissions, exact text/trust and stable input ID, cancel and own-service cleanup. No phone or Agent host was used. |
| Bundled Skill can be read manually using its actual path. | Package layout receipts, [Skill](../skills/ferry-dock/SKILL.md), source-reviewed prompt paths. | SOURCE_REVIEWED instructions. No automatic discovery, installation, image display, host wake-up or executed Codex-host prompt is asserted. |

## Current alpha.2 preview

Version `0.1.0-alpha.2` is a verified local packaging snapshot of clean source
`a351555ccd1615795bc2a6c10dd7e97a633a074f`. Its black, white, and gray styling
and translucent layers do not change the transfer/request contract or introduce
a second backend. QR backgrounds and quiet zones remain opaque. Its
[manifest](benchmarks/2026-10-29-alpha2-artifacts.json),
[validation receipt](benchmarks/2026-10-29-alpha2-validation.json), and
[rebuild receipt](benchmarks/2026-10-29-alpha2-reproducibility.json) are independent
of the historical alpha.1 evidence below. Later evidence-document commits do not
rebuild these artifacts or their bundled snapshot documentation; generation-time
manifest `nativeValidation` fields are not the subsequent validation result.

| Current-revision claim | Evidence | Status and limit |
| --- | --- | --- |
| Desktop-light ordinary transfer renders and completes the UI path. | Implementation lead's actual Safari run in [verification](verification.md); original ignored CUA JPEG `bin/previews/desktop-light.jpg`. | RECORDED_PASS for rendering, synthetic UI text send → one received item → Copy label **Copied**. Actual OS paste was not repeated; the JPEG is not a public asset. |
| Dark/phone-size GUI acceptance is complete. | GUI work paused at an interactive desktop authentication boundary; a read-only inventory recheck did not restore access. | BLOCKED, no retry/bypass and no pass inferred. [Calculated contrast](ui-contrast.md) is source evidence, not actual dark-browser rendering. The blocker is not a code/package failure. |
| The owned alpha.2 QA service was stopped. | Implementation lead's API Quit/cleanup in verification. | RECORDED_PASS: HTTP 202, socket closed, control removed, own QA files cleaned. The screenshot QR is revoked; private browser-window closure is deferred at the GUI boundary. This is not a new UI Quit or Finder/default-cache pass. |
| Automated regression remains passing. | Implementation lead's Go tests and compiled/script checks in verification. | RECORDED_PASS: 12 HTTP / 27 synthetic request / 11 UI VM / SCRIPT_HTTP. No physical-phone, real Codex-host, OS paste, dark-mode or phone-size pass is inferred. |
| All eight alpha.2 packages passed archive checks. | Alpha.2 manifest and validation receipt above. | RECORDED_PASS: archive/binary hashes, actual Mach-O/ELF/PE target headers, metadata, permissions and layouts. Native execution on all eight targets is not implied. |
| Mac arm64 packaged native lifecycle passed. | `smoke-package.py --require-all`, exit zero, alpha.2 validation receipt. | RECORDED_PASS: implicit app flags without `desktop`, Chinese/space extraction path, private HOME and `PATH=/nonexistent`, readiness, CLI compatibility, reuse, Quit, stale recovery, occupied-port/unknown-service safety and cleanup. Uses `--no-open --state-dir ... --listen 127.0.0.1:0`; Finder/default-cache/default-browser auto-opening remain NOT_RUN, as do Intel Mac/Windows/Linux native execution. |
| Alpha.2 rebuild output is byte-identical under the recorded inputs. | Alpha.2 rebuild receipt above. | RECORDED_PASS: two complete builds with the same clean source/toolchain into different directories matched all ten outputs; alpha.1's ten output hashes remained unchanged. This is not an arbitrary cross-toolchain guarantee. |
| The alpha.2 Apple Silicon app ZIP is 3,290,056 bytes. | Manifest entry `ferry-dock-0.1.0-alpha.2-darwin-arm64-app.zip`, SHA-256 `5c872fa71f6376344397fbec91cf24d7f5e68c75a700a6227ee3ac8fc2c15051`. | RECORDED_PASS for the frozen local artifact, not a public download or signed/notarized release. |
| Alpha.1 startup measurements also describe alpha.2. | Alpha.2 receipt explicitly marks startup benchmark NOT_REPEATED. | Unsupported. No new alpha.2 readiness timing is claimed; preserve the older 20-sample result with its alpha.1 `3d6fca8` identity. |

## Historical local packaging preview, 2026-10-29

The packaged delivery uses one Go command for both native CLI archives and the
macOS app, with `DefaultMode=desktop` for the app. Version `0.1.0-alpha.1` is a
verified historical local preview from clean source
`3d6fca8c843281b9ab2806966fc2661e3cccbe52`, not a published GitHub Release.
It predates the next visual revision; newer sources need their own evidence.
The [manifest](benchmarks/2026-10-29-artifacts.json),
[package/native/readiness receipt](benchmarks/2026-10-29-desktop-preview.json),
and [same-input rebuild receipt](benchmarks/2026-10-29-reproducibility.json)
record the completed checks. Manifest `nativeValidation` fields describe
generation-time state; the later receipt records scoped native results without
rewriting it. Actual Safari loopback S1–S6 observations are recorded in
[verification](verification.md). They do not establish Finder/default-cache,
default-browser auto-opening, Gatekeeper, physical-phone/LAN/QR, or real
Codex-host acceptance. [Distribution](distribution.md) records final artifact
evidence separately. Earlier executions keep their source/binary identities.

| Packaging/runtime claim | Source or evidence | Current status and limit |
| --- | --- | --- |
| Preview users can run a prebuilt app/CLI without installing Git, Go, or Node. | [Same Go command](../cmd/ferry-dock/main.go), [build metadata](../internal/buildinfo/version.go), [packager](../scripts/package.py), desktop receipt. | RECORDED_PASS for Mac arm64 packaged app/CLI with private HOME and `PATH=/nonexistent`. All eight archives passed structural checks; other targets' native execution remains NOT_RUN. Packagers still need developer tools. |
| The macOS app is the same Go executable with desktop as its no-argument default, not a Swift/Node backend. | `DefaultMode` dispatch in [main.go](../cmd/ferry-dock/main.go), linker flags and bundle executable in [package.py](../scripts/package.py), desktop receipt. | RECORDED_PASS for Mac arm64 default-mode flag dispatch without a `desktop` subcommand. App path is `Ferry Dock.app/Contents/MacOS/ferry-dock`; zero-argument Finder/browser acceptance is separate and NOT_RUN. |
| Native archives and app Resources include docs and a manual local Skill. | `documentation()` and archive entries in [package.py](../scripts/package.py); [Skill path resolution](../skills/ferry-dock/SKILL.md); desktop receipt. | RECORDED_PASS for all eight archive layouts. No global Skill, PATH, login item, or Agent configuration was installed by these checks; actual Codex-host use is NOT_RUN. |
| The launcher starts/reopens its own background Go service, opens the browser, and exits. Closing the browser does not quit. | `Run`, detached child, private readiness and `openBrowser` in [desktop.go](../internal/desktop/desktop.go); desktop controls in [app.js](../internal/relay/web/app.js). | SOURCE_REVIEWED for launch. Safari UI Quit has RECORDED_PASS S5; automatic default-browser opening and Finder/default-cache launch remain NOT_RUN. |
| Relaunch verifies the owner capability/instance ID and serializes startup instead of taking over an unknown service. | Startup lock, `readState`, `existing`, and `verify` in [desktop.go](../internal/desktop/desktop.go); desktop receipt. | RECORDED_PASS for Mac arm64 reuse, stale recovery, occupied-port rejection and unknown-service/private-state preservation. Startup serialization is source-reviewed; this is not a blanket concurrency or other-platform pass. |
| Default desktop LAN mode listens on all IPv4 interfaces at a free port, advertises an eligible private IPv4, and falls back visibly to a loopback listener when ambiguous/unavailable. | `lanAddress`, `primaryInterface`, `runService` and [desktop network UI](../internal/relay/web/app.js). | SOURCE_REVIEWED. Selection controls the advertised URL; this is not phone reachability or LAN acceptance. Reused instances retain their configuration; foreground `serve` retains its loopback default. |
| Quit is an owner/loopback-authenticated operation and clears the service's in-memory sessions/requests. | Desktop handlers in [server.go](../internal/relay/server.go), `DesktopConfig.Quit`, `runService`, desktop receipt, and Safari S5. | RECORDED_PASS for actual Safari click → stopped message, socket refusal and owned control-file cleanup, plus Mac arm64 packaged lifecycle/cleanup. Private cache/startup.log may remain; secure erasure is not promised. |
| `version` returns version, commit, OS, architecture and default mode without a model/network call. | `buildinfo.Current` and command dispatch in [cli.go](../cmd/ferry-dock/cli.go), artifact manifest and desktop receipt. | RECORDED_PASS for Mac arm64 app/CLI output and all-target archive metadata; SOURCE_REVIEWED for no model/network call. A version label is not Release publication or publisher identity. |
| The eight local archives have recorded identities and a same-input rebuild result. | Artifact manifest and rebuild receipt above. | RECORDED_PASS: all eight archive/binary hashes, target headers, metadata, permissions and layouts; two complete builds matched all ten outputs byte-for-byte. Scope is the same clean source/toolchain, not arbitrary build environments. |
| The Apple Silicon app ZIP is 3,274,113 bytes. | `darwin-arm64-app.zip` entry in the artifact manifest, SHA-256 `5fcec3986d47765b9a5b0c966c15be9723a58339160e6798a82f36afd6e746c0`. | RECORDED_PASS for the fixed alpha.1 artifact. Later documentation/UI changes do not rebuild it or inherit its checks. |
| Packaged app readiness has a measured local baseline. | Desktop receipt: 20 fresh process/private-state samples, Apple M4 Pro / Darwin arm64 / Go 1.27.3, `--no-open --state-dir ... --listen 127.0.0.1:0`. | RECORDED_MEASUREMENT: p50 82.281 ms, p95 85.225 ms, maximum 98.025 ms; zero recorded errors, every instance quit/cleaned. Definition includes launcher exit-zero, control read and authenticated HTTP instance validation. Caches were not flushed; excludes browser/Finder/default-cache/Gatekeeper/LAN discovery/phone/Agent, not OS cold boot or a platform ranking. |
| Local artifacts have public Release/download URLs. | Packaging has no upload/publication step. | NOT_PUBLISHED. Do not fabricate links or call a generated local archive a public release. |
| Local app generation proves Developer ID signing, Apple notarization or Gatekeeper/Finder acceptance. | Packager performs no publisher signing or notarization; signature metadata is recorded separately. | Unsupported. Ad-hoc linker signing is not verified publisher identity. Finder/default-browser auto-opening/quarantine/Gatekeeper remain NOT_RUN; separate Safari UI evidence does not establish them. |
| Earlier HTTP/CLI tests and performance results validate the new app's launch/first-use experience. | Historic source/binary records below and [prior baseline](performance-baseline.md). | Unsupported. Preserve those scopes; new packaging/native/UI results need their own evidence. |

## Earlier text/request audit

This audit maps public product statements to implementation and verification.
It does not turn a design contract, a test definition, or an intended command
into an executed result. Audit date: 2026-10-28. The independent local checks below
used macOS arm64 and Go 1.27.3 against the collection-request working tree based
on `13e5b27435c3f35578398570667328396b41ff88`. The final CLI changes were rebuilt
and checked separately at frozen commit
`5d3caff0833ff52e805a4a874e7f07d82e39c624` (E8). Browser, real-phone, and actual
Codex-host acceptance were **NOT_RUN** during those earlier executions; later
Safari-only observations are recorded separately in verification S1–S6.

## Reading the status column

- **SOURCE_REVIEWED:** the named source supports the stated behavior; no passing
  behavioral result beyond the specifically named checks is asserted.
- **PASS_LOCAL:** this audit independently executed the named local check; its
  stated scope excludes browser, physical-phone, and actual Agent-host behavior.
- **RECORDED_PASS:** a completed check is named in the verification record. Its
  scope and revision matter; it does not imply a phone or Agent-host test.
- **RECORDED_MEASUREMENT:** the named report/raw artifact was checked for
  consistency; observations retain that run's conditions and are not guarantees.
- **NOT_RUN:** acceptance or a command has not been executed for this audit.
- **OUT_OF_SCOPE:** the behavior is deliberately absent from this delivery.

The earlier ordinary-transfer checks in [verification](verification.md) are
recorded evidence for that slice. Current collection evidence comes from the
separate executions below. A passing test definition and an executed real host
workflow are different kinds of evidence.

## Independent execution record

The runtime executable for this audit was built in a private `/tmp` directory so
that it did not replace another worker's binary. Go used existing `/tmp` caches
with `GOPROXY=off`; this verifies a cached build, not a fresh offline installation.

| ID | Executed check | Result |
| --- | --- | --- |
| E1 | `go build -trimpath -o /tmp/ferry-dock-claims-audit/ferry-dock ./cmd/ferry-dock` using Go 1.27.3 | PASS_LOCAL; no build diagnostics. |
| E2 | Compiled `serve --help` and `request create/status/wait/read/cancel --help` | PASS_LOCAL; examples match actual flags. Both TTL flags accept duration syntax; request TTL must be an integral number of seconds (`15m` or `900s`, not bare `900`). |
| E3 | `python3 scripts/smoke-request.py --binary /tmp/ferry-dock-claims-audit/ferry-dock` | PASS_LOCAL: **27 synthetic task-collection checks**. Includes POSIX SIGINT of wait, request isolation, repeat IDs, sample proposal edit deduplication, cancel/expiry, limits, and private control-file cleanup. |
| E4 | `python3 scripts/smoke-http.py --binary /tmp/ferry-dock-claims-audit/ferry-dock` | PASS_LOCAL: **12 compiled-program HTTP checks**, loopback only. |
| E5 | `node scripts/test-ui.cjs` | PASS_LOCAL: **10/10 UI VM checks**. Uses a narrow fake DOM, not a rendered browser. |
| E6 | `go test ./...` with Go 1.27.3 | PASS_LOCAL for the command and relay packages; brand/host report no test files. This independent run was not race-instrumented. |
| E7 | Private-loopback README/Skill CLI exercise with `--ttl 15m --max-bytes 16384`, then status, zero-second wait, cancel, and read | PASS_LOCAL: **9 checks** including 900-second expiry, QR PNG, pending semantics, canceled input removal, rejection of bare `--ttl 900`, and normal control-file cleanup. Logs and capabilities were not printed. |
| E8 | Rebuild at `5d3caff0833ff52e805a4a874e7f07d82e39c624`, then `go test ./cmd/ferry-dock -run 'TestInterruptedCancelReportsUnknownMutationOutcome\|TestWaitInterruptedDuringResponseBodyIsStillWaitCanceled\|TestRequestReadNeverTruncatesOversizedResult' -count=1` | PASS_LOCAL: final targeted CLI regression, 0.379 s. This final check covered the changes made after E1–E7, without repeating a load suite. |
| E9 | Independent private cached build at `2c3d695`, README/Skill command exercise, and final POSIX shell syntax check | PASS_LOCAL: 37 command/retention/cleanup checks, including the real 10-second pending wait and later collection. All 14 final shell blocks passed syntax checking. A Windows PE cross-build confirms the explicit `.exe` documentation; native execution is NOT_RUN. |
| E10 | `node scripts/smoke-ui.cjs --binary bin/ferry-dock` against the unchanged Go/application freeze | PASS_LOCAL: SCRIPT_HTTP, 2.634 s, independently also 2.728 s. The served script, DOM adapter, compiled service, real HTTP and CLI complete request and ordinary paths. Offline/response-loss faults are local injection; clipboard is a test double. Rendered browser, actual network outage, phone/LAN, QR scan and Codex host are NOT_RUN. |

The managed sandbox initially prevented temporary `127.0.0.1`/`::1` listener
binding. Those attempts did not enter the HTTP assertions. E3, E4 and E6 passed
when rerun in the approved environment permitting their own short-lived loopback
listeners; no network settings were changed. An initial E7 harness attempt hit
Python 3.9's variable fractional-second timestamp parsing limit. Normalizing that
harness's timestamp comparison produced the nine-check pass; this was not a
service failure.

The implementation worker also recorded the following at the final freeze; see
[verification](verification.md). They are **RECORDED_PASS**, separate from this
auditor's own E1–E8 executions: `go vet ./...`, `go test -race -cover ./...`
(relay 88.9%, CLI 42.8%), another 27-check synthetic scenario on the frozen binary,
and `CGO_ENABLED=0` cross-builds for Windows amd64 and Linux amd64. Package coverage
is not a product acceptance percentage. Cross-builds were not native execution,
and the new local slice has no completed remote CI result claimed here.

## Recorded performance baseline

The performance worker completed one [formal run](performance-baseline.md) with
[raw JSON](benchmarks/2026-10-28-macos-arm64.json). This auditor read the artifacts
and recomputed nearest-rank p50/p95/p99/max for all eight reported latency
distributions; counts and summaries agree. The raw file SHA-256 matches its
report (`55d57ce416b6d1a0c1447da2356b135f1cc05a683f38e7e21a96931df5798a85`).
The baseline was not rerun for this audit.

- Environment: Apple M4 Pro/macOS arm64, Go 1.27.3, loopback HTTP, non-race binary
  with embedded revision `5d3caff` and `vcs.modified=true`. This is not a clean
  tagged-release build. The binary SHA-256 was unchanged after measurement.
- Across 100 process starts, p95 was **8.091 ms**, p99 **12.718 ms**, and the first
  and maximum sample **479.428 ms**. The maximum's cause is unknown; p95 is not an
  “every startup takes 8 ms” guarantee.
- Empty-process RSS after 60.012 seconds was **11.86 MiB**. The highest observed
  sample when retaining 16 MiB of ordinary text was **45.17 MiB**, unchanged about
  0.5 seconds after closure. Sampling is not a proven high-water bound; no
  immediate OS reclamation or leak diagnosis is implied.
- There were no unexpected HTTP errors. Ordinary text used ten clients and 1,000
  successful 1 KiB submit/read cycles per phase; request operations had only 32
  samples. The pending-wait phase verified eight occupied wait slots and ended
  them through explicit cancellation. Short local workloads do not establish
  sustained capacity, causal wait overhead, or stable production tail latency.

These are **recorded conditional observations**, not universal performance
guarantees, a cross-language ranking, real LAN throughput, phone tap-to-display
latency, or Agent/model processing speed.

## Product and runtime

| Claim | Source or test evidence | Status and limit |
| --- | --- | --- |
| Basic phone-to-computer text transfer does not require AI, an Agent account, or a Skill. | [Service entry point](../cmd/ferry-dock/main.go), [ordinary session routes](../internal/relay/server.go), [browser UI](../internal/relay/web/app.js). | SOURCE_REVIEWED. A running program on the computer is required. |
| The phone uses its browser; no phone app installation is required. | [Embedded HTML](../internal/relay/web/index.html) and JavaScript implement the sender form. | SOURCE_REVIEWED. Real Android/iOS browser and LAN acceptance is NOT_RUN. The computer runs an executable; build tooling is for contributors, not prebuilt-preview runtime use. |
| One Go service embeds its browser assets and generates the QR locally. | `//go:embed` and `qrcode.Encode` in [server.go](../internal/relay/server.go) and [requests.go](../internal/relay/requests.go); dependency in [go.mod](../go.mod). | SOURCE_REVIEWED. No remote QR renderer is involved. |
| The running Ferry Dock service/UI do not need a cloud relay, analytics endpoint, model call, Node runtime, or database. | [HTML](../internal/relay/web/index.html) loads local assets; [app.js](../internal/relay/web/app.js) uses same-origin API fetches; reviewed Go runtime paths contain no analytics/model client. | SOURCE_REVIEWED for this service/UI boundary. Installing Go or downloading dependencies may need the network. This is not a claim that a clean source build works offline. |
| The complete optional Agent workflow is guaranteed to remain local or never send feedback to a cloud model. | [Skill](../skills/ferry-dock/SKILL.md), [product shape](product-shape.md), and the README distinguish service transfer from Agent consumption. | Unsupported. Once CLI output is supplied to an Agent, model transmission and retention depend on that host. Ferry Dock does not control that separate data path. Ordinary non-AI transfer still needs no AI account. |
| State is temporary and is discarded when the process exits. | In-memory maps in [server.go](../internal/relay/server.go) and [requests.go](../internal/relay/requests.go). | SOURCE_REVIEWED. Restart/crash recovery and durable delivery are not provided. Browser session storage, history, clipboard managers, OS swap, and crash dumps are separate from server retention. |
| Parallel requests return input to the originating request, rather than reading a global latest message. | `RequestSnapshot.RequestID`, `readerRequestLocked`, and `ReadRequest` in [requests.go](../internal/relay/requests.go). | SOURCE_REVIEWED. Request/handle selection is explicit. A matching task label is not permission. |
| A manual local Skill explains an optional Codex workflow. | [Skill](../skills/ferry-dock/SKILL.md); it is included in the source and packaged documentation. | SOURCE_REVIEWED as workflow text. Manual loading is required; real Codex-host execution is NOT_RUN. It does not install global configuration, require a source checkout, or wake a paused host. |
| npm/npx, MCP, browser extensions, file/image/audio transfer, remote phone control, and continuous clipboard synchronization are provided. | [Product shape](product-shape.md) and [request contract](contracts/request-v1.md) explicitly exclude them. | OUT_OF_SCOPE. Do not present these as current capabilities or scheduled deliverables. |

## Ordinary text sessions

| Claim | Source or test evidence | Status and limit |
| --- | --- | --- |
| Computer creation, phone text submission, incremental retrieval, and closure are implemented. | `create`, `submit`, `list`, `close` in [server.go](../internal/relay/server.go); `TestSessionTextRoundTrip` in [server_test.go](../internal/relay/server_test.go). | PASS_LOCAL: E4/E6 at their revisions; RECORDED_PASS Safari loopback ordinary send/receive S1. Physical-phone/LAN/QR remains NOT_RUN. |
| The phone can submit but cannot read/manage sessions, and A's sender key cannot submit to B. | `owner`/`validToken` and session-key checks; `TestCapabilitiesAreScoped`. | PASS_LOCAL: E4/E6. Ordinary computer authority is process-wide, not a separate reader capability per ordinary session. |
| Text is preserved, including meaningful leading/trailing whitespace. | Nonblank validation is separate from stored `Message.Text`; `TestSessionTextRoundTrip`; Safari S1. | PASS_LOCAL: E4/E6 API; RECORDED_PASS Safari Copy plus actual system Cmd+V with whitespace/newlines/Chinese/emoji/literal HTML. Other browsers and phone clipboard behavior remain NOT_RUN. |
| Lost-response retries do not create duplicate messages. | Session-scoped idempotency map; `TestIdempotencyAndCursorRecovery`, `TestConcurrentRetriesProduceOneReceipt`. | PASS_LOCAL: E4/E6. Same key with changed text conflicts; retry deduplication lasts only as long as in-memory session state. |
| Closing or expiring a session revokes access and removes retained content. | `close`, `purgeLocked`, `PurgeExpired`; `TestCloseAndExpiryRevokeContent`. | PASS_LOCAL: E4/E6. Application-state removal is not cryptographic memory erasure. |
| Ordinary input is bounded to 64 KiB/text, 128 messages/session, 1 MiB/session, and 16 active sessions. | Constants and limit checks in [server.go](../internal/relay/server.go); `TestSessionResourceLimits`, `TestRejectsMalformedAndOversizedInput`. | PASS_LOCAL: E6. These are payload/count limits, not a measured RSS guarantee. |
| The computer offers Copy with a selectable-text fallback; phone clipboard reading is optional. | Clipboard functions and click handlers in [app.js](../internal/relay/web/app.js); Safari S1/S4. | RECORDED_PASS for successful system copy/paste and one 390×844 Safari RDM layout sample. Clipboard permission/failure/fallback paths and physical-phone clipboard reading were not exercised. No background monitoring is implemented. |

## Collection requests and authority

| Claim | Source or test evidence | Status and limit |
| --- | --- | --- |
| The server assigns a request ID; task ID and prompt supply context. | `CreateRequestInput`, `RequestSnapshot`, `CreateRequest` in [requests.go](../internal/relay/requests.go); `TestRequestCreateSeparatesCapabilitiesAndMetadata`. | SOURCE_REVIEWED. `taskId` is caller-controlled correlation metadata, not an authenticated host task identity. |
| Each request has independent reader and sender capabilities. The computer token creates requests but is not returned as request-consumer authority. | `CreateRequest`, `readerRequestLocked`, `senderRequestLocked`; `TestRequestCreateSeparatesCapabilitiesAndMetadata`. | PASS_LOCAL: E3/E6. The control file still contains process-level computer authority. Normal service startup prints the owner URL; an Agent launching it must redirect logs privately as the Skill requires. |
| A/B readers and senders cannot cross-read/write, even when task labels match. | Per-record capability checks; `TestRequestDeliveryIsScopedAndReadsAreRepeatable` in [requests_test.go](../internal/relay/requests_test.go). | PASS_LOCAL: E3/E6. Capability isolation is an application boundary, not OS isolation between programs running as the same user. |
| A phone can inspect its prompt and submit one text response, but cannot read the result or cancel collection. | `requestInfoHTTP`, `submitRequestHTTP`, reader-only result/cancel paths in [requests.go](../internal/relay/requests.go); request role-negative tests. | PASS_LOCAL: E3/E6 API, E5 script; RECORDED_PASS Safari prompt/submit/received form and refresh lock S2. This used a desktop loopback page, not a physical phone. |
| Changing A to B in one sender tab binds subsequent submission to B rather than stale A. | `hashchange` reload handling in [app.js](../internal/relay/web/app.js), the eleventh VM regression, and fresh-binary Safari S6. | RECORDED_PASS: no manual reload, B prompt shown; A remained pending/no input and only B received target text. Owned service/window/files were cleaned. |
| The request accepts one response. Same-key/same-text retry returns the original receipt; another delivery conflicts. | `deliveryKey`, stored input, and the received-state branch of `submitRequestHTTP`; `TestRequestDeliveryIsScopedAndReadsAreRepeatable`. | PASS_LOCAL: E3/E6. This is delivery deduplication, not exactly-once Agent execution. |
| Repeated reads return the same stable input ID and do not consume the input. | `ReadRequest` returns the retained value; `TestRequestDeliveryIsScopedAndReadsAreRepeatable`. | PASS_LOCAL: E3/E6. The consumer must deduplicate downstream effects by request/input identity. |
| Phone feedback is marked `untrusted_user_input`. | `RequestInput.Trust` construction in [requests.go](../internal/relay/requests.go); trust-marker assertion in request tests; [Skill result checks](../skills/ferry-dock/SKILL.md). | SOURCE_REVIEWED. The marker does not itself stop an Agent; the consumer must treat text as task data and must not execute embedded commands, follow embedded links, or change Agent configuration because that text requests it. |
| The Skill checks the saved request ID, task label, state, input ID, and trust marker before use. | “Before using a result” in the [Skill](../skills/ferry-dock/SKILL.md). | SOURCE_REVIEWED as workflow guidance. A mismatch must stop consumption; relabeling another request is not a recovery path. Real host enforcement is NOT_RUN. |
| An interrupted consumer can reread without blindly applying an edit twice. | Stable input IDs in the core; completion and uncertain-effect handling in the [Skill](../skills/ferry-dock/SKILL.md); sample consumer in [smoke-request.py](../scripts/smoke-request.py). | PASS_LOCAL: E3 demonstrates one synthetic consumer's repeated-read deduplication. An effect completed before its bookkeeping may require inspecting the artifact; the general recovery rule is guidance, not a universal exactly-once transaction or real-host result. |
| Request cancel/expiry remove received text while retaining short-lived terminal metadata. | `CancelRequest`, `purgeRequestsLocked`; `TestRequestCancellationAndExpiryRemoveInput`. | PASS_LOCAL: E3/E6. Terminal metadata has a two-minute accessible retention window; background reference cleanup is periodic. No persistence/recovery guarantee is added. |
| Request input defaults to 16 KiB and can use a smaller limit; task/prompt/TTL/request count are bounded. | `MaxRequestTextBytes`, `MaxRequests`, `CreateRequest` and per-request submit validation in [requests.go](../internal/relay/requests.go); `TestRequestRejectsInvalidUnicodeAndHonorsTextByteLimit`, `TestRequestRetentionCapacityIsBoundedAndReclaimed`. | PASS_LOCAL: E3/E6/E7. Decoded text limit differs from the ordinary 64 KiB session text limit. Oversized input is rejected rather than truncated. |
| Wait is bounded to ten seconds; timeout and wait interruption do not cancel the request. | `WaitRequest` in [requests.go](../internal/relay/requests.go); `TestRequestWaitTimeoutAndInterruptionDoNotCancel`, `TestRequestWaitWakesOnDeliveryAndActiveContextInterruption`; [Skill](../skills/ferry-dock/SKILL.md). | PASS_LOCAL: E3/E6/E7. This is wait cancellation; a separately issued request cancel is a mutation with different semantics. |
| At most eight waits leave normal transfer capacity available. | Wait admission channel; `TestRequestWaitAdmissionLeavesOrdinaryTransferAvailable` in [requests_test.go](../internal/relay/requests_test.go). | PASS_LOCAL: E6 for the functional gate. This is not yet a measured wait-pressure latency budget result. |
| Interrupting request creation or cancellation is distinguishable from interrupting a wait. A mutation may already have committed. | `fetchJSON`, `transportProblem`, and wait-specific context handling in [cli.go](../cmd/ferry-dock/cli.go); `TestInterruptedCancelReportsUnknownMutationOutcome` and `TestWaitInterruptedDuringResponseBodyIsStillWaitCanceled` in [cli_test.go](../cmd/ferry-dock/cli_test.go); recovery guidance in the [Skill](../skills/ferry-dock/SKILL.md). | PASS_LOCAL: E8 tests interrupted cancel and response-body wait cancellation. SOURCE_REVIEWED: create transport errors use `outcome_unknown`, ordinary interrupted reads use `operation_canceled`. A cancel with uncertain outcome requires status through the same handle. Creation without a retained handle may leave an unknown request until TTL; do not promise it was absent or blindly retry. Only interrupted wait is guaranteed not to issue request cancellation. |

## Commands and end-to-end evidence

The command rows below record the earlier text/request CLI audits and retain
their named revisions. Packaging and desktop changes have separate gates above.
Placeholder LAN addresses and private runtime paths must be replaced; do not
paste secret control/handle contents into a prompt or a public log.

| Command or scenario | Expected evidence | Status |
| --- | --- | --- |
| `go build -trimpath -o bin/ferry-dock ./cmd/ferry-dock` | A compiled current-revision executable; record Go/OS/architecture and source revision. | PASS_LOCAL: E1 used a private `/tmp` output path for independence, with the same package/build mode. |
| `./bin/ferry-dock -help` and backward-compatible no-subcommand service mode | Real help matches documented flags; loopback-only default. | PASS_LOCAL: E2 verifies serve help; E4 launches backward-compatible service flags without a subcommand. |
| `serve --control-file PATH` | Private local control file; no accidental overwrite or disclosure; owned service cleans up its own runtime artifacts/process. | PASS_LOCAL: E3/E7 verify POSIX private mode and normal cleanup; E6 includes `TestPrivateFilesAreNeverOverwritten`. Windows directory ACL acceptance is not established by this macOS run. |
| `request create --control PATH --task-id LABEL --prompt TEXT --handle PATH --ttl 15m --max-bytes 16384` | Structured stdout, private request handle and QR; no process computer token in request-create stdout. | PASS_LOCAL: E2/E3/E7. Normal service startup output is separately secret-bearing and was suppressed/redirected. |
| `request status/read --handle PATH` | Exact matching request snapshot/result, stable input ID, no need to expose the handle secret to the model. | PASS_LOCAL: E2/E3/E7. E6 includes explicit oversized-result rejection rather than truncated output. |
| `request wait --handle PATH --timeout 10s` | Pending timeout is structured and repeatable; Ctrl+C ends only the wait; a subsequent read still works. | PASS_LOCAL: E2/E3/E6. POSIX SIGINT tested; Windows console interruption is not established by this run. |
| `request cancel --handle PATH` | Explicit request cancellation, distinguishable from stopping a wait; input removed. | PASS_LOCAL: E3/E6/E7. A transport-interrupted mutation can have an uncertain outcome; inspect status rather than claim cancellation failed or never happened. |
| Ordinary compiled-program loopback smoke | Start service, exercise HTTP fidelity/roles/retries/close/expiry, terminate only the owned process. | PASS_LOCAL: E4, 12 checks. |
| Served sender/computer script → compiled service → CLI continuation | Exercise actual embedded `app.js` and HTTP boundaries, exact text, authority rejection, expired drafts, response-loss deduplication, poll recovery and normal cleanup. | PASS_LOCAL: E10 with a DOM adapter. It is not browser E2E or an actual OS clipboard test. |
| README Banner at the head with theme variants and a narrow preview | Check both root README-relative paths and inspect 320×100 light/dark vector renders. | PASS_LOCAL for static paths and visual render. Actual GitHub rendering and a physical phone viewport are NOT_RUN; the batch was not yet public during this audit. |
| Synthetic proposal → submitted feedback → current-request read → consumer edit | A compiled CLI harness must assert task/request identity, stable input ID, and a second read without a duplicate consumer effect. | PASS_LOCAL: E3, 27 checks. The sample consumer uses deterministic code; a synthetic HTTP sender is not a physical phone, LLM, or Agent host. |
| Actual desktop Safari copy/paste and scoped request UI | Safari 27.0.1 private window, real system clipboard, request/read/reload, one RDM viewport, ended-page states, UI Quit, fresh-binary same-tab A→B change. | RECORDED_PASS S1–S6. No blanket permission/fallback, in-flight outage, default-browser auto-open, Finder, or other-browser pass is inferred. |
| Real Android Chrome and iOS Safari LAN scan/send | Record device, OS/browser, network reachability, QR, request prompt, submit, retry, expiry and isolation. | NOT_RUN. |
| A real Codex task manually loads the repository Skill and continues the same proposal | Record the actual host's tool/image/wait behavior and resulting artifact. | NOT_RUN. The Skill file and synthetic harness are not substitutes. |
| Cross-compilation or CI across operating systems | [Verification](verification.md) records final `CGO_ENABLED=0` Windows/Linux amd64 builds. Current workflow results are available in [GitHub Actions](https://github.com/Yankj/ferry-dock/actions/workflows/ci.yml). | RECORDED_PASS for the historical cross-builds. Match CI to its own commit; build/unit/synthetic CI success does not establish native desktop first-launch, real-phone or Agent-host acceptance. Earlier text-alpha CI does not validate later revisions. |

## Performance and security wording

| Claim | Evidence | Status and permitted wording |
| --- | --- | --- |
| Startup p95 ≤ 150 ms, idle RSS ≤ 32 MiB, text p95 ≤ 10 ms/p99 ≤ 25 ms. | [Performance plan](performance.md) defines provisional budgets; the [formal baseline](performance-baseline.md) and [raw JSON](benchmarks/2026-10-28-macos-arm64.json) record one conditional run. | RECORDED_MEASUREMENT, report/raw independently checked. The stated local observations fall below those numerical budgets for their exact sampled workloads; the budgets remain targets, not service guarantees or a Go/Node/Rust ranking. Keep the 479.428 ms startup maximum and post-close RSS alongside relevant summaries. |
| Browser display latency is the same as HTTP handler latency. | Browser polling in [app.js](../internal/relay/web/app.js); measurement separation in [performance plan](performance.md). | Unsupported. User-visible time includes polling and network/browser work. |
| Ordinary retained text is bounded by 16 MiB of payload. | 16 sessions × 1 MiB in [server.go](../internal/relay/server.go). | SOURCE_REVIEWED as the ordinary-session payload bound only. New requests add up to 64 × 16 KiB = 1 MiB of input payload; metadata, in-flight bodies/copies, responses, assets and runtime make RSS larger. No RSS result is implied. |
| The service encrypts LAN transfers or provides end-to-end encryption. | Accepted HTTP-only origins and listener in [server.go](../internal/relay/server.go), [entry point](../cmd/ferry-dock/main.go). | Unsupported. Say HTTP on a trusted, reachable LAN; content and bearer capabilities can be observed/tampered with on the network. |
| Random capabilities, Host/Origin validation and CSP enforce useful application boundaries. | `NewToken`, per-operation capability checks, `ServeHTTP` headers and checks; `TestHostOriginAndSecurityHeaders`, role-negative tests. | SOURCE_REVIEWED. These do not authenticate the network, replace TLS, or isolate hostile programs with the same OS-user access. |
| A QR bypasses routing, Wi-Fi isolation, or firewall restrictions. | Explicit listen/public-origin configuration; [Skill](../skills/ferry-dock/SKILL.md) forbids changing network/security settings to pair. | Unsupported. A phone must already be able to reach the configured origin. |
| Fragment URLs and private runtime files make capability disclosure harmless. | Fragment parsing in [app.js](../internal/relay/web/app.js); capability guidance in [Skill](../skills/ferry-dock/SKILL.md). | Unsupported. A disclosed sender URL grants submission authority; a disclosed reader/control file grants its scope of authority. Keep them private and outside committed/public paths. |
| “Temporary” guarantees secure erasure or delivery surviving restart. | Memory-only state and lifecycle cleanup; [architecture](architecture.md). | Unsupported. State removal is not secure RAM/swap erasure, and process loss discards retained input and deduplication records. |

## Remaining acceptance gates

1. E8 completed the final CLI check for the earlier `5d3caff` freeze. The later
   alpha.1 and alpha.2 desktop/package checks above have their own clean
   `3d6fca8` and `a351555` identities. They are not recertified by E8 or the prior
   core-startup baseline. Alpha.2 dark/phone-size GUI remains blocked and its OS
   paste was not repeated; do not extend the partial light-mode result.
2. Preserve the scope of Safari S1–S6; keep Finder/default-cache/default-browser
   auto-opening, Android/iOS LAN/QR and real Codex-host acceptance NOT_RUN until
   their own evidence exists.
3. Publish performance numbers only with a named reference environment and raw
   samples. The product ambition alone is not evidence of a budget being met.
