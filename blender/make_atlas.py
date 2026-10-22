"""Window / shop interior atlases (8x8 and 4x4 cells) so every glass pane shows a different room.

Run:  blender -b --factory-startup -P make_atlas.py
Cells are what you would see through a pane in daylight: darker rooms, curtains, blinds, tube lights.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_textures import blur, save, tile_noise  # noqa: E402  (also regenerates the base textures; cheap)

rng = np.random.default_rng(2008)
C = 256


def hexrgb(h):
    h = h.lstrip('#')
    return np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)], np.float32)


WALLS = ['#d9d0bc', '#e0dfd8', '#b9c9b5', '#d8c0a8', '#bcc8cf', '#cfc7a9', '#e2d6c4']
CURTAINS = ['#e9e3d3', '#d9c6a5', '#c98f8f', '#8fae9a', '#7f97b8', '#e6d27a', '#b88c6e', '#f1efe8', '#a35f5f', '#cdb7d4']


def window_cell():
    y, x = np.mgrid[0:C, 0:C].astype(np.float32) / C
    wall = hexrgb(rng.choice(WALLS)) * rng.uniform(0.28, 0.55)
    img = np.ones((C, C, 3), np.float32) * wall
    img *= (0.75 + 0.35 * (1 - np.abs(y - 0.45) * 1.6))[..., None].clip(0.5, 1.1)
    img[y < 0.13] *= 0.7                                                     # ceiling
    if rng.random() < 0.3:                                                   # fluorescent tube
        x0 = rng.uniform(0.1, 0.5)
        img[(y > 0.06) & (y < 0.085) & (x > x0) & (x < x0 + 0.38)] = (1.0, 1.0, 0.97)
    for _ in range(rng.integers(1, 4)):                                      # furniture silhouettes
        fx, fw, fh = rng.uniform(0, 0.8), rng.uniform(0.15, 0.45), rng.uniform(0.2, 0.6)
        col = hexrgb(rng.choice(['#3a2f26', '#5a4a3a', '#2b2b2b', '#6c6255', '#8a8478'])) * rng.uniform(0.4, 0.8)
        img[(x > fx) & (x < fx + fw) & (y > 1 - fh)] = col
    kind = rng.random()
    if kind < 0.18:                                                          # venetian blinds
        slat = (np.sin(y * np.pi * 2 * 22) > 0.2).astype(np.float32)
        col = hexrgb(rng.choice(['#e8e6de', '#d4cdb8', '#9fb4c4']))
        drop = rng.uniform(0.4, 1.0)
        m = (y < drop)[..., None]
        img = np.where(m, col * (0.55 + 0.4 * slat[..., None]), img)
    elif kind < 0.85:                                                        # curtains
        col = hexrgb(rng.choice(CURTAINS))
        folds = 0.72 + 0.28 * np.sin(x * np.pi * 2 * rng.uniform(7, 13) + rng.uniform(0, 6)) ** 2
        sheer = rng.random() < 0.35
        mode = rng.choice(['left', 'right', 'both', 'full'])
        cover = {'left': x < rng.uniform(0.3, 0.6), 'right': x > rng.uniform(0.4, 0.7),
                 'both': (x < rng.uniform(0.15, 0.35)) | (x > rng.uniform(0.65, 0.85)), 'full': x >= 0}[mode]
        cur = col[None, None, :] * folds[..., None] * rng.uniform(0.75, 1.0)
        if rng.random() < 0.3:                                               # printed pattern
            pat = (np.sin(x * 60) * np.sin(y * 60) > 0.6).astype(np.float32)[..., None]
            cur = cur * (1 - 0.25 * pat)
        a = 0.55 if sheer else 1.0
        img = np.where(cover[..., None], img * (1 - a) + cur * a, img)
    img *= (0.9 + 0.2 * tile_noise(C, 4, seed=int(rng.integers(1e6))))[..., None]
    return img.clip(0, 1)


def rect(img, x, y, x0, x1, y0, y1, col):
    img[(x > x0) & (x < x1) & (y > y0) & (y < y1)] = col


def depth(img, x, y, k=0.45):
    """Room seen through glass: the middle of the view is the far, dimmer back wall."""
    r = np.sqrt((x - 0.5) ** 2 + (y - 0.42) ** 2) * 1.6
    return img * (1 - k + k * r.clip(0, 1))[..., None]


def tubes(img, x, y, rows=2):
    for r in range(rows):
        yy = 0.03 + r * 0.045
        x0 = rng.uniform(0.05, 0.45)
        rect(img, x, y, x0, x0 + rng.uniform(0.25, 0.45), yy, yy + 0.012, (1.0, 1.0, 0.96))


GOODS = ['#b89a5c', '#8e4a3d', '#d0ccc0', '#56708a', '#6e8a5e', '#c9b79a', '#b9493c', '#d6bf4a', '#4a6690', '#e4e2da', '#7a6a58']


def shelves(img, x, y, n, y_top=0.16, y_bot=0.86, sat=1.0):
    for s in range(n):
        y0 = y_top + (s + 1) * (y_bot - y_top) / n
        rect(img, x, y, 0, 1, y0, y0 + 0.012, (0.3, 0.28, 0.25))
        xx = rng.uniform(0, 0.03)
        while xx < 0.98:
            w = rng.uniform(0.012, 0.045)
            h = rng.uniform(0.3, 0.85) * (y_bot - y_top) / n
            col = hexrgb(rng.choice(GOODS))
            col = col * sat + col.mean() * (1 - sat)
            rect(img, x, y, xx, xx + w, y0 - h, y0, col * rng.uniform(0.55, 0.9))
            xx += w + rng.uniform(0.0, 0.01)


def shop_cell(n):
    """Shops of the ground-floor arcade: 士多 grocery, 茶餐廳, 五金 hardware, 地產 agency, closed store room."""
    y, x = np.mgrid[0:n, 0:n].astype(np.float32) / n
    kind = rng.choice(['grocery', 'cafe', 'hardware', 'agency', 'store'], p=[0.3, 0.2, 0.2, 0.15, 0.15])
    back = hexrgb(rng.choice(['#d8d2c2', '#cfc9b4', '#c3cbc6', '#d9cdb5'])) * rng.uniform(0.45, 0.65)
    img = np.ones((n, n, 3), np.float32) * back
    img[y < 0.1] *= 0.6
    img[y > 0.84] = hexrgb(rng.choice(['#8a8070', '#6f6a62', '#9a9284'])) * 0.6     # floor
    if kind == 'grocery':
        shelves(img, x, y, rng.integers(4, 6), sat=0.8)
        if rng.random() < 0.6:                                                      # drinks fridge
            fx = rng.uniform(0.55, 0.75)
            rect(img, x, y, fx, fx + 0.22, 0.2, 0.84, (0.75, 0.82, 0.85))
            shelves_f = img[(y > 0.2) & (y < 0.84) & (x > fx) & (x < fx + 0.22)]
            img[(y > 0.2) & (y < 0.84) & (x > fx) & (x < fx + 0.22)] = shelves_f * (0.85 + 0.15 * np.sin(np.arange(len(shelves_f)) * 0.7))[:, None]
        rect(img, x, y, 0.0, rng.uniform(0.35, 0.6), 0.66, 0.84, hexrgb('#7d6a52') * 0.7)    # counter
    elif kind == 'cafe':
        img[(y > 0.12) & (y < 0.5)] = hexrgb(rng.choice(['#e6e1d3', '#d9e0dc'])) * 0.7   # tiled wall
        for k in range(rng.integers(4, 9)):                                           # menu strips on the wall
            mx = 0.05 + k * 0.11
            rect(img, x, y, mx, mx + 0.08, 0.16, 0.36, hexrgb(rng.choice(['#c8423a', '#f0e9d6', '#e3c34d'])) * 0.8)
        rect(img, x, y, 0, 1, 0.4, 0.44, (0.55, 0.6, 0.62))                           # mirror band
        for k in range(4):                                                            # tables and stools
            tx = 0.03 + k * 0.25 + rng.uniform(-0.02, 0.02)
            rect(img, x, y, tx, tx + 0.18, 0.6, 0.63, hexrgb('#d9d4c6') * 0.75)
            rect(img, x, y, tx + 0.08, tx + 0.1, 0.63, 0.84, (0.25, 0.25, 0.25))
            for sx in (tx - 0.03, tx + 0.17):
                rect(img, x, y, sx, sx + 0.04, 0.7, 0.84, hexrgb(rng.choice(['#a8352d', '#2f5f8f', '#d8cfa8'])) * 0.7)
        tubes(img, x, y, 2)
    elif kind == 'hardware':
        shelves(img, x, y, 3, y_top=0.3, sat=0.6)
        for k in range(rng.integers(10, 20)):                                         # goods hanging from the ceiling
            hx, hl = rng.uniform(0, 0.95), rng.uniform(0.08, 0.3)
            rect(img, x, y, hx, hx + rng.uniform(0.02, 0.06), 0.1, 0.1 + hl, hexrgb(rng.choice(GOODS + ['#3f8fcf', '#d9493a'])) * 0.75)
    elif kind == 'agency':
        img[(y > 0.1) & (y < 0.84)] = hexrgb('#e9e6dc') * 0.55
        rect(img, x, y, 0.1, 0.9, 0.62, 0.68, hexrgb('#6b5a46') * 0.7)               # desk
        tubes(img, x, y, 3)
        for gx in range(5):                                                           # listing sheets taped to the glass
            for gy in range(3):
                if rng.random() < 0.8:
                    lx, ly = 0.04 + gx * 0.19, 0.14 + gy * 0.17
                    rect(img, x, y, lx, lx + 0.15, ly, ly + 0.14, (0.93, 0.92, 0.88))
                    rect(img, x, y, lx + 0.01, lx + 0.14, ly + 0.01, ly + 0.035, hexrgb(rng.choice(['#c8423a', '#2f5f8f'])))
    else:
        img *= 0.45
        for k in range(rng.integers(5, 12)):                                          # stacked cartons
            bx, bw, bh = rng.uniform(0, 0.9), rng.uniform(0.08, 0.2), rng.uniform(0.08, 0.3)
            rect(img, x, y, bx, bx + bw, 0.84 - bh, 0.84, hexrgb('#9b7f58') * rng.uniform(0.35, 0.6))
    img = depth(img, x, y, 0.4)
    return blur(img, 1).clip(0, 1)


def library_cell(n):
    """Public library reading room: steel shelving, reading tables, tube lights."""
    y, x = np.mgrid[0:n, 0:n].astype(np.float32) / n
    img = np.ones((n, n, 3), np.float32) * hexrgb('#d6d4c8') * 0.55
    img[y < 0.1] *= 0.7
    tubes(img, x, y, 2)
    img[y > 0.84] = hexrgb('#8f8a7c') * 0.55
    shelves(img, x, y, 5, y_top=0.14, y_bot=0.78, sat=0.45)
    for k in range(int(rng.integers(0, 3))):                                          # shelf-end panels
        px = rng.uniform(0.05, 0.85)
        rect(img, x, y, px, px + 0.06, 0.14, 0.84, hexrgb('#9aa59b') * 0.6)
    if rng.random() < 0.6:                                                            # reading table in front
        rect(img, x, y, 0.0, 1.0, 0.7, 0.74, hexrgb('#a08a68') * 0.65)
        rect(img, x, y, 0.0, 1.0, 0.74, 0.84, hexrgb('#5a5146') * 0.5)
    img = depth(img, x, y, 0.35)
    return blur(img, 1).clip(0, 1)


atlas = np.zeros((8 * C, 8 * C, 3), np.float32)
for i in range(8):
    for j in range(8):
        atlas[j * C:(j + 1) * C, i * C:(i + 1) * C] = window_cell()
save('T_WindowAtlas_BC', atlas)
S = 512
shop = np.zeros((4 * S, 4 * S, 3), np.float32)
for i in range(4):
    for j in range(4):
        shop[j * S:(j + 1) * S, i * S:(i + 1) * S] = shop_cell(S)
save('T_ShopAtlas_BC', shop)
lib = np.zeros((4 * S, 4 * S, 3), np.float32)
for i in range(4):
    for j in range(4):
        lib[j * S:(j + 1) * S, i * S:(i + 1) * S] = library_cell(S)
save('T_LibraryAtlas_BC', lib)
print('ATLAS_DONE')
