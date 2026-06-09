const CACHE = "poker-advisor-v1";
const ASSETS = ["/", "/index.html", "/style.css", "/app.js", "/manifest.json"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(ASSETS)));
  self.skipWaiting();   // 재배포 시 즉시 활성화
});

self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((keys) =>
    Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))));
});

self.addEventListener("fetch", (e) => {
  if (e.request.url.includes("/advise")) return;          // 추천은 항상 네트워크
  e.respondWith(caches.match(e.request).then((r) => r || fetch(e.request)));
});
