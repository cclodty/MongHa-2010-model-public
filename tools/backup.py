"""Zip the project's own work into backups/mongha_<date>.zip.

Kept: scripts (tools, blender), generated textures, the web viewer, Blender/FBX/GLB exports, markers, stills and MP4s,
the Unreal project's Config, .uproject and its own Content (MongHa, Maps, Python), notes (*.md).
Skipped: flythrough PNG frame folders (re-render with tools/ue_12_fly.py), the exported site (tools/export_site.py), the
unbaked preview (tools/preview.py), older backups, Unreal's Saved/Intermediate/DerivedDataCache and Fab / Megaplant /
Dekogon content (re-addable from Fab).
usage: py -3 tools/backup.py
"""
import datetime
import os
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INCLUDE = ['tools', 'blender', 'textures', 'web', 'export', 'refs', 'MongHa2010/Config', 'MongHa2010/Content/MongHa',
           'MongHa2010/Content/Maps', 'MongHa2010/Content/Python', 'MongHa2010/MongHa2010.uproject']
SKIP_DIRS = {'mongha_site', 'web_preview', '__pycache__'}
SKIP_PREFIX = ('fly_',)          # export/renders/fly_* PNG sequences
SKIP_FILES = {'mongha_2010_site.zip'}

out = os.path.join(ROOT, 'backups', f'mongha_{datetime.datetime.now():%Y-%m-%d_%H%M}.zip')
n, size = 0, 0
with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
    for name in [f for f in os.listdir(ROOT) if f.endswith('.md')]:
        z.write(os.path.join(ROOT, name), name)
        n += 1
    for item in INCLUDE:
        full = os.path.join(ROOT, item)
        if os.path.isfile(full):
            z.write(full, item)
            n += 1
            continue
        for base, dirs, files in os.walk(full):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not (d.startswith(SKIP_PREFIX) and os.path.basename(base) == 'renders')]
            for f in files:
                if f in SKIP_FILES:
                    continue
                p = os.path.join(base, f)
                z.write(p, os.path.relpath(p, ROOT))
                n += 1
                size += os.path.getsize(p)
print('BACKUP', out, n, 'files,', round(size / 1e6), 'MB in,', round(os.path.getsize(out) / 1e6), 'MB zip')
