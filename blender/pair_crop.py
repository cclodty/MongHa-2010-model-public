"""Same region of photo and render, stacked (photo on top), scaled.
blender -b --factory-startup -P blender/pair_crop.py -- photo render out.png x0 y0 x1 y1 scale"""
import sys

import bpy
import numpy as np

a = sys.argv[sys.argv.index('--') + 1:]
x0, y0, x1, y1 = (int(v) for v in a[3:7])
sc = float(a[7])


def load(p):
    im = bpy.data.images.load(p)
    w, h = im.size
    return np.array(im.pixels[:], np.float32).reshape(h, w, 4)[::-1, :, :3]


def crop(arr):
    c = arr[y0:y1, x0:x1]
    H, W = int(c.shape[0] * sc), int(c.shape[1] * sc)
    yi = np.clip((np.arange(H) / sc).astype(int), 0, c.shape[0] - 1)
    xi = np.clip((np.arange(W) / sc).astype(int), 0, c.shape[1] - 1)
    return c[yi][:, xi]


p, r = crop(load(a[0])), crop(load(a[1]))
out = np.concatenate([p, np.ones((8, p.shape[1], 3), np.float32), r], 0)
h, w = out.shape[:2]
rgba = np.ones((h, w, 4), np.float32)
rgba[..., :3] = np.clip(out, 0, 1)
im = bpy.data.images.new('o', w, h, alpha=False)
im.pixels[:] = rgba[::-1].ravel()
im.filepath_raw = a[2]
im.file_format = 'PNG'
im.save()
print('PAIR', a[2])
