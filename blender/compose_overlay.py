"""Side-by-side and 50 % blend of a photo and a render of the same camera.
blender -b --factory-startup -P blender/compose_overlay.py -- photo.jpg render.png out_prefix"""
import sys

import bpy
import numpy as np

a = sys.argv[sys.argv.index('--') + 1:]


def load(p):
    im = bpy.data.images.load(p)
    w, h = im.size
    return np.array(im.pixels[:], np.float32).reshape(h, w, 4)[::-1, :, :3]


def save(arr, path):
    h, w = arr.shape[:2]
    rgba = np.ones((h, w, 4), np.float32)
    rgba[..., :3] = np.clip(arr, 0, 1)
    im = bpy.data.images.new('o', w, h, alpha=False)
    im.pixels[:] = rgba[::-1].ravel()
    im.filepath_raw = path
    im.file_format = 'PNG'
    im.save()
    print('SAVED', path)


ph, rd = load(a[0]), load(a[1])
assert ph.shape == rd.shape, (ph.shape, rd.shape)
save(0.5 * ph + 0.5 * rd, a[2] + '_blend.png')
gap = np.ones((ph.shape[0], 12, 3), np.float32)
save(np.concatenate([ph, gap, rd], 1), a[2] + '_side.png')
