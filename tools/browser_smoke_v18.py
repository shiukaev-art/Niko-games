#!/usr/bin/env python3
"""Browser smoke suite for every public NIKO ARCADE screen and game start."""
import os, sys
from playwright.sync_api import sync_playwright
BASE=os.environ.get('NIKO_TEST_URL','http://127.0.0.1:8765/Niko-games/')
PAGES=[
 'club.html','index.html','games/snake.html','games/tetris.html',
 'games/runner.html','games/obby.html','games/sudoku.html',
 'premium/neon.html','premium/magic.html','kids/sofia.html',
 'kids/coloring.html','kids/math.html','adventures/fishing.html',
 'beauty/index.html','beauty/places40.html','heritage/index.html',
 'ossetian/index.html','retro/index.html','retro/player.html',
 'retro/tv.html','retro/controller.html','retro/join.html',
 'feedback/index.html','help/connection.html',
 'repair.html','refresh-v18.html'
]
ACTIONS={
 'beauty/index.html':'#start',
 'ossetian/index.html':'#start',
 'kids/math.html':'#answers button:first-child',
 'games/snake.html':'#start',
 'games/tetris.html':'#start',
 'games/runner.html':'#start',
 'games/obby.html':'#restart',
 'games/sudoku.html':'#restart',
 'premium/neon.html':'#play',
 'premium/magic.html':'#play',
 'kids/sofia.html':'#random',
 'kids/coloring.html':'#magic',
 'adventures/fishing.html':'#catch',
}
# Known WebGL and third-party font issues are excluded; game JavaScript errors are not.
failures=[]
with sync_playwright() as pw:
  browser=pw.chromium.launch(headless=True,args=['--no-sandbox','--disable-dev-shm-usage','--autoplay-policy=no-user-gesture-required'])
  context=browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True,device_scale_factor=2,service_workers='block')
  for filename in PAGES:
    page=context.new_page(); errors=[];assets=[]
    page.on('pageerror',lambda e: errors.append(str(e)))
    page.on('response',lambda response:assets.append((response.status,response.url)) if response.status>=400 and response.url.startswith(BASE) else None)
    try:
      url=BASE+filename
      resp=page.goto(url,wait_until='domcontentloaded',timeout=14000)
      page.wait_for_timeout(350)
      if not resp or resp.status!=200:raise RuntimeError('HTTP '+str(resp.status if resp else 'none'))
      if page.locator('body').inner_text(timeout=2500).strip()=='' :raise RuntimeError('Blank page')
      intro=page.locator('.niko-intro-skip')
      if intro.is_visible(): intro.click()
      if filename in ('games/obby.html','games/sudoku.html'):
        page.locator('#classic-intro button').click()
      if filename in ACTIONS:
        button=page.locator(ACTIONS[filename]).first
        button.wait_for(state='attached',timeout=4000)
        button.click(timeout=5000)
        page.wait_for_timeout(200)
        if filename=='games/runner.html':
          page.locator('#overlay').wait_for(state='hidden',timeout=3000)
          page.wait_for_function("Number(document.querySelector('#score').textContent)>0",timeout=5000)
      if filename=='retro/index.html':
        page.locator('#shared-library a[href*="player.html"]').first.wait_for(state='attached',timeout=10000)
        n=page.locator('#shared-library a[href*="player.html"]').count()
        if n!=11:raise RuntimeError('Expected 11 cartridges, got '+str(n))
      if filename=='retro/player.html':
        page.close(); page=context.new_page(); errors=[]; assets=[]
        page.on('pageerror',lambda e: errors.append(str(e)))
        resp=page.goto(BASE+'retro/player.html?id=shared-sonic',wait_until='domcontentloaded',timeout=14000)
        page.wait_for_function("document.title.includes('Sonic')",timeout=16000)
      if 'Ждём подключение' in page.title() or 'Ждём подключение' in page.locator('h1').all_text_contents():
        raise RuntimeError('Loaded offline fallback instead of game')
      if errors:raise RuntimeError('JavaScript: '+str(errors[:2]))
      if assets:raise RuntimeError('Bad local files: '+str(assets[:4]))
      print('PASS',filename,'action='+ACTIONS.get(filename,'open'),flush=True)
    except Exception as e:
      failures.append((filename,str(e)[:2500]));print('FAIL',filename,failures[-1][1],flush=True)
    finally:page.close()
  # Test the internal emulator through its real parent handshake, for every ROM.
  import json, urllib.request
  catalog=json.load(urllib.request.urlopen(BASE+'retro/catalog.json'))
  for cart in catalog['games']:
    page=context.new_page()
    try:
      page.goto(BASE+'retro/player.html?id='+cart['id'],wait_until='domcontentloaded')
      intro=page.locator('.niko-intro-skip')
      if intro.is_visible(): intro.click()
      launch=page.frame_locator('iframe').get_by_text('Запустить игру',exact=True)
      launch.click(timeout=60000)
      page.wait_for_function("document.querySelector('#player-status').textContent.includes('Сохранения')",timeout=90000)
      print('PASS cartridge boot',cart['id'],flush=True)
    except Exception as e:
      failures.append((cart['id'],str(e)))
      print('FAIL cartridge boot',cart['id'],str(e),flush=True)
    finally: page.close()
  browser.close()
if failures:
  print('FAILED:',len(failures),'/',len(PAGES),file=sys.stderr)
  sys.exit(1)
print('PASS browser smoke:',len(PAGES),'pages',len(ACTIONS),'game interactions and 11 ROM links')
