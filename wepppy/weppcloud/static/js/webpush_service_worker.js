// /static/js/sw.js
/* global self, clients */

const LOG_PREFIX = "[wepppush-sw]";

/**
 * Minimal push payload:
 * { "run_id": "<awesome_codename>", "type": "COMPLETED"|"EXCEPTION"|"TRIGGER", "ts": 1733962190123 }
 */
self.addEventListener("push", (event) => {
  try {
    if (!event.data) return;
    const payload = event.data.json();
    const { run_id, type, ts } = payload;

    // Basic title/body; tune as needed.
    const title = type === "EXCEPTION"
      ? `WEPPcloud: Run ${run_id} failed`
      : type === "COMPLETED"
        ? `WEPPcloud: Run ${run_id} completed`
        : `WEPPcloud: Run ${run_id} update`;

    const tsStr = ts ? new Date(ts).toLocaleString() : "";
    const body = tsStr ? `${type} at ${tsStr}` : type;

    // Use a stable tag to coalesce notifications per run
    const tag = `run:${run_id}`;
    const data = {
      run_id,
      // You can change this to your canonical route
      url: `${self.registration.scope}runs/${encodeURIComponent(run_id)}/`,
      // keep raw payload if you want to hydrate later
      payload
    };

    event.waitUntil(
      self.registration.showNotification(title, {
        body,
        tag,
        renotify: true,
        requireInteraction: false,
        data,
        icon: "/static/img/weppcloud-icon-192.png", // optional
        badge: "/static/img/weppcloud-badge-72.png" // optional
      })
    );
  } catch (e) {
    // swallow; SW should never throw
    // eslint-disable-next-line no-console
    console.warn(LOG_PREFIX, "push handler error:", e);
  }
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

// Optional: manage versioned cleanup if you later add caches
self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
});