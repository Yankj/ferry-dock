# Ferry Dock: phone text, in the work it belongs to

**A small local bridge from your phone to your computer.**

Ferry Dock lets a person bring text from a phone into a computer inbox or the task that asked for it. The computer runs one small Go service; the phone scans a QR and uses a browser. Ordinary transfer needs no account, mobile app, cloud service, or AI model.

In the task flow, an Agent working on a proposal asks for the comments held in a phone chat. The phone page names that proposal and asks for the missing text. The user pastes and sends. Only the request's reader can retrieve the result, and the original task uses the feedback to revise the proposal.

**Delivery status:** ordinary temporary text sessions, one-response collection requests, the JSON CLI, and a repository-local Codex Skill are implemented. Automated HTTP tests and a synthetic compiled-CLI proposal scenario provide separate evidence from browser, real-phone, and actual Codex-host acceptance, which remain `NOT_RUN` until recorded. This document does not turn unverified behavior into a shipped compatibility claim.

## Who is it for?

People doing work on a computer while relevant text lives on their phone: proposal comments in a chat, a copied error message, or notes needed by an active coding task. The first design serves one person and nearby devices on a reachable, trusted local network.

It also serves an Agent that can call a local CLI and has a concrete reason to request that text. Basic transfer remains useful without an Agent.

## What problem does it remove?

Moving text is easy in isolation; moving it with the right context can involve switching to a chat or notes app, sending to oneself, locating the message on the computer, and explaining where it belongs. Ferry Dock provides a direct scan, paste, send path, followed by copying or continuing the requesting task. This describes its interaction, not a measured speed advantage over those alternatives.

Task collection adds a specific prompt, a request identity, bounded waiting, and a result accessible through that request's capability. It does not make an Agent responsible for deciding everything on the phone.

## Why not use messaging, AirDrop, or another local transfer tool?

Those are reasonable alternatives when they already make the handoff easy. Ordinary transfer alone is not a claim that Ferry Dock must replace them.

Ferry Dock's intended distinction is the optional task-bound loop: a shell-capable Agent creates the request and gets its result back through the same interface. The user sees the information needed for that work, and parallel requests keep separate permissions. The project must demonstrate that advantage in a real task rather than infer it from adding an AI label.

## Is this a cloud drive or a general Agent platform?

No. The accepted form is a Go executable, small web pages, and an optional repository-local Codex Skill. There is no hosted account, durable file library, team workspace, or catalogue of Agent integrations in this scope.

npm/npx, MCP, and a browser extension are not implemented or scheduled. Revisit them only when installation is the main demonstrated barrier, a specific client lacks shell access, or desktop selected-text sharing becomes a separate primary need. See [the product-shape decision](docs/product-shape.md).

## How does the ordinary mode work?

Start the service and open its private computer URL. The page creates a temporary session and shows a locally generated QR. Scan it on the phone, paste text, and send. The computer retrieves it and offers Copy. End the session when finished, or let it expire.

Ordinary sessions allow repeated text submissions and remain separate from one-response collection requests. No model or Skill is required to run the service or transfer text.

## What must be installed, and where can it run?

The phone uses a browser with JavaScript; it does not install a Ferry Dock app. The computer must obtain or build the executable. Source builds need Go and may download dependencies; this slice does not provide a binary release or package installer. After building, the application's pages, QR generation, and brand assets are local, without a runtime cloud API or telemetry call in the transfer code.

Build and CI platform results are not evidence that a physical phone, mobile clipboard permission, camera scanner, or network works. Real Android/iOS and actual Codex-host acceptance must name the tested device or host and remain `NOT_RUN` when not exercised.

## What exactly is a collection request?

It is a temporary question accepting one plain-text response. The server assigns a request ID and independent sender and reader capabilities. The caller supplies a task label and prompt; the label is correlation metadata, not authorization.

The phone can see its question and submit once. It cannot read the result or cancel the request. The reader handle can inspect state, wait within a bound, read, or cancel only that request. The process computer capability creates requests and is not returned to request consumers. [Request v1](docs/contracts/request-v1.md) defines the exact lifecycle and limits.

## Where does the text go, and how long does it stay?

The phone submits directly to the computer's configured local HTTP service. Ordinary sessions retain text in memory until ended or expired, with a default 15-minute lifetime. A collection request inherits service retention unless given its own lifetime, at most 24 hours. Its reader can retrieve the input until cancellation or observed expiry removes it; terminal metadata can remain for at most two minutes.

The no-cloud/model-call description applies to the Ferry Dock service. When the optional Skill hands a CLI result to an Agent, that host determines whether content reaches a cloud model and how it is retained. The complete Agent workflow is not guaranteed to stay local; ordinary transfer still requires no AI account.

Stopping or restarting the service loses in-memory content. A control file or request handle holds authority and connection information, not a backup of the phone's text. The user's browser, clipboard, logs they explicitly produce, and a proposal edited from the feedback may retain their own copies; temporary service retention is not secure erasure or a promise that all copies disappear.

## What happens if nobody answers within the wait?

The CLI wait is at most ten seconds. Timeout returns `pending` without canceling collection. The Agent can do other authorized work and query again. Interrupting a wait also ends only that wait; canceling the request is a distinct operation.

Nothing here promises that a paused Codex host will automatically wake up. The repository Skill describes a workflow; it is not a host event mechanism.

## Does interrupting any CLI command mean nothing happened?

No. The wait-specific guarantee applies only to `request wait`: timeout or an interrupted wait does not send a request cancellation. Creating a request and explicitly canceling one are mutations. If their connection or response is interrupted, `outcome_unknown` means the server may already have applied the operation.

Check cancellation with `request status` using the same handle before claiming it succeeded or retrying. If creation saved a handle, query through it. If no handle was saved, an unknown request may remain until its TTL; do not blindly repeat creation. Stopping the service is different again: it discards in-memory sessions and requests.

## Can the same phone input cause an edit twice?

Delivery retries with the same key and text return the original receipt. Reads remain repeatable and return a stable input ID; they do not consume the result.

The consumer must deduplicate business effects using that input ID. If an edit was completed, a repeated read should not apply it again. If work stopped between editing and recording completion, the consumer must inspect the proposal's current state before retrying. The server does not promise a universal exactly-once transaction between Agent execution and an artifact edit.

## Is phone text an instruction to the Agent?

It is returned with the trust marker `untrusted_user_input`. Relevant comments can inform the original task, but the channel cannot grant permissions or override system/tool rules. The Skill forbids executing embedded commands, following links, or changing Agent configuration because the submitted text asks for it.

## Is the transfer encrypted?

This slice uses HTTP on a trusted LAN, with no TLS provisioning or end-to-end encryption. Content and capabilities can be exposed to a network observer. High-entropy, request-scoped capabilities enforce application permissions; they do not provide transport confidentiality.

The service must be reachable from the phone. A QR does not bypass Wi-Fi client isolation, routing, or a firewall. Capability links and private handle/control files must not be posted publicly or committed.

## Can it send files, screenshots, or audio?

Not in this slice. Both ordinary sessions and collection requests currently target plain text. Files require their own streaming, quota, cancellation, integrity, and cleanup design; treating a file as a text body is not the intended path.

## How fast and reliable is it?

The implementation uses one Go process and embedded browser assets. The existing automated suite exercises temporary text sessions, fidelity, retry deduplication, cursor retrieval, capabilities, expiry, and limits; a compiled-program smoke test exercises the HTTP path.

Those are correctness checks, not a performance ranking or mobile acceptance. The first [measured baseline](docs/performance-baseline.md), with [raw samples](docs/benchmarks/2026-10-28-macos-arm64.json), records one macOS arm64 / Go 1.27.3 run of startup, RSS, and synthetic loopback API workloads against a frozen binary. Read startup percentiles with the observed maximum and note that closing inboxes did not immediately lower RSS. This is not a clean tagged-release build, a mobile tap-to-display measurement, Agent execution speed, or a cross-language ranking.

See [performance budgets](docs/performance.md), [verification](docs/verification.md), and [claims and evidence](docs/claims-evidence.md) for the conditions and remaining acceptance gaps. Do not interpret an ambition or a test fixture as a measured production result.

## What evidence makes this delivery complete?

The collection slice must pass request isolation, limits, expiry/cancellation, retry and repeated-read behavior, timeout/interruption, and regression checks for ordinary transfer. A compiled-CLI synthetic proposal scenario must show the request, feedback, and a consumer that avoids repeating the effect for the same input ID.

Synthetic execution must be labeled as such. Browser copying/pasting, a real phone scanning the QR, and an actual Codex task continuing require separate recorded acceptance. They stay `NOT_RUN` when the environment cannot exercise them.
