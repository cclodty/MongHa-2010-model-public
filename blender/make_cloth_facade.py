"""Laundry garment atlas (colour + cut-out mask) and a tileable high-rise facade for the context towers.

Run:  blender -b --factory-startup -P make_cloth_facade.py
Writes textures/T_ClothAtlas_BC|Mask, T_Facade_BC|R and export/cloth_cells.json (garment type + size per cell).
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_textures import blur, save, tile_noise  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
rng = np.random.default_rng(1997)


def hexrgb(h):
    h = h.lstrip('#')
    return np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)], np.float32)


# ---------------------------------------------------------------- garments, 4 x 4 cells of 512 px
N, C = 4, 512
# washed-out household colours, as hung out in Macau estates
CLOTH = ['#ecebe4', '#e4e0d4', '#b9c7d3', '#8ea3b8', '#c9c3b5', '#7d8790', '#c98e86', '#d8b4b0', '#e2d39a', '#9fb39a',
         '#41506b', '#5a5c5e', '#a8564c', '#efe9dc', '#d9cfc0', '#6f8fa8']
# garment: (width m, height m)
SIZES = dict(towel=(0.45, 0.85), tshirt=(0.62, 0.66), shirt=(0.68, 0.8), trousers=(0.42, 1.0), shorts=(0.44, 0.5),
             dress=(0.52, 0.95), sheet=(0.95, 1.15), pillow=(0.5, 0.7), socks=(0.32, 0.3))
TYPES = ['towel', 'tshirt', 'shirt', 'trousers', 'tshirt', 'towel', 'shorts', 'dress',
         'sheet', 'tshirt', 'trousers', 'pillow', 'socks', 'shirt', 'towel', 'tshirt']


def poly_mask(x, y, pts):
    """Even-odd point-in-polygon on a pixel grid (pts in 0..1, y down)."""
    inside = np.zeros(x.shape, bool)
    n = len(pts)
    for i in range(n):
        (x0, y0), (x1, y1) = pts[i], pts[(i + 1) % n]
        cond = (y0 > y) != (y1 > y)
        xint = x0 + (y - y0) * (x1 - x0) / (y1 - y0 + 1e-9)
        inside ^= cond & (x < xint)
    return inside


def shape(kind, x, y):
    if kind in ('towel', 'sheet', 'pillow'):
        return (x > 0.03) & (x < 0.97) & (y > 0.0) & (y < 0.99)
    if kind == 'tshirt':
        m = poly_mask(x, y, [(0.3, 0.0), (0.7, 0.0), (0.97, 0.12), (0.88, 0.36), (0.76, 0.3), (0.76, 0.99), (0.24, 0.99), (0.24, 0.3), (0.12, 0.36), (0.03, 0.12)])
        return m & ~(((x - 0.5) ** 2 / 0.012 + y ** 2 / 0.006) < 1)
    if kind == 'shirt':
        m = poly_mask(x, y, [(0.32, 0.0), (0.68, 0.0), (0.92, 0.08), (0.99, 0.75), (0.86, 0.77), (0.8, 0.3), (0.8, 0.99), (0.2, 0.99), (0.2, 0.3), (0.14, 0.77), (0.01, 0.75), (0.08, 0.08)])
        return m & ~(((x - 0.5) ** 2 / 0.008 + y ** 2 / 0.004) < 1)
    if kind == 'trousers':
        return poly_mask(x, y, [(0.12, 0.0), (0.88, 0.0), (0.95, 0.99), (0.56, 0.99), (0.5, 0.3), (0.44, 0.99), (0.05, 0.99)])
    if kind == 'shorts':
        return poly_mask(x, y, [(0.1, 0.0), (0.9, 0.0), (0.98, 0.95), (0.56, 0.95), (0.5, 0.45), (0.44, 0.95), (0.02, 0.95)])
    if kind == 'dress':
        return poly_mask(x, y, [(0.32, 0.0), (0.68, 0.0), (0.72, 0.3), (0.95, 0.99), (0.05, 0.99), (0.28, 0.3)])
    if kind == 'socks':
        a = poly_mask(x, y, [(0.05, 0.0), (0.4, 0.0), (0.4, 0.7), (0.48, 0.95), (0.2, 0.95), (0.05, 0.75)])
        b = poly_mask(x, y, [(0.55, 0.0), (0.92, 0.0), (0.92, 0.75), (0.98, 0.95), (0.7, 0.95), (0.55, 0.72)])
        return a | b
    raise ValueError(kind)


def garment(kind):
    y, x = np.mgrid[0:C, 0:C].astype(np.float32) / C
    col = hexrgb(rng.choice(CLOTH))
    img = np.ones((C, C, 3), np.float32) * col
    pat = rng.random()
    if kind in ('towel', 'sheet') and pat < 0.6:                      # towel bands / sheet stripes
        band = ((y > 0.08) & (y < 0.14)) | ((y > 0.86) & (y < 0.92))
        img[band] = hexrgb(rng.choice(CLOTH)) * 0.9
    if pat < 0.25:                                                    # stripes
        sc = hexrgb(rng.choice(CLOTH))
        st = (np.sin(x * np.pi * 2 * rng.uniform(6, 14)) > 0.3)
        img[st] = img[st] * 0.4 + sc * 0.6
    elif pat < 0.4:                                                   # checks
        sc = hexrgb(rng.choice(CLOTH))
        f = rng.uniform(5, 10)
        ck = (np.sin(x * np.pi * 2 * f) > 0.4) | (np.sin(y * np.pi * 2 * f) > 0.4)
        img[ck] = img[ck] * 0.55 + sc * 0.45
    elif pat < 0.5:                                                   # small print
        sc = hexrgb(rng.choice(CLOTH))
        dots = (np.sin(x * 90) * np.sin(y * 90)) > 0.8
        img[dots] = sc
    # hanging folds, damp darker hem, soft fabric noise
    folds = 0.86 + 0.14 * np.sin(x * np.pi * 2 * rng.uniform(3, 6) + rng.uniform(0, 6)) ** 2
    img *= folds[..., None] * (1.0 - 0.12 * y[..., None])
    img *= (0.94 + 0.12 * tile_noise(C, 8, seed=int(rng.integers(1e6))))[..., None]
    m = shape(kind, x, y).astype(np.float32)
    return blur(img, 1).clip(0, 1), blur(m, 1)


cloth = np.zeros((N * C, N * C, 3), np.float32)
mask = np.zeros((N * C, N * C), np.float32)
cells = []
for k, kind in enumerate(TYPES):
    i, j = k % N, k // N
    g, m = garment(kind)
    cloth[j * C:(j + 1) * C, i * C:(i + 1) * C] = g
    mask[j * C:(j + 1) * C, i * C:(i + 1) * C] = m
    cells.append(dict(i=i, j=j, kind=kind, size=SIZES[kind]))
save('T_ClothAtlas_BC', cloth)
save('T_ClothAtlas_Mask', mask)
with open(os.path.join(ROOT, 'export', 'cloth_cells.json'), 'w', encoding='utf-8') as fh:
    json.dump(dict(n=N, cells=cells), fh, indent=1)

# ---------------------------------------------------------------- high-rise facade, 4 floors x 4 bays = 12 m x 12 m, 2048 px
P = 2048
S = P / 12.0                                                          # px per metre
y, x = np.mgrid[0:P, 0:P].astype(np.float32)
wall = hexrgb('#d7d0c2')
fac = np.ones((P, P, 3), np.float32) * wall
rough = np.ones((P, P), np.float32) * 0.85
tiles = ((np.mod(x, 0.11 * S) < 1.2) | (np.mod(y, 0.06 * S) < 1.2))   # small facade tiles
fac[tiles] *= 0.9
for f in range(4):
    for b in range(4):
        ox, oy = b * 3 * S, f * 3 * S                                 # bay origin (top-left)
        wx0, wx1 = ox + 0.7 * S, ox + 2.3 * S
        wy0, wy1 = oy + 0.7 * S, oy + 2.1 * S                         # window (y down; sill at 0.9 m above floor)
        win = (x > wx0) & (x < wx1) & (y > wy0) & (y < wy1)
        glass = hexrgb(rng.choice(['#3d4a52', '#46545c', '#2f3a40', '#5b6870'])) * (0.8 + 0.4 * ((y - wy0) / (wy1 - wy0)))[..., None]
        if rng.random() < 0.5:                                        # curtain behind the glass
            cc = hexrgb(rng.choice(['#d9cfb8', '#c7b79a', '#e2dfd6', '#a9b7c0']))
            cur = win & (x < wx0 + (wx1 - wx0) * rng.uniform(0.3, 1.0))
            fac[cur] = cc * 0.75
            win = win & ~cur
        fac[win] = glass[win]
        rough[(x > wx0) & (x < wx1) & (y > wy0) & (y < wy1)] = 0.12
        frame = ((x > wx0 - 6) & (x < wx1 + 6) & (y > wy0 - 6) & (y < wy1 + 6)) & ~((x > wx0) & (x < wx1) & (y > wy0) & (y < wy1))
        frame |= (np.abs(x - (wx0 + wx1) / 2) < 3) & (y > wy0) & (y < wy1)
        fac[frame] = hexrgb('#c9cbc8')
        rough[frame] = 0.4
        if rng.random() < 0.65:                                       # 鐵窗 window cage
            cage = ((x > wx0 - 10) & (x < wx1 + 10) & (y > wy0 - 10) & (y < wy1 + 14))
            bars = cage & ((np.mod(x - wx0, 0.12 * S) < 3) | (np.abs(y - wy1 - 10) < 4) | (np.abs(y - wy0 + 6) < 3))
            fac[bars] = hexrgb(rng.choice(['#5d615f', '#7b7f7c', '#3e4241'])) * 0.9
            rough[bars] = 0.5
        if rng.random() < 0.5:                                        # window AC box under / beside
            ax = ox + rng.choice([0.15, 2.35]) * S
            ac = (x > ax) & (x < ax + 0.55 * S) & (y > oy + 1.6 * S) & (y < oy + 2.0 * S)
            fac[ac] = hexrgb('#d8d6ce') * 0.9
            fac[ac & (np.mod(y, 6) < 2)] *= 0.7
        # rust / dirt streak below the sill
        st = (x > wx0 + rng.uniform(0, 0.5) * S) & (x < wx0 + rng.uniform(0.6, 1.6) * S) & (y > wy1) & (y < wy1 + rng.uniform(0.4, 1.2) * S)
        fade = np.clip(1 - (y - wy1) / (1.2 * S), 0, 1)
        fac[st] *= (1 - 0.25 * fade[st])[..., None]
    fl = (y > (f + 1) * 3 * S - 0.12 * S) & (y < (f + 1) * 3 * S)       # floor slab line
    fac[fl] *= 0.85
grime = blur(tile_noise(P, 6, seed=7), 4)
fac *= (0.85 + 0.25 * grime)[..., None]
save('T_Facade_BC', fac.clip(0, 1))
save('T_Facade_R', rough)
print('CLOTH_FACADE_DONE')
