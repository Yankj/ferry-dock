# Ferry Dock / 渡口 — npm packaging preview

A thin npm entry for the same Go text-transfer core. This packaging preview
supports **macOS Apple Silicon with arm64 Node.js 22 or newer**. Use a supported
Node LTS. It does not require Go or another Mac app. Other platforms, including
an x64 Node process under Rosetta, are outside this package's platform allowlist.

The package name is a candidate until its npm owner and publication are
confirmed. Do not treat a proposed `npx` command as a published package.

After installing a verified local package, run `ferry-dock` to start/reopen the
desktop flow. No arguments means `desktop` for this npm entry; explicit
`version`, `desktop`, `serve` and `request ...` arguments go to the same native
CLI unchanged. Its stdout remains the native command's output, including JSON.

The native binary is carried inside the package and checked against `core.json`.
No `postinstall`, runtime download, compiler or network fetch is used to obtain
it. Registry download/installation itself may need network access; an already
installed package can run without a registry connection. The SHA check detects
an inconsistent installed binary; it is not publisher signing or encryption.

The Go launcher owns the background service. Closing the browser does not stop
it. **Quit Ferry Dock** on the computer page stops it and clears all in-memory
sessions and requests. Reopening may reuse a verified service started by an
older package; this alpha does not attest its version or silently replace it.
Do not quit a service shared by other tasks merely to upgrade the npm package.

MacOS may warn or block this unsigned/unnotarized executable. No OS protection
bypass is provided. HTTP on the trusted LAN is not encrypted; phone invitations,
reader handles and control files are private capabilities. Physical-phone QR,
mobile permissions and actual Codex-host acceptance are separate checks.

Manual Skill: `skills/ferry-dock/SKILL.md`. Its relative request contract is
included at `docs/contracts/request-v1.md`. The package does not install a Skill
globally or modify Agent configuration. With the package root known, an Agent
can use `native/ferry-dock` directly for the pinned core interface, or the npm
entry for its default-desktop behavior. Keep process state and request handles
in private runtime storage, not inside the installed package.

Core and current instructions: https://github.com/Yankj/ferry-dock

MIT; dependency attribution is included in `THIRD_PARTY_NOTICES.md`.
