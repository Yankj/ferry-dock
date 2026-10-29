#!/usr/bin/env python3
"""Verify a local App ZIP and prove that signature/resource tampering is caught.

Only private temporary copies are changed. This never launches or signs an App,
changes OS protections, removes quarantine, or assesses publisher trust.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("ferry_dock_package_checks", ROOT / "scripts/smoke-package.py")
package_checks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(package_checks)


def require(value, message):
    if not value:
        raise RuntimeError(message)


def verify(app):
    result = subprocess.run(["/usr/bin/codesign", "--verify", "--deep", "--strict",
                             "--verbose=4", str(app)],
                            capture_output=True, text=True, timeout=20, check=False)
    return {"exitCode": result.returncode,
            "diagnostic": (result.stdout + result.stderr).strip().replace(str(app), "<App>")}


def extract(archive, destination):
    # Reject unsafe/link/non-file members before asking the system ZIP extractor
    # to perform the same extraction path a normal macOS recipient uses.
    entries = package_checks.members(archive)
    require("Ferry Dock.app/Contents/Info.plist" in entries, "ZIP has no expected App bundle")
    result = subprocess.run(["/usr/bin/ditto", "-x", "-k", str(archive), str(destination)],
                            capture_output=True, timeout=20, check=False)
    require(result.returncode == 0, "system ZIP extraction failed")
    return destination / "Ferry Dock.app"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True, help="new sealed App ZIP")
    parser.add_argument("--legacy-archive", type=Path, help="optional original broken ZIP for a read-only contrast")
    parser.add_argument("--receipt", type=Path, help="optional sanitized JSON evidence output")
    args = parser.parse_args()
    require(sys.platform == "darwin" and Path("/usr/bin/codesign").is_file(), "signature regression requires macOS codesign")
    archive = args.archive.resolve()
    results = {}
    with tempfile.TemporaryDirectory(prefix="ferry-dock-app-signature-test-") as temporary:
        base = Path(temporary)
        app = extract(archive, base / "round trip with spaces 渡口")
        require((app / "Contents/_CodeSignature/CodeResources").is_file(), "new App lacks CodeResources")
        results["original"] = verify(app)
        require(results["original"]["exitCode"] == 0, "new whole App strict signature check failed")
        for label in ("changedInfo", "changedResource", "missingResourceSeal"):
            changed = base / label / "Ferry Dock.app"
            changed.parent.mkdir()
            shutil.copytree(app, changed)
            if label == "changedInfo":
                target = changed / "Contents/Info.plist"
                info = plistlib.loads(target.read_bytes())
                info["FerryDockVersion"] = str(info.get("FerryDockVersion", "")) + "-tampered"
                target.write_bytes(plistlib.dumps(info, sort_keys=True))
            elif label == "changedResource":
                target = changed / "Contents/Resources/FerryDock.icns"
                require(target.is_file(), "expected sealed icon resource is absent")
                with target.open("ab") as stream:
                    stream.write(b"signature-regression-test")
            else:
                (changed / "Contents/_CodeSignature/CodeResources").unlink()
            results[label] = verify(changed)
            require(results[label]["exitCode"] != 0, label + " unexpectedly passed strict bundle verification")
        if args.legacy_archive:
            legacy = extract(args.legacy_archive.resolve(), base / "original legacy archive")
            results["legacy"] = verify(legacy)
            require(results["legacy"]["exitCode"] != 0, "legacy contrast did not reproduce the known signature failure")
    receipt = {"status": "PASS_LOCAL", "archive": archive.name,
               "archiveSha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
               "checks": results, "noSigningPerformed": True,
               "noSecurityAttributesRemoved": True,
               "notRun": ["Gatekeeper or publisher trust acceptance", "Finder launch",
                          "browser/phone/Agent interaction", "Developer ID signing or notarization"]}
    text = json.dumps(receipt, ensure_ascii=False, indent=2) + "\n"
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(text)
    print(text, end="")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as error:
        raise SystemExit("App signature regression failed: " + str(error))
