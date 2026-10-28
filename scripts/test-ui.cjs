"use strict";

// Script-level regressions, not browser E2E. The narrow fake DOM below exercises
// app.js event handlers and HTTP boundaries. It does not render HTML/CSS or test
// browser validation, clipboard permissions, QR scanning, or real networking.
// Run with Node 18+: node scripts/test-ui.cjs
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const webDirectory = path.join(__dirname, "..", "internal", "relay", "web");
const appPath = path.join(webDirectory, "app.js");
const source = fs.readFileSync(appPath, "utf8");
const html = fs.readFileSync(path.join(webDirectory, "index.html"), "utf8");
const elementIds = new Set(Array.from(html.matchAll(/\bid="([^"]+)"/g), (match) => match[1]));
const cases = [];
const test = (name, run) => cases.push({ name, run });
const settle = () => new Promise(setImmediate);
const reply = (status, body) => ({
  status,
  ok: status >= 200 && status < 300,
  json: async () => body,
});
const snapshot = (overrides = {}) => ({
  requestId: "r1",
  taskId: "proposal <img onerror=run()>",
  prompt: "Please review\n<script>never execute</script>",
  state: "pending",
  createdAt: "2026-10-28T00:00:00Z",
  expiresAt: "2026-10-29T00:00:00Z",
  maxTextBytes: 16384,
  ...overrides,
});

function boot({ hash = "#request=r1&key=sender", stored = {}, fetches = [] } = {}) {
  const elements = new Map();
  function element(id) {
    assert.ok(elementIds.has(id), `Missing #${id} in index.html`);
    if (!elements.has(id)) {
      elements.set(id, {
        value: "",
        textContent: "",
        hidden: true,
        disabled: false,
        readOnly: false,
        handlers: {},
        classList: { add() {}, toggle() {} },
        addEventListener(name, handler) { this.handlers[name] = handler; },
        dispatchEvent(event) { return this.handlers[event.type]?.(event); },
        focus() {},
      });
    }
    return elements.get(id);
  }
  const memory = new Map(Object.entries(stored).map(([key, value]) => [key, JSON.stringify(value)]));
  const calls = [];
  const responses = [...fetches];
  let random = 0;
  const context = {
    document: { getElementById: element, body: { classList: { add() {} } } },
    location: { pathname: "/send", hash },
    history: { replaceState() {} },
    sessionStorage: {
      getItem: (key) => memory.get(key) || null,
      setItem: (key, value) => memory.set(key, value),
      removeItem: (key) => memory.delete(key),
    },
    URLSearchParams,
    TextEncoder,
    Uint8Array,
    AbortSignal: { timeout() {} },
    window: { isSecureContext: false },
    navigator: {},
    // Deterministic IDs let tests compare retries; this is not a random source
    // used by the application, which retains the browser's crypto API.
    crypto: { getRandomValues(bytes) { bytes.fill(++random); return bytes; } },
    setTimeout() {},
    fetch: async (url, options) => {
      calls.push({ url, options });
      const next = responses.shift();
      if (next instanceof Error) throw next;
      if (!next) throw new Error(`Unexpected fetch ${url}`);
      return next;
    },
  };
  vm.runInNewContext(source, context, { filename: appPath });
  return {
    element, memory, calls,
    input(text) {
      element("text").value = text;
      element("text").dispatchEvent({ type: "input" });
    },
    submit() { return element("send-form").handlers.submit({ preventDefault() {} }); },
    retry() { return element("retry-request").handlers.click(); },
  };
}

test("request details use text content; custom UTF-8 limit rejects without truncation", async () => {
  const ui = boot({ fetches: [reply(200, snapshot({ maxTextBytes: 8 }))] });
  await settle();
  assert.equal(ui.element("request-task").textContent, "For proposal <img onerror=run()>");
  assert.equal(ui.element("request-prompt").textContent, "Please review\n<script>never execute</script>");
  assert.equal(ui.calls[0].options.headers.Authorization, "Bearer sender");
  ui.input("😀😀😀");
  assert.equal(ui.element("bytes").textContent, "12 / 8 bytes");
  await ui.submit();
  assert.equal(ui.calls.length, 1);
  assert.equal(ui.element("text").value, "😀😀😀");
  assert.match(ui.element("sender-status").textContent, /8 bytes/);
  assert.equal(JSON.parse(ui.memory.get("ferryDock.phone")).kind, "request");
});

test("lost response retries the same draft with the same key; 200 locks the request", async () => {
  const ui = boot({ fetches: [reply(200, snapshot()), new Error("Network interrupted"), reply(200, { id: "i1" })] });
  await settle();
  ui.input("  feedback\n");
  await ui.submit();
  assert.equal(ui.element("text").value, "  feedback\n");
  assert.equal(ui.element("send").disabled, false);
  await ui.submit();
  assert.deepEqual(JSON.parse(ui.calls[1].options.body), JSON.parse(ui.calls[2].options.body));
  assert.equal(ui.calls[1].url, "/api/requests/r1/input");
  assert.equal(ui.element("sender-status").textContent, "Received.");
  assert.equal(ui.element("send").disabled, true);
  assert.equal(ui.element("text").readOnly, true);
  await ui.submit();
  assert.equal(ui.calls.length, 3);
});

test("first 201 receipt locks the request without claiming Agent processing", async () => {
  const ui = boot({ fetches: [reply(200, snapshot()), reply(201, { id: "i1" })] });
  await settle();
  ui.input("Works");
  await ui.submit();
  assert.equal(ui.element("send").textContent, "Received");
  assert.equal(ui.element("text").value, "Works");
  assert.doesNotMatch(ui.element("sender-status").textContent, /agent|processed|reviewed/i);
});

test("failed info loading preserves an editable draft and offers explicit retry", async () => {
  const ui = boot({ fetches: [new Error("Offline"), reply(200, snapshot({ maxTextBytes: 1024 }))] });
  ui.input("Keep my draft");
  await settle();
  assert.equal(ui.element("send").disabled, true);
  assert.equal(ui.element("retry-request").hidden, false);
  assert.equal(ui.element("text").readOnly, false);
  await ui.retry();
  assert.equal(ui.element("text").value, "Keep my draft");
  assert.equal(ui.element("send").disabled, false);
  assert.match(ui.element("bytes").textContent, /1 KiB/);
  assert.equal(ui.calls[1].url, "/api/requests/r1/info");
});

test("gone and unauthorized requests preserve drafts without session fallback", async () => {
  for (const status of [401, 410]) {
    const ui = boot({ fetches: [reply(status, { code: status === 410 ? "gone" : "unauthorized", error: "Ended" })] });
    ui.input("Keep");
    await settle();
    assert.equal(ui.element("text").value, "Keep");
    assert.equal(ui.element("send").disabled, true);
    assert.equal(ui.element("retry-request").hidden, true);
    assert.equal(JSON.parse(ui.memory.get("ferryDock.phone")).kind, "request");
    assert.match(ui.element("sender-status").textContent, /still here/);
  }
});

test("already received request accepts no new response", async () => {
  const ui = boot({ fetches: [reply(200, snapshot({ state: "received" }))] });
  await settle();
  ui.input("A second response");
  await ui.submit();
  assert.equal(ui.calls.length, 1);
  assert.equal(ui.element("send").disabled, true);
  assert.equal(ui.element("text").readOnly, true);
  assert.match(ui.element("sender-status").textContent, /already/);
});

test("conflict refreshes info and prevents another response when received", async () => {
  const ui = boot({ fetches: [
    reply(200, snapshot()),
    reply(409, { code: "conflict", error: "Already received" }),
    reply(200, snapshot({ state: "received" })),
  ] });
  await settle();
  ui.input("Kept feedback");
  await ui.submit();
  assert.equal(ui.element("text").value, "Kept feedback");
  assert.equal(ui.element("send").disabled, true);
  assert.equal(ui.calls[2].url, "/api/requests/r1/info");
  await ui.submit();
  assert.equal(ui.calls.length, 3);
});

test("legacy session keeps 64 KiB and supports repeated messages with new keys", async () => {
  const ui = boot({
    hash: "",
    stored: { "ferryDock.phone": { id: "s1", key: "send-session" } },
    fetches: [reply(201, { id: "m1" }), reply(201, { id: "m2" })],
  });
  assert.equal(ui.calls.length, 0);
  assert.equal(JSON.parse(ui.memory.get("ferryDock.phone")).kind, "session");
  ui.input("x".repeat(65536));
  await ui.submit();
  assert.equal(ui.calls[0].url, "/api/sessions/s1/messages");
  assert.equal(JSON.parse(ui.calls[0].options.body).text.length, 65536);
  assert.equal(ui.element("text").value, "");
  assert.equal(ui.element("send").disabled, false);
  ui.input("next");
  await ui.submit();
  assert.notEqual(JSON.parse(ui.calls[0].options.body).idempotencyKey, JSON.parse(ui.calls[1].options.body).idempotencyKey);
});

test("ended ordinary session preserves draft and clears obsolete context", async () => {
  const ui = boot({ hash: "#session=s1&key=k", fetches: [reply(410, { error: "Session ended" })] });
  ui.input("Keep");
  await ui.submit();
  assert.equal(ui.element("text").value, "Keep");
  assert.equal(ui.memory.has("ferryDock.phone"), false);
  assert.equal(ui.element("send").disabled, true);
});

test("incomplete explicit request never restores an old ordinary session", async () => {
  const ui = boot({ hash: "#request=r1", stored: { "ferryDock.phone": { id: "s1", key: "old" } } });
  assert.equal(ui.calls.length, 0);
  assert.equal(ui.element("send").disabled, true);
  assert.equal(ui.memory.has("ferryDock.phone"), false);
});

(async () => {
  let failures = 0;
  for (const { name, run } of cases) {
    try { await run(); console.log(`PASS ${name}`); }
    catch (error) { failures++; console.error(`FAIL ${name}`); console.error(error); }
  }
  console.log(`${cases.length - failures}/${cases.length} UI VM checks passed. Browser/phone E2E: NOT_RUN.`);
  if (failures) process.exitCode = 1;
})().catch((error) => { console.error(error); process.exitCode = 1; });
