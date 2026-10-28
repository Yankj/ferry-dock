# Architecture and trust boundary

Tapbeam's text alpha uses one Go process and one in-memory session store. The binary embeds the browser UI and QR generator. It has no database, external runtime, remote QR renderer, or model dependency.

This is the design contract for the alpha. Exact routes, defaults, flags, and error payloads must be checked against the implementation; the operations below describe required semantics rather than a separately versioned public API. Unimplemented future integrations are not implied by this document.

## Components

```text
computer browser (owner)                phone browser (sender)
        |                                         |
        | create / retrieve / close               | submit text
        +------------------+----------------------+
                           |
                    Go HTTP boundary
             validation, authorization, limits
                           |
                in-memory session store
           lifecycle, ordered messages, deduplication
```

- **Command entry point:** validates configuration, selects listening and advertised addresses, starts the HTTP server, and handles shutdown. LAN mode requires an explicitly configured phone origin reachable from the phone; local-only mode uses loopback. The advertised origin is never derived from an untrusted request's `Host` value.
- **Embedded web UI:** serves the local receiver and phone sender views. A bundled QR generator encodes the phone link without a network request to another service. Browser code renders received text as text, never as executable HTML.
- **HTTP boundary:** restricts methods and origins, authenticates each protected operation, parses bounded requests, and maps lifecycle and validation failures to explicit errors.
- **Session store:** owns state transitions and atomic duplicate detection. HTTP handlers do not bypass it to read or mutate message state.
- **Lifecycle cleanup:** removes expired state and releases retained messages. Request-time expiry checks are required even if scheduled cleanup has not yet run.

Static assets and content submission share the same process. Sharing a process does not grant every browser the same permissions.

## Session model

The process has one owner capability, generated at startup, that authorizes creation, retrieval, and closure across its sessions. Each session contains an opaque identifier, an independently generated sender capability, an expiration time, an ordered message collection, and a map from accepted client idempotency keys to messages. Creating a session does not create a new owner capability.

Each message contains a server-generated receipt identifier (`id`), server-assigned sequence, original text, and acceptance timestamp. The client-generated `idempotencyKey` is distinct from that receipt identifier and is retained in the session's deduplication map.

The session identifier locates state; it is not authorization. Capability keys are generated using the operating system's cryptographically secure randomness and must have sufficient entropy to resist guessing. They must never be derived from a short PIN, timestamp, IP address, or each other.

The lifecycle is:

```text
create → active → closed
              └→ expired
```

Only an active, unexpired session accepts delivery or retrieval. Closing is idempotent for an authorized owner. Creation of a new session does not recycle old identifiers or keys. Process termination discards all state; there is no recovery journal.

## Operations and authority

| Operation | Required authority | Semantics |
| --- | --- | --- |
| Create session | Process owner capability | Creates a temporary session and returns its identifier, expiry, sender URL/QR, and text limit. It does not return a new owner capability. An existing phone capability never authorizes creation. |
| Submit text | Session's sender capability | Validates the body, then atomically accepts one message or returns the existing receipt for a duplicate. Does not return inbox history. |
| Retrieve text | Process owner capability | Returns the requested session's messages in increasing sequence after a confirmed cursor. Does not silently advance beyond messages returned. |
| Close session | Process owner capability | Invalidates that session's sender capability and removes its retained data from accessible application state. The process owner capability remains valid for other sessions and new session creation. |

The terminal prints the owner capability in a loopback computer URL. Owner APIs authorize the Bearer capability; they do not require a loopback `RemoteAddr`. When a LAN listener is enabled, someone who obtains the owner capability can exercise its authority through a configured origin. Keep that capability on the computer. The displayed phone link carries only the session identifier and sender capability. A URL fragment can keep the sender capability out of the initial HTTP request target; phone JavaScript then sends it in an authorization header for API requests. Fragments can still be retained in browser history or exposed to someone who sees the screen. They are not encryption.

Capabilities must not appear in access logs, error messages, analytics, QR-rendering requests, or referrer traffic. Do not put the owner capability into the phone link. A browser's storage is not a security boundary against scripts running in the same origin, so load no third-party script into either view.

## Delivery contract

Request bodies use a small, explicit JSON schema. Reject malformed JSON, unsupported fields where the schema is strict, invalid text, and data above the configured byte limit. Check non-emptiness without altering accepted text. Limits must be applied before retaining an entire untrusted body.

The sender generates an `idempotencyKey` once for a draft and reuses it when retrying that delivery. The server separately generates the message's receipt identifier. Duplicate detection is scoped to the session and is atomic with insertion:

- New idempotency key and valid text: allocate a sequence and return an acceptance receipt.
- Existing idempotency key with identical text: return the original receipt and retain one message.
- Existing idempotency key with different text: reject as a conflict.

The deduplication entry remains available for the retained session lifetime. A receipt means the process accepted the message into volatile state. It is not proof of durable storage, human viewing, or clipboard completion.

The receiver uses incremental retrieval with a server sequence. It updates its cursor only after handling the messages returned by retrieval, and deduplicates display by the server-generated receipt identifier. A submit response must not advance a receiver cursor, because another sender may have submitted an earlier message concurrently. An interrupted retrieval can safely be retried from the last confirmed cursor.

Short polling is sufficient for this alpha's low-frequency text workload. SSE or another notification transport can be considered after measuring a need; it must preserve the same cursor and recovery semantics.

## Bounds and retention

The implementation must explicitly bound request bytes, text bytes, messages per session, active sessions, session lifetime, and HTTP time spent reading requests. When a limit is reached, reject the operation with a useful response rather than silently dropping prior messages or increasing memory without a bound. Document the actual defaults and configuration in the user-facing run instructions.

Messages and deduplication records live only in process memory. Expiration and closure must remove references to their content. This does not promise cryptographic erasure from RAM, operating-system swap, crash dumps, browser history, screenshots, or clipboard managers. Do not add disk persistence or content logging as an invisible implementation detail.

The browser must preserve an unsent draft after a request failure. After successful sending, any draft clearing is a UI choice; it must not be confused with server retention. Clipboard contents remain under the user's operating system and other clipboard tools.

## HTTP threat model

The supported alpha environment is a trusted LAN on which the phone can reach the computer directly. HTTP exposes content and capabilities to a network observer able to inspect traffic. An active network attacker can tamper with requests or the page. Separate capability keys constrain what a sender can do inside the application; they do not mitigate those HTTP transport threats.

| Threat | Application boundary or mitigation | Remaining limit |
| --- | --- | --- |
| A phone reads the inbox or ends another session | Authorize every operation against the required capability and session; negative permission tests are release gates. | Anyone possessing an owner key has that owner's authority. |
| A malicious website reaches the local service | Validate allowed Host values and origins; use browser security headers, expose no permissive CORS policy, and require the process owner capability for session creation. | Owner APIs are capability-protected, not restricted by the client's network address. These controls do not authenticate the LAN or replace TLS. |
| Submitted text runs script | Use text-only DOM rendering, same-origin bundled assets, and a restrictive Content Security Policy. | A compromised computer or same-origin script can access the UI's data. |
| Memory or slow-request exhaustion | Bound bodies, sessions, retained messages, lifetimes, and HTTP read time; fail explicitly at capacity. | A trusted-LAN alpha is not an internet-facing denial-of-service service. |
| A leaked QR code authorizes someone else | Give it sender-only authority, use unguessable keys, and revoke it when the session closes or expires. | Anyone who can see or copy the code can submit while it is valid. |
| A lost response creates duplicate text | Session-scoped client idempotency keys and atomic deduplication. | Restart loses both accepted content and deduplication records. |

Do not infer an allowed origin from an arbitrary incoming `Host` header, allow wildcard origins for convenience, or assume cookies distinguish services on different ports. Validate configured origins and listening addresses explicitly. Reverse proxy and public internet deployments require a separate design and are outside the initial support boundary.

Ordinary LAN HTTP pages may not expose the asynchronous Clipboard API. Manual system paste on the phone is the required baseline. The computer's loopback page may attempt a user-initiated clipboard write; on failure it must leave visible selectable text. The alpha does not silently read a phone's clipboard or capture another application's screen.

## Extension boundary

Future Agent tooling can create a collection request, obtain its phone link, wait or query within bounded time, and retrieve accepted materials. Task and request metadata can be added around the session model without requiring a model for basic transfer. A tool result does not itself guarantee that an Agent host can resume an interrupted task; each integration must define that behavior.

Files and images require explicit streaming, storage quotas, safe filenames, content disposition, cleanup, and download authorization. They should not be added by treating arbitrary file bodies as text messages.

## Design references

The design considered [DropLocal at `16c9fe0`](https://github.com/shiyuanhai/droplocal/tree/16c9fe05e048b2c5ebbe2e75ccb4619620bd9653) for quick local startup and QR-based entry, and [Ferry at `5b78829`](https://github.com/max1874/ferry/tree/5b7882947ef34ae422004ae81ccc2da509693fe1) for an embedded Go UI and incremental retrieval. Tapbeam narrows the initial product to ephemeral receiving sessions with separate owner and sender authority. These are design references, not a claim of shared implementation or compatibility. No upstream source code is copied into these documents.
