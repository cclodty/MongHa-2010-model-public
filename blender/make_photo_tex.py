"""Web versions of the Poly Haven CC0 scans in cc0/: albedo normalised (mean 0.5, partly desaturated where the model
supplies the colour), OpenGL normal maps and roughness, resized for the browser. Also a 'grime' detail map.

Run:  blender -b --factory-startup -P make_photo_tex.py
"""
import os
import subprocess

import bpy
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CC0, WEB = os.path.join(ROOT, 'cc0'), os.path.join(ROOT, 'web', 'tex')
# name -> (source folder, desaturation 0..1, size)
SETS = {'plaster': ('painted_plaster_wall', 0.85, 1024), 'cfloor': ('concrete_floor_worn_001', 0.7, 1024),
        'asphalt': ('asphalt_02', 0.3, 1024), 'roof': ('clay_roof_tiles_02', 0.0, 1024), 'shutter': ('painted_metal_shutter', 1.0, 1024)}


def load(path):
    im = bpy.data.images.load(path)
    w, h = im.size
    a = np.array(im.pixels[:], np.float32).reshape(h, w, 4)[:, :, :3]
    bpy.data.images.remove(im)
    return a


def save_jpg(name, a, size):
    tmp = os.path.join(ROOT, 'textures', f'_{name}.png')
    h, w = a.shape[:2]
    rgba = np.ones((h, w, 4), np.float32)
    rgba[:, :, :3] = np.clip(a, 0, 1)
    im = bpy.data.images.new(name, w, h, alpha=False)
    im.pixels.foreach_set(rgba.ravel())
    im.filepath_raw = tmp
    im.file_format = 'PNG'
    im.save()
    bpy.data.images.remove(im)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', tmp, '-vf', f'scale={size}:{size}', '-q:v', '3', os.path.join(WEB, name + '.jpg')], check=True)
    os.remove(tmp)


def srgb_to_lin(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lin_to_srgb(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1 / 2.4) - 0.055)


for name, (folder, desat, size) in SETS.items():
    base = os.path.join(CC0, folder)
    a = srgb_to_lin(load(os.path.join(base, 'Diffuse.jpg')))     # Blender reads JPG pixels as sRGB-encoded values
    lum = a @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    a = a * (1 - desat) + lum[..., None] * desat
    a *= 0.5 / max(float(a.mean()), 1e-4)                          # mean 0.5 in linear; the viewer's colour x2 restores albedo
    save_jpg(name, lin_to_srgb(a), size)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', os.path.join(base, 'nor_gl.jpg'), '-vf', f'scale={size}:{size}', '-q:v', '3',
                    os.path.join(WEB, name + '_n.jpg')], check=True)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', os.path.join(base, 'Rough.jpg'), '-vf', f'scale={size // 2}:{size // 2}', '-q:v', '4',
                    os.path.join(WEB, name + '_r.jpg')], check=True)
    print('photo set', name, folder)

# grime: large-scale stains from the weathered plaster, high-passed, mean 0.5 (viewer multiplies by 2)
g = srgb_to_lin(load(os.path.join(CC0, 'painted_plaster_wall', 'Diffuse.jpg'))) @ np.array([0.2126, 0.7152, 0.0722], np.float32)
g = g / max(float(g.mean()), 1e-4)
g = np.clip(1 + (g - 1) * 1.6, 0.55, 1.25) * 0.5
save_jpg('grime', np.repeat(g[..., None], 3, -1), 1024)
print('PHOTO_TEX_DONE')
