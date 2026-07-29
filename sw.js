const CACHE='gw-v6';
const CORE=['index.html','icon.svg','icon-192.png','icon-512.png','manifest.webmanifest'];
self.addEventListener('install',e=>{ e.waitUntil(caches.open(CACHE).then(c=>c.addAll(CORE)).then(()=>self.skipWaiting())); });
self.addEventListener('activate',e=>{ e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim())); });
self.addEventListener('message',e=>{ if(e.data==='SKIP_WAITING') self.skipWaiting(); });
self.addEventListener('fetch',e=>{
  const url=new URL(e.request.url);
  // 首页 HTML：先给缓存（秒开），后台静默拉最新（下次打开即新）。解决沙箱休眠返回假200休眠页吞掉缓存的问题。
  if(e.request.mode==='navigate' || url.pathname.endsWith('index.html') || url.pathname==='/'){
    e.respondWith(
      caches.match(e.request).then(cached=>{
        if(cached){
          fetch(e.request,{cache:'reload'}).then(res=>{ const cp=res.clone(); caches.open(CACHE).then(c=>c.put(e.request,cp)); }).catch(()=>{});
          return cached;
        }
        return fetch(e.request,{cache:'reload'}).then(res=>{ const cp=res.clone(); caches.open(CACHE).then(c=>c.put(e.request,cp)); return res; });
      })
    );
    return;
  }
  // 其余静态资源：cache-first（提升速度，支持离线图标）
  e.respondWith(
    caches.match(e.request).then(r=> r || fetch(e.request).then(res=>{ const cp=res.clone(); caches.open(CACHE).then(c=>c.put(e.request,cp)); return res; }).catch(()=>r))
  );
});
