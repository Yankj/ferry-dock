"use strict";
(() => {
  const $ = (id) => document.getElementById(id);
  const maxText = 65536;
  const encoder = new TextEncoder();
  const store = {
    get(key) { try { return JSON.parse(sessionStorage.getItem(key)); } catch { return null; } },
    set(key, value) { try { sessionStorage.setItem(key, JSON.stringify(value)); } catch { /* Current page still works without storage. */ } },
    remove(key) { try { sessionStorage.removeItem(key); } catch { /* Optional persistence. */ } },
  };
  const fragment = new URLSearchParams(location.hash.slice(1));
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
    if (!response.ok) { const error = new Error(body?.error || "Request failed"); error.status = response.status; throw error; }
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
    $("sender").hidden = false;
    let phone = fragment.has("session") && fragment.has("key") ? { id: fragment.get("session"), key: fragment.get("key") } : store.get("tapbeam.phone");
    if (phone) store.set("tapbeam.phone", phone);
    if (!phone) { status("sender-status", "Scan a new QR code on your computer to start.", true); $("send").disabled = true; return; }
    let pending = null;
    $("text").addEventListener("input", () => {
      const bytes = encoder.encode($("text").value).length;
      $("bytes").textContent = `${(bytes / 1024).toFixed(1)} / 64 KiB`;
      $("bytes").classList.toggle("error", bytes > maxText);
      if (pending && pending.text !== $("text").value) pending = null;
    });
    if (window.isSecureContext && navigator.clipboard?.readText) {
      $("paste").hidden = false;
      $("paste").addEventListener("click", async () => {
        try { $("text").value = await navigator.clipboard.readText(); $("text").dispatchEvent(new Event("input")); status("sender-status", ""); }
        catch { status("sender-status", "Touch and hold the text box, then choose Paste."); }
        $("text").focus();
      });
    }
    $("send-form").addEventListener("submit", async (event) => {
      event.preventDefault();
      const text = $("text").value;
      if (!text.trim()) { status("sender-status", "Add some text first.", true); return; }
      if (encoder.encode(text).length > maxText) { status("sender-status", "Keep this text under 64 KiB.", true); return; }
      if (!pending) {
        const bytes = new Uint8Array(16); crypto.getRandomValues(bytes);
        pending = { key: Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join(""), text };
      }
      $("send").disabled = true; $("send").textContent = "Sending…";
      try {
        await api(`/api/sessions/${encodeURIComponent(phone.id)}/messages`, phone.key, { method: "POST", body: JSON.stringify({ idempotencyKey: pending.key, text: pending.text }) });
        if ($("text").value === text) { $("text").value = ""; $("text").dispatchEvent(new Event("input")); }
        pending = null;
        status("sender-status", "Received. Ready on your computer.");
      } catch (error) {
        status("sender-status", error.status === 410 ? "This session has ended. Scan a new QR code on your computer." : `${error.message}. You can try again.`, true);
      } finally { $("send").disabled = false; $("send").textContent = "Send to computer"; }
    });
    return;
  }

  const owner = fragment.get("owner") || store.get("tapbeam.owner");
  if (!owner) { $("entry").hidden = false; return; }
  store.set("tapbeam.owner", owner);
  $("receiver").hidden = false;
  let active = store.get("tapbeam.active"), cursor = 0, generation = 0, busy = false;
  const seen = new Set();
  function present() {
    $("invite").hidden = !active; $("create").hidden = !!active;
    if (active) { $("qr").src = active.qrDataUrl; $("send-link").href = active.sendUrl; }
  }
  function ended() {
    active = null; generation++; store.remove("tapbeam.active");
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
      else status("receiver-status", `${error.message}. Reconnecting…`, true);
    } finally { busy = false; }
  }
  $("create").addEventListener("click", async () => {
    $("create").disabled = true; $("create").textContent = "Starting…";
    try {
      active = await api("/api/sessions", owner, { method: "POST", body: "{}" });
      generation++; cursor = 0; seen.clear(); $("messages").replaceChildren(); $("empty").hidden = false; $("count").textContent = "0";
      store.set("tapbeam.active", active); present(); status("receiver-status", ""); poll();
    } catch (error) { status("receiver-status", `${error.message}. Reopen the computer link from your terminal if Tapbeam restarted.`, true); }
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
