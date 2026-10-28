# Performance budgets and measurement plan

These are provisional engineering targets, not measured Tapbeam results or cross-language rankings. The first published baseline must name its reference machine and include raw samples. Revise a target with evidence and a recorded rationale.

## Alpha targets

Measure a compiled executable, not `go run`. Use a fixed commit and toolchain, loopback HTTP, no debugger or race instrumentation, and an otherwise idle machine. Report the OS, CPU, RAM, power mode, and build flags alongside results.

| Metric | Initial target | Workload |
| --- | --- | --- |
| Startup to HTTP readiness | p95 ≤ 150 ms | 100 fresh processes; readiness means a successful HTTP response, not a startup log line |
| Idle resident memory | ≤ 32 MiB | One running process, no sessions, after 60 seconds; record both initial and settled values |
| Text API latency | p95 ≤ 10 ms, p99 ≤ 25 ms | 10 local clients, 1 KiB text, a mixture of submissions and incremental reads; exclude the browser polling interval |
| Frontend delivery | ≤ 64 KiB uncompressed HTML + CSS + JS | Count first-party assets required for each page; record generated QR bytes separately |
| State growth | Within configured bounds | Fill the allowed sessions/messages with maximum-size text; record peak RSS and retained heap |

The alpha permits 16 sessions, each bounded by 128 messages and 1 MiB of text. Stored message bodies are therefore bounded by 16 MiB. That is a payload bound, not a process RSS guarantee. Metadata, in-flight JSON parsing, copies, responses, and the runtime consume additional memory. Measure the complete process before expanding defaults or adding files.

Incremental browser polling adds user-visible delay beyond API latency. Measure phone tap-to-computer display separately, including polling and network time. A fast handler alone does not establish a fast transfer experience.

## Reproducible checks

1. Record `git rev-parse HEAD`, `go version`, OS/architecture, build command, limits, and listener configuration.
2. Build once with `go build -trimpath -o bin/tapbeam ./cmd/tapbeam`. Run correctness checks separately with `go test -race ./...`; do not use race-enabled timings as a release baseline.
3. Run cold-process startup samples and idle RSS sampling using platform-native process metrics. State whether filesystem caches were warm; process restart is not an OS cold boot.
4. Use a fixed payload corpus: ASCII, multi-byte UTF-8, preserved whitespace, near-limit bodies, and invalid/oversized requests. Keep success and rejection latency separate.
5. Run timed HTTP workloads after warm-up. Record request counts, concurrency, percentiles, errors, throughput, peak RSS, allocations, and CPU. Expired/full sessions must not silently change the successful workload into cheap rejections.
6. Exercise duplicate retries, concurrent closure/expiry, reconnect retrieval, and quota saturation. Confirm correctness after the load test.
7. Save the command, raw data, and summary with the environment. Compare repeated runs on the same machine before attributing a change to code.

When Go benchmarks exist, run `go test -run '^$' -bench . -benchmem -count 10 ./...` and compare distributions. An empty benchmark run is not a performance result. HTTP load, startup, and RSS need separate harnesses; no all-in-one benchmark harness is claimed in this alpha.

## Gates before file transfer

Files are not implemented yet. Before enabling them, define stream buffer and global byte quotas, then test:

- Two and eight concurrent large transfers, including a slow receiver, with peak memory independent of total file size.
- Text p99 latency while files transfer; set and validate a mixed-workload budget before release.
- Backpressure, upload/download cancellation, connection loss, full disk, quota rejection, and cleanup of partial files.
- Byte count and end-to-end SHA-256 agreement; do not treat a successful HTTP response as an integrity check.
- Throughput against direct HTTP on the same network and disk, with absolute values and overhead reported.

## Device acceptance

Use real Android Chrome and iOS Safari on a reachable LAN. Record device, OS, browser, Wi-Fi topology, QR scan, manual paste, copy fallback, submit acknowledgement, expiry, and recovery after temporary disconnection. Test one computer at a time and two independent computers to check that links and content do not cross sessions. Loopback tests and viewport emulation do not establish mobile network or clipboard behavior.
