#!/usr/bin/env python3
"""Make NIKO ARCADE v18 robust on GitHub Pages without deleting local player data."""
from pathlib import Path
import json, re, sys, shutil

ROOT=Path(sys.argv[1]).expanduser().resolve()
if not (ROOT/'club.html').exists() and (ROOT/'public'/'club.html').exists(): ROOT=ROOT/'public'
if not (ROOT/'club.html').is_file(): raise SystemExit('Missing club.html')

def read(path): return (ROOT/path).read_text('utf-8')
def write(path,value): (ROOT/path).write_text(value,'utf-8')
def once(source,old,new,label):
    count=source.count(old)
    if count!=1: raise RuntimeError(f'{label}: expected one occurrence, got {count}')
    return source.replace(old,new,1)

# No music AI / songs section, including hidden routes.
shutil.rmtree(ROOT/'music-studio',ignore_errors=True)
shutil.rmtree(ROOT/'intro',ignore_errors=True)
for p in ROOT.rglob('*.html'):
    if p.name in ('club.html','index.html'):
        s=p.read_text('utf-8')
        if 'music-studio' in s or 'Создай свою песню' in s:raise RuntimeError(f'Removed song feature still referenced in {p}')
intro=read('intro.js')
assert 'Nikolai Shiukaev' in intro and 'Shiucaev' not in intro
write('intro.js',intro.replace('niko-intro-shiukaev-v17','niko-intro-shiukaev-v18'))

sw=read('sw.js')
sw=once(sw,'const VERSION = 17;', 'const VERSION = 18;', 'version')
sw=once(sw,"const CACHE = 'niko-arcade-offline-v17';", "const CACHE = 'niko-arcade-offline-v18';", 'SW cache')
sw=once(sw,'const ASSET_PATHS = new Set(ASSETS);', '''// Core functionality is usable offline before the optional photos and audio finish.
const CORE_ASSETS = ASSETS.filter(path => /\\.(?:html|js|css|json|webmanifest)$/.test(path));
const ASSET_PATHS = new Set(ASSETS);''','core list')
sw=once(sw,"return { type: 'OFFLINE_STATUS', cache: CACHE, ready: missing.length === 0, missing };", """const coreMissing = missing.filter(path => CORE_ASSETS.includes(path));
  return { type: 'OFFLINE_STATUS', cache: CACHE, ready: missing.length === 0,
    coreReady: coreMissing.length === 0, missingCore: coreMissing, missing };""",'core status')
assert 'const todo = [...before.missing].sort((a,b)=>assetPriority(a)-assetPriority(b));' in sw
assert 'function assetPriority(path)' in sw
sw=once(sw,'Math.min(6, todo.length)','Math.min(3, todo.length)','mobile concurrency')
# Old Safari SW may serve a stale, cached error page; bypass on a deliberate rescue request.
sw=once(sw,"  const local = logicalPath(url.pathname);", """  if (url.searchParams.has('niko-direct')) return; // explicit un-intercepted online retry
  const local = logicalPath(url.pathname);""", 'direct fetch bypass')
# Network-first for navigation, CACHE fallback if cellular is interrupted.
sw=once(sw,'''  if (cached) return cached;
  try {
    // Fresh code/styles/documents prevent the old cache forcing repeated reloads.
    const response = await fetchFresh(path, cached ? 3000 : 10000);''', '''  if (cached && !navigation) return cached;
  if (cached && self.navigator?.onLine === false) return cached;
  try {
    // Prefer the current HTML on reconnect; fall back to the last verified file.
    const response = await fetchFresh(path, cached ? 4000 : 10000);''', 'network-first pages')
write('sw.js',sw)

pwa=read('pwa.js')
pwa=once(pwa,"const EXPECTED_SHELL_CACHE = 'niko-arcade-offline-v17';", "const EXPECTED_SHELL_CACHE = 'niko-arcade-offline-v18';", 'pwa version')
write('pwa.js',pwa)
repair=read('repair.html')
if 'niko-arcade-offline-v17' not in repair: raise RuntimeError('repair cache mismatch')
write('repair.html',repair.replace('niko-arcade-offline-v17','niko-arcade-offline-v18'))

clubjs=read('club.js')
start=clubjs.index('function offlineState(')
end=clubjs.index('\n',start)
old=clubjs[start:end]
new="""function offlineState(state=window.ArcadePWA?.state){
ready=state?.ready===true;
$('offline').textContent=ready?'Все игры и ресурсы сохранены для офлайн ✓':
state?.coreReady?'Основные игры готовы офлайн ✓ · дополнительные файлы загружаются':
state?.supported===false?'Можно играть онлайн · офлайн-сохранение недоступно':
navigator.onLine?'Игры доступны онлайн · готовим офлайн-копию…':
'Без интернета. Для офлайн-копии открой клуб с интернетом один раз.';
}"""
clubjs=once(clubjs,old,new,'offline status text')
write('club.js',clubjs)

# Stable rescue URL: intentionally NOT a known SW asset, so even the old broken
# worker passes through a clean online page. Profiles and IndexedDB stay intact.
rescue=r'''<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><meta name="theme-color" content="#101722"><title>NIKO ARCADE — исправление загрузки</title><style>
:root{color-scheme:dark}body{font:17px/1.5 system-ui,Arial,sans-serif;background:#101722;color:#f7e7c6;display:grid;place-items:center;min-height:100vh;margin:0}main{max-width:600px;margin:20px;padding:22px}h1{font-size:clamp(26px,6vw,44px);margin:0 0 12px}p{color:#c5c9d2}a,button{display:inline-block;background:#edd096;color:#1f2530;border:0;border-radius:14px;padding:15px 24px;margin-top:12px;text-decoration:none;font:700 17px system-ui;cursor:pointer}#message{min-height:42px}
</style></head><body><main><h1>Обновляем NIKO ARCADE</h1><p>Исправляем загрузку игр на iPhone. Рекорды, логин и сохранённые картриджи останутся на устройстве.</p><p id="message" role="status">Проверяем старую офлайн-копию…</p><a id="go" href="/Niko-games/club.html?v18=1">Открыть игру →</a></main>
<script>(async()=>{
const el=document.getElementById('message');
try{
 if('serviceWorker' in navigator){const regs=await navigator.serviceWorker.getRegistrations();
 for(const reg of regs){const scope=new URL(reg.scope);if(scope.origin===location.origin&&(scope.pathname.startsWith('/Niko-games/')||reg.active?.scriptURL?.includes('/Niko-games/sw.js')))await reg.unregister();}}
 if('caches' in window){const keys=await caches.keys();for(const key of keys){if(/^niko-arcade-offline-v\d+$/.test(key)||/^pagesfix\d+-/.test(key))await caches.delete(key);}}
 el.textContent='Старый кэш очищен. Открываем исправленную игру…';
}catch(err){el.textContent='Можно открыть игру. Если старые ошибки останутся, обнови страницу в Safari.';}
setTimeout(()=>location.replace('/Niko-games/club.html?v18='+Date.now()),850);
})();</script></body></html>'''
write('refresh-v18.html',rescue)

# A prominent rescue link should remain usable even if a previous SW version
# caused a download to stop partway through.
club=read('club.html')
if 'href="/Niko-games/repair.html"' not in club: raise RuntimeError('Missing repair link')
club=club.replace('href="/Niko-games/repair.html"','href="/Niko-games/refresh-v18.html"',1)
club=club.replace('NIKO ARCADE · PLAY YOUR WAY','NIKO ARCADE v18 · PLAY YOUR WAY',1)
write('club.html',club)
shutil.copyfile(ROOT/'club.html',ROOT/'index.html')

# When a verified cart was served as HTTP 503 by an old worker but real cellular
# internet is present, retry against the host, preserving catalog SHA checks.
cat=read('retro/catalog.js')
needle="""      const response = await fetch(siteAsset(path), { signal: controller.signal, credentials: 'same-origin', redirect: 'error' });
      if (!response.ok) throw new Error(navigator.onLine ? 'Не удалось загрузить игру. Повтори попытку.' : 'Картридж ещё не скачан. Подключись к сети и нажми «Скачать для офлайн» в каталоге.');"""
replacement="""      const options = { signal: controller.signal, credentials: 'same-origin', redirect: 'error' };
      let response = await fetch(siteAsset(path), options);
      // If the active SW returned a stale synthetic error, try the real static file.
      if (!response.ok && navigator.onLine) {
        try { response = await fetch(siteAsset(path) + '?niko-direct=1', options); } catch {}
      }
      if (!response.ok) throw new Error(navigator.onLine ? 'Картридж не загрузился. Открой «Исправить загрузку» на главной странице и попробуй снова.' : 'Картридж ещё не сохранён. Подключись к сети и нажми «Скачать для офлайн».');"""
cat=once(cat,needle,replacement,'retro fetch fallback')
write('retro/catalog.js',cat)

# Remove unrelated old navigation links; preserve icons as normal files.
assert not (ROOT/'tabletop').exists()
assert not (ROOT/'music-studio').exists()
assert 'Shiukaev' in read('intro.js')
assert "niko-arcade-offline-v18" in read('sw.js')
assert "niko-arcade-offline-v18" in read('pwa.js')
assert "niko-arcade-offline-v18" in read('repair.html')
assert '/Niko-games/refresh-v18.html' in read('club.html')
print('v18 ready: repaired SW, cache, reload, offline core status, ROM retry, removed music studio')
