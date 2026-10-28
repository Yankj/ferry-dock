# Security

Tapbeam is an early alpha for a trusted local network. Only the current `main` branch is maintained; there is no stable release or guaranteed response time yet.

## Deployment boundary

- Default binding is loopback. LAN access is an explicit operator choice.
- HTTP does not provide transport confidentiality. A network observer can obtain content or bearer capabilities. Do not expose the alpha directly to the Internet.
- Treat the computer link as a management credential and phone links as session submission credentials. QR codes contain capabilities, not just an address.
- Session data is temporary and in memory. Closing a session, expiry, or stopping the process removes availability; this is not a secure-memory-erasure guarantee.
- Browser restrictions still apply to clipboard access. The project does not support hidden capture or background clipboard monitoring.

See [the architecture threat model](docs/architecture.md) for the enforced boundaries and known limits.

## Reporting a vulnerability

Do not post working exploits, capability links, or private content in a public issue.

If GitHub offers **Report a vulnerability** on [this repository's Security page](https://github.com/Yankj/tapbeam/security), use that private channel. Private reporting availability is a repository setting and is not guaranteed by this document. Otherwise, open an issue containing only “Requesting a private security reporting channel” and a broad component name. A maintainer can then arrange a private channel before you share sensitive details.

Once a private channel is available, include the affected commit, prerequisites, minimal reproduction, expected impact, and any suggested mitigation. Use synthetic content and redact credentials.
