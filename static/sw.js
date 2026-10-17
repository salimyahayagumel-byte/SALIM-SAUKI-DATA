/* SALIM SAUKI DATA PWA service worker. Never cache API responses or credentials. */
const CACHE_NAME = "salim-sauki-data-shell-v1";
const APP_SHELL = [
  "/",
  "/static/manifest.webmanifest",
  "/static/css/style.css",
  "/static/js/dashboard.js",
  "/static/img/masfox-logo.jpg",
  "/static/img/app-icon-192.png",
  "/static/img/app-icon-512.png"
];

self.addEventListener("install", event => {
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE_NAME);
    await cache.addAll(APP_SHELL);
    await self.skipWaiting();
  })());
});

self.addEventListener("activate", event => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter(key => key.startsWith("salim-sauki-data-shell-") && key !== CACHE_NAME).map(key => caches.delete(key)));
    await self.clients.claim();
  })());
});

self.addEventListener("fetch", event => {
  const request = event.request;
  const url = new URL(request.url);
  if (request.method !== "GET" || url.origin !== self.location.origin) return;
  // Live APIs, scanner endpoints, and health routes must always reach the server.
  if (url.pathname.startsWith("/api/") || url.pathname === "/health" || url.pathname === "/ready") return;

  if (request.mode === "navigate") {
    event.respondWith((async () => {
      try {
        const response = await fetch(request);
        if (response.ok) {
          const cache = await caches.open(CACHE_NAME);
          cache.put("/", response.clone()).catch(() => {});
        }
        return response;
      } catch (_) {
        return (await caches.match("/")) || new Response("<h1>SALIM SAUKI DATA</h1><p>You are offline. Reconnect to load live signals and PNL.</p>", {headers:{"Content-Type":"text/html; charset=utf-8"}, status:200});
      }
    })());
    return;
  }

  if (url.pathname.startsWith("/static/")) {
    event.respondWith((async () => {
      const cached = await caches.match(request);
      const network = fetch(request).then(response => {
        if (response.ok && response.type === "basic") {
          caches.open(CACHE_NAME).then(cache => cache.put(request, response.clone())).catch(() => {});
        }
        return response;
      });
      if (cached) { network.catch(() => {}); return cached; }
      return network;
    })());
  }
});
