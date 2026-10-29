# Ferry Dock: phone text, in the work it belongs to

**A small local bridge from your phone to your computer.**

Ferry Dock lets a person bring text from a phone into a computer inbox or the task that asked for it. The computer runs one small Go service; the phone scans a QR and uses a browser. Ordinary transfer needs no account, mobile app, cloud service, or AI model.

In the task flow, an Agent working on a proposal asks for the comments held in a phone chat. The phone page names that proposal and asks for the missing text. The user pastes and sends. Only the request's reader can retrieve the result, and the original task uses the feedback to revise the proposal.

**Current status:** `0.1.0-alpha.2` is being prepared with a black, white, and gray interface and translucent visual layers. Transfer/request semantics are unchanged. Real Safari desktop-light ordinary send/receive and the **Copied** label passed; system paste was not repeated. Dark/phone-size GUI acceptance is blocked by an interactive authentication boundary. Go tests and the 12 HTTP / 27 synthetic request / 11 VM / SCRIPT_HTTP checks passed; final package acceptance is pending. [Verification](docs/verification.md) records the exact scopes. There is no published GitHub Release or public binary download URL.

**Historical preview evidence:** eight local `0.1.0-alpha.1` archives from clean source `3d6fca8` passed archive checks and same-input rebuild comparison. Mac arm64 packaged lifecycle/CLI/safety checks passed with `--no-open` and private state; Safari 27.0.1 has separate scoped UI passes. Its app ZIP is 3,274,113 bytes. These results belong to that fixed snapshot, not the pending alpha.2 revision. Finder/default-cache discovery, default-browser auto-opening, Gatekeeper, real-phone/LAN/QR, actual Codex-host and Windows/Linux native acceptance remain `NOT_RUN`. [Distribution](docs/distribution.md) identifies the artifacts and receipts.

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

No. The accepted form is one Go core, distributed as a macOS browser-launcher app or portable native CLI, with small web pages and an optional bundled local Codex Skill. These packages do not introduce another backend. There is no hosted account, durable file library, team workspace, or catalogue of Agent integrations in this scope.

npm/npx, MCP, and a browser extension are not implemented or scheduled. Revisit them only when installation is the main demonstrated barrier, a specific client lacks shell access, or desktop selected-text sharing becomes a separate primary need. See [the product-shape decision](docs/product-shape.md).

## How does the ordinary mode work?

Open the prebuilt macOS app, or explicitly run `desktop` from an extracted native CLI package. The launcher starts/reopens its verified Go service and opens the system browser. The page creates a temporary session and shows a locally generated QR. Scan it on the phone, paste text, and send. The computer retrieves it and offers Copy. End the session when finished, or let it expire.

Ordinary sessions allow repeated text submissions and remain separate from one-response collection requests. No model or Skill is required to run the service or transfer text.

## What must be installed, and where can it run?

The default user path is a prebuilt app or native CLI, not a Git clone or a Go/Node installation. The phone uses a browser with JavaScript. Local preview recipients extract the package matching their OS/architecture; no global PATH or Agent configuration is changed. Public binary downloads have not been published, so a version label must not be turned into an invented Release link.

The `.app` is this product, not an extra desktop platform. The first-use path is ZIP extraction → open the app → scan; subsequent use is open → scan. There is no installation wizard, registration, or login item to configure.

Git and Go are contributor/source-build prerequisites. The packaging script also uses Python's standard library, but preview users do not run that script. After packaging, the application's pages, QR generation, and brand assets are local, without a runtime cloud API or telemetry call in the Ferry Dock service/UI.

Build and CI platform results are not evidence that a physical phone, mobile clipboard permission, camera scanner, or network works. Real Android/iOS and actual Codex-host acceptance must name the tested device or host and remain `NOT_RUN` when not exercised.

## Is the app a second native UI or another backend?

No. `Ferry Dock.app/Contents/MacOS/ferry-dock` is built from the same Go command as the standalone CLI, with desktop as its no-argument default. It launches the existing browser interface; no Swift, Electron, or second request store is introduced. The app's executable also supports `version` and `request` commands. Usage documents and the manual Skill are bundled under `Contents/Resources`.

## Does closing the browser quit the app?

No. The short-lived launcher exits after starting/reopening its own background service and opening the browser. Close the browser and the service keeps running. Reopen the app to return to the verified instance. **Quit Ferry Dock** on the local computer page authenticates the computer capability and loopback request, then stops the service and clears all in-memory sessions and collection requests.

The desktop launcher serializes startup and checks its saved owner capability and instance ID before reusing a service. An unknown service is an error, not something to kill or replace automatically. Quitting a shared service affects other tasks; canceling one request does not.

## Must I enter an IP address?

Default desktop LAN mode listens on all IPv4 interfaces at a free port and advertises a private IPv4 address from the OS primary interface, or the only eligible private address. If no choice is unambiguous, it binds loopback and reports **Local only**. A physical phone cannot reach loopback. Advanced `--listen` and `--public-url` configuration uses a verified origin and applies only to a new instance, not one reused on relaunch. Selection does not bypass Wi-Fi isolation, VPN routing, or a firewall.

Foreground `serve` retains its explicit operator configuration and loopback default. Neither entry point makes HTTP encrypted.

Desktop listener overrides are limited to `127.0.0.1:PORT` or `0.0.0.0:PORT`, with numeric ports 0–65535; other configurations use `serve`. Automatic candidates exclude point-to-point VPN interfaces.

## Is the preview signed, notarized, or accepted by Gatekeeper?

The packaging script performs no Developer ID signing or Apple notarization. A linker ad-hoc signature is not publisher identity. Local bundle/version/HTTP or Safari loopback checks do not prove downloaded-file first launch, Finder/default-browser auto-opening, or Gatekeeper acceptance. [Apple's signing and notarization guidance](https://developer.apple.com/developer-id/) describes those separate checks. Windows previews are also publisher-unsigned; [Microsoft's SmartScreen overview](https://learn.microsoft.com/en-us/windows/security/operating-system-security/virus-and-threat-protection/microsoft-defender-smartscreen/) describes download/app reputation checks. No bypass procedure is provided. Artifact hashes and observed acceptance scopes are in [distribution](docs/distribution.md).

## What exactly is a collection request?

It is a temporary question accepting one plain-text response. The server assigns a request ID and independent sender and reader capabilities. The caller supplies a task label and prompt; the label is correlation metadata, not authorization.

The phone can see its question and submit once. It cannot read the result or cancel the request. The reader handle can inspect state, wait within a bound, read, or cancel only that request. The process computer capability creates requests and is not returned to request consumers. [Request v1](docs/contracts/request-v1.md) defines the exact lifecycle and limits.

## Where does the text go, and how long does it stay?

The phone submits directly to the computer's local HTTP service. Ordinary sessions retain text in memory until ended or expired, with a default 15-minute lifetime. A collection request inherits service retention unless given its own lifetime, at most 24 hours. Its reader can retrieve the input until cancellation or observed expiry removes it; terminal metadata can remain for at most two minutes. Closing the browser does not end desktop service retention; **Quit Ferry Dock** does.

The no-cloud/model-call description applies to the Ferry Dock service. When the optional Skill hands a CLI result to an Agent, that host determines whether content reaches a cloud model and how it is retained. The complete Agent workflow is not guaranteed to stay local; ordinary transfer still requires no AI account.

Stopping or restarting the service loses in-memory content. A control file or request handle holds authority and connection information, not a backup of the phone's text. Private cache directories and `startup.log` may remain after Quit; shutdown is not an uninstall or a zero-residue promise. The user's browser, clipboard and an edited proposal may retain their own copies; temporary service retention is not secure erasure.

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

One Go service owns the state and embedded browser assets; a short-lived desktop launcher starts or reopens it. The existing automated suite exercises temporary text sessions, fidelity, retry deduplication, cursor retrieval, capabilities, expiry, and limits; a compiled-program smoke test exercises the HTTP path.

Those are correctness checks, not a performance ranking or mobile acceptance. The earlier [measured baseline](docs/performance-baseline.md), with [raw samples](docs/benchmarks/2026-10-28-macos-arm64.json), records one macOS arm64 / Go 1.27.3 run against a specific prior CLI/core binary. Read startup percentiles with the observed maximum and note that closing inboxes did not immediately lower RSS. It does not measure this app's launch, browser opening, downloaded-file trust checks, mobile interaction, or Agent execution speed, and is not a clean tagged-release build or cross-language ranking.

See [performance budgets](docs/performance.md), [verification](docs/verification.md), and [claims and evidence](docs/claims-evidence.md) for the conditions and remaining acceptance gaps. Do not interpret an ambition or a test fixture as a measured production result.

## What evidence makes this delivery complete?

The collection slice must pass request isolation, limits, expiry/cancellation, retry and repeated-read behavior, timeout/interruption, and regression checks for ordinary transfer. A compiled-CLI synthetic proposal scenario must show the request, feedback, and a consumer that avoids repeating the effect for the same input ID.

Synthetic execution must be labeled as such. Recorded Safari loopback acceptance includes real copy/paste and the specific UI cases in [verification](docs/verification.md). It is not physical-phone QR/LAN, Finder/default-browser auto-opening, or actual Codex-host acceptance; those stay `NOT_RUN` until their own evidence exists.

The historical alpha.1 local archives passed target/header/hash/layout/metadata checks, and Mac arm64 passed packaged app flag-dispatch, readiness, CLI compatibility, reuse, quit, stale/unknown-service safety and cleanup checks. A second full build matched all eight archives, manifest and checksums byte-for-byte. Those receipts are pinned to `3d6fca8`; later documentation/UI changes do not rebuild the packages. Alpha.2 requires its own visual and package evidence. Generating or testing a local `.app` is still not public distribution or Finder/Gatekeeper/phone acceptance.
