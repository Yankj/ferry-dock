# Product shape: a small local bridge

Ferry Dock brings phone-side text into work already happening on a computer. Its value is a short, contextual handoff: the person supplies missing text, the right task receives it, and work can continue without another messaging inbox or a required AI service.

This document records the delivered text scope. [Request v1](contracts/request-v1.md) defines the collection interface; source, executed commands, and the verification record establish the evidence for each claim. No real-phone or Codex-host result is implied here.

## Two useful paths, one local service

**Ordinary transfer:** open the prebuilt macOS app or native CLI's desktop command, scan the browser page's QR, paste and send on the phone, then copy on the computer. It needs no Git, Go, Node, account, or AI component at runtime. The phone page stays ready for subsequent messages within the temporary session. Source building is a contributor path.

**Task collection:** an Agent needs one piece of phone-side text. It creates a request naming the work and missing input, displays a QR, and reads only that request's result through a private handle. The original task interprets the feedback and continues. The first collection format is one plain-text response.

The service and phone page do the transfer. The CLI gives a shell-capable Agent a machine-readable interface. A manual local Codex Skill, included in native archives and the app's Resources, explains when to collect information, how to wait, and how to use results safely. It does not require a source checkout, install itself globally, or wake a host.

## The proposal scenario

1. The user and Agent draft a proposal on the computer.
2. Relevant changes are in a phone chat. The Agent creates a collection request labeled with the proposal and asks for those comments.
3. The phone opens the request-specific page and shows the question. The user pastes the comments and sends once.
4. The Agent reads the result associated with that request and revises the same proposal within the original task's scope.

A second task can request different text at the same time. Its reader and sender capabilities are independent. A shared or altered task label cannot grant access to the first request. Repeated reads return the same input ID; the consumer checks that ID before repeating a business action.

## Deliberate form

The current product is **one Go core + prebuilt macOS app/native CLI + scan-to-open web pages + an optional local Codex Skill**. The app is a Go launcher for the existing browser UI, compiled from the same command with `DefaultMode=desktop`; it is not another backend or a separate Swift/Electron UI. State and transfer semantics remain shared.

Current alpha.2 packages are frozen at clean source `a351555`; the Mac Apple Silicon CLI is available in the [public prerelease](https://github.com/Yankj/ferry-dock/releases/tag/v0.1.0-alpha.2), while App and other-platform packages remain local previews. The interface uses black, white, and gray with translucent layers. Transfer/request semantics and the one-core product shape remain unchanged. All eight archives and same-input rebuild checks passed; Mac arm64 packaged lifecycle/CLI/safety checks passed. Real Safari desktop-light ordinary send/receive and the **Copied** label passed; system paste was not repeated. Dark/phone-size GUI checks remain blocked by an interactive authentication boundary. QR codes keep an opaque background and quiet zone; transparency is for surrounding UI layers, not the scan surface. [Contrast calculations](ui-contrast.md) are distinct from real dark-mode rendering. [Distribution](distribution.md) records the fixed artifact identities and remaining gates.

Version `0.1.0-alpha.1` remains a verified historical local packaging snapshot of clean source `3d6fca8`, with archive/rebuild checks and scoped Mac arm64 lifecycle evidence. Those results do not accept alpha.2. No alpha.1 Release or public artifact URL has been published; the alpha.2 CLI is available separately. [Distribution](distribution.md) separates local artifacts from public availability and Finder/first-launch acceptance.

For users, the `.app` is Ferry Dock itself: first ZIP extraction → open → QR, then open → QR on later use. It adds no installation wizard, registration, login item, or additional desktop platform/runtime.

| Form | Decision | Evidence that would justify revisiting |
| --- | --- | --- |
| Prebuilt macOS launcher app, native Go CLI, and web pages | Current distribution form; local packaging validation is separate from publication | Default users should not need a compiler, Git checkout, or Node. Preserve one Go core. |
| Bundled/manual local Codex Skill | Current optional workflow guide | Validate a real Codex task; do not require it for ordinary transfer or install it globally. |
| npm/npx launcher | Not implemented or scheduled | Installation is demonstrated to be the main barrier for intended users. |
| MCP adapter | Not implemented or scheduled | An identified client needs collection tools and has no usable shell interface. |
| Browser extension or plugin | Not implemented or scheduled | Desktop selected-text sharing becomes an independent primary use case. |

This is not a plan to accumulate all five forms. Another adapter must reuse the existing core and earn its maintenance cost with a specific access problem.

## Desktop lifecycle

The short-lived launcher starts its own background Go service, waits for private control readiness, opens the system browser, and exits. Reopening verifies the saved owner capability and instance ID before returning to the known service. Startup is serialized; an unknown service is not automatically changed.

Closing the browser leaves the service running. **Quit Ferry Dock** on the owner/loopback computer page stops it and discards every in-memory session/request; private cache directories or `startup.log` may remain. Ending a session or canceling one task request has a narrower scope. There is no automatic global PATH, login item, Agent configuration, or system-service installation in this packaging scope.

Default desktop LAN mode listens on all IPv4 interfaces at a free port and advertises an eligible private IPv4 address, or visibly falls back to a loopback listener when the address is ambiguous/unavailable. Reopening a verified instance retains its current configuration. Operator `serve` keeps its explicit configuration. Neither selection nor a QR guarantees phone reachability or encryption.

## What makes it different

- A phone page asks for the missing input for one piece of work instead of opening an undifferentiated shared inbox.
- Request-scoped sender and reader capabilities isolate collection results; a task label supplies context without becoming a permission.
- Short waits return a useful pending state. Timeout does not discard a request, and another read can resume collection.
- Stable input IDs make repeated retrieval recognizable. Delivery retry deduplication and downstream business-effect deduplication remain separate responsibilities.
- The ordinary text path works without a model, account, cloud relay, or Agent setup.

## Boundaries

Ferry Dock is not a general cloud drive, persistent chat, mobile control tool, or multi-client Agent platform. The current slice does not include files, photos, screen capture, audio, durable history, automatic clipboard monitoring, or an Internet relay. It does not install global Agent configuration.

HTTP on a trusted, reachable LAN is the transport boundary. Capabilities separate application permissions, but HTTP does not hide them or submitted text from a network observer. A QR is a capability-bearing invitation, not encryption.

Phone content is returned as `untrusted_user_input`; it cannot alter Agent instructions or grant execution permission. A Skill cannot wake a paused host. CLI waiting, host continuation, and applying a proposal edit are different steps with separate evidence.

Local operation describes the Ferry Dock service. Once a result is passed into an Agent, its host controls cloud-model transmission and retention; the optional Agent chain is not guaranteed to be local-only.

## Completion evidence

The release should demonstrate both ordinary transfer and a synthetic compiled-CLI proposal loop, plus negative tests for cross-request reads/writes, labels, bounds, expiry, cancellation, retry deduplication, stable input IDs, and interrupted waits. Synthetic tests must be labeled synthetic. Actual Safari loopback UI checks have recorded scoped passes, including same-tab request switching on a fresh binary. Finder/default-browser auto-opening, Android/iOS LAN/QR, Gatekeeper, and actual Codex-host acceptance remain `NOT_RUN` until their own evidence exists.

Performance ambition is expressed through [budgets and reproducible measurements](performance.md), not a claim that Go alone makes the product fastest. Do not publish startup, memory, tail-latency, or mobile-compatibility results that have not been measured.
