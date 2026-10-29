# macOS App packaging defect

## Observed failure

A supplied screenshot shows the extracted **Ferry Dock.app** and the macOS
message “Ferry Dock”已损坏，无法打开。你应该将它移到废纸篓。
The archive had expanded; this is an application-open failure, not evidence that
the ZIP container itself was unreadable. No screenshot or Library identifier is
included in this repository.

The original frozen alpha.2 artifacts were checked without changing them or the
user's downloaded copy. Both Mac App ZIPs passed CRC, archive/executable SHA,
Mach-O architecture, Info.plist, executable-mode and system `ditto` extraction
checks. The arm64 application's total file size was 7,870,933 bytes, consistent
with the screenshot's 7.9 MB display; the user's downloaded-copy hash was not
available, so that size is supporting evidence rather than file identity proof.

| Original artifact check | Actual result |
| --- | --- |
| arm64 complete App, `codesign --verify --deep --strict --verbose=4` | Exit 1: `code has no resources but signature indicates they must be present`. |
| Same arm64 executable bytes copied outside the App | Exit 0: valid on disk; satisfies its Designated Requirement. |
| arm64 signature display | Linker ad-hoc signature, `Identifier=a.out`, `Info.plist=not bound`, `Sealed Resources=none`, no TeamIdentifier. |
| Intel App / executable | Exit 1: `code object is not signed at all`. |
| `spctl` assessment | Signing-subsystem internal error, not a conclusive Gatekeeper policy result. |
| `syspolicy_check distribution` | Bounded checks timed out and were terminated; no acceptance conclusion. |

## Cause and verification gap

The packager assembled `.app` directories around Go executables but never signed
the completed application. Go's linker signature described the arm64 program as
a standalone executable; it did not bind the bundle's Info.plist or seal its
resources. The Intel executable had no signature. This is a reproduced packaging
defect in the supplied build, consistent with the reported open failure.

Earlier archive/hash and direct-executable loopback checks did not validate the
complete bundle. Running its executable on a developer machine without a real
download/first-launch test did not exercise the failing path. Those earlier
results remain scoped records, not evidence of a valid or accepted App bundle.

## Source correction

The alpha.3 packager stages all application files first, then signs the **new
complete bundle** with a local ad-hoc seal and immediately verifies it using
`codesign --verify --deep --strict`. The ZIP is made from those exact sealed
bytes, including `_CodeSignature/CodeResources`. Signing modifies the executable,
so its manifest hash is taken afterward. App packaging requires macOS and its
system `codesign`; `--cli-only` can build command archives without App packaging.

The normal macOS package check now reconstructs both complete App bundles from
their ZIPs and verifies them before invoking any executable. Archive-only mode
still checks bytes/layout and explicitly does not establish signature validity.
Regression checks alter Info.plist, a resource and the seal in separate private
copies and require verification to fail. Original frozen artifacts are retained.

## Distribution boundary

A valid ad-hoc resource seal establishes local bundle integrity, **not Developer
ID publisher identity, notarization or Gatekeeper acceptance**. No quarantine
attribute was removed and no OS protection was changed. The old alpha.1/alpha.2
App is no longer recommended for downloaded use; the public alpha.2 standalone
CLI remains a separate artifact with its existing unsigned-release limitations.
The npm entry continues to pin that standalone CLI; it is not a repair of a
downloaded App and has not been published to a registry.

The new alpha.3 App is a local structural-fix candidate. Normal browser/ChatGPT
downloaded-file first launch remains unaccepted until the separately authorized
publisher-signing/notarization and real first-launch checks are completed.
It must not be described as a trusted, ready-to-distribute Mac application.

Apple distinguishes resource sealing, signature validity and trust policy in
[TN2206](https://developer.apple.com/library/archive/technotes/tn2206/_index.html).
Publisher distribution additionally follows [Apple's notarization guidance](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution).
