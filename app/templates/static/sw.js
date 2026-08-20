const CACHE_NAME = 'medic-ya-cache-v4';
const ASSETS = [
  '/',
  '/login',
  '/static/manifest.json',
  '/static/pwa_icon.jpg',
  '/static/js/map.js',
  '/static/js/main.js',
  'https://cdn.tailwindcss.com',
  'https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css',
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css',
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'
];

// Instalar y almacenar activos estáticos
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('Abriendo caché y almacenando estáticos...');
        return cache.addAll(ASSETS);
      })
      .then(() => self.skipWaiting())
  );
});

// Activar y limpiar cachés anteriores
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(name => {
          if (name !== CACHE_NAME) {
            console.log('Borrando caché antigua:', name);
            return caches.delete(name);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

// Interceptar peticiones y servir desde caché si está disponible
self.addEventListener('fetch', event => {
  // Ignorar peticiones a la API REST (para que siempre devuelva datos frescos del backend)
  if (event.request.url.includes('/api/')) {
    return;
  }
  
  event.respondWith(
    caches.match(event.request)
      .then(cachedResponse => {
        if (cachedResponse) {
          return cachedResponse;
        }
        return fetch(event.request).then(networkResponse => {
          // Guardar respuestas dinámicas si es necesario (ej: imágenes del mapa u hojas de estilo locales)
          if (event.request.method === 'GET' && networkResponse.status === 200) {
            const cacheCopy = networkResponse.clone();
            caches.open(CACHE_NAME).then(cache => cache.put(event.request, cacheCopy));
          }
          return networkResponse;
        });
      }).catch(() => {
        // Fallback offline en caso de falla de red completa
        return caches.match('/');
      })
  );
});
