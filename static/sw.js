// Service Worker — Proximity Match PWA
// Enables offline shell, "Add to Home Screen", and asset caching.

const CACHE_NAME = 'proximity-v1';
const SHELL_ASSETS = [
  '/',
  '/static/manifest.json',
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css',
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js',
];

// ── Install: pre-cache the app shell ──────────────────────────────────────────
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) =>
      cache.addAll(SHELL_ASSETS).catch(() => {/* ignore partial failures */})
    )
  );
  self.skipWaiting();
});

// ── Activate: remove stale caches ─────────────────────────────────────────────
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// ── Fetch: network-first for API, cache-first for static assets ───────────────
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET and cross-origin requests that aren't CDN assets
  if (request.method !== 'GET') return;

  // API routes — always network (never cache auth/match data)
  const apiPaths = ['/register', '/login', '/me', '/checkin', '/matches', '/history', '/ws'];
  if (apiPaths.some((p) => url.pathname.startsWith(p))) {
    event.respondWith(fetch(request));
    return;
  }

  // Static assets and the app shell — cache-first with network fallback
  event.respondWith(
    caches.match(request).then((cached) => {
      if (cached) return cached;
      return fetch(request).then((response) => {
        if (response.ok) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
        }
        return response;
      });
    }).catch(() => {
      // If offline and nothing cached, return a minimal offline page
      if (request.destination === 'document') {
        return caches.match('/');
      }
    })
  );
});
