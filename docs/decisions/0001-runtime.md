# ADR 0001: Go core with embedded web assets

Status: accepted for the alpha. Date: 2026-10-28.

## Decision

Use one Go program for the local HTTP service, temporary session state, and embedded HTML/CSS/JavaScript. Keep the browser client framework-free. Optional CLI/Skill and MCP entry points will adapt the same operations; ordinary transfer will not need AI or another runtime.

This is a packaging and maintenance decision with performance requirements. It is not evidence that Go is universally faster than Node or Rust. No equivalent three-language benchmark has been run for Ferry Dock.

## Context

The initial workload is a few local devices sending bounded text. The intended product also needs a short launch path, no phone installation, predictable cleanup, and an implementation that contributors can inspect. Future file transfer must stream with bounded buffering and cancellation. Language choice cannot substitute for those properties.

## Options

| Option | Strengths for this project | Costs and questions to measure |
| --- | --- | --- |
| Node.js + TypeScript | Shared language with the browser; mature HTTP/stream APIs; convenient npm entry point. Node supports backpressure and single executable applications. | An npm launch normally needs Node; a standalone package has its own build/platform constraints. Measure startup, resident memory, and tail latency when CPU work shares the event loop. Correct stream backpressure remains required. |
| Go | Standard HTTP server, built-in embedding, simple native executable distribution, and a compact concurrency model. Fits a small local service without a database or frontend build. | Garbage collection and allocations still affect memory and latency. Bound state and queues, profile real workloads, and test concurrent state transitions. Cross-platform build success does not replace device acceptance. |
| Rust | Native distribution and direct control over allocation; ownership supports memory and thread safety without a garbage collector. A strong option for tight memory limits or measured hot paths. | HTTP/async choices add design surface for this small service. Ownership and cancellation must still be designed correctly. Measure whether the control produces a relevant improvement before accepting the extra maintenance cost. |

Node's stream support makes it a viable I/O implementation: a writable that returns `false` must be allowed to drain before more writes. Its executable packaging is also real, so “Node cannot ship a binary” is not a reason to reject it. See the official [backpressure guide](https://nodejs.org/learn/modules/backpressuring-in-streams) and [single executable documentation](https://nodejs.org/api/single-executable-applications.html).

Go's [HTTP package](https://pkg.go.dev/net/http) and [embed package](https://pkg.go.dev/embed) cover the initial server and asset packaging. Its [garbage collector guide](https://go.dev/doc/gc-guide) explains the memory/CPU tradeoff that still needs measurement. Rust's [official language overview](https://rust-lang.org/) documents its ownership and no-GC model; those properties do not determine Ferry Dock's end-to-end speed by themselves.

MCP does not force the core into TypeScript. The official [SDK listing, version 2026-07-28](https://modelcontextprotocol.io/docs/2026-07-28/sdk) lists TypeScript, Go, and Rust as Tier 1. SDK availability is a future adapter consideration, not a reason to add an MCP dependency to plain transfer now.

## Consequences

- One service owns session state and permissions. Avoid maintaining separate Node and native backends.
- Build the web UI into the executable; avoid runtime CDN, font, QR, and model calls.
- Start with bounded memory and explicit expiry. Add persistence only for a demonstrated need.
- A future npm package may be a thin launcher for platform binaries. It would need checksum verification and a clear update story, not a second server implementation.
- Keep the first protocol small enough to test through real HTTP requests.

## Revisit when

Revisit this decision if repeatable measurements miss [the budgets](../performance.md) after profiling and fixing identified costs, a target platform cannot support the chosen build, or a concrete adapter requirement cannot be met cleanly. Compare equivalent semantics, limits, transport, and hardware before considering a rewrite. Preserve the external behavior so the comparison measures implementation rather than reduced work.
