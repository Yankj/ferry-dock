#!/usr/bin/env python3
"""Validate local archives and this runner's native CLI lifecycle, without a browser.

Python standard library only. This does not install software, modify PATH or OS
protections, sign/notarize packages, or validate Finder/phone/download behavior.
Capabilities, control-file contents, URLs, and child output are never printed.
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path, PurePosixPath
import platform
import plistlib
import re
import shutil
import signal
import stat
import struct
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
from urllib.parse import parse_qs, urlsplit
import zipfile

from native_format import inspect_binary


MAX_ARCHIVE_BYTES = 256 << 20
MAX_RESPONSE_BYTES = 256 << 10
TARGETS = {(goos, arch, "cli") for goos in ("darwin", "linux", "windows")
           for arch in ("arm64", "amd64")} | {("darwin", arch, "app") for arch in ("arm64", "amd64")}
CLI_TARGETS = {target for target in TARGETS if target[2] == "cli"}
CHECKS = []


class Failure(Exception):
    """Only fixed, capability-free messages are exposed to the terminal."""


def check(condition, message):
    if not condition:
        raise Failure(message)
    CHECKS.append(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def validate_binary_header(data, goos, goarch):
    """Check the actual container/CPU, independently of its manifest label.

    This is not a platform runtime test or a signature/loader acceptance check.
    Go's per-target artifacts are thin 64-bit little-endian executables.
    """
    try:
        return inspect_binary(data, goos, goarch)
    except (ValueError, struct.error):
        raise Failure("archived executable format/target/static-link metadata is invalid") from None


def host_target():
    goos = {"darwin": "darwin", "win32": "windows"}.get(sys.platform,
             "linux" if sys.platform.startswith("linux") else "unsupported")
    machine = platform.machine().lower()
    if goos == "windows":
        # 64-bit Python may itself be emulated on Windows ARM64. This is the
        # OS-provided native architecture, not Python's compile target.
        class SystemInfo(ctypes.Structure):
            _fields_ = [("architecture", ctypes.c_ushort), ("reserved", ctypes.c_ushort),
                        ("pageSize", ctypes.c_ulong), ("minimumAddress", ctypes.c_void_p),
                        ("maximumAddress", ctypes.c_void_p), ("processorMask", ctypes.c_size_t),
                        ("processors", ctypes.c_ulong), ("processorType", ctypes.c_ulong),
                        ("allocationGranularity", ctypes.c_ulong),
                        ("processorLevel", ctypes.c_ushort), ("processorRevision", ctypes.c_ushort)]
        value = SystemInfo()
        ctypes.WinDLL("kernel32", use_last_error=True).GetNativeSystemInfo(ctypes.byref(value))
        machine = {9: "amd64", 12: "arm64"}.get(value.architecture, "unsupported")
    arch = {"x86_64": "amd64", "amd64": "amd64", "arm64": "arm64", "aarch64": "arm64"}.get(machine, "unsupported")
    return goos, arch


def private_write(path, data):
    descriptor = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(data)


def safe_member(name):
    value = PurePosixPath(name)
    check(name and "\\" not in name and not value.is_absolute()
          and all(part not in ("..", ".", "") for part in name.split("/"))
          and ":" not in value.parts[0], "archive contains an unsafe member path")
    return value


def members(archive):
    """Return bounded regular-file bytes/modes; never extract links or devices."""
    entries = {}
    total = 0
    if archive.name.endswith(".zip"):
        with zipfile.ZipFile(archive) as source:
            check(len(source.infolist()) <= 2000, "archive has too many entries")
            for item in source.infolist():
                name = item.filename.rstrip("/")
                safe_member(name)
                mode = item.external_attr >> 16
                check(not stat.S_ISLNK(mode), "archive contains a symbolic link")
                if item.is_dir():
                    continue
                check(stat.S_IFMT(mode) in (0, stat.S_IFREG), "archive contains non-file content")
                total += item.file_size
                check(total <= MAX_ARCHIVE_BYTES, "archive exceeds the uncompressed byte bound")
                check(name not in entries, "archive contains duplicate members")
                entries[name] = (source.read(item), mode & 0o777)
    else:
        with tarfile.open(archive, "r:gz") as source:
            count = 0
            for item in source:
                count += 1
                check(count <= 2000, "archive has too many entries")
                name = item.name.rstrip("/")
                safe_member(name)
                if item.isdir():
                    continue
                check(item.isfile(), "archive contains a link or non-file content")
                total += item.size
                check(total <= MAX_ARCHIVE_BYTES, "archive exceeds the uncompressed byte bound")
                check(name not in entries, "archive contains duplicate members")
                stream = source.extractfile(item)
                check(stream is not None, "archive member could not be read")
                with stream:
                    entries[name] = (stream.read(MAX_ARCHIVE_BYTES + 1), item.mode & 0o777)
    return entries


def validate_contents(entries, docs_prefix, binary_path, is_app):
    """Explicit public-product payload allowlist, independent of the builder."""
    top_docs = {"README.md", "README.zh-CN.md", "PRFAQ.md", "SECURITY.md", "CONTRIBUTING.md", "CODE_OF_CONDUCT.md"}
    exact = {binary_path, "LICENSE", "README.txt"} if is_app else {binary_path, docs_prefix + "LICENSE", docs_prefix + "README.txt"}
    if is_app:
        exact |= {"Ferry Dock.app/Contents/Info.plist", "Ferry Dock.app/Contents/_CodeSignature/CodeResources",
                  docs_prefix + "FerryDock.icns", docs_prefix + "LICENSE"}
    text_suffixes = {".md", ".svg", ".html", ".json"}
    secret = re.compile(rb"(?:-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----|"
                        rb"\bgh[pousr]_[A-Za-z0-9]{30,}\b|\bgithub_pat_[A-Za-z0-9_]{40,}\b|"
                        rb"\bnpm_[A-Za-z0-9]{30,}\b|\bBearer [A-Za-z0-9_-]{32,}\b|"
                        rb"#(?:owner|key)=[A-Za-z0-9_-]{32,})")
    index = []
    for name, (data, mode) in sorted(entries.items()):
        if name not in exact:
            check(name.startswith(docs_prefix), "archive payload contains a file outside its public documentation prefix")
            relative = name[len(docs_prefix):]
            path = PurePosixPath(relative)
            check(not any(part.startswith(".") for part in path.parts)
                  and (relative in top_docs or (relative.startswith(("docs/", "skills/ferry-dock/", "brand/"))
                       and path.suffix in text_suffixes | {".png"})),
                  "archive payload contains an unapproved source/runtime/documentation file")
            check(mode == 0o644, "archived documentation mode differs from the public payload contract")
        if name != binary_path and PurePosixPath(name).suffix in text_suffixes | {".txt"}:
            check(secret.search(data) is None, "archive text matches a credential or active-capability pattern")
        index.append({"path": name, "mode": mode, "sha256": sha(data)})
    return {"count": len(index), "sha256": sha(json.dumps(index, sort_keys=True, separators=(",", ":")).encode())}


def validate_archives(directory, require_all, require_cli_targets=False, native_target=None):
    manifest_path = directory / "manifest.json"
    check(manifest_path.is_file() and manifest_path.stat().st_size <= (1 << 20), "package manifest is missing or oversized")
    manifest_data = manifest_path.read_bytes()
    manifest = json.loads(manifest_data)
    check(manifest.get("schema") == 1 and manifest.get("product") == "Ferry Dock", "package manifest schema/product differs from the contract")
    check(isinstance(manifest.get("version"), str) and manifest["version"], "manifest version is missing")
    source = manifest.get("source", {})
    check(isinstance(source.get("dirty"), bool) and isinstance(source.get("commit"), str)
          and re.fullmatch(r"[0-9a-f]{40,64}", source["commit"]), "manifest source identity is invalid")
    check(source.get("binaryCommit") == source["commit"] + ("-dirty" if source["dirty"] else ""), "manifest dirty/binary commit attribution differs")
    check(manifest.get("build") == {"cgoEnabled": False, "trimpath": True, "vcsStamping": False, "pgo": False}, "manifest build flags differ from the packaging contract")
    artifacts = manifest.get("artifacts")
    check(isinstance(artifacts, list) and artifacts, "manifest has no package artifacts")
    sums_path = directory / "SHA256SUMS"
    check(sums_path.is_file() and sums_path.stat().st_size <= (1 << 20), "SHA256SUMS is missing or oversized")
    sums = {}
    for line in sums_path.read_text(encoding="utf-8").splitlines():
        matched = re.fullmatch(r"([0-9a-f]{64})  ([A-Za-z0-9._+-]+)", line)
        check(matched is not None and matched[2] not in sums, "checksum file contains an invalid or duplicate entry")
        sums[matched[2]] = matched[1]
    names = {"manifest.json"}
    targets = set()
    selected = {}
    for artifact in artifacts:
        name = artifact.get("file", "")
        check(re.fullmatch(r"[A-Za-z0-9._+-]+", name) is not None and name not in names, "manifest artifact name is invalid or duplicate")
        names.add(name)
        target = (artifact.get("goos"), artifact.get("goarch"), artifact.get("kind"))
        check(target in TARGETS and target not in targets, "manifest target is unsupported or duplicate")
        targets.add(target)
        expected_mode = "desktop" if target[2] == "app" else "serve"
        check(artifact.get("defaultMode") == expected_mode, "manifest defaultMode is inconsistent with artifact kind")
        check(artifact.get("nativeValidation") == "NOT_RUN", "build manifest must not claim native acceptance")
        signing = artifact.get("signing", {})
        check(signing.get("developerIdSigned") is False and signing.get("notarized") is False,
              "unsigned local alpha manifest unexpectedly claims publisher signing/notarization")
        check(signing.get("publisherSigned", False) is False,
              "local alpha manifest unexpectedly claims publisher signing")
        legacy_app = (target[2] == "app" and manifest["version"] in
                      ("0.1.0-alpha.1", "0.1.0-alpha.2")
                      and signing.get("bundleSigned", False) is False)
        if target[2] == "app" and not legacy_app:
            check(signing.get("scope") == "bundle" and signing.get("adHoc") is True
                  and signing.get("bundleSigned") is True
                  and signing.get("bundleVerified") is True
                  and signing.get("resourceSealed") is True
                  and signing.get("strictVerification") == "PASS"
                  and signing.get("identifier") == "io.github.yankj.ferry-dock",
                  "new app manifest must record a verified complete ad-hoc bundle signature")
        archive = directory / name
        check(archive.is_file() and archive.stat().st_size <= MAX_ARCHIVE_BYTES, "archive is missing or exceeds its byte bound")
        data = archive.read_bytes()
        check(len(data) == artifact.get("size") and sha(data) == artifact.get("sha256")
              and sums.get(name) == sha(data), "archive checksum or size does not match its manifest")
        entries = members(archive)
        binary = artifact.get("binary", {})
        binary_path = binary.get("path", "")
        check(binary_path in entries, "manifest binary is missing from its archive")
        contents, mode = entries[binary_path]
        check(len(contents) == binary.get("size") and sha(contents) == binary.get("sha256"), "archived binary checksum/size differs from manifest")
        observed_format = validate_binary_header(contents, target[0], target[1])
        if "binaryFormat" in artifact or manifest["version"] not in ("0.1.0-alpha.1", "0.1.0-alpha.2", "0.1.0-alpha.3"):
            check(artifact.get("binaryFormat") == observed_format,
                  "executable header/linkage inspection differs from manifest")
            check(artifact.get("runtimeRequirements") == {
                "cpuBaseline": "x86-64-v1" if target[1] == "amd64" else "armv8.0",
                "minimumOsAcceptance": "NOT_RUN",
                "linuxLibc": "not dynamically linked" if target[0] == "linux" else "NOT_APPLICABLE"},
                "runtime requirements claim differs from independently checked build metadata")
        check(mode & 0o111 != 0 and mode & 0o022 == 0, "archived binary executable permissions are invalid")
        if target[2] == "app":
            check(binary_path == "Ferry Dock.app/Contents/MacOS/ferry-dock", "app binary path differs from its bundle contract")
            info_path = "Ferry Dock.app/Contents/Info.plist"
            check(info_path in entries, "app Info.plist is missing")
            info = plistlib.loads(entries[info_path][0])
            check(info.get("CFBundleExecutable") == "ferry-dock" and info.get("CFBundlePackageType") == "APPL"
                  and info.get("NSLocalNetworkUsageDescription"), "app bundle executable/type/network purpose is invalid")
            check(info.get("LSUIElement") is True, "browser-launching app bundle must identify its background UI role")
            check(info.get("FerryDockVersion") == manifest["version"]
                  and info.get("FerryDockCommit") == source["binaryCommit"],
                  "app bundle version/source attribution differs from manifest")
            icon_path = "Ferry Dock.app/Contents/Resources/" + info.get("CFBundleIconFile", "")
            check(icon_path in entries and entries[icon_path][0].startswith(b"icns"), "app icon is missing or not ICNS")
            check("LICENSE" in entries and "README.txt" in entries
                  and "Ferry Dock.app/Contents/Resources/LICENSE" in entries, "app license or local-use instructions are missing")
            if not legacy_app:
                seal_path = "Ferry Dock.app/Contents/_CodeSignature/CodeResources"
                check(seal_path in entries, "new app has no bundled resource signature")
                envelope = plistlib.loads(entries[seal_path][0])
                check(isinstance(envelope.get("files2"), dict) and envelope["files2"],
                      "new app resource signature has no version-two sealed resources")
            docs_prefix = "Ferry Dock.app/Contents/Resources/"
        else:
            stem = "ferry-dock-{}-{}-{}".format(manifest["version"], target[0], target[1])
            check(binary_path == stem + ("/ferry-dock.exe" if target[0] == "windows" else "/ferry-dock")
                  and stem + "/LICENSE" in entries and stem + "/README.txt" in entries,
                  "CLI archive layout or instructions differ from the contract")
            docs_prefix = stem + "/"
        check(all(docs_prefix + relative in entries for relative in
                  ("README.md", "README.zh-CN.md", "SECURITY.md", "skills/ferry-dock/SKILL.md")),
              "archive is missing product/security documentation or its optional local Skill")
        content_metadata = validate_contents(entries, docs_prefix, binary_path, target[2] == "app")
        if "contents" in artifact or manifest["version"] not in ("0.1.0-alpha.1", "0.1.0-alpha.2", "0.1.0-alpha.3"):
            check(artifact.get("contents") == content_metadata, "archive content allowlist metadata differs from its manifest")
        if target[:2] == (native_target or host_target()):
            selected[target[2]] = (artifact, entries)
    check(set(sums) == names and sums.get("manifest.json") == sha(manifest_data), "checksum file does not cover exactly the manifest and all archives")
    actual_names = {item.name for item in directory.iterdir() if item.is_file()}
    check(actual_names == names | {"SHA256SUMS"}, "package directory contains unlisted files")
    if require_all:
        check(targets == TARGETS, "--require-all expected six CLI and two macOS app archives")
    if require_cli_targets:
        check(CLI_TARGETS <= targets, "--require-cli-targets expected all six CLI archives")
    print("PASS PACKAGE: all {} archive hashes, binary hashes/target headers, metadata, permissions, and layouts verified.".format(len(artifacts)))
    return manifest, selected


def strict_bundle_check(app):
    """Verify the complete reconstructed bundle without launching or signing it."""
    codesign = Path("/usr/bin/codesign")
    check(sys.platform == "darwin" and codesign.is_file(),
          "complete app signature checks require macOS codesign")
    result = subprocess.run([str(codesign), "--verify", "--deep", "--strict",
                             "--verbose=4", str(app)],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            timeout=20, check=False)
    check(result.returncode == 0, "complete app strict signature verification failed")


def write_entries(destination, entries):
    for name, (data, mode) in entries.items():
        member = destination.joinpath(*safe_member(name).parts)
        member.parent.mkdir(parents=True, exist_ok=True)
        member.write_bytes(data)
        member.chmod(mode)


def validate_app_signatures(directory, manifest):
    """Check both macOS architectures, not only the one this host can execute.

    Legacy archive-only checks remain readable, but a normal macOS run must
    catch their unsealed/unsigned App defect before invoking any executable.
    """
    checked = 0
    with tempfile.TemporaryDirectory(prefix="ferry-dock-app-signatures-") as temporary:
        for artifact in manifest["artifacts"]:
            if artifact.get("kind") != "app":
                continue
            destination = Path(temporary) / artifact["goarch"]
            write_entries(destination, members(directory / artifact["file"]))
            strict_bundle_check(destination / "Ferry Dock.app")
            checked += 1
    if checked:
        print("PASS PACKAGE_SIGNATURE: {} complete App bundles reconstructed from ZIPs passed codesign --verify --deep --strict; publisher trust/notarization is not implied.".format(checked))


def process_matches(pid, executable):
    """Inspect only a PID from this test's private control state before signaling."""
    if pid < 1:
        return False
    if sys.platform == "darwin":
        library = ctypes.CDLL("/usr/lib/libproc.dylib", use_errno=True)
        buffer = ctypes.create_string_buffer(4096)
        count = library.proc_pidpath(pid, buffer, len(buffer))
        return count > 0 and os.fsdecode(buffer.value) == str(executable.resolve())
    if sys.platform.startswith("linux"):
        try:
            return Path("/proc/{}/exe".format(pid)).resolve() == executable.resolve()
        except OSError:
            return False
    if sys.platform == "win32":
        # Never truncate a 64-bit process HANDLE through ctypes' default int
        # restype. Query only the PID named by this test's private state.
        from ctypes import wintypes
        library = ctypes.WinDLL("kernel32", use_last_error=True)
        library.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        library.OpenProcess.restype = wintypes.HANDLE
        library.CloseHandle.argtypes = [wintypes.HANDLE]
        library.CloseHandle.restype = wintypes.BOOL
        library.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD,
                                                       wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
        library.QueryFullProcessImageNameW.restype = wintypes.BOOL
        library.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        library.GetExitCodeProcess.restype = wintypes.BOOL
        handle = library.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        try:
            status = wintypes.DWORD()
            if not library.GetExitCodeProcess(handle, ctypes.byref(status)) or status.value != 259:
                return False
            size = wintypes.DWORD(32768)
            buffer = ctypes.create_unicode_buffer(size.value)
            return (bool(library.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)))
                    and os.path.normcase(os.path.realpath(buffer.value)) == os.path.normcase(str(executable.resolve())))
        finally:
            library.CloseHandle(handle)
    return False


class NativeCheck:
    def __init__(self, manifest, selected, timeout):
        self.manifest, self.selected = manifest, selected
        self.deadline = time.monotonic() + timeout
        self.instances = []
        self.state_directories = []
        self.cleanup_uncertain = False
        self.base = Path(tempfile.mkdtemp(prefix="ferry-dock-package-smoke-"))
        self.home = self.base / "private home"
        self.home.mkdir(mode=0o700)
        self.env = os.environ.copy()
        self.env.update({"HOME": str(self.home), "PATH": "/nonexistent", "TMPDIR": str(self.base)})
        if os.name == "nt":
            self.env.update({"USERPROFILE": str(self.home), "LOCALAPPDATA": str(self.home / "Local"),
                             "TEMP": str(self.base), "TMP": str(self.base)})
        self.binary = None
        self.default_mode = None

    def remaining(self, maximum):
        value = min(maximum, self.deadline - time.monotonic())
        check(value > 0, "native package smoke exceeded its overall deadline")
        return value

    def execute(self, binary, arguments, success=True):
        with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
            child = subprocess.Popen([str(binary)] + arguments, cwd=str(binary.parent), env=self.env,
                                     stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr)
            try:
                child.wait(timeout=self.remaining(10))
            except BaseException:
                # A desktop launcher owns a newly detached child until ready.
                # Give its signal context/defer time to stop that child before
                # resorting to KILL, which could strand unpublished state.
                try:
                    child.terminate()
                except ProcessLookupError:
                    pass
                try:
                    child.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    if arguments and (arguments[0] == "desktop" or
                                      (binary == self.binary and arguments[0] == "--no-open")):
                        self.cleanup_uncertain = True
                    child.kill()
                    child.wait(timeout=2)
                raise
            stdout.seek(0)
            data = stdout.read(MAX_RESPONSE_BYTES + 1)
            stderr.seek(0, os.SEEK_END)
            check(len(data) <= MAX_RESPONSE_BYTES and stderr.tell() <= MAX_RESPONSE_BYTES, "packaged command exceeded its output byte bound")
            operation = arguments[0] if arguments and arguments[0] in ("version", "--version", "desktop", "request", "--no-open") else "command"
            if operation == "request" and len(arguments) > 1 and arguments[1] in ("create", "status", "wait", "read", "cancel"):
                operation += " " + arguments[1]
            check((child.returncode == 0) == success,
                  "packaged {} returned unexpected exit status {}".format(operation, child.returncode))
            return json.loads(data) if data and success else None

    def state_path(self, name):
        directory = self.base / name
        self.state_directories.append(directory)
        return directory

    def read_state(self, directory):
        path = directory / "control.json"
        check(path.is_file() and path.stat().st_size <= 4096, "desktop did not publish bounded control state")
        if os.name != "nt":
            check(directory.stat().st_mode & 0o077 == 0 and path.stat().st_mode & 0o077 == 0,
                  "desktop runtime directory/control file is not private")
        state = json.loads(path.read_bytes())
        origin = urlsplit(state.get("serverUrl", ""))
        check(state.get("schemaVersion") == 1 and origin.scheme == "http" and origin.hostname == "127.0.0.1"
              and origin.port and origin.path == "" and not origin.query and not origin.fragment
              and origin.username is None and isinstance(state.get("ownerToken"), str) and len(state["ownerToken"]) >= 32
              and isinstance(state.get("instanceId"), str) and len(state["instanceId"]) >= 32
              and isinstance(state.get("pid"), int) and state["pid"] > 0, "desktop control schema/capability/origin is invalid")
        check(process_matches(state["pid"], self.binary), "desktop state does not name the packaged executable owned by this test")
        return state

    def request(self, state, route, method="GET", authorized=True, timeout=None, payload=None, token=None):
        origin = urlsplit(state["serverUrl"])
        check(origin.scheme == "http" and origin.hostname == "127.0.0.1" and origin.port,
              "test refused an HTTP target outside numeric loopback")
        connection = http.client.HTTPConnection("127.0.0.1", origin.port, timeout=timeout or self.remaining(2))
        try:
            headers = {"Origin": state["serverUrl"]}
            if authorized:
                headers["Authorization"] = "Bearer " + (token or state["ownerToken"])
            body = json.dumps(payload if payload is not None else {}).encode("utf-8") if method == "POST" else None
            if body is not None:
                headers["Content-Type"] = "application/json"
            connection.request(method, route, body=body, headers=headers)
            response = connection.getresponse()
            data = response.read(MAX_RESPONSE_BYTES + 1)
            check(len(data) <= MAX_RESPONSE_BYTES, "desktop HTTP response exceeded its byte bound")
            return response.status, json.loads(data) if data else None
        finally:
            connection.close()

    def launch(self, directory, port="127.0.0.1:0", success=True):
        # The app build must dispatch flags to its desktop default. An explicit
        # `desktop` subcommand would not exercise this packaged entry point.
        prefix = [] if self.default_mode == "desktop" else ["desktop"]
        return self.execute(self.binary, prefix + ["--no-open", "--state-dir", str(directory), "--listen", port], success)

    def wait_stopped(self, state, directory, timeout=6):
        deadline = time.monotonic() + min(timeout, self.remaining(timeout))
        while process_matches(state["pid"], self.binary) or (directory / "control.json").exists():
            check(time.monotonic() < deadline, "owned desktop process/control file did not stop within the cleanup deadline")
            time.sleep(0.025)

    def quit(self, state, directory):
        status, _ = self.request(state, "/api/desktop/quit", "POST")
        check(status == 202, "authenticated desktop quit did not return 202")
        self.wait_stopped(state, directory)

    def run(self):
        binaries = {}
        for kind, (artifact, entries) in self.selected.items():
            destination = self.base / "解压 渡口 package" / kind
            write_entries(destination, entries)
            if kind == "app":
                strict_bundle_check(destination / "Ferry Dock.app")
            binary = destination / artifact["binary"]["path"]
            version = self.execute(binary, ["version"])
            check(version == {"version": self.manifest["version"], "commit": self.manifest["source"]["binaryCommit"],
                              "os": artifact["goos"], "arch": artifact["goarch"], "defaultMode": artifact["defaultMode"]},
                  "native packaged version metadata differs from manifest")
            check(self.execute(binary, ["--version"]) == version, "--version and version disagree")
            binaries[kind] = binary
        check("cli" in binaries, "native validation requires this host's CLI archive")
        self.binary = binaries["cli"]
        self.default_mode = "serve"
        directory = self.state_path("桌面 state")
        self.launch(directory)
        first = self.read_state(directory)
        self.instances.append((first, directory))
        code, identity = self.request(first, "/api/desktop")
        check(code == 200 and identity.get("desktop") is True and identity.get("instanceId") == first["instanceId"]
              and identity.get("publicUrl") == first["serverUrl"], "desktop identity/readiness differs from the owned state")
        check(self.request(first, "/api/desktop", authorized=False)[0] == 401
              and self.request(first, "/api/desktop/quit", "POST", authorized=False)[0] == 401,
              "desktop control accepted an unauthenticated request")
        handle = self.base / "private request.json"
        created = self.execute(binaries["cli"], ["request", "create", "--control", str(directory / "control.json"),
                               "--task-id", "package-smoke", "--prompt", "Synthetic package smoke input", "--handle", str(handle)])
        check(created.get("request", {}).get("taskId") == "package-smoke", "packaged CLI cannot use desktop control state")
        self.transfer_scenario(first, binaries["cli"], created, handle, directory)
        canceled = self.execute(binaries["cli"], ["request", "cancel", "--handle", str(handle)])
        check(canceled.get("state") == "canceled", "packaged CLI could not cancel its synthetic request")
        if "app" in binaries:
            # App/CLI builds differ in default command only, and must share an
            # equal-version service without replacing or ending it.
            self.execute(binaries["app"], ["--no-open", "--state-dir", str(directory), "--listen", "127.0.0.1:0"])
            check(self.read_state(directory) == first, "same-version App could not reuse CLI desktop service")
        self.launch(directory)
        reused = self.read_state(directory)
        check(reused == first, "repeated launcher did not reuse the same verified desktop instance")
        self.quit(first, directory)
        private_write(directory / "control.json", json.dumps(first).encode())
        self.launch(directory)
        second = self.read_state(directory)
        self.instances.append((second, directory))
        check(second["instanceId"] != first["instanceId"], "stale private state reused an ended instance")
        self.quit(second, directory)
        check(not (directory / "launch.lock").exists(), "desktop startup lock remained after successful launch")
        print("PASS PACKAGE_NATIVE: packaged CLI, Chinese/space path + isolated home + PATH=/nonexistent, version metadata, readiness, request/ordinary transfer, reuse, quit, and stale recovery.")
        if "app" in binaries:
            self.binary, self.default_mode = binaries["app"], "desktop"
            app_directory = self.state_path("App default startup")
            self.launch(app_directory)
            app_state = self.read_state(app_directory)
            self.instances.append((app_state, app_directory, self.binary))
            self.quit(app_state, app_directory)
            self.binary, self.default_mode = binaries["cli"], "serve"
            print("PASS PACKAGE_APP_NATIVE: optional macOS App flags dispatch to desktop mode; same-version App/CLI service reuse works.")
        self.unknown_service(first)

    def transfer_scenario(self, state, binary, created, handle, directory):
        def command(operation, path=handle, *options):
            return self.execute(binary, ["request", operation, "--handle", str(path), *options])

        pending = command("wait", handle, "--timeout", "10ms")
        check(pending.get("timedOut") is True and pending.get("request", {}).get("state") == "pending"
              and command("status").get("state") == "pending", "bounded native wait timeout canceled its request")
        other_handle = self.base / "第二 task.json"
        second = self.execute(binary, ["request", "create", "--control", str(directory / "control.json"),
                              "--task-id", "independent-package-task", "--prompt", "Synthetic second task", "--handle", str(other_handle)])
        fragment = parse_qs(urlsplit(created["sendUrl"]).fragment)
        sender, identifier = fragment["key"][0], fragment["request"][0]
        feedback = "  客户意见: add a pilot.\nquotes ' \" $HOME ; & | are data. 👋  "
        payload = {"idempotencyKey": "native-package-once", "text": feedback}
        route = "/api/requests/" + identifier
        status, receipt = self.request(state, route + "/input", "POST", payload=payload, token=sender)
        check(status == 201, "native request synthetic phone submission failed")
        status, duplicate = self.request(state, route + "/input", "POST", payload=payload, token=sender)
        check(status == 200 and duplicate.get("id") == receipt.get("id"), "native idempotent retry duplicated a receipt")
        check(self.request(state, "/api/requests/" + second["request"]["requestId"] + "/input", "POST",
                           payload=payload, token=sender)[0] == 401,
              "native request A sender was allowed to submit to request B")
        check(self.request(state, route + "/result", token=sender)[0] == 401,
              "native request sender gained result reading authority")
        waited = command("wait", handle, "--timeout", "1s")
        read, repeated = command("read"), command("read")
        check(waited.get("request", {}).get("state") == "received" and not waited.get("timedOut")
              and read.get("input", {}).get("text") == feedback
              and read.get("input", {}).get("trust") == "untrusted_user_input"
              and read["input"]["id"] == repeated.get("input", {}).get("id") == receipt.get("id"),
              "native wait/read changed exact untrusted input or its repeatable receipt")
        check(command("read", other_handle).get("input") is None, "native second task received request A input")
        check(command("cancel", other_handle).get("state") == "canceled", "native second task could not cancel")
        short_handle = self.base / "short request.json"
        short = self.execute(binary, ["request", "create", "--control", str(directory / "control.json"),
                             "--task-id", "expiry", "--prompt", "Synthetic expiry", "--ttl", "1s", "--handle", str(short_handle)])
        check(command("wait", short_handle, "--timeout", "2s").get("request", {}).get("state") == "expired",
              "native request did not expire during bounded wait")
        check(short["request"]["requestId"] != identifier, "native request IDs collided")
        status, session = self.request(state, "/api/sessions", "POST")
        check(status == 201, "ordinary session cannot be created by native package")
        ordinary_sender = parse_qs(urlsplit(session["sendUrl"]).fragment)["key"][0]
        ordinary_route = "/api/sessions/" + session["id"]
        check(self.request(state, ordinary_route + "/messages", "POST", token=ordinary_sender, payload=payload)[0] == 201,
              "ordinary text could not be submitted to native package")
        status, inbox = self.request(state, ordinary_route)
        check(status == 200 and inbox.get("messages", [{}])[0].get("text") == feedback,
              "ordinary native inbox changed Unicode/whitespace text")

    def unknown_service(self, ended_state):
        class Sentinel(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'{"sentinel":true}')
            def log_message(self, *args):
                pass
        server = ThreadingHTTPServer(("127.0.0.1", 0), Sentinel)
        server.daemon_threads = True
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        thread.start()
        try:
            origin = "http://127.0.0.1:{}".format(server.server_port)
            unknown = {**ended_state, "serverUrl": origin}
            blocked = self.state_path("occupied port")
            self.launch(blocked, "127.0.0.1:{}".format(server.server_port), success=False)
            check(not (blocked / "control.json").exists(), "failed occupied-port launch left control state")
            directory = self.state_path("unknown recorded service")
            directory.mkdir(mode=0o700)
            data = json.dumps(unknown).encode()
            private_write(directory / "control.json", data)
            self.launch(directory, success=False)
            check((directory / "control.json").read_bytes() == data, "unknown recorded service caused state to be deleted or replaced")
            status, body = self.request(unknown, "/sentinel", authorized=False)
            check(status == 200 and body == {"sentinel": True}, "unknown service was changed or stopped")
            print("PASS PACKAGE_SAFETY: explicit occupied port fails without taking it over; unknown recorded service and private state remain untouched.")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=1)

    def cleanup(self):
        # Only signal a recorded PID after its executable matches this test's
        # unique extracted app path. Never inspect or stop unrelated services.
        failures = []
        if self.binary is not None:
            candidates = {entry[0]["pid"]: (entry[0], entry[2] if len(entry) > 2 else self.binary) for entry in self.instances}
            for directory in self.state_directories:
                try:
                    value = json.loads((directory / "control.json").read_bytes())
                    if isinstance(value.get("pid"), int):
                        if value["pid"] not in candidates:
                            candidates[value["pid"]] = (value, self.binary)
                except (OSError, ValueError, TypeError):
                    pass
            for pid, (state, binary) in candidates.items():
                if not process_matches(pid, binary):
                    continue
                try:
                    self.request(state, "/api/desktop/quit", "POST", timeout=0.5)
                except Exception:
                    pass
                deadline = time.monotonic() + 2
                while process_matches(pid, binary) and time.monotonic() < deadline:
                    time.sleep(0.025)
                signals = (signal.SIGTERM,) if os.name == "nt" else (signal.SIGTERM, signal.SIGKILL)
                for requested_signal in signals:
                    if not process_matches(pid, binary):
                        break
                    try:
                        os.kill(pid, requested_signal)
                    except ProcessLookupError:
                        break
                    deadline = time.monotonic() + 2
                    while process_matches(pid, binary) and time.monotonic() < deadline:
                        time.sleep(0.025)
                if process_matches(pid, binary):
                    failures.append(pid)
        check(not failures, "a verified owned package process remained alive after bounded cleanup")
        check(not self.cleanup_uncertain,
              "force-killed launcher background cleanup could not be confirmed; private temporary files retained")
        shutil.rmtree(self.base)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", type=Path, required=True, help="version directory containing manifest.json and SHA256SUMS")
    parser.add_argument("--require-all", action="store_true", help="require all six CLI and two app archives")
    parser.add_argument("--require-cli-targets", action="store_true", help="require all six native CLI archives; macOS Apps are optional")
    parser.add_argument("--native-target", choices=sorted("/".join(target[:2]) for target in CLI_TARGETS),
                        help="expected actual runner OS/architecture; refuses a different native host")
    parser.add_argument("--archive-only", action="store_true", help="check archive metadata only; skip complete app signature and native lifecycle checks explicitly")
    parser.add_argument("--timeout", type=float, default=60, help="native scenario deadline in seconds, excluding bounded cleanup")
    parser.add_argument("--receipt", type=Path, help="optional capability-free JSON validation receipt")
    args = parser.parse_args()
    check(1 <= args.timeout <= 300, "timeout must be between 1 and 300 seconds")
    observed = host_target()
    expected = tuple(args.native_target.split("/")) if args.native_target else observed
    if not args.archive_only:
        check(expected == observed, "requested native target differs from this runner's actual OS/CPU")
    manifest, selected = validate_archives(args.dist.resolve(), args.require_all, args.require_cli_targets, expected)
    has_apps = any(item.get("kind") == "app" for item in manifest["artifacts"])
    if args.archive_only:
        print("NOT_RUN: complete App codesign verification and native lifecycle (--archive-only).")
    else:
        if has_apps and sys.platform == "darwin":
            validate_app_signatures(args.dist.resolve(), manifest)
        elif has_apps:
            print("NOT_RUN: optional macOS App strict signature verification on this non-macOS runner.")
        native = NativeCheck(manifest, selected, args.timeout)
        try:
            native.run()
        finally:
            native.cleanup()
        print("PASS PACKAGE_CLEANUP: verified owned processes stopped; private extracted/runtime files removed.")
    if os.name == "nt" and not args.archive_only:
        print("NOT_RUN: Windows ACL privacy audit and console Ctrl+C; TerminateProcess cleanup is not graceful signal validation.")
    print("NOT_RUN: Finder double-click, browser rendering, real phone/LAN, downloaded Gatekeeper/SmartScreen acceptance, notarization, and native runtimes other than this runner's target.")
    print("NOT_RUN: zero-argument Finder app launch and OS-default cache-directory discovery; lifecycle uses app --no-open --state-dir.")
    if args.receipt:
        receipt = {"schemaVersion": 1, "status": "PASS_ARCHIVE_ONLY" if args.archive_only else "PASS_NATIVE",
                   "version": manifest["version"], "source": manifest["source"],
                   "manifestSha256": sha((args.dist / "manifest.json").read_bytes()),
                   "host": {"os": observed[0], "arch": observed[1], "python": platform.python_version()},
                   "nativeTarget": None if args.archive_only else "/".join(expected),
                   "archiveCount": len(manifest["artifacts"]), "checks": len(CHECKS),
                   "requiredCliTargets": args.require_cli_targets,
                   "nativeLifecycle": "NOT_RUN" if args.archive_only else "PASS",
                   "nativeAppSignature": "PASS" if has_apps and not args.archive_only and sys.platform == "darwin" else "NOT_RUN",
                   "notRun": ["actual phone/LAN/QR/clipboard/browser", "actual Codex host", "downloaded OS trust/first launch",
                              "minimum upstream OS versions", "OS-default runtime directory", "other OS/CPU native execution"],
                   "windowsAclAudit": "NOT_RUN", "windowsConsoleCtrlC": "NOT_RUN"}
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("Local archives only: no installation, global Agent configuration, security-setting change, or publication occurred.")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("FAIL PACKAGE: " + (str(error) if isinstance(error, Failure) else type(error).__name__ + " (details withheld to protect capability data)"), file=sys.stderr)
        sys.exit(1)
