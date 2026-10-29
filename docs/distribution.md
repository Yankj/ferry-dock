# Distribution: prebuilt first

The public user path is a portable **macOS Apple Silicon CLI**. Download, extract, and run `desktop`; Git, Go, Node and a separately installed Mac App are not required. The macOS app and other-platform packages remain local previews. Source builds and packaging tools belong to the contributor path.

## Availability

The [v0.1.0-alpha.2 prerelease](https://github.com/Yankj/ferry-dock/releases/tag/v0.1.0-alpha.2) publishes exactly three assets:

| Public asset | Purpose |
| --- | --- |
| [Apple Silicon CLI archive](https://github.com/Yankj/ferry-dock/releases/download/v0.1.0-alpha.2/ferry-dock-0.1.0-alpha.2-darwin-arm64.tar.gz) | macOS arm64 portable command; 3,260,347 bytes. |
| [SHA256SUMS](https://github.com/Yankj/ferry-dock/releases/download/v0.1.0-alpha.2/SHA256SUMS) | Two entries: that CLI archive and the original manifest. |
| [manifest.json](https://github.com/Yankj/ferry-dock/releases/download/v0.1.0-alpha.2/manifest.json) | Original full local-build provenance, including unpublished artifacts. |

The tag and artifact source are exactly `a351555ccd1615795bc2a6c10dd7e97a633a074f`; subsequent repository changes are documentation/evidence. This is an unsigned, unnotarized **test release**, not proof of downloaded-file OS acceptance. The original manifest inventories eight local artifacts, but the release includes only the Mac arm64 CLI. Its release-specific checksum list therefore has no missing App/other-platform entries. Download all three files into the same directory, then run:

```sh
shasum -a 256 -c SHA256SUMS
tar -xzf ferry-dock-0.1.0-alpha.2-darwin-arm64.tar.gz
cd ferry-dock-0.1.0-alpha.2-darwin-arm64
./ferry-dock version
./ferry-dock desktop
```

The archive and its bundled documentation remain immutable at `a351555`. Some bundled text predates public availability; use the online [English](usage.md) or [Chinese](usage.zh-CN.md) guide for current status. The original local `dist/0.1.0-alpha.2/SHA256SUMS` still covers all eight archives and is distinct from the release's CLI-only checksum list.

All eight local archives passed package checks, Mac arm64 packaged lifecycle/CLI/safety checks passed, and a same-input rebuild matched all ten local outputs byte-for-byte. Real Safari desktop-light ordinary send/receive and the **Copied** label passed; system paste was not repeated. Dark/phone-size GUI checks remain blocked by an interactive authentication boundary. Go tests and the 12 HTTP / 27 synthetic request / 11 VM / SCRIPT_HTTP checks passed. [Verification](verification.md) preserves these scopes; publication does not expand them.

## Frozen alpha.2 artifact snapshot

The [artifact manifest](benchmarks/2026-10-29-alpha2-artifacts.json) records source, toolchain, targets, sizes, binary/archive hashes and signing metadata. The table inventories the local build; only its Apple Silicon CLI has been published at the link above:

| Local archive | Bytes |
| --- | ---: |
| `ferry-dock-0.1.0-alpha.2-darwin-arm64.tar.gz` | 3,260,347 |
| `ferry-dock-0.1.0-alpha.2-darwin-arm64-app.zip` | 3,290,056 |
| `ferry-dock-0.1.0-alpha.2-darwin-amd64.tar.gz` | 3,529,954 |
| `ferry-dock-0.1.0-alpha.2-darwin-amd64-app.zip` | 3,560,691 |
| `ferry-dock-0.1.0-alpha.2-linux-amd64.tar.gz` | 3,482,298 |
| `ferry-dock-0.1.0-alpha.2-linux-arm64.tar.gz` | 3,155,650 |
| `ferry-dock-0.1.0-alpha.2-windows-amd64.zip` | 3,581,387 |
| `ferry-dock-0.1.0-alpha.2-windows-arm64.zip` | 3,216,317 |

Apple Silicon app ZIP SHA-256: `5c872fa71f6376344397fbec91cf24d7f5e68c75a700a6227ee3ac8fc2c15051`.

The [validation receipt](benchmarks/2026-10-29-alpha2-validation.json) records exit-zero `smoke-package.py --require-all`: all eight archive/binary hashes, actual Mach-O/ELF/PE target headers, metadata, permissions and layouts passed. Mac arm64 native checks passed implicit app flag dispatch without a `desktop` subcommand, a Chinese/space extraction path, private HOME with `PATH=/nonexistent`, readiness, CLI compatibility, reuse, Quit, stale recovery, occupied-port/unknown-service safety and owned cleanup. Invocation used `--no-open --state-dir ... --listen 127.0.0.1:0`; it was not zero-argument Finder/default-cache launch or default-browser auto-opening. Intel Mac, Windows and Linux native execution remain **NOT_RUN**.

The [rebuild receipt](benchmarks/2026-10-29-alpha2-reproducibility.json) records two complete builds from the same clean source/toolchain into different directories: all eight archives, `manifest.json` and `SHA256SUMS` matched byte-for-byte. All ten alpha.1 output hashes remained unchanged. This is not an arbitrary cross-toolchain reproducibility guarantee.

These archives and their bundled snapshot documentation stay fixed at `a351555`; later evidence-document commits do not rebuild them. Manifest `nativeValidation: NOT_RUN` describes generation time, while the separate validation receipt records the subsequent scoped pass. **No new alpha.2 startup timing is claimed.** The alpha.1 measurements below remain historical and must not be applied to alpha.2.

Finder/default-cache discovery, default-browser auto-opening, downloaded Gatekeeper acceptance, physical-phone LAN/QR, actual Codex-host and other-platform native acceptance remain **NOT_RUN**. Dark/phone-size GUI is **BLOCKED** as described above; calculated contrast is not an actual dark render or a full accessibility audit.

## Frozen alpha.1 artifact snapshot

Version `0.1.0-alpha.1` is a **verified historical local preview** frozen at clean source `3d6fca8c843281b9ab2806966fc2661e3cccbe52`. The eight archives passed package checks; a second complete build using the same source/toolchain produced identical bytes for all eight archives, the manifest, and checksums. This fixed snapshot predates the next visual revision. Later documentation or UI changes do not change these files or inherit their results. Alpha.1 has no GitHub Release, public artifact URL, package registry upload, or installer. Do not construct an alpha.1 download link from its version label; only the alpha.2 CLI availability above is public.

The `.app` is Ferry Dock itself. First use is ZIP extraction → open → QR; later use is open → QR. There is no installation wizard, registration, login item, or additional Go/Node platform to install.

The packaging script wrote local outputs under `dist/0.1.0-alpha.1/`, with `manifest.json` and `SHA256SUMS`. These are generated build outputs, not files a public source checkout can assume are present. The committed [artifact manifest](benchmarks/2026-10-29-artifacts.json) records their sizes, target/binary/archive hashes, toolchain, and signing metadata:

| Local archive | Bytes |
| --- | ---: |
| `ferry-dock-0.1.0-alpha.1-darwin-arm64.tar.gz` | 3,245,614 |
| `ferry-dock-0.1.0-alpha.1-darwin-arm64-app.zip` | 3,274,113 |
| `ferry-dock-0.1.0-alpha.1-darwin-amd64.tar.gz` | 3,516,139 |
| `ferry-dock-0.1.0-alpha.1-darwin-amd64-app.zip` | 3,544,548 |
| `ferry-dock-0.1.0-alpha.1-linux-amd64.tar.gz` | 3,469,990 |
| `ferry-dock-0.1.0-alpha.1-linux-arm64.tar.gz` | 3,142,368 |
| `ferry-dock-0.1.0-alpha.1-windows-amd64.zip` | 3,565,167 |
| `ferry-dock-0.1.0-alpha.1-windows-arm64.zip` | 3,200,038 |

Apple Silicon app ZIP SHA-256: `5fcec3986d47765b9a5b0c966c15be9723a58339160e6798a82f36afd6e746c0`. These names identify local files, not download links. The manifest's `nativeValidation: NOT_RUN` fields are generation-time metadata; subsequent scoped validation is recorded in the separate [desktop receipt](benchmarks/2026-10-29-desktop-preview.json), without rewriting the original manifest.

## macOS preview recipients

1. Obtain the local `.app` ZIP supplied for your architecture. Apple Silicon uses `darwin-arm64`; Intel uses `darwin-amd64`. There is no universal-binary claim.
2. Extract `Ferry Dock.app` and open it. It contains the same Go program as the CLI, compiled with desktop as its no-argument default; it is a launcher for a browser interface, not a separate Swift/Electron backend.
3. The launcher starts its own background Go service, waits for private control readiness, opens the system browser, and exits. The computer page displays the phone entry and network status. Phone use requires a reachable trusted LAN.
4. Closing the browser tab leaves the service running. Reopen the app to return to its verified instance. Use **Quit Ferry Dock** on the local computer page to stop it and discard all in-memory sessions and requests.

If several tasks share that service, ending one request is different from quitting the application. Cancel only the request that is no longer needed.

Quit clears the service's in-memory data and normal control-file cleanup is scoped to the instance. Private runtime/cache directories and `startup.log` may remain; no zero-residue uninstall or secure-memory-erasure claim is made.

A local executable check does not establish Finder double-click, system-browser rendering, downloaded-file quarantine, Gatekeeper, or physical-phone acceptance. Those remain separate validation gates.

## Native CLI preview recipients

Extract the archive for the correct OS and architecture. The package root contains `ferry-dock` (`ferry-dock.exe` on Windows), usage documents, licenses, and `skills/ferry-dock/SKILL.md`. No global PATH or Agent configuration is modified.

In a macOS/Linux POSIX shell, from that extracted directory:

```sh
./ferry-dock version
./ferry-dock desktop
```

On Windows, the corresponding command prefix is `.\ferry-dock.exe` in PowerShell. Cross-built archives must not be described as natively accepted on every target platform.

`desktop` needs a configured system browser/opener. A browser-open error can occur after the service is ready; it does not mean nothing started. Use the known private control path or retry opening it. Headless/advanced operators can use foreground `serve` and explicitly configure phone reachability.

Both the app's embedded executable and standalone CLI support `version`, `desktop`, `serve`, and the existing `request create/status/wait/read/cancel` interface. The CLI archive defaults to `serve` when invoked without a subcommand; the app defaults to `desktop`. Use an explicit subcommand when the distinction matters.

`version` returns JSON containing `version`, `commit`, `os`, `arch`, and `defaultMode`. A version string alone is not proof of a published Release or verified publisher identity.

## Service, network, and state

Default desktop LAN mode listens on `0.0.0.0` at a free port. It advertises an eligible private IPv4 on the OS primary interface, or the only eligible private IPv4; point-to-point VPN interfaces are excluded from automatic candidates. Ambiguous/no-LAN cases instead bind loopback and the computer page reports local-only access. Selection does not establish phone reachability through Wi-Fi isolation, other VPN routing, or a firewall.

The private state directory defaults to the OS user cache plus `ferry-dock/runtime`. On macOS the control file is:

```text
~/Library/Caches/ferry-dock/runtime/control.json
```

It contains process authority. Pass its path to `request create --control ...`; do not print, commit, or share its contents. A task's reader handle is a separate capability scoped to one request.

Desktop startup serializes launch attempts and checks the saved computer capability and instance ID before reusing a service. An unknown service is an error, not a target for automatic termination. Advanced operators can supply `desktop --listen ... --public-url ...` or use foreground `serve`. Overrides apply only when starting a new instance; a verified reused instance retains its existing configuration. Changing it requires intentionally ending that service first, which discards all of its sessions/requests. Do not quit a shared instance merely to apply a task's flags. `--no-open` suppresses browser opening for tests and is not evidence of UI acceptance.

Desktop `--listen` accepts only `127.0.0.1:PORT` or `0.0.0.0:PORT`, with a numeric port in 0–65535. Use `serve` for other listener configurations.

HTTP is not encrypted. Data remains in service memory until session/request expiry, cancellation, or shutdown. Normal application shutdown loses that content; control files and handles are not backups.

## Packaging and provenance for contributors

In a matching source checkout, `scripts/package.py` uses Go plus Python's standard library to produce local archives, bundle metadata, the canonical icon, licenses, documentation, and the optional Skill. It builds the existing `cmd/ferry-dock`; the app differs through `DefaultMode=desktop`, not another backend. Contributor/evidence documents may refer to source files that are not part of a prebuilt package.

The script refuses existing output directories. Dirty trees require explicit `--allow-dirty` and are identified in build metadata. `--offline` requires cached Go dependencies; it does not turn a fresh installation into an offline build. Packagers need tools that preview recipients do not.

`manifest.json` records source/dirty state, toolchain, target, binary path/hash, archive hash, and signature metadata. `SHA256SUMS` covers generated archives and the manifest. A checksum checks bytes against the supplied record; it does not replace trusted distribution or publisher signing.

The packaging script performs no Developer ID signing, Apple notarization, upload, registry publication, or security-setting change. The arm64 executable's linker ad-hoc signature is not verified publisher identity, and the app bundle is not Developer ID signed or notarized. [Apple's Gatekeeper signing guidance](https://developer.apple.com/developer-id/) describes publisher signing and notarization as separate checks. Windows previews are publisher-unsigned; [Microsoft's SmartScreen overview](https://learn.microsoft.com/en-us/windows/security/operating-system-security/virus-and-threat-protection/microsoft-defender-smartscreen/) describes downloaded app reputation checks. Local package tests do not establish downloaded-file acceptance; disabling protections is not part of this preview.

## Alpha.1 validation record

The [desktop receipt](benchmarks/2026-10-29-desktop-preview.json) records exit-zero `smoke-package.py --require-all`: all eight archive/binary hashes, target headers, metadata, permissions, and layouts passed. Mac arm64 native checks passed app default-mode flag dispatch, Chinese/space extraction path, private HOME with `PATH=/nonexistent`, version/readiness, CLI compatibility, reuse, Quit, stale recovery, occupied/unknown-service safety, and owned cleanup. The app executable was invoked with `--no-open --state-dir ... --listen 127.0.0.1:0`, without a `desktop` subcommand. This verifies flag dispatch, not zero-argument Finder/default-cache launch.

The [rebuild receipt](benchmarks/2026-10-29-reproducibility.json) records all ten outputs byte-identical across two complete builds from the same clean source and toolchain into different directories. It is not a claim about arbitrary toolchains or build environments.

On Apple M4 Pro / Darwin arm64 with Go 1.27.3, 20 fresh app processes with fresh private state reached authenticated loopback readiness at p50 **82.281 ms**, p95 **85.225 ms**, maximum **98.025 ms**, with no recorded errors; every instance was quit and cleaned. Timing starts before invocation and ends after exit-zero, control read, and authenticated instance validation. OS/filesystem caches were not flushed. The explicit loopback/no-open test excludes LAN discovery, browser rendering, Finder, Gatekeeper, phone interaction and Agent execution; it is not an OS cold-start or cross-platform ranking.

Safari 27.0.1 loopback UI acceptance is separately recorded in [verification](verification.md): real ordinary copy/paste, task submission and later same-handle reading after a wait timeout, received-page locking, a 390×844 layout sample, ended-page states, UI Quit, and fresh-binary same-tab A→B invitation switching. It does not establish Finder/no-argument default-cache launch, default-browser auto-opening, downloaded-file Gatekeeper, physical-phone/LAN/QR, other native platforms, or actual Codex-host acceptance. Those remain **NOT_RUN**. Ended-page tests are not an actual in-flight network-failure test.

The older [loopback performance baseline](performance-baseline.md) measured a specific prior CLI/core binary. It is not a measurement of this app's launch, OS trust prompts, browser opening, or packaged cold-start experience. [Verification](verification.md) and [claims/evidence](claims-evidence.md) keep the scopes separate.
