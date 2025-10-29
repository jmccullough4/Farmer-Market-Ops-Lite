self.addEventListener('install', (event) => {
  event.waitUntil((async () => {
    const cache = await caches.open('marketops-static-v1');
    await cache.addAll(['/', '/manifest.webmanifest']);
  })());
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);
  // Network-first for API, cache-first for static
  if (url.pathname.startsWith('/api/')) {
    event.respondWith((async () => {
      try {
        const res = await fetch(event.request);
        return res;
      } catch (e) {
        return new Response(JSON.stringify({ offline: true }), { status: 202, headers: { 'Content-Type': 'application/json' } });
      }
    })());
  } else {
    event.respondWith((async () => {
      const cache = await caches.open('marketops-static-v1');
      const cached = await cache.match(event.request);
      if (cached) return cached;
      try {
        const res = await fetch(event.request);
        cache.put(event.request, res.clone());
        return res;
      } catch (e) {
        return new Response('offline', { status: 200 });
      }
    })());
  }
});
