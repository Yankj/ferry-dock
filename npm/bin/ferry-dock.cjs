#!/usr/bin/env node
"use strict";

// Distribution only: no install hooks, shell commands or runtime downloads.
const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");
const { spawn } = require("node:child_process");
const { constants } = require("node:os");

function fail(message, code = 1) {
  process.stderr.write(`Ferry Dock: ${message}\n`);
  process.exitCode = code;
}
function jsonFile(file, limit = 16384) {
  const info = fs.lstatSync(file);
  if (!info.isFile() || info.size > limit) throw new Error("invalid_metadata");
  return JSON.parse(fs.readFileSync(file, "utf8"));
}
function main() {
  const major = Number(process.versions.node.split(".")[0]);
  if (!Number.isInteger(major) || major < 22) {
    fail("the npm entry requires Node.js 22 or newer; use a supported Node LTS or the native CLI download.");
    return;
  }
  const target = `${process.platform}-${process.arch}`;
  if (!["darwin-arm64", "darwin-x64", "linux-arm64", "linux-x64", "win32-arm64", "win32-x64"].includes(target)) {
    fail(`unsupported platform ${target}; no binary will be downloaded. Use a supported native CLI build.`);
    return;
  }
  let binary;
  try {
    const root = path.resolve(__dirname, "..");
    const own = jsonFile(path.join(root, "package.json"));
    const metadata = jsonFile(path.join(root, "core.json"));
    const expected = metadata.platforms && metadata.platforms[target];
    if (metadata.schemaVersion !== 2 || metadata.version !== own.version || !expected ||
        own.optionalDependencies?.[expected.packageName] !== own.version ||
        !/^(?:@[a-z0-9][a-z0-9._-]*\/)?[a-z0-9][a-z0-9._-]*$/.test(expected.packageName || "") ||
        !/^[a-f0-9]{64}$/.test(expected.binarySha256 || "") ||
        !Number.isSafeInteger(expected.binarySize) || expected.binarySize < 1 || expected.binarySize > 32 * 1024 * 1024) {
      throw new Error("invalid_metadata");
    }
    let packagePath;
    try { packagePath = require.resolve(`${expected.packageName}/package.json`); }
    catch (error) {
      if (error.code === "MODULE_NOT_FOUND") {
        fail(`required platform package ${expected.packageName}@${own.version} is missing. Reinstall the same version with optional dependencies enabled (not --omit=optional). For offline local installation, supply both the entry and matching platform tarballs. No fallback download was attempted.`, 127);
        return;
      }
      throw error;
    }
    const installed = jsonFile(packagePath);
    const nativeRoot = path.dirname(packagePath);
    const actual = jsonFile(path.join(nativeRoot, "core.json"));
    if (installed.name !== expected.packageName || installed.version !== own.version ||
        actual.schemaVersion !== 2 || actual.version !== own.version || actual.target !== target ||
        actual.binarySha256 !== expected.binarySha256 || actual.binarySize !== expected.binarySize ||
        actual.commit !== metadata.commit || actual.manifestSha256 !== metadata.manifestSha256) {
      throw new Error("wrong_version");
    }
    binary = path.join(nativeRoot, "native", process.platform === "win32" ? "ferry-dock.exe" : "ferry-dock");
    const info = fs.lstatSync(binary);
    if (!info.isFile() || info.size !== expected.binarySize) throw new Error("invalid_executable");
    if (process.platform !== "win32") fs.accessSync(binary, fs.constants.X_OK);
    const digest = crypto.createHash("sha256").update(fs.readFileSync(binary)).digest("hex");
    if (digest !== expected.binarySha256) throw new Error("checksum_mismatch");
  } catch (error) {
    if (error.code === "ENOENT") fail("platform executable or metadata is missing; reinstall this exact package version.", 127);
    else if (error.code === "EACCES") fail("platform executable is not accessible or executable.", 126);
    else if (error.message === "wrong_version") fail("platform package identity/version does not match the entry; reinstall both at the same exact version.");
    else if (error.message === "checksum_mismatch") fail("platform executable checksum mismatch; reinstall this exact package version.");
    else fail("platform executable verification failed; reinstall this exact package version.");
    return;
  }
  const supplied = process.argv.slice(2);
  const args = supplied.length ? supplied : ["desktop"];
  const windows = process.platform === "win32";
  // POSIX: separate process group, forwarding only to our known child. Windows:
  // share the console so terminal Ctrl+C reaches Go directly; child.kill(SIGINT)
  // on Windows would force terminate rather than request graceful cancellation.
  const child = spawn(binary, args, { shell: false, stdio: "inherit", detached: !windows, windowsHide: true });
  const handlers = new Map();
  let finished = false;
  for (const signal of (windows ? ["SIGINT", "SIGBREAK"] : ["SIGINT", "SIGTERM", "SIGHUP"])) {
    const handler = () => {
      if (!windows && !finished && child.pid && child.exitCode === null && child.signalCode === null) {
        try { child.kill(signal); } catch { /* Only this known child; it may already have exited. */ }
      }
    };
    handlers.set(signal, handler);
    process.on(signal, handler);
  }
  function cleanup() {
    finished = true;
    for (const [signal, handler] of handlers) process.removeListener(signal, handler);
  }
  child.once("error", (error) => {
    cleanup();
    fail("could not start the verified platform executable.", error.code === "ENOENT" ? 127 : error.code === "EACCES" ? 126 : 1);
  });
  child.once("close", (code, signal) => {
    if (finished) return;
    cleanup();
    if (Number.isInteger(code)) process.exitCode = code;
    else if (signal && constants.signals[signal]) {
      process.exitCode = 128 + constants.signals[signal];
      if (!windows) {
        try { process.kill(process.pid, signal); } catch { /* Conventional numeric fallback. */ }
      }
    } else process.exitCode = 1;
  });
}
main();
