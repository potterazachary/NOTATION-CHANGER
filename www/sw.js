// Klavar offline support and "Share to Klavar". The build number below is filled in by the
// GitHub Pages deploy, so every release gets a fresh cache.
const VERSION = '__BUILD__';
const CACHE = 'klavar-' + VERSION;
const SHELL = ['./', 'index.html', 'build-info.js', 'manifest.webmanifest',
  'vendor/jszip.min.js', 'vendor/opensheetmusicdisplay.min.js',
  'icons/icon-192.png', 'icons/icon-512.png', 'icons/apple-touch-icon.png'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys()
    .then(keys => Promise.all(keys.filter(k => k.startsWith('klavar-') && k !== CACHE && k !== 'klavar-share').map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener('fetch', e => {
  const req = e.request, url = new URL(req.url);

  // A score shared from another app (Android): keep it, then open Klavar to load it.
  if (req.method === 'POST' && url.pathname.endsWith('/share-target')){
    e.respondWith((async () => {
      try {
        const fd = await req.formData();
        const f = fd.get('score');
        const c = await caches.open('klavar-share');
        if (f && f.size){
          await c.put('shared-file', new Response(f, { headers: { 'x-name': encodeURIComponent(f.name || 'shared-score') } }));
          return Response.redirect('./?shared=1', 303);
        }
        // Shared text (for example a chord chart copied from a chord website).
        const text = [fd.get('text'), fd.get('url')].filter(Boolean).join('\n');
        if (text){
          await c.put('shared-text', new Response(text));
          return Response.redirect('./?sharedtext=1', 303);
        }
      } catch (err) {}
      return Response.redirect('./', 303);
    })());
    return;
  }
  if (req.method !== 'GET') return;

  // Pages: try the network first so updates show up, fall back to the saved copy offline.
  if (req.mode === 'navigate'){
    e.respondWith(fetch(req).then(r => {
      const copy = r.clone(); caches.open(CACHE).then(c => c.put('index.html', copy)); return r;
    }).catch(() => caches.match('index.html')));
    return;
  }

  // Everything else (scripts, icons, fonts): saved copy first, refreshed in the background.
  const sameOrigin = url.origin === location.origin;
  const fonts = /fonts\.(googleapis|gstatic)\.com$/.test(url.hostname);
  if (!sameOrigin && !fonts) return;
  e.respondWith(caches.open(CACHE).then(async c => {
    const hit = await c.match(req);
    const net = fetch(req).then(r => { if (r.ok || r.type === 'opaque') c.put(req, r.clone()); return r; }).catch(() => hit);
    return hit || net;
  }));
});
