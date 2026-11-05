#!/usr/bin/env python3
"""Apply NIKO ARCADE v17 repair to extracted v15 Pages site in place.

Transforms only static-site assets; never handles private player records or tokens.
"""
from pathlib import Path
import sys, shutil, re, json
ROOT=Path(sys.argv[1]).expanduser().resolve()
if not (ROOT/'club.html').is_file():
    if (ROOT/'public'/'club.html').is_file(): ROOT=ROOT/'public'
    else: raise SystemExit('Expected a site with club.html in '+str(ROOT))
def read(name):return (ROOT/name).read_text(encoding='utf-8')
def write(name,text):(ROOT/name).write_text(text,encoding='utf-8')
def replace_once(s,old,new,tag):
    if old not in s: raise RuntimeError('Cannot patch '+tag+'; v15 source differs')
    return s.replace(old,new)
# 1) Remove the song creator and family introductory photo and thank-you screen.
shutil.rmtree(ROOT/'music-studio',ignore_errors=True)
shutil.rmtree(ROOT/'intro',ignore_errors=True)
intro='''(function(){
  'use strict';
  if(window.top!==window.self||document.documentElement.hasAttribute('data-no-intro')) return;
  const key='niko-intro-shiukaev-v17';
  try { if(sessionStorage.getItem(key)) return; sessionStorage.setItem(key,'1'); } catch {}
  function start(){
    const overlay=document.createElement('section');
    overlay.className='niko-intro'; overlay.setAttribute('role','dialog');
    overlay.setAttribute('aria-modal','true'); overlay.setAttribute('aria-label','NIKO ARCADE');
    const text=document.createElement('p'); text.className='niko-intro-main';
    text.textContent='This application was developed by Nikolai Shiukaev. I hope you’ll like it.';
    const skip=document.createElement('button'); skip.className='niko-intro-skip';
    skip.textContent='Играть →'; skip.type='button';
    const overflow=document.body.style.overflow;
    let finished=false;
    function finish(){ if(finished)return; finished=true; clearTimeout(timer);overlay.remove();document.body.style.overflow=overflow;document.removeEventListener('keydown',onkey,true); }
    function onkey(event){ if(event.key==='Escape'||event.key==='Enter'){event.preventDefault();finish();} }
    skip.addEventListener('click',finish);
    overlay.append(text,skip); document.body.appendChild(overlay); document.body.style.overflow='hidden';
    document.addEventListener('keydown',onkey,true);
    const timer=setTimeout(finish,2800);
  }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',start,{once:true}); else start();
})();
'''
write('intro.js',intro)
write('intro.css', '''.niko-intro{position:fixed;inset:0;z-index:2147483000;display:flex;align-items:center;justify-content:center;padding:40px 24px;background:#02040a;color:#fff;font-family:Georgia,'Times New Roman',serif}.niko-intro-main{font-size:clamp(26px,5.2vw,56px);max-width:900px;text-align:center;font-weight:400;line-height:1.35;margin:0}.niko-intro-skip{position:absolute;bottom:max(25px,env(safe-area-inset-bottom));right:max(18px,env(safe-area-inset-right));border:1px solid #fff8;background:#fff2;color:#fff;padding:13px 22px;border-radius:40px;font:700 15px system-ui,sans-serif;cursor:pointer}.niko-intro-skip:focus-visible{outline:3px solid #f2d89c;outline-offset:3px}\n''')

s=read('club.html')
s,n=re.subn(r'<a class="v14-feature song" href="/music-studio/index\.html">[\s\S]*?</a>', '',s)
if n!=1: raise RuntimeError(f'song card deletion count={n}')
write('club.html',s)

manifest=json.loads(read('manifest.webmanifest'))
manifest['shortcuts']=[x for x in manifest.get('shortcuts',[]) if '/music-studio/' not in x.get('url','') and 'песн' not in x.get('name','').lower()]
write('manifest.webmanifest',json.dumps(manifest,ensure_ascii=False,indent=2))

# 2) Github Pages is a subpath site: scope all HTML / JS / CSS local asset URLs.
# Leave manifest cartridge entries logical /retro/*: integrity verification uses these IDs.
ROUTE_PAT=(r'(?:club\.html|index\.html|repair\.html|manifest\.webmanifest|sw\.js|'
           r'icon-\d+\.png|favicon\.svg|superhero\.jpeg|'
           r'(?:(?:retro|games|kids|premium|beauty|heritage|adventures|photos|ossetia|ossetian|'
           r'feedback|help|intro)/[^\s"\'\`<>)]*|'
           r'(?:compat|intro|club|arcade|pwa|install|modern-audio|menu-music|display|backgrounds|'
           r'newgames|runner|v14-common)\.(?:js|css)))')
# Literal first-quote + local /route. Never rewrite '/api' or third-party URLs.
prefix_re=re.compile(r'(?P<head>["\'\`(=])/(?P<route>'+ROUTE_PAT+r')')
count=0
for p in sorted(ROOT.rglob('*')):
    if not p.is_file() or p.suffix.lower() not in {'.html','.js','.css','.json','.webmanifest'}: continue
    rel=p.relative_to(ROOT).as_posix()
    if rel in {'sw.js','retro/catalog.json','retro/runtime/4.2.3/offline-manifest.json'}: continue
    if rel.startswith('retro/runtime/'): continue
    s=p.read_text(encoding='utf-8')
    s,n=prefix_re.subn(lambda m:m.group('head')+'/Niko-games/'+m.group('route'),s)
    count+=n
    if s!=p.read_text(encoding='utf-8'):p.write_text(s,encoding='utf-8')
print('Prefixed routes:',count)

# PWA scope and cache identity must agree across scripts.
s=read('pwa.js')
s=replace_once(s,"const EXPECTED_SHELL_CACHE = 'niko-arcade-offline-v10'", "const EXPECTED_SHELL_CACHE = 'niko-arcade-offline-v17'", 'pwa-cache')
s=replace_once(s,"{ scope: '/', updateViaCache: 'none' }", "{ scope: '/Niko-games/', updateViaCache: 'none' }", 'pwa-scope')
write('pwa.js',s)
# Repair page: safe root-path fixed, version checker correct and works with missing controller.
s=read('repair.html')
s=replace_once(s,"e.data?.cache === 'niko-arcade-offline-v10'","e.data?.cache === 'niko-arcade-offline-v17'",'repair-version')
s=replace_once(s,"{scope:'/', updateViaCache:'none'}","{scope:'/Niko-games/', updateViaCache:'none'}",'repair-scope')
s=s.replace("await version(reg.active) && await version(navigator.serviceWorker.controller)","await version(reg.active) && (!navigator.serviceWorker.controller || await version(navigator.serviceWorker.controller))")
write('repair.html',s)

# Browser catalog: manifests use logical paths. Prefix only when fetching on Pages.
s=read('retro/catalog.js')
s=replace_once(s,"  async function timedFetch(path, timeout) {", """  function siteAsset(path){
    const script=document.currentScript?.src || new URL('catalog.js',location.href).href;
    const base=new URL('../',script).pathname.replace(/\\/$/,'');
    return path.startsWith(base+'/') ? path : base+path;
  }
  async function timedFetch(path, timeout) {""",'catalog-to-site')
s=replace_once(s,"const response = await fetch(path, { signal:","const response = await fetch(siteAsset(path), { signal:",'catalog-fetch')
# Fix script-resolution after execution: document.currentScript is null inside async calls.
s=s.replace("    const script=document.currentScript?.src || new URL('catalog.js',location.href).href;\n    const base=new URL('../',script).pathname.replace(/\\/$/,'');", "    const base='/Niko-games';")
write('retro/catalog.js',s)

# 3) SW: keep verified cartridge SHA logic, map logical paths to /Niko-games/ URLs.
s=read('sw.js')
s=replace_once(s,'const VERSION = 14;', 'const VERSION = 17;', 'sw-version')
s=replace_once(s,"const CACHE = 'niko-arcade-offline-v14';", "const CACHE = 'niko-arcade-offline-v17';", 'sw-cache')
s=replace_once(s,"  '/intro/splash.jpeg',", "  // intro now consists of a single text-only slide", 'sw-intro')
s=replace_once(s,"'/music-studio/index.html', '/music-studio/studio.js'", "'/kids/math.html'",'sw-music')
# avoid one redundant /kids/math.html if repeated - will handle with unique list below
s=s.replace("'/beauty/places40.js', '/kids/math.html',", "'/beauty/places40.js',")
# add splashless standalone index; and shareable root page
s=s.replace("  '/club.html', '/club.css'", "  '/index.html', '/club.html', '/club.css'")
# dynamic scope prefix of the actual registered SW, rooted in repository subdirectory
s=replace_once(s,"const RETRO_CACHE = 'niko-retro-pinned-4.2.3-v1';", """const RETRO_CACHE = 'niko-retro-pinned-4.2.3-v1';
const SITE_BASE = new URL(self.registration.scope).pathname.replace(/\\/$/, '');
const sitePath = path => SITE_BASE + path;
const logicalPath = path => SITE_BASE ? (path.startsWith(SITE_BASE + '/') ? path.slice(SITE_BASE.length) : null) : path;
""", 'sw-base')
# ensure metadata checks new real path
s=replace_once(s,"    const sameFile = PAGE_PATHS.has(path)\n      ? PAGE_ALIASES.get(finalURL.pathname) === path : finalURL.pathname === path;", "    const actual = logicalPath(finalURL.pathname);\n    const sameFile = PAGE_PATHS.has(path)\n      ? PAGE_ALIASES.get(actual) === path : actual === path;", 'sw-response-validate')
# verify all HTML page types by exact static HTML shell marker and title, not by wrong arcade.js assumption
start=s.index('function validHTML(text, path) {')
end=s.index('\nfunction validJSON(text, path) {',start)
s=s[:start]+"""function validHTML(text, path) {
  // All mini-games have their own entry scripts, not necessarily arcade.js.
  // Require a real NIKO HTML shell; reject soft-200 errors and login screens.
  return /^\\s*<!doctype\\s+html/i.test(text) && /<html\\b/i.test(text) &&
    /<title[^>]*>[^<]+<\/title>/i.test(text.slice(0,9000)) &&
    !/<title[^>]*>[^<]*(?:404|not found|sign in|access denied)<\/title>/i.test(text.slice(0,9000));
}
"""+s[end:]
s=replace_once(s,"const request = new Request(new URL(path, self.location.origin)", "const request = new Request(new URL(sitePath(path), self.location.origin)", 'sw-fetch-fresh')
s=s.replace('await cache.put(path, response.clone());','await cache.put(sitePath(path), response.clone());')
s=s.replace('const response = await cache.match(path);','const response = await cache.match(sitePath(path));')
s=s.replace('const response = await (await caches.open(CACHE)).match(path);','const response = await (await caches.open(CACHE)).match(sitePath(path));')
s=s.replace('const stored = await (await caches.open(CACHE)).match(path);','const stored = await (await caches.open(CACHE)).match(sitePath(path));')
s=s.replace('await (await caches.open(RETRO_CACHE)).match(entry.path);','await (await caches.open(RETRO_CACHE)).match(sitePath(entry.path));')
s=s.replace('await (await caches.open(RETRO_CACHE)).put(entry.path, response.clone());','await (await caches.open(RETRO_CACHE)).put(sitePath(entry.path), response.clone());')
# Precache only current release code to avoid old broken scripts
s=s.replace("    for (const name of [CACHE, ...legacy]) {", "    for (const name of (/(?:\\.html|\\.css|\\.js|\\.json|\\.webmanifest)$/.test(path) ? [CACHE] : [CACHE, ...legacy])) {")
# Cached content opens immediately, even when iPhone thinks network is online but unreachable
s=replace_once(s, "  if (cached && (isMedia || self.navigator?.onLine === false)) return cached;", "  if (cached) return cached;", 'sw-fast-offline')
s=s.replace("<a href=\"/club.html\">", "<a href=\"${sitePath('/club.html')}\">")
# Fetch interception must only match this repository's scope
s=replace_once(s,"  if (request.method !== 'GET' || url.origin !== self.location.origin || url.pathname.startsWith('/api/')) return;", """  const local = logicalPath(url.pathname);
  if (request.method !== 'GET' || url.origin !== self.location.origin || local === null || local.startsWith('/api/')) return;""", 'sw-scope-filter')
s=replace_once(s,"if (ASSET_PATHS.has(url.pathname) && /\\.(mp3|ogg)$/.test(url.pathname)) event.respondWith(audioRange(url.pathname, request).catch(() => unavailable(false)));", "if (ASSET_PATHS.has(local) && /\\.(mp3|ogg)$/.test(local)) event.respondWith(audioRange(local, request).catch(() => unavailable(false)));", 'sw-range')
s=replace_once(s,"  const path = navigation ? (PAGE_ALIASES.get(url.pathname) || url.pathname) : url.pathname;", "  const path = navigation ? (PAGE_ALIASES.get(local) || local) : local;", 'sw-path')
# Prior SW blocked SEGA .gen files because several static hosts label them chemical/x-genbank.
# The bytes are SHA-256 verified against the pinned catalog before caching/playing.
s=s.replace("if (/\\.(data|gen)$/.test(path)) return type === 'application/octet-stream' || type === 'binary/octet-stream';",
            "if (/\\.(data|gen)$/.test(path)) return type !== 'text/html' && type !== 'application/xhtml+xml' && type !== 'application/json';")
if 'chemical/x-genbank' not in s and "type !== 'text/html'" not in s:
    raise RuntimeError('Failed to patch SEGA .gen MIME recognition')
# Prioritize scripts and games over numerous pronunciation clips and gallery images
# so a phone can play even before the complete 50 MB offline package is ready.
s=s.replace("    const todo = [...before.missing];", "    const todo = [...before.missing].sort((a,b)=>assetPriority(a)-assetPriority(b));")
s=s.replace("function prepareOffline() {", "function assetPriority(path) { return /\\.(?:html|js|css|webmanifest)$/.test(path) ? 0 : /\\.json$/.test(path) ? 1 : /\\.(?:wasm|data)$/.test(path) ? 2 : 3; }\nfunction prepareOffline() {")
if 'assetPriority(path)' not in s:raise RuntimeError('Failed priority')
write('sw.js',s)

# 4) Site root index should open the app itself.
shutil.copyfile(ROOT/'club.html',ROOT/'index.html')
(ROOT/'.nojekyll').write_text('',encoding='utf-8')

# Offline status is independent of live presence; do not claim GitHub Pages has an API.
s=read('arcade.js')
s=s.replace("async function sync(){if(syncing||!navigator.onLine)return;", "async function sync(){if(location.hostname.endsWith('.github.io') && !window.NIKO_API_BASE)return;if(syncing||!navigator.onLine)return;")
write('arcade.js',s)

s=read('club.js')
# No requests to nonexistent GitHub Pages API; present the saved local best under nickname.
needle="try{const r=await fetch('/api/leaderboard?game='+game"
if needle not in s: raise RuntimeError('ranking code not located')
helper="""
const HAS_SERVER = !!window.NIKO_API_BASE || !location.hostname.endsWith('.github.io');
function localRanking(game){
  const s=Arcade.read(), nick=s.profile?.name||'Гость';
  const score=Number(s.best?.[game]||PremiumStore.read().best?.[game]||0);
  return score>0?[{rank:1,player:myId||'local',name:nick,score}]:[];
}
function renderLocalRanking(game){
  const entries=localRanking(game);allEntries=entries;total=entries.length;
  render(entries);showPlace({total,me:entries[0]||null});
  $('more').hidden=true;
  $('rank-note').textContent='Личные рекорды на этом устройстве';
  if(!entries.length) $('rank-note').textContent='Рекорды появятся после первой игры';
}
function onlineStats(){
  const host=document.getElementById('online-players');
  const note=document.getElementById('online-note');
  if(!host||!note)return;
  host.replaceChildren();
  const player=Arcade.read().profile;
  if(player){const el=document.createElement('span');el.className='online-player';el.textContent='● '+player.name+' (это ты)';host.append(el)}
  note.textContent=!navigator.onLine?'Офлайн · Локальные рекорды доступны.':
    (HAS_SERVER?'Есть интернет · список игроков обновляется сервером, когда он доступен.':
    'Общий список игроков онлайн требует сервер статистики. GitHub Pages хранит только файлы сайта.');
}
"""
s=s.replace("function showPlace(data){",helper+"\nfunction showPlace(data){",1)
s=s.replace(needle,"if(!HAS_SERVER){renderLocalRanking(game);onlineStats();$('more').disabled=false;return;}try{const r=await fetch((window.NIKO_API_BASE||'')+'/api/leaderboard?game='+game",1)
s=s.replace("function refreshProfile(){const s=Arcade.read()", "function refreshProfile(){const s=Arcade.read()",1)
s=s.replace("window.addEventListener('arcade-change',refreshProfile)","window.addEventListener('arcade-change',()=>{refreshProfile();onlineStats()})",1)
s=s.replace("refreshProfile();loadRank();offlineState();", "refreshProfile();loadRank();offlineState();onlineStats();",1)
s=s.replace("const url=location.origin+'/club.html';", "const url=location.origin+'/Niko-games/club.html';")
s += "\nwindow.addEventListener('online',onlineStats);window.addEventListener('offline',onlineStats);\n"
s=s.replace("navigator.onLine?'● Онлайн':'○ Без интернета'", "navigator.onLine?'● Интернет':'○ Без интернета'")
s=s.replace("'Есть новые рекорды на устройстве. Отправим при подключении к интернету.'", "'Рекорды сохранены на этом устройстве под твоим именем.'")
write('club.js',s)

s=read('club.html')
anchor='<section class="photo-strip"'
if anchor not in s: raise RuntimeError('photo strip not found')
presence='''<section class="presence-panel" aria-label="Пользователи в сети"><h2>Кто онлайн</h2><div id="online-players" aria-live="polite"></div><p id="online-note" role="status">Проверяем доступность статистики…</p></section>'''
s=s.replace(anchor,presence+anchor,1)
s=s.replace('<small id="offline">', '<a class="offline-refresh" href="/Niko-games/repair.html">↻ Обновить</a><small id="offline">',1)
write('club.html',s)
s=read('club.css')
s += "\n.offline-refresh{font-size:12px;color:#ffe1a8;text-decoration:underline;margin-right:9px}.presence-panel{margin:24px 0;padding:20px;border-radius:22px;border:1px solid #ffffff20;background:#0a221d;color:#fff}.presence-panel h2{font-size:21px}.presence-panel p{color:#c8d7ce;line-height:1.5}.online-player{display:inline-block;margin:10px 0;padding:10px 15px;border:1px solid #83bdaa88;border-radius:12px;color:#b5ffd7;font-weight:700}\n"
write('club.css',s)
shutil.copyfile(ROOT/'club.html',ROOT/'index.html')

# Extra: service worker must have no removed links; all asset entries exist on disk.
clean=read('sw.js')
from ast import literal_eval
assets_text=clean.split('const ASSETS = [',1)[1].split('];',1)[0]
found=re.findall(r"'(/[^']+)'",assets_text)
missing=[]
for item in found:
 if item.endswith('/') or '?' in item:continue
 if '/roms/' in item: continue
 if not (ROOT/item.lstrip('/')).exists():missing.append(item)
if missing:print('SW assets missing:',missing)
else:print('SW assets all present',len(found))
# fix on-device shortcut JSON routes (not binary rom manifests)
manifest=json.loads(read('manifest.webmanifest'))
manifest['id']='/Niko-games/club.html'
manifest['start_url']='/Niko-games/club.html'
manifest['scope']='/Niko-games/'
for icon in manifest.get('icons',[]):
 if icon.get('src','').startswith('/') and not icon['src'].startswith('/Niko-games/'):
  icon['src']='/Niko-games'+icon['src']
for shortcut in manifest.get('shortcuts',[]):
 if shortcut.get('url','').startswith('/') and not shortcut['url'].startswith('/Niko-games/'):
  shortcut['url']='/Niko-games'+shortcut['url']
 for icon in shortcut.get('icons',[]):
  if icon.get('src','').startswith('/') and not icon['src'].startswith('/Niko-games/'):
   icon['src']='/Niko-games'+icon['src']
write('manifest.webmanifest',json.dumps(manifest,ensure_ascii=False,indent=2))


# Premium game rankings depend on a server and must never block local play.
p=ROOT/'premium/storage.js'
t=p.read_text(encoding='utf-8')
t=t.replace("async function sync(){if(busy||!navigator.onLine||!Arcade.read().profile)return;", "async function sync(){if(location.hostname.endsWith('.github.io')&&!window.NIKO_API_BASE)return;if(busy||!navigator.onLine||!Arcade.read().profile)return;")
p.write_text(t,encoding='utf-8')
p=ROOT/'premium/engine.js'
t=p.read_text(encoding='utf-8')
t=t.replace(" try{me=await identity();const res=await fetch('/api/leaderboard?game='+key", " try{me=await identity();if(location.hostname.endsWith('.github.io')&&!window.NIKO_API_BASE)throw Error('server-unavailable');const res=await fetch((window.NIKO_API_BASE||'')+'/api/leaderboard?game='+key")
t=t.replace("note.textContent='Играть можно офлайн. Личный рекорд: '+(S.read().best[key]||0)+'. Общий список загрузится при подключении.'", "note.textContent='Личный рекорд: '+(S.read().best[key]||0)+'. Общий рейтинг появится после подключения сервера статистики.'")
p.write_text(t,encoding='utf-8')

p=ROOT/'beauty/places40.js'
t=p.read_text(encoding='utf-8')
pos=t.index("const grid=document.getElementById('grid')")
t=t[:pos]+'const grid=document.getElementById(\'grid\');\nconst fallbackPhotos=[\'dargavs\',\'keli\',\'tsey\',\'kurtat\',\'galiat\',\'ikorta\',\'khardisar\',\'beloti\',\'vladikavkaz\',\'tiri\',\'dzivgis\',\'tskhinval\'];\nfunction localPhoto(label,index){\n const l=label.toLowerCase();\n const named=[[\'даргавс\',\'dargavs\'],[\'кель\',\'keli\'],[\'кели\',\'keli\'],[\'цей\',\'tsey\'],[\'цеи\',\'tsey\'],[\'кармадон\',\'kurtat\'],[\'галиат\',\'galiat\'],[\'дигор\',\'galiat\'],[\'куртат\',\'kurtat\'],[\'згид\',\'tiri\'],[\'башня\',\'ikorta\']];\n const match=named.find(([key])=>l.includes(key));\n const name=match?match[1]:fallbackPhotos[index%fallbackPhotos.length];\n return \'/Niko-games/beauty/media/\'+name+\'.jpg\';\n}\nfunction fileUrl(f){return C+encodeURIComponent(f)+\'?width=1100\'}\nfunction render(filter=\'all\'){\n grid.innerHTML=\'\';\n places.filter(p=>filter===\'all\'||p[1]===filter).forEach((p,i)=>{\n  const card=document.createElement(\'article\'); card.className=\'place\';\n  const original=fileUrl(p[3]); const local=localPhoto(p[0],i);\n  const offline=navigator.onLine===false;\n  const link=\'https://commons.wikimedia.org/wiki/File:\'+encodeURIComponent(p[3]).replace(/%20/g,\'_\');\n  card.innerHTML=`<div class="place-media"><img loading="lazy" src="${offline?local:original}" alt="${p[0]}"></div><div class="place-copy"><span class="v14-badge">${String(i+1).padStart(2,\'0\')} / 40</span><h2>${p[0]}</h2><p>${p[2]}</p><small>📍 Северная Осетия — Алания</small><div class="credit"><a href="${link}" target="_blank" rel="noopener">Фото места: Wikimedia Commons ↗</a></div></div>`;\n  const img=card.querySelector(\'img\'); const credit=card.querySelector(\'.credit\');\n  function showLocal(){img.onerror=null;img.src=local;img.alt=\'Иллюстрация горной Осетии, не фотография конкретного места\';card.classList.add(\'place-using-local\'); if(!credit.querySelector(\'.local-photo-note\')){const note=document.createElement(\'span\');note.className=\'local-photo-note\';note.textContent=\'Офлайн-иллюстрация · \';credit.prepend(note)}}\n  img.onerror=showLocal;\n  if(offline)showLocal();\n  grid.append(card);\n });\n}\ndocument.querySelectorAll(\'[data-f]\').forEach(b=>b.onclick=()=>{document.querySelectorAll(\'[data-f]\').forEach(x=>x.classList.remove(\'active\'));b.classList.add(\'active\');render(b.dataset.f);audio.fx(\'tap\')});render();\naddEventListener(\'online\',()=>render(document.querySelector(\'[data-f].active\')?.dataset.f||\'all\'));\naddEventListener(\'offline\',()=>render(document.querySelector(\'[data-f].active\')?.dataset.f||\'all\'));\naddEventListener(\'pointerdown\',()=>audio.recover(),{passive:true,once:true});\n})();\n'
p.write_text(t,encoding='utf-8')
