# Distribution: prebuilt first

The public user path is a portable **macOS Apple Silicon CLI**. Download, extract, and run `desktop`; Git, Go, Node and a separately installed Mac App are not required. The macOS app and other-platform packages remain local previews. Source builds and packaging tools belong to the contributor path.

## Availability

The [v0.1.0-alpha.2 prerelease](https://github.com/Yankj/ferry-dock/releases/tag/v0.1.0-alpha.2) publishes exactly three assets:

| Public asset | Purpose |
| --- | --- |
| [Apple Silicon CLI archive](https://github.com/Yankj/ferry-dock/releases/download/v0.1.0-alpha.2/ferry-dock-0.1.0-alpha.2-darwin-arm64.tar.gz) | macOS arm64 portable command; 3,260,347 bytes. |
| [SHA256SUMS](https://github.com/Yankj/ferry-dock/releases/download/v0.1.0-alpha.2/SHA256SUMS) | Two entries: that CLI archive and the original manifest. |
| [manifest.json](https://github.com/Yankj/ferry-dock/releases/download/v0.1.0-alpha.2/manifest.json) | Original full local-build provenance, including unpublished artifacts. |

The native tag and artifact source are exactly `a351555ccd1615795bc2a6c10dd7e97a633a074f`. Later repository documentation and the npm entry do not replace that frozen native executable. This is an unsigned, unnotarized **test release**, not proof of downloaded-file OS acceptance. The original manifest inventories eight local artifacts, but the release includes only the Mac arm64 CLI. Its release-specific checksum list therefore has no missing App/other-platform entries. Download all three files into the same directory, then run:

```sh
shasum -a 256 -c SHA256SUMS
tar -xzf ferry-dock-0.1.0-alpha.2-darwin-arm64.tar.gz
cd ferry-dock-0.1.0-alpha.2-darwin-arm64
./ferry-dock version
./ferry-dock desktop
```

The archive and its bundled documentation remain immutable at `a351555`. Some bundled text predates public availability; use the online [English](usage.md) or [Chinese](usage.zh-CN.md) guide for current status. The original local `dist/0.1.0-alpha.2/SHA256SUMS` still covers all eight archives and is distinct from the release's CLI-only checksum list.

All eight local archives passed the then-existing archive/metadata checks, Mac arm64 direct packaged-executable lifecycle/CLI checks passed, and a same-input rebuild matched all ten local outputs byte-for-byte. Those checks omitted complete App-bundle signature validation and did not catch the later reproduced defect below. Real Safari desktop-light ordinary send/receive and the **Copied** label passed; system paste was not repeated. Dark/phone-size GUI checks remain blocked by an interactive authentication boundary. Go tests and the 12 HTTP / 27 synthetic request / 11 VM / SCRIPT_HTTP checks passed. [Verification](verification.md) preserves these scopes; publication does not expand them.

## App packaging incident: alpha.1 and alpha.2

The old alpha.1/alpha.2 `.app` previews are **not recommended launchers**. Do
not keep following their bundled “extract and open” instructions or redistribute
them as working App downloads. The archives are retained unchanged as evidence;
the public alpha.2 CLI Release is not an App ZIP and is not being overwritten.

Inspection of the retained alpha.2 Apple Silicon App found:

- ZIP CRC/SHA-256, extraction and executable modes passed.
- `codesign --verify --deep --strict` on the complete App failed with
  `code has no resources but signature indicates they must be present`.
- The same executable passed strict verification outside the App bundle.
- The old ad-hoc signature covered the Go executable without binding the
  completed Info.plist/resource envelope; sealed App resources were absent.
  The retained Intel App was unsigned.

This is a bundle-signing defect, not evidence that changing file permissions or
re-downloading identical ZIP bytes will repair it. The native CLI has no App
resource envelope; that distinction does not make its unsigned downloaded-file
trust or Gatekeeper acceptance a pass.

The alpha.3 repair finishes staging every App resource, ad-hoc signs the
completed bundle, strictly verifies it, archives those sealed bytes, then
extracts and verifies again. The formal private candidate passed these
structural checks; its results are separate from the old archive/runtime
checks. No old tag/Release/archive is overwritten, no new App Release is
published, and no quarantine removal or OS-protection bypass is part of the
repair. See the [incident and correction](packaging-incident.md).

## Alpha.3 private structural fix

Version `0.1.0-alpha.3` was built from clean source
`269af8e11e1b0099c6308d9d82887d31c58a4152` as a **private local candidate**.
The Apple Silicon App archive is
`dist/0.1.0-alpha.3/ferry-dock-0.1.0-alpha.3-darwin-arm64-app.zip`,
**3,336,619 bytes**, SHA-256
`654ab5a7e0b9aa585b2245b4b1b5cb0146e63c031ccb0ea63778562d95b5849f`.
This local path is not a public download link, GitHub Release or new tag.

| Formal alpha.3 check | Actual scope/result |
| --- | --- |
| Complete App signatures | Both Darwin architectures passed strict complete-bundle verification after ZIP round-trip. `_CodeSignature/CodeResources` is included and executable hashes are recorded after signing. |
| System extraction and tamper regression | `ditto`-extracted arm64 baseline passed. Changing Info.plist, changing a resource or deleting the seal each failed verification as expected. The retained alpha.2 contrast still failed with its original missing-resources error. |
| Mac arm64 native runtime | Private HOME, `PATH=/nonexistent`, `--no-open`, private state and loopback lifecycle/CLI/reuse/Quit, stale/occupied/unknown-service safety and owned cleanup passed. No GUI or default-browser launch was inferred. |
| Same-input rebuild | Two complete builds from the same clean source/toolchain produced identical bytes for four Darwin archives, the manifest and checksums: six outputs. |
| Publisher and downloaded-first-launch acceptance | No Developer ID identity or Apple notarization. Gatekeeper, real browser/ChatGPT download first launch, Finder, automatic browser opening, phone and Codex-host acceptance remain unaccepted. |

The archive and its bundled documentation remain fixed at `269af8e`; this
post-build evidence update does not rewrite them. Complete local ad-hoc
verification fixes the reproduced resource-envelope defect, but does **not**
make the candidate a trusted, ready-to-distribute Mac app. See
[verification](verification.md) for the exact receipts and remaining gates.

## Alpha.4 platform matrix

`0.1.0-alpha.4` is the next **unpublished local candidate**, separate from the frozen alpha.2 Release and alpha.3 App repair. There is no alpha.4 tag, Release URL or published npm version. A source checkout does not contain generated `dist/` archives. This matrix does not convert a cross-build or test definition into native acceptance.

| Native target | CLI archive | npm platform package candidate | Public download | Alpha.4 build / native status |
| --- | --- | --- | --- | --- |
| macOS arm64 | `ferry-dock-0.1.0-alpha.4-darwin-arm64.tar.gz` | `ferry-dock-darwin-arm64` | Alpha.2 CLI only, linked above | Built/inspected; scoped native PASS |
| macOS amd64 | `ferry-dock-0.1.0-alpha.4-darwin-amd64.tar.gz` | `ferry-dock-darwin-x64` | None | Built/inspected; native amd64 NOT_RUN |
| Linux amd64 | `ferry-dock-0.1.0-alpha.4-linux-amd64.tar.gz` | `ferry-dock-linux-x64` | None | Built/inspected; native NOT_RUN |
| Linux arm64 | `ferry-dock-0.1.0-alpha.4-linux-arm64.tar.gz` | `ferry-dock-linux-arm64` | None | Built/inspected; native NOT_RUN |
| Windows amd64 | `ferry-dock-0.1.0-alpha.4-windows-amd64.zip` | `ferry-dock-win32-x64` | None | Built/inspected; native NOT_RUN |
| Windows arm64 | `ferry-dock-0.1.0-alpha.4-windows-arm64.zip` | `ferry-dock-win32-arm64` | None | Built/inspected; native NOT_RUN |

The formal local build is clean source `b14aa42133c3a5c00032aa4e2affe873c46a84be`, Go 1.27.3, with `CGO_ENABLED=0`, `GOAMD64=v1` and `GOARM64=v8.0`. The [artifact inventory](benchmarks/2026-10-29-alpha4-artifacts.json) records exact binary/archive sizes, SHA-256, source/toolchain and format fields. Native output is `dist/native/0.1.0-alpha.4/`; npm output is `dist/npm-final/0.1.0-alpha.4/`. These are generated local paths, not public URLs or guaranteed source-checkout files.

| Target | CLI archive bytes | Matching npm platform TGZ bytes |
| --- | ---: | ---: |
| macOS arm64 | 3,341,674 | 3,130,745 |
| macOS amd64 | 3,612,931 | 3,386,155 |
| Linux amd64 | 3,567,264 | 3,336,495 |
| Linux arm64 | 3,240,081 | 3,025,798 |
| Windows amd64 | 3,679,228 | 3,424,567 |
| Windows arm64 | 3,314,564 | 3,070,496 |

The thin npm entry is **13,599 bytes**; an installation needs it plus one matching native package, rather than every platform binary. Optional sealed Mac App ZIPs are 3,349,636 bytes (arm64) and 3,726,908 bytes (amd64), outside the six-CLI matrix. They remain unsigned-publisher test artifacts, not trusted App downloads.

[Native validation](benchmarks/2026-10-29-alpha4-native-validation.json) passed all eight archive/binary/metadata/layout/allowlist checks, both complete Mac App signatures and the scoped Mac arm64 native lifecycle. The latter used Chinese/space paths, private state, loopback and `--no-open`, with no Go/Node in PATH; it exercised ordinary Unicode text, request isolation/timeout/submission/retry/read/cancel/expiry, reuse, Quit, stale/unknown-port safety and owned cleanup. The [App seal regression](benchmarks/2026-10-29-alpha4-app-signature-validation.json) also passed baseline verification and rejected changed Info.plist, changed resources and a missing resource seal. None of this is downloaded-file or GUI acceptance.

[Npm validation](benchmarks/2026-10-29-alpha4-npm-validation.json) passed **181 assertions** on Mac arm64, Node 22.17.1/npm 10.9.2: local dual-TGZ installation/exec offline with scripts disabled, omitted/missing optional dependency diagnostics, version/corruption/missing/executable guards, literal argv/stdio/exits, POSIX signals and actual PTY Ctrl+C canceling only a wait, plus ordinary/request/retry/no-browser lifecycle and cleanup. Six-platform dispatch/spawn guards were VM checks; other-platform npm execution remains NOT_RUN.

The [actual alpha.2 → alpha.4 upgrade test](benchmarks/2026-10-29-alpha4-upgrade-validation.json) passed 15 checks: alpha.4 refused a running legacy instance without changing its state or stopping it, a separate private alpha.4 instance worked, and both owned test services quit cleanly. Same-input second builds matched **all ten native outputs** and **all nine npm outputs** byte-for-byte: [native comparison](benchmarks/2026-10-29-alpha4-native-reproducibility.json), [npm comparison](benchmarks/2026-10-29-alpha4-npm-reproducibility.json). This is scoped to the recorded clean source/toolchain, not arbitrary reproducibility.

The artifacts and bundled documentation remain fixed at `b14aa42`; this post-build attestation does not rebuild them. Manifest `nativeValidation: NOT_RUN` describes generation time; subsequent scoped native results are in the separate receipts. All five other OS/CPU native targets, minimum upstream OS versions, OS-default state directory, Windows ACL/interactive console Ctrl+C, default-browser/OS download trust, physical-phone LAN/QR and actual Codex-host acceptance remain uncompleted as applicable. The 13 configured CI jobs have **not run for this batch**; a workflow definition is not remote test evidence.

Go `amd64` is Node/npm `x64`; Go `windows` is Node/npm `win32`. The native archive is chosen for the intended OS/CPU. The npm entry selects for the **running Node process**; hardware alone does not determine a Rosetta or emulation process architecture. A successful selection is not an emulation/runtime acceptance result.

The common native CLI layout is one outer `ferry-dock-VERSION-OS-ARCH/` directory containing the executable (`ferry-dock.exe` on Windows), build metadata, usage documents, licenses and `skills/ferry-dock/SKILL.md`. A native package requires no Git, Go, Node or global installation at runtime. The CLI's no-argument default remains foreground `serve`; explicitly use `desktop` for the background service/browser path.

The alpha.4 manifest/checksum record is generated alongside the new archives and identifies its source, toolchain, CGO setting, platform, bytes and hashes. Never apply an alpha.2 or alpha.3 checksum to alpha.4. Native and npm checksums describe their separate archive sets. Only files in the matching checksum list should be expected during a full-list check.

## OS runtime and trust boundaries

These are packaging constraints and upstream requirements, **not a tested product minimum-OS promise**:

- Go 1.27 upstream lists macOS 13+, Windows 10+/Server 2016+, and a Linux kernel floor of 3.2, with architecture caveats. See [Go minimum requirements](https://go.dev/wiki/MinimumRequirements). This candidate has not been tested on those oldest versions. Its exact compiler and platform evidence belong to the manifest and receipts, not the version label alone.
- Linux CLI builds use `CGO_ENABLED=0`; ELF inspection must confirm no interpreter/dynamic dependencies. This avoids a glibc-versus-musl binary dependency, but does not establish every distro/kernel, resolver configuration or browser integration. Native runtime results remain separate.
- Windows archives contain a console `.exe`, not a GUI app or installer. Quoted PowerShell paths and `.exe`/npm `.cmd` handling are distinct from POSIX syntax. Private state/handles must live in a current-user directory with appropriate inherited ACLs; POSIX mode-bit checks on a Mac do not establish Windows ACL protection.
- Windows background creation uses a detached new process group; a caller's Windows Job Object may still govern child lifetime. Console Ctrl+C delivery and Node's signal emulation require native Windows evidence. An `os.kill`/VM test elsewhere cannot establish that behavior.
- `desktop` needs an available system browser/opener; Linux headless environments can use foreground `serve` and an explicit phone-reachable origin. Default-browser/Finder/shell integration and real-phone LAN/QR acceptance remain separate.
- macOS candidates have no Developer ID signing or Apple notarization. Optional App bundles retain complete-bundle ad-hoc sealing, which fixes the reproduced resource defect without establishing publisher trust. Windows binaries are publisher-unsigned and may encounter SmartScreen/reputation checks. There is no quarantine removal, protection bypass or certificate enrollment in this packaging work.

## npm packaging preview: local only

The locally built alpha.4 candidate has one thin entry, `ferry-dock@0.1.0-alpha.4`, and six native platform candidates from the matrix, each pinned as an **exact same-version optional dependency**. It reuses the matching Go CLI, not another backend. Names are not reserved or published, and no public registry `npx` command is available.

The entry requires a supported Node.js 22+ runtime. It resolves only the platform package for its Node process, verifies matching package/core version, binary size and SHA-256, then spawns the executable without a shell. No arguments supply `desktop`; explicit arguments are preserved. Platform packages carry the binaries directly. There are no install lifecycle scripts, custom postinstall downloads or startup fetches. A future npm registry install would still download the npm packages normally; no network-free installation from a registry is promised.

For a separately supplied, verified **local** preview, install both the entry TGZ and your platform TGZ. Example for arm64 Mac:

```sh
npm install --offline --ignore-scripts --no-audit --no-fund --package-lock=false --prefix ./ferry-dock-node /absolute/path/ferry-dock-darwin-arm64-0.1.0-alpha.4.tgz /absolute/path/ferry-dock-0.1.0-alpha.4.tgz
cd ferry-dock-node
npm exec --offline --yes=false -- ferry-dock version
npm exec --offline --yes=false -- ferry-dock
```

Both-language guides list all platform filenames and PowerShell syntax: [English](usage.md#node-users-local-package-only), [中文](usage.zh-CN.md#node-用户仅本地包). A missing native optional dependency is an error, not permission to fetch a replacement. Do not use `--omit=optional` for a normal installation. Unknown OS/architecture, missing package, wrong package version, invalid metadata or altered binary must fail before launch.

Locations under the chosen install prefix:

- entry: `node_modules/.bin/ferry-dock` (npm creates platform-specific command shims);
- Go core: `node_modules/ferry-dock-PLATFORM-ARCH/native/ferry-dock` or `ferry-dock.exe`;
- manual Skill: `node_modules/ferry-dock/skills/ferry-dock/SKILL.md`;
- contract: `node_modules/ferry-dock/docs/contracts/request-v1.md`.

The entry carries no global Skill/MCP/Agent configuration, PATH change, login item or OS service. Runtime control/handle files belong outside the package. Installing new package files does not replace an already running service. Alpha.4 desktop verifies authenticated instance identity plus version/commit; a legacy or mismatched service is preserved and startup fails with deliberate Quit/separate-state guidance. Finish shared work before Quit; all in-memory sessions/requests are discarded. Matching metadata is not a binary-hash attestation, especially for source builds labeled `dev`/`unknown`.

Maintainers can prepare local packages from a matching source checkout, verified alpha.4 native `dist` directory, Python and existing Node/npm:

```sh
python3 scripts/package-npm.py \
  --dist /absolute/path/native-dist/0.1.0-alpha.4 \
  --node /absolute/path/node \
  --npm-cli /absolute/path/npm-cli.js \
  --out dist/npm
```

The builder is a local packaging operation, not login, publication or a release upload. Test installation with scripts disabled and empty configs/cache; do not substitute a cached registry package for the supplied TGZ. The packaging/validation receipts must report exact files, sizes/hashes and the OS/CPU that actually executed. A configured six-runner CI matrix is **NOT_RUN** until a matching commit has run remotely.

### Historical alpha.2 npm evidence

The previous single-Mac TGZ remains fixed at `dist/npm-verified/0.1.0-alpha.2/ferry-dock-0.1.0-alpha.2.tgz`, 3,139,752 bytes, SHA-256 `5a50504b7d726fa1fa80a31d9aae776db6e57c1b02a8daa635d1dfd6fedfc680`. This is an existing local artifact, not a guaranteed checkout file or public download. It bundles the exact alpha.2/a351555 native binary. Its [79-check receipt](benchmarks/2026-10-29-npm-validation.json) and two byte-identical packs establish scoped Mac arm64/Node 22.17.1/npm 10.9.2 offline install, argv/stdio/exits, signal/PTY wait interruption and no-browser lifecycle results for that version only. Its old live-service advisory did not check backend version. These results do not validate alpha.4 or all six platforms.

Homebrew, MCP and browser extensions remain outside this work. The published native Mac download above remains available while npm ownership/authentication and release approval are unresolved.

## Go install from the fixed tag

For users who already have Go 1.26+ and network access, the fixed module command is:

```sh
GOBIN="$(pwd)/ferry-dock-bin" go install github.com/Yankj/ferry-dock/cmd/ferry-dock@v0.1.0-alpha.2
./ferry-dock-bin/ferry-dock desktop
```

This selects a user-controlled local destination without modifying global PATH,
and compiles source instead of downloading the prebuilt release binary. The
installed command defaults to foreground `serve`, so include `desktop` to use
the browser launcher. Verify source-module identity with:

```sh
go version -m ./ferry-dock-bin/ferry-dock
```

The expected module line identifies `github.com/Yankj/ferry-dock`
`v0.1.0-alpha.2`, checksum
`h1:25n36E7ullJ7Vci/EtyA/AhTXmApSphEeupn1/aanfo=`. Its tag points to
`a351555ccd1615795bc2a6c10dd7e97a633a074f`. This source tag predates release
linker metadata: application `version` reports `dev`, `unknown`, `darwin`,
`arm64`, and default mode `serve` in the tested Mac build. It must not be
described as returning the prebuilt binary's release version/commit fields.

[A fresh install](benchmarks/2026-10-29-go-install-validation.json) using Go 1.27.3 on Mac arm64, public Go proxy/checksum service
and new module/build caches passed 31 local assertions: command help, private
loopback desktop readiness/reuse, ordinary exact-text transfer, scoped request
pending/submission/read/cancel, and owned-service Quit/cleanup. No browser,
physical phone, default cache, Codex host, Go 1.26 native or other-platform
acceptance was inferred. A separate `CGO_ENABLED=0 CC=/nonexistent` source
install passed build/version/desktop-help checks; the runtime flow was not
repeated for that variant. Offline installation is not promised: a cached
`GOPROXY=off` retry failed its module deprecation lookup. Standard Go
toolchain/compiler requirements and network policy still apply.

`go install` installs only the executable. Obtain the optional repository Skill
separately and pass its actual local path to the Agent; this route does not
install or auto-discover a Skill.

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

The historical `.app` packaged Ferry Dock itself rather than another desktop platform. Its former ZIP → open → QR instructions are withdrawn because of the complete-bundle signature defect. Archive and direct-executable checks below are retained evidence, not an App first-launch recommendation.

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

Do not use the historical alpha.1/alpha.2 App ZIP as a launcher. Its complete
bundle signature failed the newly added check, even though the old archive and
internal-executable runtime checks passed. Keep the old artifacts only for
reproducibility and incident evidence; do not try permission/quarantine changes
as a repair.

The alpha.3 App is a private repair candidate, not a published release. Its
formal structural signature, archive round-trip, tamper and scoped Mac arm64
no-browser runtime checks passed for the exact bytes above. Complete local
ad-hoc verification still does not establish Developer ID/notarization or a
trusted browser download's first launch. Use the public native CLI route for
the current published package, with its separate unsigned-executable limitations.

The intended future App remains a small container for the same Go launcher,
not a new backend, registration flow or installer. That architectural goal is
not an instruction to open one of the defective old bundles.

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

The packaging script performs no Developer ID signing, Apple notarization, upload, registry publication, or security-setting change. The corrected alpha.3 App is ad-hoc signed as a complete bundle; the frozen alpha.2 CLI's linker ad-hoc signature is separate. Neither supplies verified publisher identity or Apple notarization. [Apple's Gatekeeper signing guidance](https://developer.apple.com/developer-id/) describes publisher signing and notarization as separate checks. Windows previews are publisher-unsigned; [Microsoft's SmartScreen overview](https://learn.microsoft.com/en-us/windows/security/operating-system-security/virus-and-threat-protection/microsoft-defender-smartscreen/) describes downloaded app reputation checks. Local package tests do not establish downloaded-file acceptance; disabling protections is not part of this preview.

## Alpha.1 validation record

The [desktop receipt](benchmarks/2026-10-29-desktop-preview.json) records exit-zero `smoke-package.py --require-all`: all eight archive/binary hashes, target headers, metadata, permissions, and layouts passed. Mac arm64 native checks passed app default-mode flag dispatch, Chinese/space extraction path, private HOME with `PATH=/nonexistent`, version/readiness, CLI compatibility, reuse, Quit, stale recovery, occupied/unknown-service safety, and owned cleanup. The app executable was invoked with `--no-open --state-dir ... --listen 127.0.0.1:0`, without a `desktop` subcommand. This verifies flag dispatch, not complete App-bundle signature integrity or zero-argument Finder/default-cache launch. The later reproduced signature defect withdraws the historical App launch recommendation.

The [rebuild receipt](benchmarks/2026-10-29-reproducibility.json) records all ten outputs byte-identical across two complete builds from the same clean source and toolchain into different directories. It is not a claim about arbitrary toolchains or build environments.

On Apple M4 Pro / Darwin arm64 with Go 1.27.3, 20 fresh app processes with fresh private state reached authenticated loopback readiness at p50 **82.281 ms**, p95 **85.225 ms**, maximum **98.025 ms**, with no recorded errors; every instance was quit and cleaned. Timing starts before invocation and ends after exit-zero, control read, and authenticated instance validation. OS/filesystem caches were not flushed. The explicit loopback/no-open test excludes LAN discovery, browser rendering, Finder, Gatekeeper, phone interaction and Agent execution; it is not an OS cold-start or cross-platform ranking.

Safari 27.0.1 loopback UI acceptance is separately recorded in [verification](verification.md): real ordinary copy/paste, task submission and later same-handle reading after a wait timeout, received-page locking, a 390×844 layout sample, ended-page states, UI Quit, and fresh-binary same-tab A→B invitation switching. It does not establish Finder/no-argument default-cache launch, default-browser auto-opening, downloaded-file Gatekeeper, physical-phone/LAN/QR, other native platforms, or actual Codex-host acceptance. Those remain **NOT_RUN**. Ended-page tests are not an actual in-flight network-failure test.

The older [loopback performance baseline](performance-baseline.md) measured a specific prior CLI/core binary. It is not a measurement of this app's launch, OS trust prompts, browser opening, or packaged cold-start experience. [Verification](verification.md) and [claims/evidence](claims-evidence.md) keep the scopes separate.
