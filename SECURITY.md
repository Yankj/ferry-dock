# Security

Ferry Dock is an early alpha for a trusted local network. Only the current `main` branch is maintained; there is no stable release or guaranteed response time yet.

## Deployment boundary

- Foreground `serve` defaults to loopback and requires explicit LAN configuration. Desktop selects an available port; when it identifies a private IPv4 address, it listens on `0.0.0.0` and advertises that address. The listener accepts connections on every IPv4 interface, not only the advertised one. Ambiguous/unavailable address selection falls back to loopback with a local-only notice. Use a trusted network; no firewall or network setting is changed.
- Desktop quit requires the owner capability, a loopback remote address and the configured local Host. A phone sender capability cannot quit the service. The private desktop control file can create task requests and must not be shared.
- HTTP does not provide transport confidentiality. A network observer can obtain content or bearer capabilities. Do not expose the alpha directly to the Internet.
- Treat the computer link as a management credential and phone links as session submission credentials. QR codes contain capabilities, not just an address.
- Session data is temporary and in memory. Closing a session, expiry, or stopping the process removes availability; this is not a secure-memory-erasure guarantee.
- Browser restrictions still apply to clipboard access. The project does not support hidden capture or background clipboard monitoring.

See [the architecture threat model](docs/architecture.md) for the enforced boundaries and known limits.

## Reporting a vulnerability

Do not post working exploits, capability links, or private content in a public issue.

If GitHub offers **Report a vulnerability** on [this repository's Security page](https://github.com/Yankj/ferry-dock/security), use that private channel. Private reporting availability is a repository setting and is not guaranteed by this document. Otherwise, open an issue containing only “Requesting a private security reporting channel” and a broad component name. A maintainer can then arrange a private channel before you share sensitive details.

Once a private channel is available, include the affected commit, prerequisites, minimal reproduction, expected impact, and any suggested mitigation. Use synthetic content and redact credentials.
