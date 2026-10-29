"use strict";
// VM-only checks. They do not execute another platform or emulate its kernel.
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");
const ENTRY = path.resolve("vm-entry");
const NATIVE = path.resolve("vm-native");
const crypto = require("node:crypto");
const source = fs.readFileSync(process.argv[2] || require("node:path").join(__dirname, "bin/ferry-dock.cjs"), "utf8");
const binary = Buffer.from("fake");
const hash = crypto.createHash("sha256").update(binary).digest("hex");
const targets = ["darwin-arm64", "darwin-x64", "linux-arm64", "linux-x64", "win32-arm64", "win32-x64"];
const version = "0.1.0-alpha.4";
function inspect(target, {oldNode = false, missing = false, mismatch = false, args = []} = {}) {
  const [platform, arch] = target.split("-");
  const name = "ferry-dock-" + target;
  const root = {version, optionalDependencies: {[name]: version}};
  const core = {schemaVersion: 2, version, commit: "a".repeat(40), manifestSha256: "b".repeat(64),
    platforms: {[target]: {packageName: name, binarySize: binary.length, binarySha256: hash}}};
  const native = {schemaVersion: 2, version, target, commit: core.commit, manifestSha256: core.manifestSha256,
    binarySize: binary.length, binarySha256: hash};
  const contents = new Map([
    [path.join(ENTRY, "package.json"), JSON.stringify(root)], [path.join(ENTRY, "core.json"), JSON.stringify(core)],
    [path.join(NATIVE, "package.json"), JSON.stringify({name, version: mismatch ? "0.0.0" : version})],
    [path.join(NATIVE, "core.json"), JSON.stringify(native)],
  ]);
  let spawned = null, stderr = "";
  const stop = new Error("expected VM stop");
  const fake = Object.create(process);
  Object.defineProperties(fake, {
    platform: {value: platform}, arch: {value: arch}, versions: {value: {node: oldNode ? "18.0.0" : "22.17.1"}},
    argv: {value: [process.execPath, "/entry/bin/ferry-dock.cjs", ...args]},
    stderr: {value: {write(s) { stderr += s; }}}, stdout: {value: {write() { throw new Error("stdout contamination"); }}},
    exitCode: {value: undefined, writable: true}, on: {value() { return fake; }}, removeListener: {value() { return fake; }}
  });
  const fakeFS = {
    constants: fs.constants,
    lstatSync(file) { return {isFile: () => true, size: contents.has(file) ? Buffer.byteLength(contents.get(file)) : binary.length}; },
    readFileSync(file, encoding) { if (contents.has(file)) return contents.get(file); return encoding ? binary.toString() : binary; },
    accessSync() {}
  };
  function load(name) {
    if (name === "node:fs") return fakeFS;
    if (name === "node:child_process") return {spawn(file, argv, options) { spawned = {file, argv, options}; throw stop; }};
    return require(name);
  }
  load.resolve = () => { if (missing) { const e = new Error("missing"); e.code = "MODULE_NOT_FOUND"; throw e; } return path.join(NATIVE, "package.json"); };
  try { vm.runInNewContext(source, {require: load, process: fake, __dirname: path.join(ENTRY, "bin"), Buffer, console}); }
  catch (error) { if (error !== stop) throw error; }
  return {spawned, code: fake.exitCode, stderr};
}
for (const target of targets) {
  const result = inspect(target);
  if (!result.spawned || JSON.stringify(result.spawned.argv) !== '["desktop"]') throw new Error(target + " default dispatch");
  const options = result.spawned.options;
  if (options.shell !== false || options.stdio !== "inherit" || options.detached !== !target.startsWith("win32-") || options.windowsHide !== true) throw new Error(target + " spawn options");
  if (!result.spawned.file.endsWith(path.sep + (target.startsWith("win32-") ? "ferry-dock.exe" : "ferry-dock"))) throw new Error(target + " executable suffix");
  const args = ["request", "create", "--prompt", '中文 "quoted" $(never); `never`'];
  if (JSON.stringify(inspect(target, {args}).spawned.argv) !== JSON.stringify(args)) throw new Error(target + " literal argv");
  const missing = inspect(target, {missing: true});
  if (missing.spawned || missing.code !== 127 || !missing.stderr.includes("optional")) throw new Error(target + " missing optional package");
  const mismatch = inspect(target, {mismatch: true});
  if (mismatch.spawned || mismatch.code !== 1 || !mismatch.stderr.includes("version")) throw new Error(target + " exact version guard");
}
for (const state of [inspect("freebsd-x64"), inspect("linux-riscv64"), inspect("darwin-arm64", {oldNode: true})]) {
  if (state.spawned || state.code !== 1 || !state.stderr) throw new Error("unsupported platform/runtime guard");
}
process.stdout.write(JSON.stringify({scope: "VM_ONLY", targets: targets.length, noArgsToDesktop: true, literalArgv: true, noShell: true,
  missingOptionalDependency: true, exactVersionMismatch: true, unknownPlatform: true, nodeMinimum: true, windowsSharedConsole: true}) + "\n");
