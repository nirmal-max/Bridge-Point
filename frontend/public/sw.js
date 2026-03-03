// Bridge Point — Service Worker (Production Hardened)
// DO NOT cache API or auth endpoints.
const CACHE_NAME = "bridgepoint-v2";
const OFFLINE_URL = "/offline.html";

// Paths that must NEVER be cached
const NO_CACHE_PATTERNS = [
  "/api/",
  "/backend/",
  "/ws/",
  "/auth/",
  "/health",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.add(OFFLINE_URL))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);

  // Never cache API, auth, or WebSocket requests
  if (NO_CACHE_PATTERNS.some((p) => url.pathname.startsWith(p))) {
    return; // Let the browser handle it normally
  }

  // For navigation requests, try network first, fall back to offline page
  if (event.request.mode === "navigate") {
    event.respondWith(
      fetch(event.request).catch(() => caches.match(OFFLINE_URL))
    );
  }
});
