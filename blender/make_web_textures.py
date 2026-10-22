"""Second-generation textures for the web viewer (round 3 review):
- T_Mosaic2: 2.5 cm wall mosaic with crisp grout and gentle tile-to-tile variation (tinted per block in the viewer)
- T_Streaks: rain streaks and dirt bands, used as an occlusion multiplier over facades (4 m x 8 m tile)
- T_CourtPave: the courtyard's pale slabs framed by blue-grey bands (photo 14), rotated 45 deg in the viewer
- T_LibraryAtlas: reading rooms seen through the library glass (ceiling lights, tables, low shelves at the back)

Run:  blender -b --factory-startup -P make_web_textures.py
"""
import os
import subprocess
import sys

import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEX, WEB = os.path.join(ROOT, 'textures'), os.path.join(ROOT, 'web', 'tex')
rng = np.random.default_rng(2011)


def save(name, arr, web=None, q=3):
    a = np.asarray(arr, np.float32)
    if a.ndim == 2:
        a = np.repeat(a[..., None], 3, -1)
    h, w = a.shape[:2]
    rgba = np.ones((h, w, 4), np.float32)
    rgba[..., :3] = np.clip(a[..., :3], 0, 1)
    img = bpy.data.images.new(name, w, h, alpha=False)
    img.pixels.foreach_set(np.flipud(rgba).ravel())
    path = os.path.join(TEX, name + '.png')
    img.filepath_raw = path
    img.file_format = 'PNG'
    img.save()
    bpy.data.images.remove(img)
    if web:
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', path, '-q:v', str(q), os.path.join(WEB, web + '.jpg')], check=True)
    print('saved', name, w, h)


def blur(a, r):
    out = a.copy()
    for ax in (0, 1):
        acc = np.zeros_like(out)
        for k in range(-r, r + 1):
            acc += np.roll(out, k, axis=ax)
        out = acc / (2 * r + 1)
    return out


def noise(n, cells, oct_=4, seed=0):
    r = np.random.default_rng(seed)
    out = np.zeros((n, n), np.float32)
    amp, tot = 1.0, 0.0
    for o in range(oct_):
        c = cells * 2 ** o
        g = r.random((c, c)).astype(np.float32)
        y = np.linspace(0, c, n, endpoint=False)
        i0 = np.floor(y).astype(int) % c
        i1 = (i0 + 1) % c
        t = y - np.floor(y)
        t = t * t * (3 - 2 * t)
        rows = g[i0] * (1 - t)[:, None] + g[i1] * t[:, None]
        out += amp * (rows[:, i0] * (1 - t)[None, :] + rows[:, i1] * t[None, :])
        tot += amp
        amp *= 0.5
    return out / tot


def normal_from_height(h, k):
    gx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * k
    gy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * k
    n = np.stack([-gx, gy, np.ones_like(h)], -1)   # DirectX-style green flipped below for three (OpenGL)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    n[..., 1] *= -1
    return n * 0.5 + 0.5


# ---------------------------------------------------------------- wall mosaic, 1024 px = 0.5 m, 20 x 20 tiles
N, T = 1024, 20
y, x = np.mgrid[0:N, 0:N].astype(np.float32)
u, v = x * T / N, y * T / N
tx, ty = u.astype(int), v.astype(int)
fx, fy = u % 1, v % 1
tile = rng.normal(0, 0.035, (T, T)).astype(np.float32)[ty, tx] + 0.86
glaze = 1.0 + 0.05 * (1 - np.clip(((fx - 0.35) ** 2 + (fy - 0.35) ** 2) * 6, 0, 1))
grout = (np.minimum(np.minimum(fx, 1 - fx), np.minimum(fy, 1 - fy)) < 0.045)
base = tile * glaze
base[grout] = 0.66
base *= 0.97 + 0.06 * noise(N, 6, seed=1)
save('T_Mosaic2_BC', base, 'mosaic2')
height = np.where(grout, 0.0, 1.0) - 0.15 * (np.minimum(np.minimum(fx, 1 - fx), np.minimum(fy, 1 - fy)) < 0.12)
save('T_Mosaic2_N', normal_from_height(blur(height.astype(np.float32), 1), 2.0), 'mosaic2_n')

# ---------------------------------------------------------------- rain streaks / grime bands, 512 x 1024 = 4 m x 8 m
W, H = 512, 1024
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
col = noise(W, 24, 3, seed=5)[0]                          # per-column streak strength
streak = np.clip((col - 0.45) * 2.4, 0, 1)[None, :] * (0.4 + 0.6 * noise(H, 3, 2, seed=6)[:, :W])
fade = 0.55 + 0.45 * np.sin(yy / H * np.pi * 2 * 2) ** 2  # streaks start under each floor band and fade down
g = 1.0 - 0.32 * streak * fade
g *= 0.92 + 0.08 * noise(W, 5, seed=8)[np.arange(H) % W][:, :W]
g = blur(g.astype(np.float32), 1)
save('T_Streaks', np.clip(g, 0, 1), 'streaks')

# ---------------------------------------------------------------- courtyard paving, 1024 px = 4 m: 2 m pale slabs, 0.16 m green bands
# (green by 2008-10: photo 1, MH023; sunlit about #87ae8d)
N = 1024
y, x = np.mgrid[0:N, 0:N].astype(np.float32)
m = N / 4.0
slab = 0.80 + 0.05 * noise(N, 10, seed=11) + 0.06 * (rng.random((N, N)).astype(np.float32) - 0.5) * 0.6
for k in range(2):
    for j in range(2):
        slab[int(j * 2 * m):int((j + 1) * 2 * m), int(k * 2 * m):int((k + 1) * 2 * m)] *= rng.uniform(0.96, 1.03)
joint = (np.mod(x, 0.5 * m) < 2) | (np.mod(y, 0.5 * m) < 2)
slab[joint] *= 0.86
band = (np.mod(x + 0.08 * m, 2 * m) < 0.16 * m) | (np.mod(y + 0.08 * m, 2 * m) < 0.16 * m)
img = np.stack([slab, slab * 0.995, slab * 0.98], -1)
bc = np.array([0.40, 0.58, 0.47], np.float32) * (0.9 + 0.12 * noise(N, 12, seed=12))[..., None]
img[band] = bc[band]
img *= (0.93 + 0.1 * noise(N, 3, seed=13))[..., None]     # weathering patches
save('T_CourtPave_BC', img, 'courtpave')
h = np.where(band | joint, 0.0, 1.0).astype(np.float32)
save('T_CourtPave_N', normal_from_height(blur(h, 2), 1.2), 'courtpave_n')


# ---------------------------------------------------------------- library reading rooms (4 x 4 cells of 512)
def hexrgb(hh):
    hh = hh.lstrip('#')
    return np.array([int(hh[i:i + 2], 16) / 255 for i in (0, 2, 4)], np.float32)


def reading_room(n):
    y, x = np.mgrid[0:n, 0:n].astype(np.float32) / n
    img = np.zeros((n, n, 3), np.float32)
    hor = rng.uniform(0.40, 0.48)                         # eye level / vanishing line
    ceil = y < hor
    img[ceil] = hexrgb('#e7e6df') * (0.78 + 0.22 * (y[ceil] / hor))[:, None]
    for k in range(5):                                    # rows of fluorescent tubes receding to the horizon
        t = (k + 1) / 6
        yy = hor * (1 - t) ** 1.6 * 0.95
        hw = 0.42 * (1 - t) + 0.04
        th = 0.012 * (1 - t) + 0.003
        for cx in (0.3, 0.7):
            m = (np.abs(y - yy) < th) & (np.abs(x - (0.5 + (cx - 0.5) * (1 - t))) < hw * 0.35)
            img[m] = (1.0, 1.0, 0.97)
    wall = (y >= hor) & (y < hor + 0.18)
    img[wall] = hexrgb(rng.choice(['#d9d5c6', '#cfd6d0', '#e0dccd'])) * 0.82
    if rng.random() < 0.7:                                # low shelving along the far wall
        y0 = hor + 0.05
        xx = 0.0
        while xx < 1:
            w = rng.uniform(0.006, 0.016)
            hh = rng.uniform(0.04, 0.09)
            c = hexrgb(rng.choice(['#8c6f55', '#6d7f8f', '#a39a86', '#7d8a6f', '#b8b0a0'])) * 0.75
            m = (x > xx) & (x < xx + w) & (y > y0 + 0.12 - hh) & (y < y0 + 0.12)
            img[m] = c
            xx += w + rng.uniform(0, 0.004)
        img[(y > y0 + 0.12) & (y < y0 + 0.13)] = hexrgb('#5d5a52')
    floor = y >= hor + 0.18
    img[floor] = hexrgb('#a8a397') * (0.7 + 0.3 * (y[floor] - hor))[:, None]
    for k in range(rng.integers(1, 3)):                   # reading tables and chairs in the foreground
        ty = rng.uniform(0.66, 0.8)
        tx = rng.uniform(0.05, 0.55)
        tw = rng.uniform(0.3, 0.45)
        img[(y > ty) & (y < ty + 0.025) & (x > tx) & (x < tx + tw)] = hexrgb('#c8b48e') * 0.9
        for lx in (tx + 0.02, tx + tw - 0.03):
            img[(y > ty + 0.025) & (y < ty + 0.14) & (x > lx) & (x < lx + 0.012)] = hexrgb('#4f4a44')
        for cx in np.linspace(tx + 0.04, tx + tw - 0.08, rng.integers(2, 4)):
            img[(y > ty + 0.05) & (y < ty + 0.16) & (x > cx) & (x < cx + 0.05)] = hexrgb(rng.choice(['#3f6f5a', '#7a4a3a', '#56606b'])) * 0.8
    for cxp in rng.uniform(0.1, 0.9, rng.integers(0, 2)):  # a structural column
        img[(x > cxp) & (x < cxp + 0.035) & (y > 0.05)] = hexrgb('#ece9e1') * 0.85
    img *= (0.92 + 0.12 * noise(n, 4, seed=int(rng.integers(1e6))))[..., None]
    return blur(img, 1)


S = 512
atlas = np.zeros((4 * S, 4 * S, 3), np.float32)
for i in range(4):
    for j in range(4):
        atlas[j * S:(j + 1) * S, i * S:(i + 1) * S] = reading_room(S)
save('T_LibraryAtlas_BC', atlas, 'lib')
print('WEB_TEXTURES_DONE')
