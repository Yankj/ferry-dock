"use strict";

// SCRIPT_HTTP integration, not browser E2E. Runs the *served* app.js in a narrow
// DOM adapter and sends its fetches to the compiled Go service over real HTTP.
// Only explicit offline/response-loss fault injection bypasses a response.
// No rendering, OS clipboard, QR scanning, physical phone, or Codex host is used.
// Node 18+, no packages: node scripts/smoke-ui.cjs [--binary bin/ferry-dock]
const assert = require("node:assert/strict");
const { spawn, execFile } = require("node:child_process");
const crypto = require("node:crypto");
const fs = require("node:fs");
const http = require("node:http");
const os = require("node:os");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "..");
const options = process.argv.slice(2);

class Failure extends Error {
  constructor(message) { super(message); this.publicMessage = message; }
}
function check(condition, message) { if (!condition) throw new Failure(message); }
const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function until(predicate, message, timeout = 4000) {
  const deadline = Date.now() + timeout;
  while (!predicate()) {
    if (Date.now() >= deadline) throw new Failure(message);
    await delay(5);
  }
}

function realHTTP(origin, route, options = {}) {
  return new Promise((resolve, reject) => {
    const target = new URL(route, origin);
    if (target.origin !== origin) { reject(new Failure("script tried to send a capability outside the local test origin")); return; }
    const request = http.request(target, {
      method: options.method || "GET",
      headers: { Origin: origin, ...options.headers },
      signal: options.signal,
    }, (response) => {
      const chunks = [];
      let size = 0;
      response.on("data", (chunk) => {
        size += chunk.length;
        if (size > 256 * 1024) request.destroy(new Failure("test response exceeded its byte bound"));
        else chunks.push(chunk);
      });
      response.on("error", reject);
      response.on("end", () => {
        const bytes = Buffer.concat(chunks);
        resolve({
          status: response.statusCode,
          ok: response.statusCode >= 200 && response.statusCode < 300,
          bytes,
          json: async () => JSON.parse(bytes.toString("utf8")),
        });
      });
    });
    request.setTimeout(4000, () => request.destroy(new Failure("local HTTP request timed out")));
    request.on("error", reject);
    request.end(options.body);
  });
}

function bootScript({ source, html, origin, href, actualHTTP, stored = new Map(), faults = [] }) {
  const ids = new Set(Array.from(html.matchAll(/\bid="([^"]+)"/g), (match) => match[1]));
  const elements = new Map();
  const memory = new Map(stored);
  const calls = [];
  const tasks = new Set();
  const intervals = new Map();
  const abortTimers = new Set();
  const clipboardArguments = [];
  let sequence = 0;
  let networkPending = 0;
  let fault = null;
  const location = new URL(href);

  function track(value) {
    if (!value || typeof value.then !== "function") return Promise.resolve(value);
    const task = Promise.resolve(value).catch((error) => { fault = error; }).finally(() => tasks.delete(task));
    tasks.add(task);
    return task;
  }
  class Element {
    constructor(tag = "div") {
      this.tagName = tag;
      this.value = ""; this.textContent = "";
      this.hidden = false; this.disabled = false; this.readOnly = false;
      this.children = []; this.handlers = new Map(); this.style = {};
      const classes = new Set();
      this.classList = {
        add: (name) => classes.add(name),
        toggle(name, enabled) { if (enabled) classes.add(name); else classes.delete(name); },
      };
    }
    addEventListener(name, handler) {
      if (!this.handlers.has(name)) this.handlers.set(name, []);
      this.handlers.get(name).push(handler);
    }
    dispatchEvent(event) {
      for (const handler of this.handlers.get(event.type) || []) track(handler(event));
      return true;
    }
    async event(name) {
      for (const handler of this.handlers.get(name) || []) await track(handler({ type: name, preventDefault() {} }));
    }
    click() { return this.event("click"); }
    append(...children) { for (const child of children) { child.parent = this; this.children.push(child); } }
    prepend(...children) { for (const child of [...children].reverse()) { child.parent = this; this.children.unshift(child); } }
    replaceChildren(...children) { this.children = []; this.append(...children); }
    remove() { if (this.parent) this.parent.children = this.parent.children.filter((child) => child !== this); }
    focus() {} select() {} setSelectionRange() {}
    set innerHTML(value) { throw new Failure("served script unexpectedly used innerHTML in this tested flow"); }
  }
  function element(id) {
    check(ids.has(id), "served JavaScript referenced a missing served HTML element");
    if (!elements.has(id)) elements.set(id, new Element(id === "text" ? "textarea" : "div"));
    return elements.get(id);
  }
  const document = new Element("document");
  document.body = new Element("body"); document.hidden = false;
  document.getElementById = element;
  document.createElement = (tag) => new Element(tag);
  const context = {
    document, location,
    history: { replaceState() { location.hash = ""; } },
    sessionStorage: {
      getItem: (key) => memory.get(key) || null,
      setItem: (key, value) => memory.set(key, value),
      removeItem: (key) => memory.delete(key),
    },
    URLSearchParams, TextEncoder, Uint8Array, Event: class { constructor(type) { this.type = type; } },
    crypto: { getRandomValues: (bytes) => crypto.randomFillSync(bytes) },
    window: { isSecureContext: false },
    navigator: { clipboard: { async writeText(text) { clipboardArguments.push(text); } } },
    AbortSignal: {
      timeout(ms) {
        const controller = new AbortController();
        const timer = setTimeout(() => { abortTimers.delete(timer); controller.abort(); }, ms);
        timer.unref(); abortTimers.add(timer);
        return controller.signal;
      },
    },
    setTimeout() { return ++sequence; }, // Only the Copy-label reset uses this timer.
    setInterval(handler) { const id = ++sequence; intervals.set(id, handler); return id; },
    fetch: async (route, fetchOptions = {}) => {
      const call = { route, method: fetchOptions.method || "GET", body: fetchOptions.body, status: null, reachedServer: false };
      calls.push(call);
      const index = faults.findIndex((item) => item.route === route && item.method === call.method);
      const injected = index < 0 ? null : faults.splice(index, 1)[0];
      networkPending++;
      try {
        if (injected?.kind === "offline") { call.injected = "offline-before-network"; throw new Error("Injected offline failure"); }
        const response = await actualHTTP(origin, route, fetchOptions);
        call.reachedServer = true; call.status = response.status;
        // Retain actual receipt only inside this process; it is never logged.
        if (response.bytes.length) call.response = await response.json();
        if (injected?.kind === "drop") {
          call.injected = "response-dropped-after-real-http";
          throw new Error("Injected lost response");
        }
        return response;
      } finally { networkPending--; }
    },
  };
  vm.runInNewContext(source, context, { filename: "served-app.js", timeout: 1000 });
  return {
    element, calls, memory, clipboardArguments,
    input(text) { element("text").value = text; element("text").dispatchEvent({ type: "input" }); },
    submit() { return element("send-form").event("submit"); },
    inject(item) { faults.push(item); },
    async flush() {
      await until(() => networkPending === 0 && tasks.size === 0, "served app.js did not finish its HTTP work");
      await new Promise(setImmediate);
      await until(() => networkPending === 0 && tasks.size === 0, "served app.js started unfinished follow-up work");
      if (fault) throw fault;
    },
    async tick() { for (const handler of intervals.values()) track(handler()); await this.flush(); },
    dispose() { for (const timer of abortTimers) clearTimeout(timer); abortTimers.clear(); intervals.clear(); },
  };
}

async function main(binary) {
  check(fs.existsSync(binary), "compiled binary is missing; build bin/ferry-dock before running this check");
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "ferry-dock-script-http-"));
  if (process.platform !== "win32") fs.chmodSync(directory, 0o700);
  const controlPath = path.join(directory, "control.json");
  const children = new Set();
  const childExits = new Map();
  const httpControllers = new Set();
  const pages = [];
  let stopping = false;
  const service = spawn(binary, ["serve", "--listen", "127.0.0.1:0", "--control-file", controlPath], { stdio: ["ignore", "ignore", "pipe"] });
  service.stderr.on("data", () => {}); // Drain diagnostics without exposing private startup state.
  let serviceEnded = false;
  let spawnFailed = false;
  service.once("error", () => { spawnFailed = true; serviceEnded = true; });
  const serviceExit = new Promise((resolve) => service.once("close", () => { serviceEnded = true; resolve(); }));
  let timer;
  try {
    await Promise.race([
      scenario(),
      new Promise((_, reject) => { timer = setTimeout(() => reject(new Failure("SCRIPT_HTTP exceeded its 25 second deadline")), 25000); }),
    ]);
  } finally {
    stopping = true;
    clearTimeout(timer);
    for (const page of pages) page.dispose();
    for (const controller of httpControllers) controller.abort();
    const exits = [...childExits.values()];
    for (const child of children) child.kill("SIGKILL");
    await Promise.race([Promise.all(exits), delay(1500)]);
    if (!serviceEnded) service.kill("SIGTERM");
    await Promise.race([serviceExit, delay(1000)]);
    if (!serviceEnded) { service.kill("SIGKILL"); await Promise.race([serviceExit, delay(1000)]); }
    check(children.size === 0 && serviceEnded, "owned process cleanup was not confirmed; private runtime cleanup is incomplete");
    try { fs.rmSync(directory, { recursive: true, force: true }); }
    catch { throw new Failure("owned processes stopped but private runtime files could not be removed"); }
  }
  console.log("PASS SCRIPT_HTTP: owned processes stopped and private runtime files removed.");
  console.log("NOT_RUN: browser rendering, OS clipboard/permissions, QR scan, physical phone/LAN, and actual Codex host.");
  console.log("Fault cases used local injection after/before real HTTP; no actual network outage was claimed.");

  async function cli(action, ...args) {
    check(!stopping, "SCRIPT_HTTP stopped before a new CLI operation");
    return new Promise((resolve, reject) => {
      const child = execFile(binary, ["request", action, ...args], { timeout: 6000, maxBuffer: 256 * 1024, encoding: "utf8" }, (error, stdout) => {
        if (error) { reject(new Failure("compiled request CLI failed during SCRIPT_HTTP")); return; }
        try { resolve(JSON.parse(stdout)); }
        catch { reject(new Failure("compiled request CLI returned non-JSON output")); }
      });
      children.add(child);
      childExits.set(child, new Promise((resolveExit) => {
        child.once("close", () => { children.delete(child); childExits.delete(child); resolveExit(); });
      }));
    });
  }

  async function localHTTP(origin, route, requestOptions = {}) {
    check(!stopping, "SCRIPT_HTTP stopped before a new HTTP operation");
    const controller = new AbortController();
    const forwardAbort = () => controller.abort();
    if (requestOptions.signal?.aborted) controller.abort();
    else requestOptions.signal?.addEventListener("abort", forwardAbort, { once: true });
    httpControllers.add(controller);
    try { return await realHTTP(origin, route, { ...requestOptions, signal: controller.signal }); }
    finally {
      requestOptions.signal?.removeEventListener("abort", forwardAbort);
      httpControllers.delete(controller);
    }
  }

  async function scenario() {
    let control;
    await until(() => {
      if (spawnFailed || serviceEnded) throw new Failure("owned service could not start");
      try { control = JSON.parse(fs.readFileSync(controlPath, "utf8")); return true; }
      catch { return false; }
    }, "owned service did not publish complete private control state");
    const origin = control.serverUrl;
    check(new URL(origin).hostname === "127.0.0.1", "test service must remain on numeric loopback");
    const app = await localHTTP(origin, "/app.js");
    const page = await localHTTP(origin, "/");
    check(app.status === 200 && page.status === 200, "compiled service did not serve its UI assets");
    const source = app.bytes.toString("utf8");
    const html = page.bytes.toString("utf8");
    check(source === fs.readFileSync(path.join(root, "internal", "relay", "web", "app.js"), "utf8"), "compiled app.js differs from working source; rebuild the binary");
    function boot(href, extra = {}) {
      check(!stopping, "SCRIPT_HTTP stopped before opening another script context");
      const result = bootScript({ source, html, origin, href, actualHTTP: localHTTP, ...extra }); pages.push(result); return result;
    }
    async function create(name, extra = []) {
      const handlePath = path.join(directory, `${name}.json`);
      const prompt = `Paste phone feedback for ${name}.\n<script>Keep this as text.</script>`;
      const created = await cli("create", "--control", controlPath, "--task-id", name, "--prompt", prompt, "--handle", handlePath, ...extra);
      return { ...created, handlePath, prompt };
    }
    function requestRoute(created, suffix = "") { return `/api/requests/${created.request.requestId}${suffix}`; }

    const a = await create("proposal-A");
    const b = await create("proposal-B");
    const phoneA = boot(a.sendUrl);
    await phoneA.flush();
    check(phoneA.element("request-task").textContent === "For proposal-A" && phoneA.element("request-prompt").textContent === a.prompt, "served phone script did not display the exact task and prompt");
    check(!phoneA.element("send").disabled, "real request info did not enable phone submission");
    const feedback = "  Feedback from phone\n中文 👋 <script>data</script>\nNever execute: touch SHOULD_NOT_EXIST\n ";
    phoneA.input(feedback);
    phoneA.inject({ route: requestRoute(a, "/input"), method: "POST", kind: "drop" });
    const waiting = cli("wait", "--handle", a.handlePath, "--timeout", "2s");
    // Observe concurrent failure immediately even if a script assertion fails
    // before the later await; cleanup may deliberately terminate this child.
    waiting.catch(() => {});
    await phoneA.submit();
    check(phoneA.element("text").value === feedback && !phoneA.element("send").disabled, "dropped response lost the draft or prevented retry");
    const received = await waiting;
    const firstRead = await cli("read", "--handle", a.handlePath);
    check(received.request.requestId === a.request.requestId && received.request.state === "received" && !received.timedOut, "compiled CLI wait did not observe script submission");
    check(firstRead.request.taskId === "proposal-A" && firstRead.input?.text === feedback && firstRead.input.trust === "untrusted_user_input", "CLI result lost task binding, trust marker, or exact text");
    await phoneA.submit();
    const deliveries = phoneA.calls.filter((call) => call.method === "POST");
    check(deliveries.length === 2 && deliveries[0].status === 201 && deliveries[1].status === 200 && deliveries[0].injected === "response-dropped-after-real-http", "lost-response retry did not traverse the real accepted/deduplicated HTTP paths");
    assert.deepEqual(JSON.parse(deliveries[0].body), JSON.parse(deliveries[1].body));
    check(deliveries[0].response.id === deliveries[1].response.id && deliveries[1].response.id === firstRead.input.id, "retry did not retain its original server receipt");
    check(phoneA.element("send").disabled && phoneA.element("text").readOnly, "received request did not lock the script form");
    await phoneA.submit();
    check(phoneA.calls.filter((call) => call.method === "POST").length === 2, "received script allowed another response");
    const again = await cli("read", "--handle", a.handlePath);
    check(again.input.id === firstRead.input.id, "CLI reread changed the stable input ID");
    const resultB = await cli("read", "--handle", b.handlePath);
    check(resultB.request.requestId === b.request.requestId && resultB.request.state === "pending" && !resultB.input, "request A submission contaminated request B");
    const handleA = JSON.parse(fs.readFileSync(a.handlePath, "utf8"));
    const deniedRead = await localHTTP(origin, requestRoute(b, "/result"), { headers: { Authorization: `Bearer ${handleA.readerToken}` } });
    check(deniedRead.status === 401, "A reader capability authorized B");
    const wrongInvite = new URL(a.sendUrl);
    const wrongFragment = new URLSearchParams(wrongInvite.hash.slice(1));
    wrongFragment.set("request", b.request.requestId); wrongInvite.hash = wrongFragment.toString();
    const unauthorized = boot(wrongInvite.href);
    unauthorized.input("Keep unauthorized draft");
    await unauthorized.flush();
    check(unauthorized.calls.length === 1 && unauthorized.calls[0].status === 401 && unauthorized.element("text").value === "Keep unauthorized draft" && unauthorized.element("send").disabled, "unauthorized link lost its draft or crossed request scope");
    check(unauthorized.calls.every((call) => call.route.startsWith("/api/requests/")), "unauthorized request silently fell back to ordinary transfer");
    console.log("PASS SCRIPT_HTTP: compiled CLI create → served app.js info/input → real HTTP → CLI wait/read, A/B isolation and received lock.");

    const offline = await create("offline-retry");
    const offlinePage = boot(offline.sendUrl, { faults: [{ route: requestRoute(offline, "/info"), method: "GET", kind: "offline" }] });
    offlinePage.input("Preserve this offline draft");
    await offlinePage.flush();
    check(!offlinePage.element("retry-request").hidden && offlinePage.element("send").disabled, "offline request info did not offer explicit retry");
    await offlinePage.element("retry-request").click();
    await offlinePage.flush();
    check(offlinePage.element("text").value === "Preserve this offline draft" && !offlinePage.element("send").disabled, "real info retry lost the draft");
    offlinePage.inject({ route: requestRoute(offline, "/input"), method: "POST", kind: "offline" });
    await offlinePage.submit();
    check(offlinePage.element("text").value === "Preserve this offline draft" && !offlinePage.element("send").disabled, "offline send lost the retry draft");
    await offlinePage.submit();
    const offlineDeliveries = offlinePage.calls.filter((call) => call.method === "POST");
    check(offlineDeliveries.length === 2 && !offlineDeliveries[0].reachedServer && offlineDeliveries[1].status === 201, "offline injection/retry did not reach the intended real HTTP path");
    assert.deepEqual(JSON.parse(offlineDeliveries[0].body), JSON.parse(offlineDeliveries[1].body));
    const offlineRead = await cli("read", "--handle", offline.handlePath);
    check(offlineRead.input?.text === "Preserve this offline draft", "offline retry result changed submitted text");
    const expired = await create("expired-draft", ["--ttl", "1s"]);
    const expiry = await cli("wait", "--handle", expired.handlePath, "--timeout", "2s");
    check(expiry.request.state === "expired", "short request did not expire through the real service");
    const expiredPage = boot(expired.sendUrl);
    expiredPage.input("Keep expired draft");
    await expiredPage.flush();
    check(expiredPage.calls[0].status === 410 && expiredPage.element("text").value === "Keep expired draft" && expiredPage.element("send").disabled && !expiredPage.element("text").readOnly, "expired link lost an editable draft or remained sendable");
    console.log("PASS SCRIPT_HTTP: injected offline/loading/send retries and committed-response loss retained drafts and idempotency; real unauthorized/expired links preserved drafts.");

    const owner = boot(`${origin}/#owner=${encodeURIComponent(control.ownerToken)}`);
    await owner.flush();
    const active = JSON.parse(owner.memory.get("ferryDock.active"));
    check(active?.id && !owner.element("invite").hidden, "served computer script did not create its ordinary session");
    const ordinaryPhone = boot(active.sendUrl);
    const first = "  ordinary phone text\n中文 <b>literal</b>  ";
    ordinaryPhone.input(first); await ordinaryPhone.submit();
    ordinaryPhone.input("second ordinary text"); await ordinaryPhone.submit();
    check(ordinaryPhone.element("text").value === "" && !ordinaryPhone.element("send").disabled, "ordinary script did not remain ready for repeat sends");
    const pollRoute = `/api/sessions/${active.id}?after=0`;
    owner.inject({ route: pollRoute, method: "GET", kind: "offline" });
    await owner.tick();
    check(owner.element("messages").children.length === 0 && /Reconnecting/.test(owner.element("receiver-status").textContent), "injected computer polling failure did not retain its cursor");
    await owner.tick();
    check(owner.element("messages").children.length === 2 && owner.element("count").textContent === "2", "computer poll did not recover both real messages");
    await owner.tick();
    check(owner.calls.some((call) => call.route === `/api/sessions/${active.id}?after=2` && call.status === 200) && owner.element("messages").children.length === 2, "incremental poll repeated or skipped accepted messages");
    const reloaded = boot(`${origin}/`, { stored: owner.memory });
    await reloaded.flush();
    check(reloaded.calls.some((call) => call.route === pollRoute && call.status === 200) && reloaded.element("messages").children.length === 2, "reloaded script did not reread retained server history");
    const article = reloaded.element("messages").children.find((item) => item.children[0].textContent === first);
    check(article, "ordinary text was changed or interpreted before rendering");
    await article.children[1].children[1].click();
    check(reloaded.clipboardArguments[0] === first, "Copy handler passed changed text to its test clipboard adapter");
    await reloaded.element("close").click();
    check(!reloaded.memory.has("ferryDock.active") && reloaded.element("messages").children.length === 0, "computer script did not clear a closed session");
    ordinaryPhone.input("Keep ended-session draft"); await ordinaryPhone.submit();
    check(ordinaryPhone.element("text").value === "Keep ended-session draft" && ordinaryPhone.element("send").disabled && !ordinaryPhone.memory.has("ferryDock.phone"), "ended ordinary session accepted or discarded a draft");
    await owner.tick();
    check(!owner.memory.has("ferryDock.active") && owner.element("messages").children.length === 0, "another computer view did not observe real session closure");
    for (const page of pages) await page.flush();
    console.log("PASS SCRIPT_HTTP: ordinary served scripts created/sent/polled/recovered/reread/closed over real HTTP; Copy argument checked through a test double.");
  }
}

if (options.length && (options.length !== 2 || options[0] !== "--binary")) {
  console.error("Usage: node scripts/smoke-ui.cjs [--binary PATH]");
  process.exitCode = 2;
} else {
  const binary = path.resolve(options[1] || path.join(root, "bin", process.platform === "win32" ? "ferry-dock.exe" : "ferry-dock"));
  main(binary).catch((error) => {
    // Never print arbitrary assertion diffs, HTTP bodies, child output, runtime
    // files, or URLs: those may contain synthetic capability credentials.
    console.error(`FAIL SCRIPT_HTTP: ${error.publicMessage || "unexpected runtime failure (details withheld to protect capability data)"}`);
    const frame = String(error.stack || "").split("\n").find((line) => /smoke-ui\.cjs:\d+:\d+/.test(line));
    if (frame) console.error(frame.trim());
    process.exitCode = 1;
  });
}
