#!/usr/bin/env node
"use strict";

// npm is a distribution/entry layer. All transfer and desktop lifecycle logic
// remains in the pinned native executable; there are no install hooks/downloads.
const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");
const { spawn } = require("node:child_process");
const { constants } = require("node:os");

function fail(message, code = 1) {
  process.stderr.write(`Ferry Dock: ${message}\n`);
  process.exitCode = code;
}

function main() {
  const major = Number(process.versions.node.split(".")[0]);
  if (!Number.isInteger(major) || major < 22) {
    fail("the npm entry requires Node.js 22 or newer; use a supported Node LTS or the native CLI download.");
    return;
  }
  if (process.platform !== "darwin" || process.arch !== "arm64") {
    fail("this npm preview supports macOS Apple Silicon with arm64 Node.js only. No other binary is downloaded.");
    return;
  }

  const root = path.resolve(__dirname, "..");
  const binary = path.join(root, "native", "ferry-dock");
  try {
    const metadataPath = path.join(root, "core.json");
    const metadataInfo = fs.lstatSync(metadataPath);
    if (!metadataInfo.isFile() || metadataInfo.size > 8192) throw new Error("invalid bundled metadata");
    const metadata = JSON.parse(fs.readFileSync(metadataPath, "utf8"));
    if (metadata.schemaVersion !== 1 || metadata.os !== "darwin" || metadata.arch !== "arm64" ||
        !/^[a-f0-9]{64}$/.test(metadata.binarySha256 || "") ||
        !Number.isSafeInteger(metadata.binarySize) || metadata.binarySize < 1 || metadata.binarySize > 32 * 1024 * 1024) throw new Error("invalid bundled metadata");
    const info = fs.lstatSync(binary);
    if (!info.isFile() || info.size !== metadata.binarySize) throw new Error("the bundled executable is not a regular file of the expected size");
    fs.accessSync(binary, fs.constants.X_OK);
    const digest = crypto.createHash("sha256").update(fs.readFileSync(binary)).digest("hex");
    if (digest !== metadata.binarySha256) throw new Error("bundled executable checksum mismatch");
  } catch (error) {
    if (error.code === "ENOENT") fail("the bundled executable or metadata is missing; reinstall this exact package version.", 127);
    else if (error.code === "EACCES") fail("the bundled executable is not accessible or executable.", 126);
    else fail(error.message === "bundled executable checksum mismatch" ? error.message : "bundled executable verification failed.");
    return;
  }

  const supplied = process.argv.slice(2);
  const args = supplied.length ? supplied : ["desktop"];
  if (args[0] === "desktop" && !args.includes("--help") && !args.includes("-help") && !args.includes("-h")) {
    process.stderr.write("Ferry Dock: may reuse an existing service; the bundled version does not verify its version. Do not quit shared tasks to upgrade.\n");
  }

  // A separate POSIX process group keeps the native child out of the wrapper's
  // terminal signal group. We forward received signals to that known child.
  // This is still a waited
  // foreground command with inherited I/O, not another background service.
  const child = spawn(binary, args, { shell: false, stdio: "inherit", detached: true });
  const signals = ["SIGINT", "SIGTERM", "SIGHUP"];
  const handlers = new Map();
  let finished = false;
  for (const signal of signals) {
    const handler = () => {
      if (!finished && child.pid && child.exitCode === null && child.signalCode === null) {
        try { child.kill(signal); } catch { /* The known child may have exited. */ }
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
    fail("could not start the bundled executable.", error.code === "ENOENT" ? 127 : error.code === "EACCES" ? 126 : 1);
  });
  child.once("close", (code, signal) => {
    if (finished) return;
    cleanup();
    if (Number.isInteger(code)) {
      process.exitCode = code;
    } else if (signal && constants.signals[signal]) {
      // Preserve signal termination after removing our forwarding handlers.
      process.exitCode = 128 + constants.signals[signal];
      try { process.kill(process.pid, signal); } catch { /* Keep the conventional numeric fallback. */ }
    } else {
      process.exitCode = 1;
    }
  });
}

main();
