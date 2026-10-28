# Tapbeam

**Send from your phone. Continue on your computer.**

[简体中文](README.zh-CN.md)

Tapbeam is a small, local transfer service. Open it on your computer, scan a QR code on your phone, and send text into a temporary inbox. No phone app, cloud account, or AI model is required.

**Status: early alpha.** The first slice covers phone-to-computer plain text. File transfer and task-bound Agent inputs are planned; there is no published binary release or npm package yet.

## Try it

Build prerequisites: Go 1.26 or newer. The built program embeds its web interface and needs no Node runtime or database.

```sh
git clone https://github.com/Yankj/tapbeam.git
cd tapbeam
go run ./cmd/tapbeam
```

The default listener is `127.0.0.1:8787`, for use on this computer. To receive from a phone on a trusted local network, supply a reachable address:

```sh
go run ./cmd/tapbeam -listen 0.0.0.0:8787 -public-url http://192.168.1.20:8787
```

Replace `192.168.1.20` with your computer's LAN address. Both devices must be able to reach that address; guest Wi-Fi isolation, a VPN, or a firewall can prevent access.

1. Open the **computer URL** printed in the terminal. A session starts automatically and displays its QR code.
2. Scan the QR code with your phone, paste text, and tap **Send to computer**.
3. Click **Copy** on the computer.

Keep the computer URL private: it grants inbox management access. Share only the phone link or its QR code. Click **End session** when finished, or let it expire after 15 minutes; use **New session** to start again. Restarting the process clears its in-memory data.

To build an executable:

```sh
go build -o bin/tapbeam ./cmd/tapbeam
./bin/tapbeam -help
```

## What the alpha does

- Temporary text sessions with separate computer and phone capabilities.
- QR entry, exact text preservation, incremental inbox retrieval, and copy feedback.
- Session closure and expiry, a 64 KiB text limit, a 1 MiB inbox limit, and duplicate submission detection.
- All application assets served by the local process. No external QR service, analytics, or model call.

The phone can submit to its session; it cannot read the inbox or manage sessions. Clipboard access depends on the browser and its permissions. Manual paste remains available; the page does not monitor the clipboard in the background.

## Where this goes

The ordinary transfer flow comes first. Optional CLI/Skill and MCP adapters can later let an Agent request information, produce a phone QR, and retrieve the result in the same task. They will use the same session core. File and image transfer, richer input requests, and distribution packages are future work, not alpha features.

The core is Go with embedded HTML, CSS, and JavaScript. [The runtime decision](docs/decisions/0001-runtime.md) compares Node, Go, and Rust. [Performance budgets](docs/performance.md) define what to measure; they are targets, not benchmark claims.

## Trust boundary

This alpha uses HTTP on a trusted LAN. Traffic and bearer capabilities are not protected from a network observer. It is not an Internet-facing service. URL fragments keep keys out of ordinary request paths, but do not make shared links safe to disclose. See [architecture and threat model](docs/architecture.md) and [security reporting](SECURITY.md).

## Contribute

```sh
go fmt ./...
go vet ./...
go test ./...
go test -race ./...
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for review expectations and the distinction between automated checks and real phone acceptance. [Product scope](docs/product.md) records the shortest supported flow.

## Design references and license

[DropLocal](https://github.com/shiyuanhai/droplocal/tree/16c9fe05e048b2c5ebbe2e75ccb4619620bd9653) informed the local launch and QR experience; [Ferry](https://github.com/max1874/ferry/tree/5b7882947ef34ae422004ae81ccc2da509693fe1) informed text fidelity and incremental retrieval. Tapbeam's core is a new implementation, not a fork of either project. See [third-party notices](THIRD_PARTY_NOTICES.md) for dependency attribution and licenses.

[MIT](LICENSE).
