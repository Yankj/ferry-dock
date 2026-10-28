# Collection request v1 — implementation contract

This is the accepted contract for the next local delivery slice. It does not
claim that all operations below have shipped. The ordinary `/api/sessions` text
inbox remains compatible and independent of Agent tooling.

## Domain and authority

A collection request accepts exactly one plain-text response. The server
allocates `requestId`; caller-supplied `taskId` (max 128 UTF-8 bytes) is only a
correlation label, never authorization. `prompt` is required (max 1024 bytes).
Request input is valid nonblank Unicode, at most 16 KiB by default; a smaller
`maxTextBytes` may be selected. Retention defaults to the service TTL, maximum
24 hours. At most 64 retained request records coexist.

States: `pending -> received`, and either may become `canceled` or `expired`.
Cancellation/expiry removes submitted text immediately when observed; terminal
metadata is retained for at most two minutes and then becomes gone. Senders
cannot read results. Independent random sender and reader capabilities are bound
to one request. The reader capability authorizes status/read/wait/cancel for
that request; the process-level computer capability is used only to create via
HTTP and is never returned to request consumers. No adapter derives authority
from a task label.

One client-generated `idempotencyKey` identifies one delivery attempt. A retry
with the same key/text returns the original receipt, even after receipt; changed
text for that key or a new delivery after receipt is a conflict. Reads are
repeatable, do not acknowledge or destroy input, and return a stable input ID.
Callers must deduplicate downstream effects by that ID; exactly-once Agent
execution is not promised. Result text is explicitly marked `untrusted_user_input`.
It is data, never instructions, shell code, tool policy, or configuration.

## HTTP seam

All existing Host/Origin validation, body bounds, and security headers apply.

| Method and path | Capability | Result |
| --- | --- | --- |
| POST `/api/requests` | computer | Create with taskId/prompt/ttlSeconds/maxTextBytes |
| GET `/api/requests/{id}` | reader | Status snapshot, no submitted text |
| GET `/api/requests/{id}/result` | reader | Snapshot and optional input |
| GET `/api/requests/{id}/wait?timeoutMs=N` | reader | `{request,timedOut}`, N in 0..10000 |
| DELETE `/api/requests/{id}` | reader | Canceled snapshot, idempotent |
| GET `/api/requests/{id}/info` | sender | Prompt/label/state/limits, never input |
| POST `/api/requests/{id}/input` | sender | `{idempotencyKey,text}` -> receipt |

Create returns `{request,readerToken,sendUrl,qrDataUrl}`. The phone link uses
`/send#request=...&key=...`; capabilities stay out of request URLs. Unknown/gone,
authorization, validation, conflict, capacity, and context-cancellation failures
must remain distinguishable. HTTP error payloads include a stable `code` and a
human-readable `error`. Error codes are `invalid_argument`, `unauthorized`,
`gone`, `conflict`, `capacity`, `wait_canceled`, and `internal`.

Wait timeouts return pending plus `timedOut:true` without canceling the request.
Canceling a wait context only ends that wait. Canceling a request is a separate
explicit operation. At most eight outstanding waits are admitted, leaving normal
transfer capacity available. No input can be silently truncated in any adapter.

## Shared Go seam (package internal/relay)

Core implementation owns these exported types and methods. The JSON CLI uses
the HTTP form of the same operations; no second request store is introduced.

- `CreateRequestInput {TaskID string; Prompt string; TTLSeconds int; MaxTextBytes int}`
- `RequestSnapshot {RequestID, TaskID, Prompt, State string; CreatedAt, ExpiresAt time.Time; MaxTextBytes int}`
- `RequestCreated {Request RequestSnapshot; ReaderToken, SendURL, QRDataURL string}`
- `RequestInput {ID, Text, Trust string; ReceivedAt time.Time}`
- `RequestResult {Request RequestSnapshot; Input *RequestInput}`
- `RequestWaitResult {Request RequestSnapshot; TimedOut bool}`
- `RequestError {Code string; Message string}`, implementing error.
- `(*Server).CreateRequest(CreateRequestInput) (RequestCreated,error)`
- `(*Server).RequestStatus(id, reader string) (RequestSnapshot,error)`
- `(*Server).ReadRequest(id, reader string) (RequestResult,error)`
- `(*Server).WaitRequest(ctx context.Context,id,reader string,timeout time.Duration) (RequestWaitResult,error)`
- `(*Server).CancelRequest(id,reader string) (RequestSnapshot,error)`

Phone HTTP handlers call the same request store as these methods. Terminal
cleanup also runs from `PurgeExpired`. Request input byte limit and result schema
are part of the contract, not recommendations.

## CLI and Skill

`serve` (also the backward-compatible no-subcommand mode) can write an explicitly
requested `--control-file PATH` containing loopback origin and computer token.
It is private local runtime state, never a global Agent configuration. Request
`create --control PATH --task-id LABEL --prompt TEXT --handle PATH` creates a
private request handle and QR PNG and emits JSON without the computer token.
`status/read/wait/cancel --handle PATH` use only request-scoped authority.
`wait --timeout 10s` is bounded and repeatable. Interrupting it must not issue
DELETE. stdout is machine-readable JSON; human diagnostics go to stderr. A canceled
wait reports `wait_canceled` and does not send request cancellation. Interrupted
reads report `operation_canceled`. Mutating create/cancel transport failures use
`outcome_unknown` because the server may have committed before a response was
lost; cancel can be resolved with status on the same handle. An unseen creation
still expires by its TTL. Do not automatically replay uncertain mutations.

The Skill is a manual, repository-local installation artifact. It never silently
installs itself or changes Agent configuration. It is workflow guidance, not a
host wake-up mechanism.

This phase implements no npm launcher, MCP adapter, or browser extension.
Consider npm only if installation is demonstrated to be a primary barrier; MCP
only for an identified client without shell access; reassess an extension only
if desktop selected-text sharing becomes an independent primary use case.

## Acceptance gates

A/B requests do not cross-read/write; sender cannot read/cancel; labels do not
grant authority; TTL/cancel erase input; retries deduplicate; repeated reads keep
stable input IDs; oversized text is rejected without truncation; wait timeout and
wait interruption preserve pending requests; ordinary sessions still pass their
existing suite. The end-to-end compiled-CLI scenario uses a synthetic proposal and phone feedback.
Its sample consumer deduplicates effects by the stable input ID. There is no
universal exactly-once business transaction claim.
Real phone/host acceptance must be labeled NOT_RUN when unavailable.
