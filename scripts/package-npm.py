#!/usr/bin/env python3
"""Pack the pinned Apple Silicon Go core with its zero-dependency npm entry.

Only local files and an existing npm CLI are used. No install hooks, registry
writes, credentials, toolchain changes or binary downloads are performed.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tempfile


ROOT = Path(__file__).resolve().parents[1]
COPY_FILES = {
    "npm/package.json": "package.json",
    "npm/bin/ferry-dock.cjs": "bin/ferry-dock.cjs",
    "npm/core.json": "core.json",
    "npm/README.md": "README.md",
    "LICENSE": "LICENSE",
    "THIRD_PARTY_NOTICES.md": "THIRD_PARTY_NOTICES.md",
    "skills/ferry-dock/SKILL.md": "skills/ferry-dock/SKILL.md",
    "docs/contracts/request-v1.md": "docs/contracts/request-v1.md",
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(value, message):
    if not value:
        raise ValueError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True, help="verified local alpha.2 Mac arm64 CLI tar.gz")
    parser.add_argument("--manifest", type=Path, required=True, help="original frozen alpha.2 manifest.json")
    parser.add_argument("--out", type=Path, default=ROOT / "dist/npm", help="output parent; a new version directory is required")
    parser.add_argument("--package-name", default="ferry-dock", help="candidate name; this does not establish registry ownership")
    parser.add_argument("--package-version", default="0.1.0-alpha.2", help="npm wrapper package version")
    parser.add_argument("--node", required=True, help="existing supported Node executable; no global runtime is changed")
    parser.add_argument("--npm-cli", type=Path, required=True, help="existing npm-cli.js invoked by --node")
    args = parser.parse_args()
    require(re.fullmatch(r"(?:@[a-z0-9][a-z0-9._-]*/)?[a-z0-9][a-z0-9._-]*", args.package_name), "invalid candidate npm package name")
    require(re.fullmatch(r"\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?", args.package_version), "invalid package version")
    core = json.loads((ROOT / "npm/core.json").read_text())
    data = args.archive.read_bytes()
    manifest_data = args.manifest.read_bytes()
    require(sha(data) == core["archiveSha256"], "source archive does not match pinned SHA-256")
    require(sha(manifest_data) == core["manifestSha256"], "source manifest does not match pinned SHA-256")
    manifest = json.loads(manifest_data)
    require(manifest["version"] == core["version"] and manifest["source"]["commit"] == core["commit"] and manifest["source"]["dirty"] is False,
            "source provenance does not match pinned clean core")
    artifact = next((a for a in manifest["artifacts"] if a["file"] == core["archiveName"]), None)
    require(artifact and artifact["kind"] == "cli" and artifact["goos"] == "darwin" and artifact["goarch"] == "arm64" and artifact["binary"]["sha256"] == core["binarySha256"],
            "source manifest does not contain the pinned Mac arm64 executable")
    with tarfile.open(args.archive) as archive:
        member = archive.getmember(artifact["binary"]["path"])
        require(member.isfile() and member.size == core["binarySize"], "source executable has invalid archive type or size")
        binary = archive.extractfile(member).read()
    require(sha(binary) == core["binarySha256"], "source executable does not match pinned SHA-256")
    destination = args.out.resolve() / args.package_version
    require(not destination.exists(), "output version directory already exists; choose a new --out parent")
    destination.parent.mkdir(parents=True, exist_ok=True)
    stage = destination / "package"
    stage.mkdir(parents=True)
    for source, target in COPY_FILES.items():
        original = ROOT / source
        require(original.is_file() and not original.is_symlink(), "packaging input must be a regular source file")
        output = stage / target
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(original, output)
        output.chmod(0o755 if target == "bin/ferry-dock.cjs" else 0o644)
    package = json.loads((stage / "package.json").read_text())
    package["name"] = args.package_name
    package["version"] = args.package_version
    (stage / "package.json").write_text(json.dumps(package, indent=2) + "\n")
    native = stage / "native/ferry-dock"
    native.parent.mkdir()
    native.write_bytes(binary)
    native.chmod(0o755)
    expected_files = sorted([*COPY_FILES.values(), "native/ferry-dock"])
    with tempfile.TemporaryDirectory(prefix="ferry-dock-npm-pack-") as cache:
        user_config = Path(cache) / "user.npmrc"
        global_config = Path(cache) / "global.npmrc"
        user_config.write_text("")
        global_config.write_text("")
        environment = dict(os.environ, npm_config_update_notifier="false", npm_config_audit="false", npm_config_fund="false",
                           npm_config_userconfig=str(user_config), npm_config_globalconfig=str(global_config))
        command = [str(Path(args.node).resolve()), str(args.npm_cli.resolve()), "pack", "--ignore-scripts", "--json", "--pack-destination", str(destination),
                   "--cache", cache, "--userconfig", str(user_config), "--globalconfig", str(global_config),
                   "--registry=https://registry.npmjs.org/", "--offline", "--logs-max=0", "--loglevel=error"]
        result = subprocess.run(command, cwd=stage, env=environment, capture_output=True, text=True, timeout=60)
    require(result.returncode == 0, "local npm pack failed (no registry publication was attempted)")
    packed = json.loads(result.stdout)
    require(len(packed) == 1, "npm pack did not return exactly one local package")
    packed = packed[0]
    require(sorted(f["path"] for f in packed["files"]) == expected_files, "npm pack content differs from the explicit file allowlist")
    tarball = destination / packed["filename"]
    with tarfile.open(tarball) as archive:
        for member in archive.getmembers():
            require(member.isfile() and member.name.startswith("package/") and member.name[len("package/"):] in expected_files,
                    "packed npm archive has an unexpected member")
    print(json.dumps({"packageName": args.package_name, "packageVersion": args.package_version,
                      "coreVersion": core["version"], "coreCommit": core["commit"],
                      "stagePath": str(stage), "tarballPath": str(tarball),
                      "tarballSha256": sha(tarball.read_bytes()), "files": expected_files,
                      "pack": {key: packed[key] for key in ("filename", "size", "unpackedSize", "shasum", "integrity", "entryCount")}}, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, tarfile.TarError, subprocess.TimeoutExpired) as error:
        raise SystemExit("Ferry Dock npm packaging failed: " + str(error))
