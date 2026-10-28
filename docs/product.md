# Product contract

Ferry Dock moves text from a phone to a computer with a short, deliberate interaction: scan, paste, send, copy. The computer runs the service; the phone uses its browser. Basic use requires no account, model, cloud service, or mobile installation.

This document defines the ordinary text alpha and one-response collection slice. A criterion below is a release gate, not a claim that it has already been tested; implementation and recorded checks establish completion. See [product shape](product-shape.md) for the chosen form and [request v1](contracts/request-v1.md) for the collection contract.

## The first useful experience

1. Start Ferry Dock on the computer and open its private computer URL. The page automatically creates a temporary session and displays its QR code and phone link.
2. Scan the code on a phone that can reach the computer on the local network.
3. Paste or type text into the phone page, then press **Send to computer**.
4. The computer displays the text. Press **Copy** to put the original text on the clipboard.

The QR code is generated locally from embedded code. Rendering or scanning it does not require a third-party QR website. The phone still needs network access to the computer; the code does not bypass client isolation, routing, or firewall rules.

An active session remains useful for subsequent messages. Sending a second message must not require scanning another code. **End session** invalidates its phone link and removes its retained messages from the service; **New session** creates a fresh identifier and sender capability. The process owner capability remains valid until the process ends.

## Interface rules

- The phone's primary view is one text field and one primary send action. Show the destination and session state without a setup wizard or an account prompt.
- Enable the send action when the input is valid. Preserve the draft on a failed request and offer an explicit retry.
- Display a clear received acknowledgement after the service accepts a message. Do not describe that acknowledgement as “copied on the computer.”
- Keep the receiver's QR code, new text, copy action, and end-session action easy to find. A successful copy needs visible feedback; failure must leave the text selectable for manual copying.
- Do not require the user to choose a transport, MIME type, model, or integration before sending text.
- Do not request clipboard permission on page load. Manual system paste is the baseline. Any future read-clipboard action must be user initiated, optional, and have a manual fallback.
- Do not clear or normalize meaningful leading spaces, trailing spaces, line breaks, or Unicode characters. Whitespace-only input may be rejected without trimming accepted content.
- Show an actionable expired, closed, unreachable, or over-limit state. Do not leave a spinner running indefinitely.
- Use native semantic controls, labels, visible keyboard focus, sufficient contrast, and layouts that work with the mobile keyboard open. State must not depend on colour alone.

“Shortest path” means removing unnecessary decisions and repeated setup. It does not mean sending the clipboard automatically or hiding the user's final send action.

## Initial scope

The alpha is a single Go executable with embedded HTML, CSS, JavaScript, and a local QR generator. Its data model is temporary text sessions stored in process memory. It supports session creation, text delivery, receiver retrieval, and session closure, with expiration, body limits, bounded retention, and duplicate-request handling.

The phone receives permission to submit to one session. The computer retains a separate owner capability for retrieving messages and closing that session. A phone must not receive an inbox browser, management panel, or owner key.

## Task collection

An Agent drafting a proposal can ask for comments held in a phone chat. The request identifies that proposal and the missing input; the phone page shows the question, accepts one text response, and the requesting task reads it through a private handle. Parallel tasks do not retrieve an undifferentiated latest message.

A server-generated request ID and independent reader/sender capabilities isolate the collection. The caller's task label is correlation metadata, never authorization. Request input defaults to a 16 KiB limit, while ordinary sessions retain their separate 64 KiB message limit. Timeout returns pending without canceling collection; an interrupted wait does not delete the request.

Reads return the same stable input ID and mark the text `untrusted_user_input`. The consumer applies relevant feedback only within the original task and deduplicates completed business effects by that ID. It must inspect an uncertain prior edit before retrying after interruption. Neither repeated-read support nor the Skill promises exactly-once business execution or automatic host wake-up.

The first delivery form is Go CLI plus scan-to-open pages and an optional manual repository-local Codex Skill. Ordinary transfer continues without AI. A synthetic compiled-CLI proposal scenario and a real Codex/phone acceptance are distinct checks.

The first release targets a trusted, directly reachable LAN over HTTP. It does not claim confidentiality against another participant who can observe or modify that network. This boundary must be visible before using the service for sensitive content; see [Architecture](architecture.md).

## Later scope

These capabilities are intentionally outside the text alpha:

- File, image, camera, and audio uploads.
- MCP tools, npm/npx launchers, browser plugins, and automatic host continuation. No such adapter is scheduled by this scope.
- HTTPS provisioning, internet relay, remote pairing, and hosted accounts.
- Durable history, full-text search, device accounts, and team administration.
- Native mobile or desktop clients, operating-system share targets, and background clipboard synchronization.

Additional entry points require the concrete user problems recorded in [product shape](product-shape.md); the product does not aim to ship every form. Ordinary users must continue to use Ferry Dock without installing or configuring any AI component.

## Measurable acceptance

Record the browser, operating system, network, build revision, and result for manual checks. A local HTTP test cannot substitute for a real phone scanning the QR code.

| Scenario | Required result |
| --- | --- |
| First transfer | A computer and a real phone on a reachable LAN complete scan → paste/type → send → copy without a mobile installation, account, external QR service, or AI setup. |
| Repeat transfer | The same open phone page submits another message without rescanning or recreating the session. |
| Text fidelity | A fixture containing leading/trailing spaces, multiple lines, emoji, and non-ASCII characters is retrieved and copied byte-for-byte as submitted. |
| Empty and oversized input | Whitespace-only input is rejected. Input beyond the configured UTF-8 body limit is rejected; the service remains responsive and the phone retains its draft. |
| Acknowledgement | A success receipt identifies accepted delivery. It makes no claim that the receiver viewed or copied the message. |
| Interrupted request | Retrying an accepted delivery with the same client idempotency key does not create another message. Reusing that key with different text produces a conflict. |
| Receiver reconnect | After a temporary connection interruption, retrieval from the last confirmed cursor includes missed messages once and in order. |
| Role isolation | A phone capability can submit only to its session. It cannot read messages, close the session, or authorize another session. |
| Session end and expiry | Closed or expired sessions reject further delivery and retrieval. Their retained content is removed from the service's accessible state; an old QR code cannot reopen them. |
| Process exit | Restarting the process does not recover old messages or accept old credentials. |
| Clipboard fallback | The receiver reports copy failure accurately and leaves visible selectable text for manual copying. |
| Keyboard and mobile layout | Sending works with the software keyboard open; receiver controls can be used by keyboard and expose accessible names. |
| Resource bounds | Configured session, message, and request limits are enforced. Exhaustion produces a bounded error instead of unbounded memory growth. |
| Request association | Parallel A/B collection readers and senders cannot cross-access; matching or altered task labels grant no authority. |
| Request waiting | Timeout and interrupted waits preserve pending collection; explicit cancellation is separate and removes input. |
| Repeatable results | Repeated reads retain the same input ID; a sample consumer skips an already completed effect and reconciles an uncertain interrupted edit. |
| Input trust | Phone feedback is returned as untrusted data and cannot grant execution permission or alter Agent configuration. |

The interaction count can be measured after the phone page has loaded: the normal path is paste/type followed by one **Send to computer** action. Measure service latency separately from scan time, typing, permission prompts, and clipboard interaction. Performance budgets, hardware, and measurements belong in the performance documentation; do not publish latency or memory claims before measuring them.

## Open-source quality

The ambition is a widely trusted open-source utility. The initial release must earn that through an honest status, a reproducible build, readable implementation, tests for lifecycle and permissions, documented resource limits, and a security reporting path. Small scope is a quality choice; an alpha label must remain until the published release gates have evidence.
