"""Procedural, tileable PBR textures for the Mong-Ha estate (written as PNG for Unreal).

Run:  blender -b --factory-startup -P make_textures.py
Normal maps are DirectX convention (Unreal default). Base colours are near-neutral where
Unreal tints them per material instance (plaster colours, mosaic red / yellow).
"""
import os

import bpy
import numpy as np

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'textures')
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(1988)


def save(name, arr):
    """arr: HxWx{1,3,4} float 0..1, row 0 = top."""
    a = np.asarray(arr, dtype=np.float32)
    if a.ndim == 2:
        a = a[..., None]
    h, w, c = a.shape
    rgba = np.ones((h, w, 4), np.float32)
    if c == 1:
        rgba[..., :3] = a
    else:
        rgba[..., :c] = a
    img = bpy.data.images.new(name, w, h, alpha=True)
    img.pixels.foreach_set(np.flipud(rgba).ravel())
    img.filepath_raw = os.path.join(OUT, name + '.png')
    img.file_format = 'PNG'
    img.save()
    bpy.data.images.remove(img)
    print('saved', name, w, h)


def blur(a, r):
    """Cheap separable box blur with wrap-around (keeps tiling)."""
    out = a.copy()
    for axis in (0, 1):
        acc = np.zeros_like(out)
        for k in range(-r, r + 1):
            acc += np.roll(out, k, axis=axis)
        out = acc / (2 * r + 1)
    return out


def tile_noise(n, cells, octaves=4, seed=0):
    """Tileable value noise in 0..1."""
    g = np.random.default_rng(seed)
    out = np.zeros((n, n), np.float32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        c = cells * 2 ** o
        grid = g.random((c, c)).astype(np.float32)
        ys = np.linspace(0, c, n, endpoint=False)
        y0 = np.floor(ys).astype(int)
        f = ys - y0
        f = f * f * (3 - 2 * f)
        y1 = (y0 + 1) % c
        rows = grid[y0] * (1 - f)[:, None] + grid[y1] * f[:, None]
        layer = rows[:, y0] * (1 - f)[None, :] + rows[:, y1] * f[None, :]
        out += layer * amp
        tot += amp
        amp *= 0.5
    return out / tot


def normal_from_height(h, strength):
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 0.5 * strength
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * 0.5 * strength   # +y = down the image
    n = np.stack([-dx, -dy, np.ones_like(h)], -1)                   # DirectX: green = -dh/dy_up = +... flipped
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return n * 0.5 + 0.5


N = 1024
yy, xx = np.mgrid[0:N, 0:N].astype(np.float32)

# ---------------------------------------------------------------- 紙皮石 mosaic (1024 px = 0.5 m, 2.5 cm tiles)
cells = 20
t = N / cells
u, v = (xx % t) / t, (yy % t) / t
edge = np.minimum(np.minimum(u, 1 - u), np.minimum(v, 1 - v))
tile_h = np.clip(edge / 0.09, 0, 1) ** 0.6
ti, tj = (xx // t).astype(int), (yy // t).astype(int)
jit = rng.random((cells, cells)).astype(np.float32)[tj, ti]
grout = tile_h < 0.25
bc = 0.78 + 0.18 * (jit - 0.5)
bc = np.where(grout, 0.42, bc) * (0.9 + 0.1 * tile_noise(N, 8, seed=1))
save('T_Mosaic_BC', np.repeat(bc[..., None], 3, -1))
save('T_Mosaic_N', normal_from_height(blur(tile_h, 1), 6.0))
save('T_Mosaic_R', np.where(grout, 0.85, 0.28 + 0.1 * jit))

# ---------------------------------------------------------------- 通花磚 breeze block (1024 px = 0.6 m: 2x2 blocks, round holes)
t = N / 2
u, v = (xx % t) / t - 0.5, (yy % t) / t - 0.5
r = np.sqrt(u * u + v * v)
hole = r < 0.33
joint = (np.abs(u) > 0.47) | (np.abs(v) > 0.47)
h = np.where(joint, 0.2, 1.0) - np.clip((0.4 - r) / 0.07, 0, 1) * 0.35
h = blur(np.where(hole, 0.0, h), 2)
conc = 0.62 + 0.12 * tile_noise(N, 16, seed=2) - 0.08 * joint
save('T_Breeze_BC', np.repeat(conc[..., None], 3, -1))
save('T_Breeze_N', normal_from_height(h, 10.0))
save('T_Breeze_Mask', np.where(hole, 0.0, 1.0))

# ---------------------------------------------------------------- chain-link fence (512 px = 0.1 m diamond)
M2 = 512
y2, x2 = np.mgrid[0:M2, 0:M2].astype(np.float32) / M2
d1 = np.abs(((x2 + y2) % 1.0) - 0.5)
d2 = np.abs(((x2 - y2) % 1.0) - 0.5)
wire = (np.minimum(np.abs(d1 - 0.5), d1) < 0.035) | (np.minimum(np.abs(d2 - 0.5), d2) < 0.035)
save('T_ChainLink_Mask', np.where(wire, 1.0, 0.0))

# ---------------------------------------------------------------- terracotta roof tiles (1024 px = 1 m; 4 courses, 6 tiles per course)
course = N / 4
cv = (yy % course) / course
row = (yy // course).astype(int)
tw = N / 6
cu = ((xx + (row % 2) * tw / 2) % tw) / tw
bulge = np.sin(cu * np.pi) ** 0.7
lap = np.clip(cv / 0.85, 0, 1)
h = bulge * 0.6 + lap * 0.4
tid = ((xx + (row % 2) * tw / 2) // tw).astype(int) % 6 + row * 6
tint = rng.random(24).astype(np.float32)[tid]
shade = 0.75 + 0.25 * lap - 0.25 * (cv > 0.92)
base = np.stack([0.72 + 0.1 * tint, 0.36 + 0.06 * tint, 0.24 + 0.04 * tint], -1) * shade[..., None]
grime = blur(tile_noise(N, 6, seed=3), 3)
base *= (0.75 + 0.25 * grime)[..., None]
save('T_RoofTile_BC', base)
save('T_RoofTile_N', normal_from_height(blur(h, 2), 5.0))

# ---------------------------------------------------------------- courtyard paving (1024 px = 2 m, 0.5 m grey tiles)
t = N / 4
u, v = (xx % t) / t, (yy % t) / t
edge = np.minimum(np.minimum(u, 1 - u), np.minimum(v, 1 - v))
pi_, pj = (xx // t).astype(int), (yy // t).astype(int)
jit = rng.random((4, 4)).astype(np.float32)[pj, pi_]
dirt = tile_noise(N, 10, seed=4)
pv = 0.62 + 0.08 * (jit - 0.5) - 0.12 * dirt
pv = np.where(edge < 0.012, 0.38, pv)
save('T_Paving_BC', np.repeat(pv[..., None], 3, -1))
save('T_Paving_N', normal_from_height(blur(np.clip(edge / 0.02, 0, 1), 1), 3.0))
save('T_Paving_R', 0.75 + 0.2 * dirt)

# ---------------------------------------------------------------- plaster: fine stucco normal + weathering mask (1024 px = 1 m / 4 m)
stucco = tile_noise(N, 64, octaves=3, seed=5)
save('T_Stucco_N', normal_from_height(stucco, 2.5))
streak = np.zeros((N, N), np.float32)
for _ in range(220):
    x0 = int(rng.integers(0, N))
    w = int(rng.integers(3, 14))
    y0 = int(rng.integers(0, N))
    ln = int(rng.integers(60, 420))
    a = float(rng.uniform(0.15, 0.6))
    prof = np.linspace(a, 0, ln, dtype=np.float32)
    ys = (np.arange(ln) + y0) % N
    for k in range(w):
        streak[ys, (x0 + k) % N] = np.maximum(streak[ys, (x0 + k) % N], prof)
streak = blur(streak, 2)
mold = np.clip((tile_noise(N, 5, seed=6) - 0.55) * 3, 0, 1)
save('T_Grime_Mask', np.clip(streak * 0.8 + mold * 0.5, 0, 1))

# ---------------------------------------------------------------- rolling shutter ribs (512 px = 0.5 m)
ys = np.mgrid[0:512, 0:512][0].astype(np.float32)
rib = (np.sin(ys / 512 * 2 * np.pi * 16) * 0.5 + 0.5) ** 2
save('T_Shutter_N', normal_from_height(rib, 4.0))
print('TEXTURES_DONE')
