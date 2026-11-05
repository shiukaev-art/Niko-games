'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {webcrypto}=require('node:crypto');
const root=path.resolve(process.argv[2]);
const origin='https://shiukaev-art.github.io';
Object.defineProperty(globalThis,'navigator',{value:{onLine:true},configurable:true});
let mode='normal',fallbacks=0;
global.fetch=async function(url){
 const u=new URL(url,origin);
 assert.equal(u.origin,origin,'A ROM request escaped the host');
 assert.ok(u.pathname.startsWith('/Niko-games/'),'Unscoped retro ROM request');
 const filename=decodeURIComponent(u.pathname.slice('/Niko-games/'.length));
 assert.ok(!filename.includes('..'));
 if(mode==='fallback' && filename.endsWith('.gen') && !u.searchParams.has('niko-direct'))return new Response('Bad service worker',{status:503});
 if(u.searchParams.has('niko-direct')) fallbacks++;
 const target=path.join(root,filename);
 if(!fs.existsSync(target)) return new Response('Not found',{status:404});
 const type=filename.endsWith('.json')?'application/json':filename.endsWith('.gen')?'chemical/x-genbank':'application/octet-stream';
 return new Response(fs.readFileSync(target),{status:200,headers:{'content-type':type}});
};
const api=require(path.join(root,'retro/catalog.js'));
(async()=>{
 const games=await api.load();assert.equal(games.length,11);
 for(const game of games){
   const row=await api.read(game.id);assert(row);assert.equal(row.file.size,game.size);
   assert.equal(row.name,game.name);
 }
 mode='fallback';
 for(const game of games){const row=await api.read(game.id);assert(row?.file?.size===game.size)}
 assert.equal(fallbacks,11,'Emergency bypass was not exercised for every game');
 console.log(`PASS retro: ${games.length} cartridges, full file + SHA256 checks, ${fallbacks} direct network recoveries`);
})().catch(err=>{console.error('FAIL retro',err);process.exitCode=1});
