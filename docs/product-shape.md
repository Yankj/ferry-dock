# Product shape: a small local bridge

Ferry Dock brings phone-side text into work already happening on a computer. Its value is a short, contextual handoff: the person supplies missing text, the right task receives it, and work can continue without another messaging inbox or a required AI service.

This document records the delivered text scope. [Request v1](contracts/request-v1.md) defines the collection interface; source, executed commands, and the verification record establish the evidence for each claim. No real-phone or Codex-host result is implied here.

## Two useful paths, one local service

**Ordinary transfer:** run the Go service, open the private computer page, scan its QR, paste and send on the phone, then copy on the computer. It needs no AI component. The phone page stays ready for subsequent messages within the temporary session.

**Task collection:** an Agent needs one piece of phone-side text. It creates a request naming the work and missing input, displays a QR, and reads only that request's result through a private handle. The original task interprets the feedback and continues. The first collection format is one plain-text response.

The service and phone page do the transfer. The CLI gives a shell-capable Agent a machine-readable interface. A repository-local Codex Skill explains when to collect information, how to handle waiting, and how to use the result safely. The Skill is not a daemon, an automatic installation, or a host notification mechanism.

## The proposal scenario

1. The user and Agent draft a proposal on the computer.
2. Relevant changes are in a phone chat. The Agent creates a collection request labeled with the proposal and asks for those comments.
3. The phone opens the request-specific page and shows the question. The user pastes the comments and sends once.
4. The Agent reads the result associated with that request and revises the same proposal within the original task's scope.

A second task can request different text at the same time. Its reader and sender capabilities are independent. A shared or altered task label cannot grant access to the first request. Repeated reads return the same input ID; the consumer checks that ID before repeating a business action.

## Deliberate form

The current product is **Go CLI + scan-to-open web pages + an optional Codex Skill**. It has one local request store and one set of transfer semantics.

| Form | Decision | Evidence that would justify revisiting |
| --- | --- | --- |
| Native Go executable and web pages | Current delivery form | Keep until a concrete user problem calls for another entry point. |
| Repository-local Codex Skill | Current optional workflow guide | Validate a real Codex task; do not require it for ordinary transfer. |
| npm/npx launcher | Not implemented or scheduled | Installation is demonstrated to be the main barrier for intended users. |
| MCP adapter | Not implemented or scheduled | An identified client needs collection tools and has no usable shell interface. |
| Browser extension or plugin | Not implemented or scheduled | Desktop selected-text sharing becomes an independent primary use case. |

This is not a plan to accumulate all five forms. Another adapter must reuse the existing core and earn its maintenance cost with a specific access problem.

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

The release should demonstrate both ordinary transfer and a synthetic compiled-CLI proposal loop, plus negative tests for cross-request reads/writes, labels, bounds, expiry, cancellation, retry deduplication, stable input IDs, and interrupted waits. Synthetic tests must be labeled synthetic. Real browser, Android/iOS LAN, and actual Codex-host acceptance remain `NOT_RUN` until their specific evidence is recorded.

Performance ambition is expressed through [budgets and reproducible measurements](performance.md), not a claim that Go alone makes the product fastest. Do not publish startup, memory, tail-latency, or mobile-compatibility results that have not been measured.
