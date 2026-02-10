const CACHE_NAME = "transactions-v1";
const ASSETS = [
    "/",
    "/static/manifest.json",
    "/static/icons/icon.svg",
    "https://cdn.tailwindcss.com",

    "https://unpkg.com/htmx.org@1.9.10"
];

self.addEventListener("install", (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS))
    );
});

self.addEventListener("fetch", (event) => {
    // For HTML requests (Dashboard), try Network first, then Cache
    if (event.request.mode === 'navigate') {
        event.respondWith(
            fetch(event.request).catch(() => caches.match(event.request))
        );
        return;
    }

    // For everything else (Assets), stick to Cache First
    event.respondWith(
        caches.match(event.request).then((response) => {
            return response || fetch(event.request);
        })
    );
});
