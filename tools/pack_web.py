"""Wrap the baked GLBs as JSON (base64) so the artifact host serves them; the viewer decodes them itself.

Run after web_bake.py:  py -3 tools/pack_web.py
"""
import base64
import json
import os

ASSETS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'web', 'assets')
man = json.load(open(os.path.join(ASSETS, 'manifest.json'), encoding='utf-8'))
for f in man['files']:
    glb = os.path.join(ASSETS, f['glb'])
    data = open(glb, 'rb').read()
    out = f['glb'].replace('.glb', '.glb.json')
    with open(os.path.join(ASSETS, out), 'w', encoding='ascii') as fh:
        json.dump({'format': 'glb-base64', 'name': f['glb'], 'data': base64.b64encode(data).decode('ascii')}, fh)
    f['packed'] = out
    f['packed_bytes'] = os.path.getsize(os.path.join(ASSETS, out))
    print(out, f['packed_bytes'] // 1024, 'KB')
with open(os.path.join(ASSETS, 'manifest.json'), 'w', encoding='utf-8') as fh:
    json.dump(man, fh, ensure_ascii=False, indent=1)
print('PACKED', sum(f['packed_bytes'] for f in man['files']) // 1048576, 'MB')
