# Claims and evidence

This audit maps public product statements to implementation and verification.
It does not turn a design contract, a test definition, or an intended command
into an executed result. Audit date: 2026-10-28. The independent local checks below
used macOS arm64 and Go 1.27.3 against the collection-request working tree based
on `13e5b27435c3f35578398570667328396b41ff88`. The final CLI changes were rebuilt
and checked separately at frozen commit
`5d3caff0833ff52e805a4a874e7f07d82e39c624` (E8). Browser, real-phone, and actual
Codex-host acceptance remain **NOT_RUN**.

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
| The phone uses its browser; no phone app installation is required. | [Embedded HTML](../internal/relay/web/index.html) and JavaScript implement the sender form. | SOURCE_REVIEWED. Real Android/iOS browser and LAN acceptance is NOT_RUN. Phone installation-free does not mean the computer needs no executable or build tooling. |
| One Go service embeds its browser assets and generates the QR locally. | `//go:embed` and `qrcode.Encode` in [server.go](../internal/relay/server.go) and [requests.go](../internal/relay/requests.go); dependency in [go.mod](../go.mod). | SOURCE_REVIEWED. No remote QR renderer is involved. |
| The running Ferry Dock service/UI do not need a cloud relay, analytics endpoint, model call, Node runtime, or database. | [HTML](../internal/relay/web/index.html) loads local assets; [app.js](../internal/relay/web/app.js) uses same-origin API fetches; reviewed Go runtime paths contain no analytics/model client. | SOURCE_REVIEWED for this service/UI boundary. Installing Go or downloading dependencies may need the network. This is not a claim that a clean source build works offline. |
| The complete optional Agent workflow is guaranteed to remain local or never send feedback to a cloud model. | [Skill](../skills/ferry-dock/SKILL.md), [product shape](product-shape.md), and the README distinguish service transfer from Agent consumption. | Unsupported. Once CLI output is supplied to an Agent, model transmission and retention depend on that host. Ferry Dock does not control that separate data path. Ordinary non-AI transfer still needs no AI account. |
| State is temporary and is discarded when the process exits. | In-memory maps in [server.go](../internal/relay/server.go) and [requests.go](../internal/relay/requests.go). | SOURCE_REVIEWED. Restart/crash recovery and durable delivery are not provided. Browser session storage, history, clipboard managers, OS swap, and crash dumps are separate from server retention. |
| Parallel requests return input to the originating request, rather than reading a global latest message. | `RequestSnapshot.RequestID`, `readerRequestLocked`, and `ReadRequest` in [requests.go](../internal/relay/requests.go). | SOURCE_REVIEWED. Request/handle selection is explicit. A matching task label is not permission. |
| A repository-local Skill explains an optional Codex workflow. | [Skill](../skills/ferry-dock/SKILL.md). | SOURCE_REVIEWED as workflow text. Manual loading is required; real Codex-host execution is NOT_RUN. It does not install global configuration or wake a paused host. |
| npm/npx, MCP, browser extensions, file/image/audio transfer, remote phone control, and continuous clipboard synchronization are provided. | [Product shape](product-shape.md) and [request contract](contracts/request-v1.md) explicitly exclude them. | OUT_OF_SCOPE. Do not present these as current capabilities or scheduled deliverables. |

## Ordinary text sessions

| Claim | Source or test evidence | Status and limit |
| --- | --- | --- |
| Computer creation, phone text submission, incremental retrieval, and closure are implemented. | `create`, `submit`, `list`, `close` in [server.go](../internal/relay/server.go); `TestSessionTextRoundTrip` in [server_test.go](../internal/relay/server_test.go). | PASS_LOCAL: E4 and E6. Browser and phone behavior remain NOT_RUN. |
| The phone can submit but cannot read/manage sessions, and A's sender key cannot submit to B. | `owner`/`validToken` and session-key checks; `TestCapabilitiesAreScoped`. | PASS_LOCAL: E4/E6. Ordinary computer authority is process-wide, not a separate reader capability per ordinary session. |
| Text is preserved, including meaningful leading/trailing whitespace. | Nonblank validation is separate from the stored `Message.Text`; `TestSessionTextRoundTrip`. | PASS_LOCAL: E4/E6 for the API. Text must fit the decoded 64 KiB limit. Browser copy/paste fidelity is NOT_RUN. |
| Lost-response retries do not create duplicate messages. | Session-scoped idempotency map; `TestIdempotencyAndCursorRecovery`, `TestConcurrentRetriesProduceOneReceipt`. | PASS_LOCAL: E4/E6. Same key with changed text conflicts; retry deduplication lasts only as long as in-memory session state. |
| Closing or expiring a session revokes access and removes retained content. | `close`, `purgeLocked`, `PurgeExpired`; `TestCloseAndExpiryRevokeContent`. | PASS_LOCAL: E4/E6. Application-state removal is not cryptographic memory erasure. |
| Ordinary input is bounded to 64 KiB/text, 128 messages/session, 1 MiB/session, and 16 active sessions. | Constants and limit checks in [server.go](../internal/relay/server.go); `TestSessionResourceLimits`, `TestRejectsMalformedAndOversizedInput`. | PASS_LOCAL: E6. These are payload/count limits, not a measured RSS guarantee. |
| The computer offers Copy with a selectable-text fallback; phone clipboard reading is optional. | Clipboard functions and click handlers in [app.js](../internal/relay/web/app.js). | SOURCE_REVIEWED. Browser permission prompts, actual copy/paste and responsive rendering remain NOT_RUN. No background clipboard monitoring is implemented. |

## Collection requests and authority

| Claim | Source or test evidence | Status and limit |
| --- | --- | --- |
| The server assigns a request ID; task ID and prompt supply context. | `CreateRequestInput`, `RequestSnapshot`, `CreateRequest` in [requests.go](../internal/relay/requests.go); `TestRequestCreateSeparatesCapabilitiesAndMetadata`. | SOURCE_REVIEWED. `taskId` is caller-controlled correlation metadata, not an authenticated host task identity. |
| Each request has independent reader and sender capabilities. The computer token creates requests but is not returned as request-consumer authority. | `CreateRequest`, `readerRequestLocked`, `senderRequestLocked`; `TestRequestCreateSeparatesCapabilitiesAndMetadata`. | PASS_LOCAL: E3/E6. The control file still contains process-level computer authority. Normal service startup prints the owner URL; an Agent launching it must redirect logs privately as the Skill requires. |
| A/B readers and senders cannot cross-read/write, even when task labels match. | Per-record capability checks; `TestRequestDeliveryIsScopedAndReadsAreRepeatable` in [requests_test.go](../internal/relay/requests_test.go). | PASS_LOCAL: E3/E6. Capability isolation is an application boundary, not OS isolation between programs running as the same user. |
| A phone can inspect its prompt and submit one text response, but cannot read the result or cancel collection. | `requestInfoHTTP`, `submitRequestHTTP`, reader-only result/cancel paths in [requests.go](../internal/relay/requests.go); request role-negative tests. | PASS_LOCAL: E3/E6 at the API; E5 at the script layer. The sender URL/QR carries sender authority and remains sensitive. |
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

All command rows below are current-revision audit gates. Placeholder LAN addresses
and private runtime paths must be replaced; do not paste secret control/handle
contents into a prompt or a public log.

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
| Synthetic proposal → submitted feedback → current-request read → consumer edit | A compiled CLI harness must assert task/request identity, stable input ID, and a second read without a duplicate consumer effect. | PASS_LOCAL: E3, 27 checks. The sample consumer uses deterministic code; a synthetic HTTP sender is not a physical phone, LLM, or Agent host. |
| Real desktop browser copy/paste | Run the actual UI, permission/failure paths and responsive rendering. | NOT_RUN. |
| Real Android Chrome and iOS Safari LAN scan/send | Record device, OS/browser, network reachability, QR, request prompt, submit, retry, expiry and isolation. | NOT_RUN. |
| A real Codex task manually loads the repository Skill and continues the same proposal | Record the actual host's tool/image/wait behavior and resulting artifact. | NOT_RUN. The Skill file and synthetic harness are not substitutes. |
| Cross-compilation or CI across operating systems | [Verification](verification.md) records final `CGO_ENABLED=0` Windows/Linux amd64 builds. | RECORDED_PASS for cross-builds reported by the implementation worker. Native Windows/Linux execution and remote CI of this collection slice are NOT_RUN; earlier text-alpha CI does not apply to this revision. |

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

1. If runtime code changes after frozen commit `5d3caff`, repeat checks affected
   by those changes. E8 completes the final CLI check for that freeze.
2. Keep browser, Android/iOS LAN, and real Codex-host acceptance marked NOT_RUN
   unless their actual evidence is available.
3. Publish performance numbers only with a named reference environment and raw
   samples. The product ambition alone is not evidence of a budget being met.
