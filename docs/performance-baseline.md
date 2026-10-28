# Measured loopback baseline — 2026-10-28

One complete local run measured the compiled request/CLI slice. These are
observations from synthetic loopback traffic, not service guarantees, mobile
experience measurements, maximum capacity, or language comparisons.

[Raw JSON](benchmarks/2026-10-28-macos-arm64.json) contains every latency sample,
RSS sample, exact binary/build identity, counts, and method. Its SHA-256 is
`55d57ce416b6d1a0c1447da2356b135f1cc05a683f38e7e21a96931df5798a85`. No capabilities, submitted text, request IDs,
or response bodies are retained in that artifact.

## Environment and identity

| Item | Recorded value |
| --- | --- |
| Start | 2026-10-28 15:24:50 UTC |
| Machine | Apple M4 Pro, 14 logical CPUs, 24 GiB RAM |
| OS | macOS / Darwin 27.0.0, arm64 |
| Toolchain | Go 1.27.3, `-trimpath`, `CGO_ENABLED=1`, no race instrumentation |
| Binary size | 10,745,538 bytes |
| Embedded VCS revision | `5d3caff0833ff52e805a4a874e7f07d82e39c624` |
| Embedded VCS modified | `true`; documentation/brand work remained uncommitted |
| Binary SHA-256 | `b4a53c0b1ced3ad09945a472ee133c2b9193517cc6b0241592517eabf3815d86` |

The Go code and binary were frozen during measurement; the binary hash matched
again at completion. This is not represented as a clean tagged-release build.
Project compilation and test work was paused, but the user's desktop background
load was not controlled. Power mode was not recorded.

## Actual observations

All latency values below are milliseconds. Percentiles use nearest rank.
Request operations used one client and 32 samples; ordinary text phases used
10 clients and 1,000 successful submit/read pairs each, with 1 KiB text.

| Operation | Samples | p50 | p95 | p99 | Max |
| --- | ---: | ---: | ---: | ---: | ---: |
| Process spawn to HTTP readiness | 100 | 6.148 | 8.091 | 12.718 | 479.428 |
| Ordinary text submit | 1,000 | 0.950 | 1.880 | 2.447 | 3.875 |
| Ordinary incremental read | 1,000 | 0.523 | 1.214 | 1.892 | 2.895 |
| Request create, including QR | 32 | 1.511 | 1.584 | 1.731 | 1.731 |
| Request input submit | 32 | 0.110 | 0.206 | 0.294 | 0.294 |
| Request result read | 32 | 0.096 | 0.106 | 0.116 | 0.116 |
| Ordinary submit with 8 pending waits | 1,000 | 1.179 | 3.651 | 6.948 | 12.775 |
| Ordinary read with 8 pending waits | 1,000 | 0.788 | 3.366 | 7.127 | 10.147 |

**The first measured startup sample was 479.428 ms.** It is retained in the raw
samples and maximum; its cause was not profiled. The p95 value must not be
restated as a claim that every startup takes 8 ms. Filesystem caches were not
explicitly cleared; this was not an OS cold boot experiment.

| RSS observation | KiB | MiB |
| --- | ---: | ---: |
| Initial empty process | 12,128 | 11.84 |
| Empty process after 60.012 seconds | 12,144 | 11.86 |
| Before ordinary capacity fill, after API workloads | 32,368 | 31.61 |
| At 16 MiB retained ordinary text; highest observed sample | 46,256 | 45.17 |
| About 0.5 seconds after closing those inboxes | 46,256 | 45.17 |

There were **zero unexpected HTTP errors**. One intentional HTTP `429` capacity
probe confirmed that all eight wait slots were occupied before the ordinary
text workload. All eight waits ended through explicit cancellation after that
workload, rather than timing out. Reads were checked against the original
synthetic text and corresponding receipts; quota rejections were not counted as
successful throughput.

The ordinary phases completed in 0.178 and 0.292 seconds respectively, including
rotation/cleanup. Those are brief workload windows; their observed throughput
is not a sustained server capacity claim. This single run does not establish a
causal overhead estimate for pending waits or stable tail distributions.

The capacity phase filled the 16 MiB ordinary-text quota, not every possible
request and in-flight allocation. RSS was sampled every 250 ms plus explicit
phase snapshots. **45.17 MiB is an observed sampled peak, not a proven upper
bound.** Closing inboxes did not immediately lower RSS; this record does not
claim immediate OS reclamation or diagnose a leak.

No browser, Android/iOS device, LAN network, or tap-to-display latency was
measured. The webpage's one-second polling interval and real network delay are
additional user-visible costs. Full real-host/phone acceptance remains NOT_RUN.

## Run

Build a non-race binary from a recorded source revision, stop unrelated build
work, and run:

```sh
go build -trimpath -o bin/ferry-dock ./cmd/ferry-dock
python3 scripts/benchmark.py --binary bin/ferry-dock \
  --build-command 'go build -trimpath -o bin/ferry-dock ./cmd/ferry-dock' \
  --output bin/perf-results/baseline.json
```

Use `--go /path/to/go` if Go is not on `PATH`. The harness reads Go build metadata
but does not build, download, or install a runtime. A short functional check must
use `--calibration`; it is explicitly marked non-baseline in JSON. The normal
command requires at least 30 process starts and 60 idle seconds; defaults are
100 starts, 60 idle seconds, 10 text clients and 1,000 successful submit/read
cycles per text phase.

## Recorded phases

- Startup is process spawn through a successful `/healthz` response, without
  explicitly flushing filesystem caches. It is not an OS cold boot or a log-line-only timestamp.
- Idle RSS is sampled before creating any inbox. The record includes its first
  sample and the sample after at least 60 seconds. `ps` reads only the harness's
  own child PID; it never scans other processes.
- Ordinary text uses 1 KiB payloads and one persistent HTTP connection per
  client. Each inbox rotates below its message quota; rejection latency cannot
  silently masquerade as a successful transfer. Every read is checked against
  the corresponding receipt and original synthetic text.
- Request creation (including local QR generation), submission, and result
  retrieval are measured separately. The default 32 requests remain below the
  retained-record quota; cleanup explicitly cancels them. Stable receipt IDs,
  original text and the untrusted-data label are checked.
- The wait-pressure phase dispatches eight pending requests and confirms slot
  saturation with an expected capacity probe before running ordinary text.
  Wait results must remain pending until explicitly canceled after the workload;
  timed-out or failed waits fail the phase instead of being counted as pressure.
- The session-capacity phase retains exactly 16 MiB of ordinary text across 16
  full inboxes, samples RSS, closes them, and samples again. RSS need not fall
  immediately when references are released; it is not cryptographic erasure.

The binary hash is checked again at completion; replacing the binary during a
run fails it. Embedded binary revision and working-tree revision are recorded
separately so an old binary is not attributed to a newer checkout.

All phase durations, successful operation counts, raw latency samples, HTTP
errors, RSS samples, binary SHA-256, embedded Go VCS revision/modified state, current working-tree
commit/dirty state, OS, architecture, CPU and RAM accompany each result. Percentiles use the
nearest-rank definition; small sample tails are not confidence intervals.

## Limits

Latency includes Python request sending, HTTP round trip, and reading the
response body; client JSON decoding is excluded. Throughput includes session
rotation and cleanup. The client, sampler, OS scheduler and background software
can affect results. RSS is observed at 250 ms intervals, not an OS high-water
mark. Power mode is not currently detected. These are local engineering
baselines, not cross-language rankings, LAN throughput, mobile tap-to-display
latency, production capacity, or proof of the provisional budgets.

The default raw output directory under `bin/` is ignored by Git. This measured
run is preserved separately at the raw JSON link above. Preserve future raw
results with their summaries so distributions can be compared on the same
machine and toolchain. Real Android/iOS and browser performance remain NOT_RUN.
