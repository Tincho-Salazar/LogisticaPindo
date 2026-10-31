/* Service worker: guarda la cáscara de la app para abrirla sin conexión. La API nunca se cachea acá
   (los datos se guardan en localStorage desde api.js). */
var VERSION = 'lf-v4';
var SHELL = ['/', '/static/app.css', '/static/api.js', '/static/util.js', '/static/views.js', '/static/sheets.js', '/static/app.js', '/static/manifest.json', '/static/fonts/Inter-latin.woff2', '/static/fonts/JetBrainsMono-latin.woff2', '/static/icons/icon-192.png', '/static/icons/icon-512.png', '/static/img/logo-pindo.png'];

self.addEventListener('install', function(e){
  e.waitUntil(caches.open(VERSION).then(function(c){ return c.addAll(SHELL); }).then(function(){ return self.skipWaiting(); }));
});
self.addEventListener('activate', function(e){
  e.waitUntil(caches.keys().then(function(ks){ return Promise.all(ks.filter(function(k){ return k !== VERSION; }).map(function(k){ return caches.delete(k); })); }).then(function(){ return self.clients.claim(); }));
});
self.addEventListener('fetch', function(e){
  var url = new URL(e.request.url);
  if(e.request.method !== 'GET' || url.origin !== location.origin || url.pathname.indexOf('/api/') === 0) return;
  // red primero (para tomar versiones nuevas), caché si no hay conexión
  e.respondWith(fetch(e.request).then(function(r){
    if(r && r.ok){ var copy = r.clone(); caches.open(VERSION).then(function(c){ c.put(e.request, copy); }); }
    return r;
  }).catch(function(){ return caches.match(e.request, { ignoreSearch: true }).then(function(r){ return r || caches.match('/'); }); }));
});
