"use strict";
(() => {
  const $ = (id) => document.getElementById(id);
  const sessionTextLimit = 65536;
  const requestTextLimit = 16384;
  const encoder = new TextEncoder();
  const store = {
    get(key) { try { return JSON.parse(sessionStorage.getItem(key)); } catch { return null; } },
    set(key, value) { try { sessionStorage.setItem(key, JSON.stringify(value)); } catch { /* Current page still works without storage. */ } },
    remove(key) { try { sessionStorage.removeItem(key); } catch { /* Optional persistence. */ } },
  };
  const fragment = new URLSearchParams(location.hash.slice(1));
  // A camera/browser may reuse the existing /send tab for another invitation.
  // Reload the document before using its new authority rather than retaining
  // the previous request's closed-over capability.
  window.addEventListener?.("hashchange", () => {
    const incoming = new URLSearchParams(location.hash.slice(1));
    if (["request", "session", "owner", "key"].some((key) => incoming.has(key))) location.reload();
  });
  // Fragments never enter HTTP requests; remove them from the visible URL after reading.
  if (location.hash) history.replaceState(null, "", location.pathname);
  const status = (id, message, error = false) => { $(id).textContent = message; $(id).classList.toggle("error", error); };
  async function api(path, token, options = {}) {
    const response = await fetch(path, {
      ...options,
      headers: { Authorization: `Bearer ${token}`, ...(options.body ? { "Content-Type": "application/json" } : {}) },
      cache: "no-store",
      signal: AbortSignal.timeout(10000),
    });
    const body = response.status === 204 ? null : await response.json();
    if (!response.ok) { const error = new Error(body?.error || "Request failed"); error.status = response.status; error.code = body?.code; throw error; }
    return body;
  }
  async function copy(text, button, selectionTarget) {
    const label = button.textContent;
    let copied = false;
    try { if (navigator.clipboard?.writeText) { await navigator.clipboard.writeText(text); copied = true; } } catch { /* HTTP and browser permissions may block it. */ }
    if (!copied) {
      const input = document.createElement("textarea"); input.value = text;
      input.style.position = "fixed"; input.style.opacity = "0";
      document.body.append(input); input.select(); input.setSelectionRange(0, text.length);
      try { copied = document.execCommand("copy"); } catch { /* Fall back to visible selection. */ }
      input.remove();
    }
    button.textContent = copied ? "Copied" : "Select & copy";
    if (!copied && selectionTarget) {
      const range = document.createRange(); range.selectNodeContents(selectionTarget);
      getSelection().removeAllRanges(); getSelection().addRange(range);
      status("receiver-status", "Text selected. Use your device’s Copy command.");
    } else if (!copied) {
      status("receiver-status", "Copy was blocked. Open the send page and copy its address.", true);
    }
    setTimeout(() => { button.textContent = label; }, 1800);
  }

  if (location.pathname === "/send") {
    document.body.classList.add("sender-mode");
    $("sender").hidden = false;
    function phoneContext(value) {
      if (!value || typeof value.id !== "string" || !value.id || typeof value.key !== "string" || !value.key) return null;
      // Entries saved before request mode had no kind and always describe sessions.
      const kind = value.kind === undefined ? "session" : value.kind;
      return kind === "session" || kind === "request" ? { kind, id: value.id, key: value.key } : null;
    }
    const hasPhoneFragment = fragment.has("session") || fragment.has("request") || fragment.has("key");
    const fragmentKind = fragment.has("request") ? "request" : "session";
    const phone = phoneContext(hasPhoneFragment ? { kind: fragmentKind, id: fragment.get(fragmentKind), key: fragment.get("key") } : store.get("ferryDock.phone"));
    if (phone) store.set("ferryDock.phone", phone);
    else if (hasPhoneFragment) store.remove("ferryDock.phone");
    if (!phone) { status("sender-status", "Scan a new QR code on your computer to start.", true); $("send").disabled = true; return; }
    const isRequest = phone.kind === "request";
    let maxText = isRequest ? requestTextLimit : sessionTextLimit;
    let pending = null;
    let sending = false;
    let sessionEnded = false;
    let requestState = isRequest ? "loading" : null;
    const canPaste = window.isSecureContext && !!navigator.clipboard?.readText;
    function limitLabel() {
      return maxText >= 1024 && maxText % 1024 === 0 ? `${maxText / 1024} KiB` : `${maxText.toLocaleString()} bytes`;
    }
    function countBytes() {
      const bytes = encoder.encode($("text").value).length;
      $("bytes").textContent = maxText >= 1024 && maxText % 1024 === 0 ? `${(bytes / 1024).toFixed(1)} / ${maxText / 1024} KiB` : `${bytes.toLocaleString()} / ${maxText.toLocaleString()} bytes`;
      $("bytes").classList.toggle("error", bytes > maxText);
    }
    function presentSender() {
      $("send").disabled = sending || sessionEnded || (isRequest && requestState !== "pending");
      $("text").readOnly = isRequest && (sending || requestState === "received");
      $("paste").hidden = !canPaste || $("text").readOnly;
      $("retry-request").hidden = !isRequest || requestState !== "unavailable";
      if (sending) $("send").textContent = "Sending…";
      else if (sessionEnded) $("send").textContent = "Session ended";
      else if (!isRequest) $("send").textContent = "Send to computer";
      else if (requestState === "pending") $("send").textContent = "Send response";
      else if (requestState === "received") $("send").textContent = "Received";
      else if (requestState === "loading") $("send").textContent = "Loading request…";
      else if (requestState === "unavailable") $("send").textContent = "Load request first";
      else $("send").textContent = "Request ended";
    }
    function requestEnded(state) {
      requestState = state;
      const reason = state === "canceled" ? "This request was canceled." : state === "expired" ? "This request has expired." : state === "unauthorized" ? "This request link is no longer valid." : "This request has ended or expired.";
      status("sender-status", `${reason} Your text is still here. Ask for a new QR code to continue.`, true);
      $("sender-note").textContent = "This request is no longer accepting responses.";
      presentSender();
    }
    function requestReceived(alreadyReceived = false) {
      requestState = "received";
      status("sender-status", alreadyReceived ? "A response has already been received." : "Received.");
      $("sender-note").textContent = "This request accepts one response.";
      presentSender();
    }
    async function loadRequest() {
      requestState = "loading";
      presentSender();
      status("sender-status", "Loading request…");
      try {
        const info = await api(`/api/requests/${encodeURIComponent(phone.id)}/info`, phone.key);
        if (info?.requestId !== phone.id || typeof info.taskId !== "string" || typeof info.prompt !== "string" || !["pending", "received", "canceled", "expired"].includes(info.state) || !Number.isSafeInteger(info.maxTextBytes) || info.maxTextBytes < 1 || info.maxTextBytes > requestTextLimit) {
          throw new Error("Could not read the request details");
        }
        $("request-task").textContent = info.taskId ? `For ${info.taskId}` : "";
        $("request-task").hidden = !info.taskId;
        $("request-prompt").textContent = info.prompt;
        maxText = info.maxTextBytes;
        countBytes();
        if (info.state === "received") requestReceived(true);
        else if (info.state === "canceled" || info.state === "expired") requestEnded(info.state);
        else { requestState = "pending"; status("sender-status", ""); }
      } catch (error) {
        if (error.status === 410) requestEnded("gone");
        else if (error.status === 401) requestEnded("unauthorized");
        else {
          requestState = "unavailable";
          status("sender-status", `${error.message}. Your text is still here. Retry loading the request to continue.`, true);
        }
      } finally { presentSender(); }
    }
    $("text").addEventListener("input", countBytes);
    if (canPaste) {
      $("paste").addEventListener("click", async () => {
        if ($("text").readOnly) return;
        try {
          const text = await navigator.clipboard.readText();
          if ($("text").readOnly) return;
          $("text").value = text; $("text").dispatchEvent(new Event("input")); status("sender-status", "");
        }
        catch { status("sender-status", "Touch and hold the text box, then choose Paste."); }
        $("text").focus();
      });
    }
    $("send-form").addEventListener("submit", async (event) => {
      event.preventDefault();
      if (sending || sessionEnded || (isRequest && requestState !== "pending")) return;
      const text = $("text").value;
      if (!text.trim()) { status("sender-status", "Add some text first.", true); return; }
      if (encoder.encode(text).length > maxText) { status("sender-status", `Keep this text within ${limitLabel()}.`, true); return; }
      // Retain the attempt for an unchanged draft, including a lost success response.
      if (!pending || pending.text !== text) {
        const bytes = new Uint8Array(16); crypto.getRandomValues(bytes);
        pending = { key: Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join(""), text };
      }
      sending = true;
      presentSender();
      try {
        const path = isRequest ? `/api/requests/${encodeURIComponent(phone.id)}/input` : `/api/sessions/${encodeURIComponent(phone.id)}/messages`;
        await api(path, phone.key, { method: "POST", body: JSON.stringify({ idempotencyKey: pending.key, text: pending.text }) });
        if (isRequest) requestReceived();
        else {
          if ($("text").value === text) { $("text").value = ""; countBytes(); }
          status("sender-status", "Received. Ready on your computer.");
        }
        pending = null;
      } catch (error) {
        if (isRequest) {
          if (error.status === 410) requestEnded("gone");
          else if (error.status === 401) requestEnded("unauthorized");
          else if (error.status === 409) {
            await loadRequest();
            if (requestState === "pending") status("sender-status", "This response conflicts with an earlier attempt. Your text is still here.", true);
          } else status("sender-status", `${error.message}. Your text is still here; you can try again.`, true);
        } else {
          sessionEnded = error.status === 410 || error.status === 401;
          if (sessionEnded) store.remove("ferryDock.phone");
          status("sender-status", sessionEnded ? "This session has ended. Your text is still here. Scan a new QR code on your computer to continue." : `${error.message}. Your text is still here; you can try again.`, true);
        }
      } finally { sending = false; presentSender(); }
    });
    if (isRequest) {
      $("sender-title").textContent = "Send a response.";
      $("sender-lead").hidden = true;
      $("request-context").hidden = false;
      $("sender-note").textContent = "One response, delivered to this request. Your text stays here if sending fails.";
      $("retry-request").addEventListener("click", loadRequest);
      loadRequest();
    }
    countBytes();
    presentSender();
    return;
  }

  const previousOwner = store.get("ferryDock.owner");
  const owner = fragment.get("owner") || previousOwner;
  if (!owner) { $("entry").hidden = false; return; }
  store.set("ferryDock.owner", owner);
  $("receiver").hidden = false;
  api("/api/desktop", owner).then((info) => {
    if (info?.desktop !== true) return;
    $("desktop-controls").hidden = false;
    $("desktop-network").textContent = info.localOnly ? "Local only: no unambiguous private network address was selected. Phone access needs a reachable LAN origin." : `Phone address: ${info.publicUrl}. Use only on a trusted LAN; HTTP is not encrypted.`;
    $("quit-app").addEventListener("click", async () => {
      $("quit-app").disabled = true;
      try {
        await api("/api/desktop/quit", owner, { method: "POST", body: "{}" });
        ended();
        status("receiver-status", "Ferry Dock has stopped. Reopen the app to start again.");
        store.remove("ferryDock.active"); store.remove("ferryDock.owner");
        ["create", "close", "copy-link"].forEach((id) => { $(id).disabled = true; });
      } catch { $("quit-app").disabled = false; status("receiver-status", "Could not confirm shutdown. Retry Quit or reopen Ferry Dock.", true); }
    });
  }).catch(() => { /* Plain serve has no desktop lifecycle controls. */ });
  let active = fragment.has("owner") && owner !== previousOwner ? null : store.get("ferryDock.active"), cursor = 0, generation = 0, busy = false;
  if (!active) store.remove("ferryDock.active");
  const seen = new Set();
  function present() {
    $("invite").hidden = !active; $("create").hidden = !!active;
    if (active) { $("qr").src = active.qrDataUrl; $("send-link").href = active.sendUrl; }
  }
  function ended() {
    active = null; generation++; store.remove("ferryDock.active");
    $("messages").replaceChildren(); seen.clear(); $("count").textContent = "0"; $("empty").hidden = false;
    present();
  }
  function render(message) {
    if (seen.has(message.id)) return;
    seen.add(message.id);
    const article = document.createElement("article"); article.className = "message";
    const text = document.createElement("pre"); text.textContent = message.text; text.tabIndex = 0;
    const meta = document.createElement("div"); meta.className = "message-meta";
    const time = document.createElement("time"); time.className = "quiet"; time.dateTime = message.receivedAt; time.textContent = new Date(message.receivedAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    const button = document.createElement("button"); button.className = "secondary"; button.textContent = "Copy"; button.addEventListener("click", () => copy(message.text, button, text));
    meta.append(time, button); article.append(text, meta); $("messages").prepend(article);
    $("empty").hidden = true; $("count").textContent = String(seen.size);
  }
  async function poll() {
    if (!active || busy || document.hidden) return;
    busy = true;
    const stamp = generation, item = active;
    try {
      const response = await api(`/api/sessions/${encodeURIComponent(item.id)}?after=${cursor}`, owner);
      if (stamp !== generation) return;
      response.messages.forEach(render); cursor = response.nextCursor;
      status("receiver-status", "");
    } catch (error) {
      if (stamp !== generation) return;
      if (error.status === 410) { ended(); status("receiver-status", "Session ended. Start a new one to receive more text."); }
      else if (error.status === 401) { ended(); status("receiver-status", "Reopen the private computer link printed in your terminal.", true); }
      else status("receiver-status", `${error.message}. Reconnecting…`, true);
    } finally { busy = false; }
  }
  $("create").addEventListener("click", async () => {
    $("create").disabled = true; $("create").textContent = "Starting…";
    try {
      active = await api("/api/sessions", owner, { method: "POST", body: "{}" });
      generation++; cursor = 0; seen.clear(); $("messages").replaceChildren(); $("empty").hidden = false; $("count").textContent = "0";
      store.set("ferryDock.active", active); present(); status("receiver-status", ""); poll();
    } catch (error) { status("receiver-status", `${error.message}. Reopen the computer link from your terminal if Ferry Dock restarted.`, true); }
    finally { $("create").disabled = false; $("create").textContent = "New session"; }
  });
  $("close").addEventListener("click", async () => {
    if (!active) return;
    $("close").disabled = true;
    try { await api(`/api/sessions/${encodeURIComponent(active.id)}`, owner, { method: "DELETE" }); ended(); $("messages").replaceChildren(); seen.clear(); $("count").textContent = "0"; $("empty").hidden = false; status("receiver-status", "Session ended. Its text has been cleared."); }
    catch (error) { status("receiver-status", `${error.message}. Try ending the session again.`, true); }
    finally { $("close").disabled = false; }
  });
  $("copy-link").addEventListener("click", () => { if (active) copy(active.sendUrl, $("copy-link")); });
  setInterval(() => {
    if (active) { const seconds = Math.max(0, Math.ceil((new Date(active.expiresAt) - Date.now()) / 1000)); $("expires").textContent = `Expires in ${Math.ceil(seconds / 60)} min`; }
    poll();
  }, 1000);
  document.addEventListener("visibilitychange", poll);
  present();
  if (active) poll(); else $("create").click();
})();
