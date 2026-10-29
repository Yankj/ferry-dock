# Ferry Dock: phone text, in the work it belongs to

**A small local bridge from your phone to your computer.**

[English usage & prompts](docs/usage.md) · [中文使用指南与 Prompt](docs/usage.zh-CN.md)

<img src="brand/scenario.svg" width="800" alt="Phone text to a computer inbox, or a task response read by the same requesting Agent task.">

Ferry Dock lets a person bring text from a phone into a computer inbox or the task that asked for it. The computer runs one small Go service; the phone scans a QR and uses a browser. Ordinary transfer needs no account, mobile app, cloud service, or AI model.

In the task flow, an Agent working on a proposal asks for the comments held in a phone chat. The phone page names that proposal and asks for the missing text. The user pastes and sends. Only the request's reader can retrieve the result, and the original task uses the feedback to revise the proposal.

**Current status:** local `0.1.0-alpha.2` archives are frozen at clean source `a351555`, with a black, white, and gray interface and translucent layers. Transfer/request semantics are unchanged. All eight archives passed the then-existing archive/metadata checks, ten build outputs matched byte-for-byte on a same-input rebuild, and Mac arm64 passed direct packaged-executable lifecycle/CLI checks; complete App-bundle signature validation was missing. Its app ZIP is 3,290,056 bytes. Real Safari desktop-light ordinary send/receive and the **Copied** label passed; system paste was not repeated. Dark/phone-size GUI acceptance remains blocked by an interactive authentication boundary. Go tests and the 12 HTTP / 27 synthetic request / 11 VM / SCRIPT_HTTP checks passed. [Verification](docs/verification.md) records the exact scopes. The [public `v0.1.0-alpha.2` testing prerelease](https://github.com/Yankj/ferry-dock/releases/tag/v0.1.0-alpha.2) provides the [Apple Silicon Mac CLI](https://github.com/Yankj/ferry-dock/releases/download/v0.1.0-alpha.2/ferry-dock-0.1.0-alpha.2-darwin-arm64.tar.gz), 3,260,347 bytes, plus CLI-subset checksums and the original build manifest. Other-platform CLI packages remain local previews; the old alpha.1/alpha.2 App bundles have a reproduced signature defect and are no longer recommended. The immutable bundled documentation predates publication; use the online guide for current download instructions.

**App incident:** the alpha.1/alpha.2 `.app` previews have a known complete-bundle signature defect. The old Apple Silicon App fails strict bundle verification even though its ZIP CRC/hash and the same executable outside the bundle pass. Stop recommending or redistributing these App bundles as working launchers. A new alpha.3 packaging repair is under private structural test, not public release or a promise of downloaded-file Gatekeeper acceptance. The public alpha.2 native CLI is not wrapped in that App envelope and retains its separate unsigned-download limitations.

**Historical preview evidence:** eight local `0.1.0-alpha.1` archives from clean source `3d6fca8` passed archive checks and same-input rebuild comparison. Mac arm64 direct packaged-executable lifecycle/CLI checks passed with `--no-open` and private state; this did not validate the complete App signature; Safari 27.0.1 has separate scoped UI passes. Its app ZIP is 3,274,113 bytes. These results belong to that fixed snapshot and remain separate from alpha.2. Finder/default-cache discovery, default-browser auto-opening, Gatekeeper, real-phone/LAN/QR, actual Codex-host and Intel Mac/Windows/Linux native acceptance remain `NOT_RUN`. [Distribution](docs/distribution.md) identifies both snapshots and their receipts.

## Who is it for?

People doing work on a computer while relevant text lives on their phone: proposal comments in a chat, a copied error message, or notes needed by an active coding task. The first design serves one person and nearby devices on a reachable, trusted local network.

It also serves an Agent that can call a local CLI and has a concrete reason to request that text. Basic transfer remains useful without an Agent.

## What problem does it remove?

Moving text is easy in isolation; moving it with the right context can involve switching to a chat or notes app, sending to oneself, locating the message on the computer, and explaining where it belongs. Ferry Dock provides a direct scan, paste, send path, followed by copying or continuing the requesting task. This describes its interaction, not a measured speed advantage over those alternatives.

Task collection adds a specific prompt, a request identity, bounded waiting, and a result accessible through that request's capability. It does not make an Agent responsible for deciding everything on the phone.

For example, paste a client's phone-chat edits into a launch-proposal request; the computer task reads that feedback and revises the proposal. Or send a copied error message into the coding task that requested it. These are text handoffs: the app does not inspect chats, extract text from screenshots, control the phone, or grant the Agent new instructions or permissions.

## What is the simplest way to start?

For an Apple Silicon Mac: download the [published CLI archive](https://github.com/Yankj/ferry-dock/releases/download/v0.1.0-alpha.2/ferry-dock-0.1.0-alpha.2-darwin-arm64.tar.gz), extract it, enter its versioned directory in Terminal, and run `./ferry-dock desktop`. No Mac app, developer runtime, installer or account is required. The launcher requests the system browser to open; a successfully loaded computer page automatically creates a session and QR, without an initial New session click. Scan on the phone, paste, send, then Copy on the computer. Run the same `desktop` command again to reopen a verified running instance. Stop with **Quit Ferry Dock**; closing the tab does not stop the service.

This is a testing prerelease without Developer ID signing or Apple notarization. macOS can warn or block downloaded executables. Download/hash checks and developer-machine runs do not establish browser-download quarantine/Gatekeeper, default-browser auto-opening or real-phone acceptance. The [usage guide](docs/usage.md) gives exact download/extract/start steps, checksum verification and manual Skill prompts. App bundles and other-platform native archives are not uploaded in this release; source checkout/build is a contributor path.

Task collection adds one explicit action: `request create` saves a QR PNG and returns its path; it does not display it. The user opens that PNG, or a capable Agent displays it in the requesting conversation. The ordinary inbox QR does not become that request's QR.

## Why not use messaging, AirDrop, or another local transfer tool?

Those are reasonable alternatives when they already make the handoff easy. Ordinary transfer alone is not a claim that Ferry Dock must replace them.

Ferry Dock's intended distinction is the optional task-bound loop: a shell-capable Agent creates the request and gets its result back through the same interface. The user sees the information needed for that work, and parallel requests keep separate permissions. The project must demonstrate that advantage in a real task rather than infer it from adding an AI label.

## Is this a cloud drive or a general Agent platform?

No. The accepted form is one Go core, with a published Apple Silicon Mac CLI testing package, small web pages, and an optional local Codex Skill. A local npm wrapper and fixed-tag Go source installation are entry choices for people who already use those runtimes; they do not add another transfer backend. Other-platform native CLI packages remain local previews. Historical alpha.1/alpha.2 App bundles are retained as evidence, with their launcher recommendation withdrawn because of the signature defect. These packages do not introduce another backend. There is no hosted account, durable file library, team workspace, or catalogue of Agent integrations in this scope.

The npm entry is now implemented and locally tested, but not published to a registry; a public `npx` command is not available. MCP and a browser extension remain unimplemented: revisit them only for a specific client without usable shell access or a separate primary desktop selected-text need. Homebrew distribution is not implemented. See [the product-shape decision](docs/product-shape.md).

## How does the ordinary mode work?

Run `./ferry-dock desktop` from the extracted published Mac arm64 CLI directory. Do not use the old alpha.1/alpha.2 App launcher. The launcher starts/reopens its verified Go service and opens the system browser. The page creates a temporary session and shows a locally generated QR. Scan it on the phone, paste text, and send. The computer retrieves it and offers Copy. End the session when finished, or let it expire.

Ordinary sessions allow repeated text submissions and remain separate from one-response collection requests. No model or Skill is required to run the service or transfer text.

## What must be installed, and where can it run?

The public default is the [prebuilt Apple Silicon Mac CLI](https://github.com/Yankj/ferry-dock/releases/download/v0.1.0-alpha.2/ferry-dock-0.1.0-alpha.2-darwin-arm64.tar.gz). Download, extract, enter the package directory, and explicitly run `desktop`; no app installation, Git clone, Go/Node runtime, global PATH change, or Agent configuration change is required. The phone uses a browser with JavaScript. Only Mac arm64 has an uploaded binary in this prerelease; other-platform builds are local previews and the old App bundles are not recommended launchers.

A future corrected `.app` would package this product rather than add a separate platform; it is not required by the published CLI. The alpha.1/alpha.2 App previews must not be treated as working downloads. The native entry adds no installation wizard, registration, or login item.

Git and Go are contributor/source-build prerequisites. The packaging script also uses Python's standard library, but preview users do not run that script. After packaging, the application's pages, QR generation, and brand assets are local, without a runtime cloud API or telemetry call in the Ferry Dock service/UI.

Build and CI platform results are not evidence that a physical phone, mobile clipboard permission, camera scanner, or network works. Real Android/iOS and actual Codex-host acceptance must name the tested device or host and remain `NOT_RUN` when not exercised.

## Is the npm entry a working public npx command?

Not yet. The local `ferry-dock@0.1.0-alpha.2` TGZ is implemented and passed 79 assertions on Mac arm64 with Node 22.17.1/npm 10.9.2. It bundles the same pinned alpha.2/a351555 Go binary, has no runtime dependencies or install lifecycle scripts, and makes no backend download at installation or startup. Its JavaScript entry maps no arguments to `desktop`; explicit native arguments retain their meaning.

It currently supports Apple Silicon macOS with **arm64 Node 22+**, not x64 Node under Rosetta or other platforms. The package name is a candidate, not a confirmed npm ownership/publication claim. There is no published TGZ URL or registry `npx` recipe. Someone given the verified local file can install and run it in a private/local prefix using the [documented npm install/exec commands](docs/usage.md#node-users-local-package-only). Everyone else can use the existing native Release download. An eventual one-command registry entry requires a confirmed owner/name and an approved publication; it is not presented as usable today.

Local tests included offline script-disabled install/exec, argument/exit handling, real wait-interruption signals/PTY and explicit no-browser lifecycle checks. Default no-argument mapping and unsupported-platform guards used a VM. These do not establish public registry installation, default-browser opening, real-phone or actual Codex-host behavior. The wrapper cannot remove macOS signing/Gatekeeper or HTTP trust boundaries, and may reuse a running service without attesting its binary version. It does not quit a shared service to upgrade it.

## Can I install it with Go?

Yes, with an existing Go 1.26+ toolchain and network access. In a POSIX shell:

```sh
GOBIN="$(pwd)/ferry-dock-bin" go install github.com/Yankj/ferry-dock/cmd/ferry-dock@v0.1.0-alpha.2
go version -m ./ferry-dock-bin/ferry-dock
./ferry-dock-bin/ferry-dock desktop
```

A fresh Go 1.27.3 Mac arm64 installation passed 31 assertions for command help, private-loopback ordinary/request flows, service reuse and cleanup. The tag is `a351555`; application `version` still prints `dev` / `unknown` because that source tag has no release linker metadata. `go version -m` should identify module `github.com/Yankj/ferry-dock` at `v0.1.0-alpha.2`, which is the installation evidence. This source-build route does not promise offline installation or Go 1.26/native-other-platform acceptance. It installs only the executable: obtain the optional Skill separately and reference it manually. [Full details](docs/distribution.md#go-install-from-the-fixed-tag).

## Is the app a second native UI or another backend?

No. `Ferry Dock.app/Contents/MacOS/ferry-dock` is built from the same Go command as the standalone CLI, with desktop as its no-argument default. It launches the existing browser interface; no Swift, Electron, or second request store is introduced. The app's executable also supports `version` and `request` commands. Usage documents and the manual Skill are bundled under `Contents/Resources`. These architecture facts do not repair the known old App signature; use the CLI until a corrected private candidate has its own validation.

## Does closing the browser quit the app?

No. The short-lived launcher exits after starting/reopening its own background service and opening the browser. Close the browser and the service keeps running. Run `./ferry-dock desktop` again to return to the verified instance. **Quit Ferry Dock** on the local computer page authenticates the computer capability and loopback request, then stops the service and clears all in-memory sessions and collection requests.

The desktop launcher serializes startup and checks its saved owner capability and instance ID before reusing a service. An unknown service is an error, not something to kill or replace automatically. Quitting a shared service affects other tasks; canceling one request does not.

## Must I enter an IP address?

Default desktop LAN mode listens on all IPv4 interfaces at a free port and advertises a private IPv4 address from the OS primary interface, or the only eligible private address. If no choice is unambiguous, it binds loopback and reports **Local only**. A physical phone cannot reach loopback. Advanced `--listen` and `--public-url` configuration uses a verified origin and applies only to a new instance, not one reused on relaunch. Selection does not bypass Wi-Fi isolation, VPN routing, or a firewall.

Foreground `serve` retains its explicit operator configuration and loopback default. Neither entry point makes HTTP encrypted.

Desktop listener overrides are limited to `127.0.0.1:PORT` or `0.0.0.0:PORT`, with numeric ports 0–65535; other configurations use `serve`. Automatic candidates exclude point-to-point VPN interfaces.

## Is the preview signed, notarized, or accepted by Gatekeeper?

The packaging script performs no Developer ID signing or Apple notarization. A linker ad-hoc signature is not publisher identity. Local bundle/version/HTTP or Safari loopback checks do not prove downloaded-file first launch, Finder/default-browser auto-opening, or Gatekeeper acceptance. [Apple's signing and notarization guidance](https://developer.apple.com/developer-id/) describes those separate checks. Windows previews are also publisher-unsigned; [Microsoft's SmartScreen overview](https://learn.microsoft.com/en-us/windows/security/operating-system-security/virus-and-threat-protection/microsoft-defender-smartscreen/) describes download/app reputation checks. No bypass procedure is provided. Artifact hashes and observed acceptance scopes are in [distribution](docs/distribution.md).

## Why did macOS say the App is damaged?

The reported downloaded App error prompted a separate bundle check. The retained alpha.2 ZIP passed CRC, SHA-256, extraction and executable-mode checks. Its complete Apple Silicon App nevertheless failed `codesign --verify --deep --strict` with `code has no resources but signature indicates they must be present`; the same binary verified when checked outside the bundle. The old signature was a Go-linker ad-hoc executable signature, without a signature binding the complete Info.plist/resources envelope. The Intel App was unsigned. Archive integrity and direct executable tests missed this packaging defect.

The repair is to finish staging the entire App and its resources, sign that complete new bundle ad hoc, verify it strictly, then archive and reverify the extracted sealed bytes. The alpha.3 candidate is being tested privately; no existing Release, tag or alpha.2 archive is being overwritten. Ad-hoc structural verification does not identify a trusted publisher, obtain Apple notarization, or guarantee Gatekeeper acceptance after a browser download. No quarantine removal or security-setting bypass is part of the fix. Use the native CLI's documented route with its own unsigned-download limits while App distribution remains unaccepted.

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

To use it manually, give a shell-capable Agent the readable absolute path to the bundled `skills/ferry-dock/SKILL.md`, the executable path, and the established private control-file path. This does not register a Skill globally or assert host auto-discovery. If a wait returns pending and the host stops, ask that same conversation to continue using its saved handle. The [copyable prompts](docs/usage.md#4-let-codex-follow-the-local-skill-manually) specify identity checks, untrusted-data handling and repeated-read deduplication. Actual Codex-host acceptance is still `NOT_RUN`.

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

Alpha.2 has its own [artifact manifest](docs/benchmarks/2026-10-29-alpha2-artifacts.json), [package/native validation](docs/benchmarks/2026-10-29-alpha2-validation.json), and [same-input rebuild receipt](docs/benchmarks/2026-10-29-alpha2-reproducibility.json), pinned to clean `a351555`. Its eight archives and ten identical rebuild outputs passed the recorded checks, with native Mac arm64 direct-executable lifecycle/CLI/cleanup checks; these omitted complete App-bundle signature verification. The later signature defect withdraws the old App launch recommendation. Dark/phone-size GUI acceptance remains blocked. Later evidence-document commits do not rebuild these archives or their bundled snapshot documentation. No new alpha.2 startup timing is claimed. Alpha.1 and its measurements remain pinned to `3d6fca8`, with all ten output hashes unchanged. Generating or testing a local `.app` is still not public distribution or Finder/Gatekeeper/phone acceptance.
