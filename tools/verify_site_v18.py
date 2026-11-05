#!/usr/bin/env python3
"""Validate static GitHub Pages layout, original games and ROM integrity."""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from html.parser import HTMLParser

ROOT=Path(sys.argv[1]).resolve()
assert (ROOT/'club.html').is_file(), 'Expected club.html at published root'
assert (ROOT/'.nojekyll').is_file(), 'Missing .nojekyll'
assert not (ROOT/'music-studio').exists(), 'Song creation must be removed'
assert not (ROOT/'tabletop').exists(), 'Tabletop games must be removed'
assert not (ROOT/'intro'/'splash.jpeg').exists(), 'Intro photo must be removed'
assert 'Shiukaev' in (ROOT/'intro.js').read_text('utf8'), 'Correct introductory name missing'
assert 'Shiucaev' not in (ROOT/'intro.js').read_text('utf8'), 'Wrong name in intro'
assert 'Niko-games/' in (ROOT/'pwa.js').read_text('utf8'), 'Offline scope not fixed'
assert "niko-arcade-offline-v18" in (ROOT/'sw.js').read_text('utf8'), 'Wrong SW cache version'
assert "type !== 'text/html'" in (ROOT/'sw.js').read_text('utf8'), 'ROM MIME compatibility missing'
assert "song" not in (ROOT/'club.html').read_text('utf8').lower().split('class="v14-feature')[0], 'Removed song reference remains'

class Resources(HTMLParser):
    def __init__(self):
        super().__init__(); self.links=[]
    def handle_starttag(self, tag, attrs):
        values=dict(attrs)
        if tag in ('a','img','script','link','iframe','source'):
            value=values.get('src') or values.get('href')
            if value:self.links.append((tag,value))

pages=sorted(ROOT.rglob('*.html'))
missing=[]
for page in pages:
    html=page.read_text('utf8')
    parser=Resources();parser.feed(html)
    for tag,href in parser.links:
        if href.startswith('/Niko-games/'):
            local=ROOT/href[len('/Niko-games/'):].split('?')[0].split('#')[0]
            if not local.exists():missing.append((page.relative_to(ROOT).as_posix(),tag,href))
        elif href.startswith('/') and not href.startswith('/api/'):
            missing.append((page.relative_to(ROOT).as_posix(),tag,href+' [unscoped]'))
assert not missing, f'Broken links: {missing[:20]} ({len(missing)} total)'

js=sorted(ROOT.rglob('*.js'))
errors=[]
for p in js:
    proc=subprocess.run(['node','--check',str(p)],capture_output=True,text=True)
    if proc.returncode:errors.append((p.relative_to(ROOT).as_posix(),proc.stderr[-220:]))
assert not errors, f'Bad JavaScript: {errors[:10]}'

checks=0
for file,key,expected in [('retro/catalog.json','games',11),('retro/runtime/4.2.3/offline-manifest.json','files',None)]:
    values=json.loads((ROOT/file).read_text('utf8'))[key]
    if expected is not None: assert len(values)==expected, f'{file}: expected {expected}, got {len(values)}'
    assert values, f'{file}: empty manifest'
    for item in values:
        dest=ROOT/item['path'].lstrip('/')
        assert dest.is_file(), f'{file}: missing {item["path"]}'
        b=dest.read_bytes()
        assert len(b)==item['size'], f'{file}: wrong size {item["path"]}'
        assert hashlib.sha256(b).hexdigest()==item['sha256'], f'{file}: SHA mismatch {item["path"]}'
        checks+=1
print(f'PASS: {len(pages)} HTML pages, {len(js)} JS files, {checks} hash-verified retro binaries, no broken local links')
