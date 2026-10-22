"""Project site points with a solved camera JSON and mark them on an image (white cross + label index).
blender -b --factory-startup -P blender/mark_points.py -- cam.json image.png out.png x,y,z ..."""
import json
import sys

import bpy
import numpy as np

a = sys.argv[sys.argv.index('--') + 1:]
c = json.load(open(a[0], encoding='utf-8'))
C, fwd, right, up = (np.array(c[k]) for k in ('pos', 'fwd', 'right', 'up'))
im = bpy.data.images.load(a[1])
w, h = im.size
px = np.array(im.pixels[:], np.float32).reshape(h, w, 4)[::-1].copy()
for i, s in enumerate(a[3:]):
    P = np.array([float(v) for v in s.split(',')])
    v = P - C
    zc = v @ fwd
    u_, v_ = c['cx'] + c['f_px'] * (v @ right) / zc, c['cy'] - c['f_px'] * (v @ up) / zc
    iu, iv = int(round(u_)), int(round(v_))
    print('PT', i, s, '->', iu, iv)
    for d in range(-9, 10):
        for (x, y) in ((iu + d, iv), (iu, iv + d)):
            if 0 <= x < w and 0 <= y < h:
                px[y, x, :3] = (1, 0, 1) if abs(d) > 2 else (1, 1, 1)
out = bpy.data.images.new('m', w, h, alpha=True)
out.pixels[:] = px[::-1].ravel()
out.filepath_raw = a[2]
out.file_format = 'PNG'
out.save()
