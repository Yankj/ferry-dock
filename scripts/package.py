#!/usr/bin/env python3
"""Build local, deterministic native archives. Uses Python's standard library.

No upload, signing, notarization, installer, or security-setting changes occur.
An unclean source tree requires --allow-dirty and is identified in metadata.
"""

from __future__ import annotations

import argparse
import datetime
import gzip
import hashlib
import io
import json
import math
import os
from pathlib import Path
import plistlib
import re
import shutil
import stat
import struct
import subprocess
import sys
import tarfile
import tempfile
import xml.etree.ElementTree as ET
import zipfile
import zlib


ROOT = Path(__file__).resolve().parents[1]
TARGETS = (
    "darwin/arm64", "darwin/amd64", "linux/amd64", "linux/arm64",
    "windows/amd64", "windows/arm64",
)
BUILDINFO = "github.com/Yankj/ferry-dock/internal/buildinfo"


def run(command, *, env=None):
    result = subprocess.run(
        command, cwd=ROOT, env=env, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(f"{' '.join(map(str, command))}: {detail}")
    return result.stdout.strip()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def source_digest(output_parent, destination):
    """Identify Git-visible source bytes, including an explicitly allowed WIP.

    Output directories are omitted even when a caller chooses a location that
    is not covered by .gitignore. Never follow a source symlink outside the tree.
    """
    result = subprocess.run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
                            cwd=ROOT, capture_output=True, check=True)
    fingerprint = hashlib.sha256()
    for raw_name in sorted(set(result.stdout.split(b"\0")) - {b""}):
        name = os.fsdecode(raw_name)
        path = ROOT / name
        if path == destination or destination in path.parents:
            continue
        try:
            output_relative = path.relative_to(output_parent)
            if output_relative.parts and output_relative.parts[0].startswith(".ferry-dock-package-"):
                continue
        except ValueError:
            pass
        try:
            metadata = path.lstat()
            if path.is_symlink():
                contents = os.fsencode(os.readlink(path))
            elif path.is_file():
                contents = path.read_bytes()
            else:
                raise ValueError(f"source contains an unsupported non-file: {name}")
            mode = metadata.st_mode
        except FileNotFoundError:
            mode, contents = 0, b"missing"
        fingerprint.update(raw_name + b"\0" + str(mode).encode() + b"\0")
        fingerprint.update(len(contents).to_bytes(8, "big") + contents)
    return fingerprint.hexdigest()


def zip_bytes(entries, epoch):
    # ZIP timestamps have two-second precision and cannot represent pre-1980 dates.
    stamp = datetime.datetime.fromtimestamp(
        max(315532800, min(epoch, 4354819198)), datetime.timezone.utc,
    ).timetuple()[:6]
    result = io.BytesIO()
    with zipfile.ZipFile(result, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, (data, mode) in sorted(entries.items()):
            item = zipfile.ZipInfo(name, date_time=stamp)
            item.create_system = 3
            item.compress_type = zipfile.ZIP_DEFLATED
            item.external_attr = (stat.S_IFREG | mode) << 16
            archive.writestr(item, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    return result.getvalue()


def tar_bytes(entries, epoch):
    result = io.BytesIO()
    with gzip.GzipFile(fileobj=result, mode="wb", filename="", mtime=epoch, compresslevel=9) as gz:
        with tarfile.open(fileobj=gz, mode="w", format=tarfile.PAX_FORMAT) as archive:
            for name, (data, mode) in sorted(entries.items()):
                item = tarfile.TarInfo(name)
                item.size, item.mode, item.mtime = len(data), mode, epoch
                item.uid = item.gid = 0
                item.uname = item.gname = ""
                archive.addfile(item, io.BytesIO(data))
    return result.getvalue()


def svg_polygons(source):
    """Read only the line/rectangle geometry used by the canonical brand mark.

    This is deliberately not a general SVG renderer. Fail if the source starts
    using curves, strokes, transforms, or other geometry instead of silently
    producing an out-of-date icon. The executable does not need an SVG runtime.
    """
    document = ET.fromstring(source)
    if document.attrib.get("viewBox") != "0 0 32 32":
        raise ValueError("app icon expects the canonical 32-unit mark")
    polygons = []
    for element in document:
        name = element.tag.rsplit("}", 1)[-1]
        if name in ("title", "desc"):
            continue
        if "transform" in element.attrib or "stroke" in element.attrib:
            raise ValueError("unsupported mark transformation or stroke")
        if element.attrib.get("fill", "currentColor") != "currentColor":
            raise ValueError("app icon expects a single-colour canonical mark")
        if name == "rect":
            if float(element.attrib.get("rx", 0)) or float(element.attrib.get("ry", 0)):
                raise ValueError("rounded mark rectangles need an updated renderer")
            x, y, width, height = (float(element.attrib.get(k, 0)) for k in ("x", "y", "width", "height"))
            polygons.append([(x, y), (x + width, y), (x + width, y + height), (x, y + height)])
        elif name == "path":
            path = element.attrib["d"]
            if re.search(r"[^MmLlHhVvZz\d\s.,+-]", path):
                raise ValueError("unsupported mark path command")
            tokens = re.findall(r"[MmLlHhVvZz]|[-+]?(?:\d*\.\d+|\d+)", path)
            index, command, x, y, points = 0, None, 0.0, 0.0, []
            while index < len(tokens):
                if tokens[index].isalpha():
                    command = tokens[index]
                    index += 1
                if command in ("Z", "z"):
                    if points:
                        polygons.append(points)
                        x, y = points[0]
                        points = []
                    command = None
                    continue
                if command not in ("M", "m", "L", "l", "H", "h", "V", "v"):
                    raise ValueError("invalid canonical mark path")
                count = 2 if command in "MmLl" else 1
                values = [float(v) for v in tokens[index:index + count]]
                if len(values) != count:
                    raise ValueError("incomplete canonical mark path")
                index += count
                relative = command.islower()
                if command in "MmLl":
                    x, y = ((x + values[0], y + values[1]) if relative else tuple(values))
                elif command in "Hh":
                    x = x + values[0] if relative else values[0]
                else:
                    y = y + values[0] if relative else values[0]
                points.append((x, y))
                if command in "Mm":
                    command = "l" if relative else "L"
            if points:
                raise ValueError("canonical mark path must close")
        else:
            raise ValueError(f"unsupported canonical mark element: {name}")
    color = document.attrib["color"].lstrip("#")
    return polygons, bytes.fromhex(color)


def png_icon(size, polygons, ink):
    """Render the existing geometry on a quiet rounded-square app tile."""
    scale = size / 1024
    margin, radius = 32 * scale, 208 * scale
    mark_scale, mark_offset = 22 * scale, 160 * scale
    background = bytes.fromhex("F7F8F4")
    rows = bytearray()

    def interval(row, left, right, color):
        for pixel in range(max(0, int(math.floor(left))), min(size, int(math.ceil(right)))):
            coverage = min(right, pixel + 1) - max(left, pixel)
            if coverage > 0:
                offset = pixel * 4
                under_alpha = row[offset + 3] / 255
                alpha = coverage + under_alpha * (1 - coverage)
                channels = bytes(round((color[c] * coverage + row[offset + c] * under_alpha * (1 - coverage)) / alpha)
                                 for c in range(3))
                row[offset:offset + 4] = channels + bytes([round(255 * alpha)])

    for row_index in range(size):
        row = bytearray(size * 4)
        y = row_index + 0.5
        if margin <= y < size - margin:
            distance = max(margin + radius - y, y - (size - margin - radius), 0)
            inset = radius - math.sqrt(max(0, radius * radius - distance * distance))
            interval(row, margin + inset, size - margin - inset, background)
        mark_y = (y - mark_offset) / mark_scale
        for polygon in polygons:
            crossings = []
            for i, (x1, y1) in enumerate(polygon):
                x2, y2 = polygon[(i + 1) % len(polygon)]
                if (y1 <= mark_y < y2) or (y2 <= mark_y < y1):
                    crossings.append(x1 + (mark_y - y1) * (x2 - x1) / (y2 - y1))
            crossings.sort()
            for i in range(0, len(crossings), 2):
                interval(row, mark_offset + crossings[i] * mark_scale,
                         mark_offset + crossings[i + 1] * mark_scale, ink)
        rows.extend(b"\0" + row)

    def chunk(name, data):
        return struct.pack(">I", len(data)) + name + data + struct.pack(">I", zlib.crc32(name + data) & 0xFFFFFFFF)

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(bytes(rows), 9)) + chunk(b"IEND", b""))


def app_icon():
    polygons, ink = svg_polygons((ROOT / "brand/logo-light.svg").read_text(encoding="utf-8"))
    result = bytearray()
    for kind, size in ((b"icp4", 16), (b"icp5", 32), (b"ic07", 128),
                       (b"ic08", 256), (b"ic09", 512), (b"ic10", 1024)):
        png = png_icon(size, polygons, ink)
        result.extend(kind + struct.pack(">I", len(png) + 8) + png)
    return b"icns" + struct.pack(">I", len(result) + 8) + result


def signature_status(binary, goos):
    status = {"scope": "executable", "publisherSigned": False,
              "developerIdSigned": False, "notarized": False, "adHoc": "NOT_CHECKED"}
    if goos != "darwin":
        status["adHoc"] = "NOT_APPLICABLE"
    elif shutil.which("codesign"):
        # Inspection only. Go's Darwin linker may already emit an ad-hoc signature.
        result = subprocess.run(["codesign", "-d", "--verbose=4", str(binary)],
                                capture_output=True, text=True, check=False)
        text = result.stdout + result.stderr
        if "Signature=adhoc" in text or "flags=0x2(adhoc)" in text:
            status["adHoc"] = True
        elif "code object is not signed at all" in text:
            status["adHoc"] = False
    return status


def instructions(goos, app=False):
    if app:
        return """Ferry Dock / 渡口 — macOS alpha

Open Ferry Dock.app to launch the local desktop mode in your browser.
The app contains the same Go core as the CLI; it has no shell or Node runtime.
To stop the service, use the desktop page's shutdown control.
Usage documents and the optional Skill are in Contents/Resources. The Skill is
included as a local file; nothing installs it or changes Agent configuration.

This app has no Developer ID signing or Apple notarization. Any linker ad-hoc
signature is not a verified publisher identity. macOS may block a downloaded
app; this package does not bypass Gatekeeper. A source build is an alternative.

Physical-phone access needs a reachable LAN address and your network's normal
permissions. HTTP is not encrypted. Share invitations only with intended senders.
Files and automatic Agent-host wake-up are not provided by this alpha.

Source, usage, and security information: https://github.com/Yankj/ferry-dock
"""
    command = ".\\ferry-dock.exe" if goos == "windows" else "./ferry-dock"
    return f"""Ferry Dock / 渡口 — native CLI alpha

In this directory, run:
  {command} version
  {command} serve

Open the private computer URL printed by the service. The default listener is
127.0.0.1:8787 and cannot receive from a physical phone. To allow a phone on a
trusted LAN, use your computer's actual reachable LAN address, for example:
  {command} serve --listen 0.0.0.0:8787 --public-url http://192.168.1.20:8787

A QR does not bypass a firewall, guest Wi-Fi isolation, VPN, or routing.
HTTP is not encrypted. Stop the service with Ctrl+C. Content is in memory and
is lost at shutdown. Keep the private computer link and reader handles private.
Files and automatic Agent-host wake-up are not provided by this alpha.

This archive is a portable developer alpha, not an installer. Publisher signing
and platform-native first-launch acceptance have not been completed. Operating
system protections may warn or block downloaded executables; this package does
not disable or bypass them. Cross-compilation is not native runtime validation.
README.md and README.zh-CN.md describe the product. The optional local Skill is
in skills/ferry-dock/SKILL.md; it is not globally installed or configured.

Source, usage, and security information: https://github.com/Yankj/ferry-dock
"""


def documentation():
    # Preserve relative links in product docs and the optional Skill. Only static
    # documentation/brand files are included, never source/runtime capabilities.
    files = [ROOT / name for name in ("README.md", "README.zh-CN.md", "PRFAQ.md", "SECURITY.md",
                                      "CONTRIBUTING.md", "CODE_OF_CONDUCT.md") if (ROOT / name).is_file()]
    for directory in ("docs", "skills/ferry-dock", "brand"):
        for path in (ROOT / directory).rglob("*"):
            if path.is_file() and not path.is_symlink() and path.suffix in (".md", ".svg", ".png", ".html", ".json"):
                files.append(path)
    return {path.relative_to(ROOT).as_posix(): (path.read_bytes(), 0o644) for path in sorted(set(files))}


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", default="0.1.0-alpha.1", help="artifact/product version (default: %(default)s)")
    parser.add_argument("--target", action="append", choices=TARGETS, help="repeat for a subset (default: both Darwin architectures)")
    parser.add_argument("--all", action="store_true", help="build all six targets, including both macOS apps")
    parser.add_argument("--out", type=Path, default=ROOT / "dist", help="output parent; creates a new version directory")
    parser.add_argument("--go", default=os.environ.get("GO", "go"), help="Go executable path")
    parser.add_argument("--allow-dirty", action="store_true", help="package an explicitly marked unclean working tree")
    parser.add_argument("--offline", action="store_true", help="disable module-proxy access; dependencies must be cached")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+-]{0,63}", args.version):
        parser.error("version must be 1–64 filename-safe ASCII letters, digits, dots, dashes, underscores, or plus signs")
    if args.all and args.target:
        parser.error("choose --all or --target")
    return args


def main():
    args = parse_args()
    targets = list(TARGETS) if args.all else sorted(set(args.target or TARGETS[:2]))
    commit = run(["git", "rev-parse", "HEAD"])
    dirty = bool(run(["git", "status", "--porcelain", "--untracked-files=normal"]))
    if dirty and not args.allow_dirty:
        raise RuntimeError("source tree is unclean; commit changes or pass --allow-dirty to identify this local build honestly")
    binary_commit = commit + ("-dirty" if dirty else "")
    epoch = int(os.environ.get("SOURCE_DATE_EPOCH", run(["git", "show", "-s", "--format=%ct", "HEAD"])))
    if not 0 <= epoch <= 0xFFFFFFFF:
        raise ValueError("SOURCE_DATE_EPOCH must fit an unsigned 32-bit gzip timestamp")
    destination = args.out.resolve() / args.version
    if destination.exists():
        raise RuntimeError(f"refusing to overwrite existing output: {destination}")
    for relative in ("cmd/ferry-dock/main.go", "internal/buildinfo"):
        if not (ROOT / relative).exists():
            raise RuntimeError(f"required source is not ready: {relative}")
    fingerprint = source_digest(destination.parent, destination)
    environment = os.environ.copy()
    environment.update({"CGO_ENABLED": "0", "GOTOOLCHAIN": "local", "GOWORK": "off", "GOFLAGS": "",
                        "GOENV": "off", "GO111MODULE": "on", "GOAMD64": "v1", "GOARM64": "v8.0",
                        "GOEXPERIMENT": "", "SOURCE_DATE_EPOCH": str(epoch)})
    if args.offline:
        environment.update({"GOPROXY": "off", "GONOPROXY": "", "GOPRIVATE": ""})
    go_version = run([args.go, "version"], env=environment)
    manifest = {
        "schema": 1, "product": "Ferry Dock", "version": args.version,
        "source": {"commit": commit, "dirty": dirty, "binaryCommit": binary_commit,
                   "epoch": epoch, "treeSha256": fingerprint},
        "toolchain": {"go": go_version, "python": sys.version.split()[0], "zlib": zlib.ZLIB_VERSION,
                      "goamd64": "v1", "goarm64": "v8.0", "goexperiment": "", "goenv": "off"},
        "build": {"cgoEnabled": False, "trimpath": True, "vcsStamping": False, "pgo": False},
        "artifacts": [],
    }
    license_data = (ROOT / "LICENSE").read_bytes()
    docs = documentation()
    icon = app_icon() if any(target.startswith("darwin/") for target in targets) else None
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".ferry-dock-package-", dir=destination.parent) as temporary:
        stage = Path(temporary) / "artifacts"
        stage.mkdir()
        for target in targets:
            goos, goarch = target.split("/")
            environment.update({"GOOS": goos, "GOARCH": goarch})
            for kind in (["cli", "app"] if goos == "darwin" else ["cli"]):
                mode = "desktop" if kind == "app" else "serve"
                executable_name = "ferry-dock.exe" if goos == "windows" else "ferry-dock"
                binary = Path(temporary) / f"{goos}-{goarch}-{kind}-{executable_name}"
                flags = (f"-s -w -buildid= -X {BUILDINFO}.Version={args.version} "
                         f"-X {BUILDINFO}.Commit={binary_commit} -X {BUILDINFO}.DefaultMode={mode}")
                print(f"Building {target} {kind} ({mode})", flush=True)
                run([args.go, "build", "-mod=readonly", "-trimpath", "-buildvcs=false", "-pgo=off",
                     "-ldflags", flags, "-o", str(binary), "./cmd/ferry-dock"], env=environment)
                binary_data = binary.read_bytes()
                stem = f"ferry-dock-{args.version}-{goos}-{goarch}"
                if kind == "app":
                    binary_path = "Ferry Dock.app/Contents/MacOS/ferry-dock"
                    numeric_version = re.match(r"v?(\d+)\.(\d+)\.(\d+)", args.version)
                    bundle_version = ".".join(numeric_version.groups()) if numeric_version else "0.0.0"
                    info = {"CFBundleDevelopmentRegion": "en", "CFBundleDisplayName": "Ferry Dock / 渡口",
                            "CFBundleExecutable": "ferry-dock", "CFBundleIconFile": "FerryDock.icns",
                            "CFBundleIdentifier": "io.github.yankj.ferry-dock", "CFBundleInfoDictionaryVersion": "6.0",
                            "CFBundleName": "Ferry Dock", "CFBundlePackageType": "APPL",
                            "CFBundleShortVersionString": bundle_version, "CFBundleVersion": bundle_version,
                            "FerryDockVersion": args.version, "FerryDockCommit": binary_commit,
                            "NSHighResolutionCapable": True, "LSUIElement": True,
                            "NSLocalNetworkUsageDescription": "Receive text from your phone on your local network."}
                    entries = {binary_path: (binary_data, 0o755),
                               "Ferry Dock.app/Contents/Info.plist": (plistlib.dumps(info, sort_keys=True), 0o644),
                               "Ferry Dock.app/Contents/Resources/FerryDock.icns": (icon, 0o644),
                               "Ferry Dock.app/Contents/Resources/LICENSE": (license_data, 0o644),
                               "README.txt": (instructions(goos, app=True).encode(), 0o644),
                               "LICENSE": (license_data, 0o644)}
                    entries.update({"Ferry Dock.app/Contents/Resources/" + name: value for name, value in docs.items()})
                    filename = stem + "-app.zip"
                else:
                    binary_path = f"{stem}/{executable_name}"
                    entries = {binary_path: (binary_data, 0o755),
                               f"{stem}/README.txt": (instructions(goos).encode(), 0o644),
                               f"{stem}/LICENSE": (license_data, 0o644)}
                    entries.update({stem + "/" + name: value for name, value in docs.items()})
                    filename = stem + (".zip" if goos == "windows" else ".tar.gz")
                data = zip_bytes(entries, epoch) if filename.endswith(".zip") else tar_bytes(entries, epoch)
                (stage / filename).write_bytes(data)
                manifest["artifacts"].append({
                    "file": filename, "kind": kind, "goos": goos, "goarch": goarch,
                    "defaultMode": mode, "sha256": digest(data), "size": len(data),
                    "binary": {"path": binary_path, "sha256": digest(binary_data), "size": len(binary_data)},
                    "signing": signature_status(binary, goos), "nativeValidation": "NOT_RUN",
                })
                if kind == "app":
                    manifest["artifacts"][-1]["signing"]["bundleSigned"] = False
        manifest_data = (json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode()
        (stage / "manifest.json").write_bytes(manifest_data)
        sums = "".join(f"{digest(path.read_bytes())}  {path.name}\n" for path in sorted(stage.iterdir()))
        (stage / "SHA256SUMS").write_bytes(sums.encode("utf-8"))
        if run(["git", "rev-parse", "HEAD"]) != commit or source_digest(destination.parent, destination) != fingerprint:
            raise RuntimeError("source changed during packaging; no artifacts were delivered; freeze the source and retry")
        if destination.exists():
            raise RuntimeError(f"output appeared during build; refusing to overwrite: {destination}")
        stage.rename(destination)
    print(f"Local artifacts: {destination}")
    print("No publisher signing, notarization, native-platform acceptance, or publication was performed.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as error:
        print(f"package: {error}", file=sys.stderr)
        sys.exit(1)
