/* Reproducible GitHub Pages offline smoke test with no network or browser downloads. */
'use strict';
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const assert=require('node:assert/strict');
const {webcrypto}=require('node:crypto');
const dir=path.resolve(process.argv[2] || process.cwd());
const origin='https://niko.test', base='/Niko-games';
const events={};
const data=new Map();
class Cache {
  constructor(){this.records=new Map()}
  async match(p){const k=typeof p==='string'?p:p.url;const v=this.records.get(k);return v?new Response(v.body.slice(0),{status:v.status,headers:v.headers}):undefined}
  async put(p,response){const k=typeof p==='string'?p:p.url;this.records.set(k,{body:await response.arrayBuffer(),status:response.status,headers:new Headers(response.headers)})}
}
const caches={async open(k){if(!data.has(k))data.set(k,new Cache());return data.get(k)},async keys(){return Array.from(data.keys())},async delete(k){return data.delete(k)}};
function contentType(p){const ext=path.extname(p).toLowerCase();return ({'.html':'text/html','.js':'text/javascript','.css':'text/css','.json':'application/json','.webmanifest':'application/manifest+json','.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.webp':'image/webp','.mp3':'audio/mpeg','.ogg':'audio/ogg','.wasm':'application/wasm','.gen':'chemical/x-genbank','.data':'application/octet-stream'})[ext]||'application/octet-stream'}
let offline=false;
async function virtualFetch(request){
  if(offline) throw Error('network disconnected');
  const u=new URL(request.url||String(request));
  if(u.origin!==origin||!u.pathname.startsWith(base+'/')) throw Error('invalid host/path');
  const rel=decodeURIComponent(u.pathname.slice(base.length+1));
  if(rel.includes('..')||rel.startsWith('/'))return new Response('Forbidden',{status:403});
  const full=path.resolve(dir,rel);
  if(!full.startsWith(dir+path.sep)||!fs.existsSync(full)||!fs.statSync(full).isFile())return new Response('Not found',{status:404});
  return new Response(fs.readFileSync(full),{status:200,headers:{'content-type':contentType(full)}});
}
const self={registration:{scope:origin+base+'/'},location:{origin},navigator:{onLine:true},clients:{async claim(){},async matchAll(){return []}},skipWaiting:async()=>{},addEventListener(type,callback){events[type]=callback}};
const ctx=vm.createContext({self,caches,fetch:virtualFetch,Request,Response,Headers,AbortController,URL,console,crypto:webcrypto,TextEncoder,TextDecoder,Date,ArrayBuffer,Uint8Array,Math,setTimeout,clearTimeout});
vm.runInContext(fs.readFileSync(path.join(dir,'sw.js'),'utf8')+'\nglobalThis.testing={prepareOffline,prepareRetroOffline,offlineStatus};',ctx,{filename:'sw.js'});
(async()=>{
  const st=await ctx.testing.prepareOffline();
  assert.equal(st.ready,true,`shell missing ${st.missing.length} files: ${st.missing.slice(0,9)}`);
  const rt=await ctx.testing.prepareRetroOffline();
  assert.equal(rt.ready,true,`retro missing ${rt.missing.length} files: ${rt.missing.slice(0,9)}`);
  assert.equal(rt.games,11);
  const manifest=JSON.parse(fs.readFileSync(path.join(dir,'retro/runtime/4.2.3/offline-manifest.json'),'utf8'));
  const expectedRetro=11+manifest.files.length;
  assert.equal(rt.total,expectedRetro);
  offline=true;ctx.self.navigator.onLine=false;
  const pages=['club.html','index.html','games/snake.html','games/tetris.html','games/runner.html','games/obby.html','games/sudoku.html','premium/neon.html','premium/magic.html','kids/sofia.html','kids/math.html','kids/coloring.html','adventures/fishing.html','beauty/index.html','beauty/places40.html','ossetian/index.html','heritage/index.html','retro/index.html','retro/player.html','retro/tv.html','retro/emulator.html'];
  async function request(relative,navigate){
    let result;
    const event={request:{method:'GET',url:origin+base+'/'+relative,mode:navigate?'navigate':'cors',headers:new Headers()},respondWith(value){result=value},waitUntil() {}};
    events.fetch(event);
    assert(result,'SW did not intercept: '+relative);
    return result;
  }
  for(const page of pages){const res=await request(page,true); assert.equal(res.status,200,`offline page: ${page}`); assert.match(await res.text(),/<!doctype html>/i)}
  for(const asset of ['club.js','arcade.js','sw.js','premium/engine.js','retro/catalog.js','retro/runtime/4.2.3/data/loader.js']){
    if(asset==='sw.js')continue;
    const res=await request(asset,false);assert.equal(res.status,200,`offline script: ${asset}`)
  }
  for(const rom of ['sonic.gen','aladdin.gen','contra-hard-corps.gen','mortal-kombat-3.gen','ultimate-mortal-kombat-3.gen']){
    const res=await request('retro/roms/'+rom,false);assert.equal(res.status,200,`offline rom: ${rom}`);assert.ok((await res.arrayBuffer()).byteLength>100000);
  }
  console.log(`PASS offline: ${pages.length} pages, ${rt.total} verified retro files (${rt.games} cartridges), all scripts, with network disabled`);
})().catch(error=>{console.error('FAIL',error);process.exitCode=1});
