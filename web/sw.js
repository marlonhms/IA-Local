/*
 * Service Worker Oficial da AURA (Fase P3-4: PWA Mobile Offline-First)
 * Arquitetura de Cache Local Resiliente para Operacao em Pista
 * Regra inegociavel: ZERO referencias a CDNs externas e ZERO travessoes.
 */

const CACHE_NAME = 'aura-pwa-v18';

const PRECACHE_ASSETS = [
  '/',
  '/index.html',
  '/favicon.ico',
  '/manifest.json',
  '/icon.svg',
  '/static/icon.svg',
  '/static/css/aura.css',
  '/static/fonts/geist_variable.ttf',
  '/static/fonts/newsreader_variable.ttf',
  '/static/vendor/tailwind.min.js',
  '/static/vendor/marked.min.js',
  '/static/vendor/lucide.min.js',
  '/static/js/aura-api.js',
  '/static/js/aura-app.js',
  '/static/js/aura-storage.js',
  '/static/js/aura-history-drawer.js',
  '/static/js/aura-welcome-cockpit.js',
  '/static/js/aura-chat.js',
  '/static/js/aura-cockpit.js',
  '/static/js/aura-aux-panel.js',
  '/static/js/aura-automations.js',
  '/static/js/aura-compliance.js',
  '/static/js/aura-telemetry.js',
  '/static/js/aura-triggers.js',
  '/static/js/aura-genui.js',
  '/static/js/aura-genui-widgets.js',
  '/static/js/aura-state-manager.js',
  '/static/js/aura-security-architecture.js',
  '/static/js/aura-fx.js',
  '/static/js/aura-voice.js'
];

// Instalacao do Service Worker: Pre-cache de todos os assets locais essenciais
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.addAll(PRECACHE_ASSETS))
      .then(() => self.skipWaiting())
      .catch((error) => {
        console.warn('[AURA SW] Falha no pre-cache durante instalacao:', error);
      })
  );
});

// Ativacao do Service Worker: Limpeza de caches obsoletos e controle imediato de clientes
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames
            .filter((name) => name !== CACHE_NAME)
            .map((name) => caches.delete(name))
        );
      })
      .then(() => self.clients.claim())
  );
});

// Interceptacao de Requisicoes de Rede
self.addEventListener('fetch', (event) => {
  const request = event.request;

  // Apenas requisicoes GET sao cacheadas
  if (request.method !== 'GET') {
    return;
  }

  const url = new URL(request.url);

  // Ignora requisicoes da API (/api/) e metricas Prometheus (/metrics): rede direta com fallback defensivo
  if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/metrics')) {
    event.respondWith(
      fetch(request).catch(() => {
        return new Response(
          JSON.stringify({
            error: 'Modo Offline Ativo',
            message: 'O servidor local da AURA esta temporariamente inacessivel na pista.',
            offline: true
          }),
          {
            status: 503,
            statusText: 'Service Unavailable',
            headers: { 'Content-Type': 'application/json; charset=utf-8' }
          }
        );
      })
    );
    return;
  }

  // Estrategia Network-First para navegacao principal (/ ou text/html)
  const isNavigation = request.mode === 'navigate' ||
    (request.headers.get('accept') && request.headers.get('accept').includes('text/html'));

  if (isNavigation) {
    event.respondWith(
      fetch(request)
        .then((networkResponse) => {
          if (networkResponse && networkResponse.status === 200) {
            const clone = networkResponse.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
          }
          return networkResponse;
        })
        .catch(async () => {
          const cachedResponse = await caches.match(request, { ignoreSearch: true });
          if (cachedResponse) {
            return cachedResponse;
          }
          return caches.match('/', { ignoreSearch: true });
        })
    );
    return;
  }

  // Estrategia Cache-First para assets locais estaticos (/static/, scripts, css, icones)
  event.respondWith(
    caches.match(request, { ignoreSearch: true }).then((cachedResponse) => {
      if (cachedResponse) {
        return cachedResponse;
      }

      return fetch(request)
        .then((networkResponse) => {
          if (networkResponse && networkResponse.status === 200 && (networkResponse.type === 'basic' || networkResponse.type === 'default')) {
            const clone = networkResponse.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
          }
          return networkResponse;
        })
        .catch(() => {
          // Fallback silencioso para recursos nao encontrados offline
          return new Response('', { status: 404, statusText: 'Not Found Offline' });
        });
    })
  );
});
