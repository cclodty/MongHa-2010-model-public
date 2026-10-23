"""Rebuild the model and refresh the unbaked web preview in one go (about fifteen seconds, no GPU needed).

Run:  python tools/preview.py [--focus=label:px,py,pz:tx,ty,tz:fov] [--bevel] [--serve]
  1. blender/build_estate.py -> export/MongHa_2010.blend, export/markers.json
  2. blender/web_preview.py  -> export/web_preview/assets/ (Draco GLBs, their .glb.json wrappers, manifest.json)
  3. web/index.html, tex/ and draco/ copied next to them, so export/web_preview/ is a complete site; claude.html is the
     same page for publishing as a claude.ai artifact (that host serves .glb.json, tex/ and draco/ beside it)
--focus adds a viewpoint of what changed (site metres: x along the avenue, y up, z into the estate; fov in degrees);
the page jumps to it once per build, otherwise it reopens where the viewer left off.
--serve then serves the folder on http://localhost:8000/.
Blender: the BLENDER environment variable, else `blender` on the PATH.
"""
import json
import os
import shutil
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(ROOT, 'web')
OUT = os.path.join(ROOT, 'export', 'web_preview')
BLENDER = os.environ.get('BLENDER', 'blender')
opt = {a.split('=', 1)[0]: (a.split('=', 1)[1] if '=' in a else True) for a in sys.argv[1:] if a.startswith('--')}


def run(*args):
    t = time.time()
    r = subprocess.run([BLENDER, '-b', *args], cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if r.returncode or 'Traceback' in r.stdout + r.stderr:
        sys.exit(r.stdout[-4000:] + r.stderr[-4000:] + f'\nFAILED: {args}')
    for line in r.stdout.splitlines():
        if line.startswith(('FACES', 'WEB_PREVIEW_DONE')):
            print(line)
    print(f'  {os.path.basename(next(a for a in args if a.endswith(".py")))}: {time.time() - t:.0f}s')


run('--factory-startup', '-P', os.path.join('blender', 'build_estate.py'))
run(os.path.join('export', 'MongHa_2010.blend'), '-P', os.path.join('blender', 'web_preview.py'), '--',
    *(['--bevel'] if '--bevel' in opt else []))

man_path = os.path.join(OUT, 'assets', 'manifest.json')
if '--focus' in opt:
    label, p, t, fov = opt['--focus'].split(':')
    man = json.load(open(man_path, encoding='utf-8'))
    man['focus'] = dict(label=label, p=[float(v) for v in p.split(',')], t=[float(v) for v in t.split(',')], fov=float(fov))
    with open(man_path, 'w', encoding='utf-8') as fh:
        json.dump(man, fh, ensure_ascii=False, indent=1)

page = open(os.path.join(WEB, 'index.html'), encoding='utf-8').read()   # claude.ai adds the document skeleton; a plain server does not
open(os.path.join(OUT, 'index.html'), 'w', encoding='utf-8').write('<!doctype html>\n<meta charset="utf-8">\n' + page)
# claude.html: the page to publish as a claude.ai artifact, named apart from the baked one
open(os.path.join(OUT, 'claude.html'), 'w', encoding='utf-8').write(page.replace('<title>望廈平民新邨 2010</title>', '<title>望廈 2010 工作預覽</title>', 1))
for d in ('tex', 'draco'):
    os.makedirs(os.path.join(OUT, d), exist_ok=True)
    for n in os.listdir(os.path.join(WEB, d)):
        src, dst = os.path.join(WEB, d, n), os.path.join(OUT, d, n)
        if not os.path.exists(dst) or os.path.getmtime(src) > os.path.getmtime(dst):
            shutil.copy2(src, dst)
print('PREVIEW', OUT)

if '--serve' in opt:
    print('http://localhost:8000/  (Ctrl+C to stop)')
    subprocess.run([sys.executable, '-m', 'http.server', '8000'], cwd=OUT)
