# Contributing to Tapbeam

Small, reviewable contributions are welcome. For a new input type, transport, dependency, or persistent store, open an issue first so that the change can be evaluated against [product scope](docs/product.md).

## Local checks

Use Go 1.26 or newer. There is no frontend build step.

```sh
go fmt ./...
go vet ./...
go test ./...
go test -race ./...
go build -o bin/tapbeam ./cmd/tapbeam
```

Keep formatting changes focused on the files you touch. Run the race detector on a supported host; if unavailable, record the platform and limitation in the PR. Do not claim a check passed unless you ran it.

## Changes worth testing

For protocol or state changes, test the behavior at its boundary: role separation, session closure and expiry, exact text bytes, duplicate retry behavior, ordering after reconnection, and limits under concurrent requests. Tests should catch a plausible regression rather than repeat implementation details.

For UI changes, check keyboard access, a narrow phone viewport, empty/loading/error states, and copy/paste failure recovery. Real phone acceptance must identify OS, browser, network setup, and what was exercised. A browser emulator does not establish camera QR scanning or mobile clipboard compatibility.

Performance changes need a reproducible workload, machine and toolchain details, before/after measurements, and an explanation of the tradeoff. Follow [the measurement plan](docs/performance.md); do not infer a speedup from the language or framework alone.

## Pull requests

Explain the user-visible problem, resulting behavior, and relevant validation. Keep public examples free of real tokens, phone contents, local network identifiers, and personal data. Document any API or trust-boundary change. Generated code and AI assistance are acceptable; the contributor is responsible for correctness, licenses, and reviewability.

Keep the core small. A new dependency should have a concrete benefit, a compatible license, and a reason that the standard library is insufficient. Do not add tracking, external runtime calls, or AI requirements to ordinary transfer.

## Community

Be respectful and specific. Discuss the change rather than the person. Report suspected vulnerabilities through [SECURITY.md](SECURITY.md), not a public exploit report.

Contributions are submitted under the repository's [MIT license](LICENSE). Preserve copyright and license notices when incorporating third-party code.
