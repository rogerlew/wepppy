// /static/js/sw.js
/* global self, clients */

// sw.js
const LOG_PREFIX = "[wepppush-sw]";

/**
 * Expected payload:
 * { run_id: "<id>", type: "COMPLETED"|"EXCEPTION"|"TRIGGER", message: "<string>", ts: <ms> }
 */
self.addEventListener("push", (event) => {
  let raw = "(no payload)";
  try { if (event.data) raw = event.data.text(); } catch (_) {}

  let payload = null;
  try { payload = event.data && event.data.json(); } catch (e) {
    // eslint-disable-next-line no-console
    console.warn(LOG_PREFIX, "JSON parse failed; using fallback text:", raw);
  }

  const run_id = payload?.run_id || "unknown";
  const type   = payload?.type   || "PUSH";
  // Prefer payload.message; otherwise fall back to raw text so user sees *something*
  const body   = (payload?.message && String(payload.message).trim()) || raw;

  const title  = `WEPPcloud: Run ${run_id} ${type}`;
  const tag    = `run:${run_id}`; // stable: coalesces toasts for same run
  const data   = {
    run_id,
    url: `${self.registration.scope}runs/${encodeURIComponent(run_id)}/`,
    payload: payload || { raw }
  };

  event.waitUntil(
    self.registration.showNotification(title, {
      body,
      tag,
      renotify: true,
      requireInteraction: false,
      data
    })
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const { url } = event.notification.data || {};
  const targetUrl = url || "/";

  // Focus an existing client on the same URL if present, else open a new one
  event.waitUntil((async () => {
    const allClients = await clients.matchAll({ type: "window", includeUncontrolled: true });
    for (const c of allClients) {
      // If the tab is already on the target (or same origin), just focus it
      try {
        const u = new URL(c.url);
        const t = new URL(targetUrl, self.registration.scope);
        if (u.origin === t.origin && u.pathname === t.pathname) {
          await c.focus();
          return;
        }
      } catch (_) { /* noop */ }
    }
    await clients.openWindow(targetUrl);
  })());
});

self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
});