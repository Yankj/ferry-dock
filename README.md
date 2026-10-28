# Ferry Dock

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="brand/banner-dark.svg">
  <img src="brand/banner.svg" width="960" alt="Ferry Dock / 渡口 — From your phone. To your computer.">
</picture>

**A small local bridge from your phone to your computer.**

[简体中文](README.zh-CN.md) · [Product FAQ](PRFAQ.md) · [Brand assets](brand/README.md)

Bring text from a phone to a temporary computer inbox. When a task needs that text, a collection request can identify the question and return the answer to the request that asked for it. The phone uses a browser; ordinary transfer needs no AI component.

**Alpha:** temporary text sessions, one-response collection requests, a JSON CLI, and a repository-local Codex Skill are implemented. Files, npm/npx, MCP, and a browser plugin are not available. Browser, real-phone, and actual Codex-host acceptance remain separate from automated checks.

## Comments on your phone, proposal on your computer

You are drafting a proposal on the computer, but the client's comments are in a phone chat. Open a temporary inbox, scan, paste, send, and copy. No mobile app or account is required.

For an Agent-assisted task, name the proposal in a collection request and show its QR. The phone page asks for those comments. A private reader handle gets only that request's result, so another task's feedback does not become “the latest message” to guess from. The original task decides how to revise the proposal.

The request loop is a transfer tool, not an Agent host. A timed-out wait can be queried again; it cannot wake a paused host by itself.

## Build and run

The computer needs Go 1.26 or newer to build from source. The phone needs no installation. There is no published binary release or package installer yet. The shell examples below use macOS/Linux syntax.

```sh
git clone https://github.com/Yankj/ferry-dock.git
cd ferry-dock
go build -o bin/ferry-dock ./cmd/ferry-dock
./bin/ferry-dock serve
```

On Windows, build with `go build -o bin/ferry-dock.exe ./cmd/ferry-dock` and invoke `.\bin\ferry-dock.exe` in PowerShell. The request flags are the same; the private-directory example below uses a POSIX shell. Cross-compilation is recorded separately from native Windows acceptance.

Default binding is `127.0.0.1:8787`, which is local to the computer. To receive from a physical phone, restart with a reachable LAN address:

```sh
./bin/ferry-dock serve --listen 0.0.0.0:8787 --public-url http://192.168.1.20:8787
```

Replace `192.168.1.20` with the computer's actual LAN address. A QR does not bypass guest Wi-Fi isolation, a VPN, routing, or a firewall. The no-subcommand launch remains compatible.

Building or obtaining dependencies may need Internet access. Once built, the executable embeds its pages, QR generation, and brand assets; ordinary operation uses the local service without a cloud account or model call.

## Ordinary transfer: scan, send, copy

1. Open the private **computer URL** printed in the terminal. A session starts automatically and displays its QR.
2. Scan with your phone, paste text, and tap **Send to computer**.
3. Click **Copy** on the computer.

Keep sending from the same phone page without rescanning. **End session** clears the retained session; **New session** creates another. Sessions expire after 15 minutes by default. Restarting or stopping the service loses its in-memory text.

Ordinary text is limited to 64 KiB per message, 1 MiB and 128 messages per session, with at most 16 active sessions. Accepted text preserves whitespace and Unicode. A service receipt does not mean a person has read or copied it.

## Task collection: request, wait, read

This optional path uses the same Go service and a private local handle, not a model API. The CLI flags below match its help output; use your actual LAN origin and private local paths.

Start a service with an explicit private control file. If the earlier quickstart service is still running without one, stop it first; its temporary sessions are then cleared. This POSIX-shell example prints the private runtime directory so that a second terminal can use it:

```sh
umask 077
runtime_dir="$(mktemp -d)"
printf 'Private runtime directory: %s\n' "$runtime_dir"
./bin/ferry-dock serve --listen 0.0.0.0:8787 \
  --public-url http://192.168.1.20:8787 \
  --control-file "$runtime_dir/control.json"
```

In another terminal, set `runtime_dir` to the printed directory. The handle and its default PNG path must not already exist. On Windows, choose a directory private to your user and use its paths with the same CLI flags.

```sh
runtime_dir="/path/printed/by/the/first/terminal"
./bin/ferry-dock request create \
  --control "$runtime_dir/control.json" \
  --task-id proposal-launch \
  --prompt "Launch proposal: paste the changes from your phone chat." \
  --handle "$runtime_dir/proposal.json" --ttl 15m --max-bytes 16384
```

Show the generated QR PNG or returned private phone URL to the user. Creation output does not include the process computer token; the control file and handle still contain capabilities and must stay private. Do not print their contents, commit them, or put them under a public document root.

After the phone submits, wait and read through the same handle. Running these before submission can correctly return `pending` and no input; keep the handle and try again later.

```sh
./bin/ferry-dock request wait --handle "$runtime_dir/proposal.json" --timeout 10s
./bin/ferry-dock request read --handle "$runtime_dir/proposal.json"
```

A request accepts one response, at most 16 KiB by default. `--ttl` is a duration such as `15m` or `900s`, restricted to whole seconds; omitting it inherits service retention. Its server-generated request ID identifies the collection; `taskId` is only a correlation label. Each request has independent sender and reader capabilities. A label never grants access.

Use `request status --handle ...` to check state and `request cancel --handle ...` to end collection explicitly. A wait is bounded to ten seconds; timeout returns pending without canceling. Ctrl+C during `request wait` ends that wait only. Ctrl+C in the service terminal stops the service and loses its in-memory data.

Reads return a stable `input.id` and `trust: "untrusted_user_input"`. The consumer must validate the request/task identity and avoid repeating a completed business action for the same input ID. If an edit's outcome is uncertain after interruption, inspect the current artifact before retrying. The server does not guarantee exactly-once Agent execution.

To use the Codex workflow, explicitly reference [skills/ferry-dock/SKILL.md](skills/ferry-dock/SKILL.md) in the repository. This is a manual local artifact, not a globally installed skill or an automatic Codex configuration change. It explains bounded waiting, task checks, and treating phone text as feedback rather than executable instructions.

## One local service, explicit trust

The core is Go with embedded HTML, CSS, and JavaScript. Ordinary sessions and collection requests share the HTTP boundary and temporary in-memory service; the CLI adapts the request API rather than maintaining a second store. See [architecture](docs/architecture.md), [request v1](docs/contracts/request-v1.md), and [the runtime decision](docs/decisions/0001-runtime.md).

The computer link and control file have process management authority. An ordinary phone QR has session submission authority; a request QR and reader handle are each scoped to that request. Share the phone invitation only with the intended sender.

**Local does not mean encrypted.** This slice uses HTTP on a trusted LAN, without TLS provisioning or end-to-end encryption. An observer of that network may obtain content and capabilities. URL fragments reduce exposure in request paths; they are not encryption. Do not expose the alpha directly to the Internet. See [SECURITY.md](SECURITY.md).

Local operation and no model call describe the Ferry Dock service. If you pass a CLI result to an Agent through the optional Skill, that host may send it to a cloud model or retain it under its own policies. Ferry Dock does not make the entire Agent workflow local.

## Limits and recovery

| Situation | What to do |
| --- | --- |
| Phone cannot open the page | Check the advertised LAN address and actual device reachability. |
| Paste or Copy is unavailable | Use manual system paste or select the visible text to copy. Clipboard permissions vary by browser. |
| A wait returns pending | Keep the request handle and query again; timeout did not cancel collection. |
| Create or cancel returns `outcome_unknown` | The mutation may have happened. Query with the same saved handle; if creation saved no handle, report uncertainty and let the unknown request expire rather than blindly creating again. |
| A request is canceled or expired | Its submitted text is removed; create a new request if still needed. |
| The service restarted | Old in-memory content is gone. Create a new session or request; a local handle is not a backup. |

No file, photo, audio, screen-control, background clipboard sync, durable history, cloud relay, npm/npx launcher, MCP adapter, or browser plugin is included. Those entry points are not a scheduled expansion plan; [product shape](docs/product-shape.md) records the conditions for reconsidering one.

## Evidence and contributions

Automated checks cover ordinary HTTP behavior and request isolation, cancellation/expiry, retry deduplication, stable reads, and bounded waits. A compiled-program synthetic proposal scenario exercises the CLI and a consumer that avoids repeating an already completed edit. Synthetic HTTP/CLI execution does not establish browser, Android/iOS, or actual Codex-host acceptance; those remain **NOT_RUN** until their specific evidence exists.

```sh
go fmt ./...
go vet ./...
go test ./...
go test -race ./...
```

See [verification](docs/verification.md), [claims and evidence](docs/claims-evidence.md), and [CONTRIBUTING.md](CONTRIBUTING.md). [Performance budgets](docs/performance.md) are targets. The first [macOS arm64 / Go 1.27.3 loopback baseline](docs/performance-baseline.md) and [raw samples](docs/benchmarks/2026-10-28-macos-arm64.json) record startup, memory, and API observations, including the slowest startup and post-close RSS. They do not measure phone tap-to-display or Agent execution speed.

The local launch/QR experience considered [DropLocal](https://github.com/shiyuanhai/droplocal/tree/16c9fe05e048b2c5ebbe2e75ccb4619620bd9653), and text fidelity/incremental retrieval considered [Ferry](https://github.com/max1874/ferry/tree/5b7882947ef34ae422004ae81ccc2da509693fe1). Ferry Dock's application is a new implementation. Dependency attribution is in [third-party notices](THIRD_PARTY_NOTICES.md).

[MIT](LICENSE).
