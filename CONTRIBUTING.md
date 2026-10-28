# Contributing to Ferry Dock

Small, reviewable contributions are welcome. For a new input type, transport, dependency, or persistent store, open an issue first so that the change can be evaluated against [product shape](docs/product-shape.md). The current form is a Go CLI, scan-to-open web pages, and an optional repository-local Codex Skill; additional entry points are not a scheduled expansion plan.

## Local checks

Use Go 1.26 or newer. There is no frontend build step. These examples use a POSIX shell; on Windows, use the `.exe` build/invocation form in [the README](README.md#build-and-run).

```sh
go fmt ./...
go vet ./...
go test ./...
go test -race ./...
go build -o bin/ferry-dock ./cmd/ferry-dock
```

Keep formatting changes focused on the files you touch. Run the race detector on a supported host; if unavailable, record the platform and limitation in the PR. Do not claim a check passed unless you ran it.

The optional developer checks below need Python 3 and Node 18 or newer; neither is an application runtime dependency. After building the binary above:

```sh
python3 scripts/smoke-http.py --binary bin/ferry-dock
python3 scripts/smoke-request.py --binary bin/ferry-dock
node scripts/test-ui.cjs
node scripts/smoke-ui.cjs --binary bin/ferry-dock
```

`smoke-ui.cjs` obtains the embedded HTML and JavaScript from its own compiled service, runs that script with a DOM adapter, and uses real loopback HTTP plus the CLI. Offline and lost-response cases are explicit local fault injection. It does not render a browser, use the OS clipboard, scan a QR, or execute an actual Agent host. On Windows, pass the `.exe` binary path.

## Changes worth testing

For protocol or state changes, test the behavior at its boundary: role separation, session closure and expiry, exact text bytes, duplicate retry behavior, ordering after reconnection, and limits under concurrent requests. Tests should catch a plausible regression rather than repeat implementation details.

For collection requests, follow [request v1](docs/contracts/request-v1.md). Cover A/B request isolation for both reader and sender, labels that grant no authority, cancellation and expiry erasing input, repeatable reads with stable input IDs, and wait timeout/interruption without request cancellation. Keep ordinary-session regression coverage. A synthetic proposal consumer may demonstrate downstream deduplication; it must not claim a transaction guaranteeing exactly-once Agent execution.

Test mutation uncertainty separately: interruption during create or explicit cancel must not be reported as proof that the operation did not execute. `outcome_unknown` recovery should use a saved handle when available, and must not blindly repeat creation without one.

Keep [the repository-local Skill](skills/ferry-dock/SKILL.md), CLI help, README examples, PRFAQ, and claims-to-evidence record consistent with executed behavior. The Skill must not install itself globally, change Agent configuration, treat phone content as tool instructions, or claim to wake a host. A changed command example should be exercised with synthetic data and private runtime files before being documented as working.

For UI changes, check keyboard access, a narrow phone viewport, empty/loading/error states, and copy/paste failure recovery. Real phone acceptance must identify OS, browser, network setup, and what was exercised. A browser emulator does not establish camera QR scanning or mobile clipboard compatibility.

Record synthetic CLI/HTTP, browser, real-phone LAN, and actual Codex-host acceptance separately. Cross-platform builds do not establish real-device compatibility. Use `NOT_RUN` for checks the environment could not perform, rather than converting them into a pass.

Performance changes need a reproducible workload, machine and toolchain details, before/after measurements, and an explanation of the tradeoff. Follow [the measurement plan](docs/performance.md); do not infer a speedup from the language or framework alone.

## Pull requests

Explain the user-visible problem, resulting behavior, and relevant validation. Keep public examples free of real tokens, phone contents, local network identifiers, and personal data. Document any API or trust-boundary change. Generated code and AI assistance are acceptable; the contributor is responsible for correctness, licenses, and reviewability.

Keep the core small. A new dependency should have a concrete benefit, a compatible license, and a reason that the standard library is insufficient. Do not add tracking, external runtime calls, or AI requirements to ordinary transfer.

## Community

Be respectful and specific. Discuss the change rather than the person. Report suspected vulnerabilities through [SECURITY.md](SECURITY.md), not a public exploit report.

Contributions are submitted under the repository's [MIT license](LICENSE). Preserve copyright and license notices when incorporating third-party code.
