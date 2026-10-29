# Distribution: prebuilt first

Ferry Dock's user path is a prebuilt macOS app or native CLI archive. Git, Go, and Node are not runtime installation requirements. Source builds and packaging tools belong to the contributor path.

## Availability

Version `0.1.0-alpha.1` is a **local packaging preview**. Package generation and validation are in progress for this revision. No GitHub Release, public artifact URL, package registry upload, or installer has been published by this work. Do not construct a download link from the version label.

The `.app` is Ferry Dock itself. First use is ZIP extraction → open → QR; later use is open → QR. There is no installation wizard, registration, login item, or additional Go/Node platform to install.

The packaging script writes local outputs under `dist/0.1.0-alpha.1/` by default, with `manifest.json` and `SHA256SUMS`. These are generated build outputs, not files a public source checkout can assume are present. Final artifact names and observed validation will be recorded here after the local package checks finish.

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

The packaging script performs no Developer ID signing, Apple notarization, upload, registry publication, or security-setting change. Any Go-linker ad-hoc signature is not a verified publisher identity. Do not claim that a locally generated app will pass downloaded-file Gatekeeper checks, or instruct users to disable protections to run this preview.

## Validation record

Final archive/native package validation is pending. Record hashes, embedded version/commit/architecture, native executable checks, desktop start/reopen/quit, CLI collection through the same control file, and cleanup against the actual final artifacts before marking them passed.

Safari 27.0.1 loopback UI acceptance is separately recorded in [verification](verification.md): real ordinary copy/paste, task submission and later same-handle reading after a wait timeout, received-page locking, a 390×844 layout sample, ended-page states, UI Quit, and fresh-binary same-tab A→B invitation switching. It does not establish Finder/no-argument default-cache launch, default-browser auto-opening, downloaded-file Gatekeeper, physical-phone/LAN/QR, other native platforms, or actual Codex-host acceptance. Those remain **NOT_RUN**. Ended-page tests are not an actual in-flight network-failure test.

The older [loopback performance baseline](performance-baseline.md) measured a specific prior CLI/core binary. It is not a measurement of this app's launch, OS trust prompts, browser opening, or packaged cold-start experience. [Verification](verification.md) and [claims/evidence](claims-evidence.md) keep the scopes separate.
