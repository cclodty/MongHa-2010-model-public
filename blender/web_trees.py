"""Web-only vegetation: procedural trees, palms and planter shrubs built from leaf cards on a painted leaf atlas.

Imported by web_bake.py (the Unreal build uses Fab Megaplants instead). Species follow the photos:
broad-leaved street trees, bauhinia (two-lobed leaves), feathery bipinnate trees, fan palms; planters hold
small shrubs and bougainvillea.
"""
import math
import os
import random

import bpy
import numpy as np
from mathutils import Vector

from mh_geom import MB, M, cylv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CELL, COLS, ROWS_ = 512, 3, 2
CELLS = ['broad', 'bauhinia', 'feathery', 'palm', 'shrub', 'bouga']
rng = np.random.default_rng(1988)
prng = random.Random(1988)


def hexrgb(h):
    h = h.lstrip('#')
    return np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)], np.float32)


# ---------------------------------------------------------------- leaf atlas (RGBA, cells 512 px)
def paint_ellipse(img, alpha, cx, cy, a, b, ang, col, shade=True):
    r = int(max(a, b)) + 2
    x0, x1, y0, y1 = max(0, int(cx) - r), min(CELL, int(cx) + r), max(0, int(cy) - r), min(CELL, int(cy) + r)
    if x0 >= x1 or y0 >= y1:
        return
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    dx, dy = xx - cx, yy - cy
    c, s = math.cos(ang), math.sin(ang)
    u, v = dx * c + dy * s, -dx * s + dy * c
    d = (u / a) ** 2 + (v / b) ** 2
    m = d < 1.0
    if not m.any():
        return
    k = np.ones_like(d)
    if shade:   # midrib and a soft light-to-dark gradient across the blade
        k = 0.82 + 0.25 * (1 - np.clip(d, 0, 1)) + 0.08 * np.sign(v) - 0.12 * (np.abs(v) < b * 0.08)
    img[y0:y1, x0:x1][m] = (col[None, :] * k[m][:, None]).clip(0, 1)
    alpha[y0:y1, x0:x1][m] = 1.0


def leaf_cell(kind):
    img = np.zeros((CELL, CELL, 3), np.float32)
    al = np.zeros((CELL, CELL), np.float32)
    greens = {'broad': ['#2f5a26', '#3d6b2c', '#4b7a33', '#36622a'], 'bauhinia': ['#4f7d36', '#5f8c40', '#6d9a48', '#557f39'],
              'feathery': ['#4f8a33', '#5e9a3c', '#6aa646', '#477d2e'], 'palm': ['#3e6b34', '#4a7a3b', '#577f42'],
              'shrub': ['#2f5c28', '#3c6a2e', '#4a7634'], 'bouga': ['#3b6a2f', '#467536']}[kind]
    cx0, cy0 = CELL / 2, CELL / 2
    if kind == 'palm':          # fan leaf on a petiole, radiating from the bottom centre
        base = (CELL / 2, CELL * 0.92)
        for i in range(34):
            t = -1.35 + 2.7 * i / 33 + rng.uniform(-0.03, 0.03)
            L = rng.uniform(190, 235)
            cx, cy = base[0] + math.sin(t) * L * 0.55, base[1] - math.cos(t) * L * 0.55
            paint_ellipse(img, al, cx, cy, L * 0.52, rng.uniform(7, 10), t + math.pi / 2, hexrgb(prng.choice(greens)) * rng.uniform(0.85, 1.1))
        return img, al
    n = {'broad': 150, 'bauhinia': 46, 'feathery': 0, 'shrub': 170, 'bouga': 90}[kind]
    for i in range(n):          # back-to-front: early (back) leaves darker
        depth = i / max(n - 1, 1)
        rr = rng.random() ** 0.35 * CELL * 0.44
        th = rng.uniform(0, 2 * math.pi)
        cx, cy = cx0 + math.cos(th) * rr, cy0 + math.sin(th) * rr
        col = hexrgb(prng.choice(greens)) * (0.7 + 0.4 * depth) * rng.uniform(0.9, 1.08)
        if kind == 'broad':
            paint_ellipse(img, al, cx, cy, rng.uniform(22, 34), rng.uniform(10, 15), th + rng.uniform(-0.6, 0.6), col)
        elif kind == 'bauhinia':  # two rounded lobes split at the tip
            a, ang = rng.uniform(34, 48), th + rng.uniform(-0.8, 0.8)
            for side in (-1, 1):
                ox, oy = math.cos(ang + side * math.pi / 2) * a * 0.32, math.sin(ang + side * math.pi / 2) * a * 0.32
                paint_ellipse(img, al, cx + ox, cy + oy, a * 0.62, a * 0.42, ang + side * 0.35, col)
        elif kind == 'shrub':
            paint_ellipse(img, al, cx, cy, rng.uniform(10, 16), rng.uniform(5, 8), rng.uniform(0, 6.3), col)
        elif kind == 'bouga':
            if rng.random() < 0.55:   # magenta bracts in threes
                pc = hexrgb(prng.choice(['#c4307a', '#d2408a', '#b02868'])) * (0.75 + 0.35 * depth)
                for k in range(3):
                    a2 = k * 2.09 + rng.uniform(0, 1)
                    paint_ellipse(img, al, cx + math.cos(a2) * 7, cy + math.sin(a2) * 7, 11, 8, a2, pc, shade=False)
            else:
                paint_ellipse(img, al, cx, cy, rng.uniform(12, 18), rng.uniform(6, 9), rng.uniform(0, 6.3), col)
    if kind == 'feathery':      # bipinnate: pinnae of tiny leaflets
        for i in range(26):
            th = rng.uniform(0, 2 * math.pi)
            sx, sy = cx0 + math.cos(th) * rng.uniform(0, 60), cy0 + math.sin(th) * rng.uniform(0, 60)
            L, ang = rng.uniform(140, 210), th + rng.uniform(-0.5, 0.5)
            col = hexrgb(prng.choice(greens)) * rng.uniform(0.75, 1.1)
            for j in range(34):
                t = j / 33
                px, py = sx + math.cos(ang) * L * t, sy + math.sin(ang) * L * t
                for side in (-1, 1):
                    oa = ang + side * 1.2
                    if j % 2 == 0:   # airy: leaflets with gaps between them
                        paint_ellipse(img, al, px + math.cos(oa) * 6.0, py + math.sin(oa) * 6.0, 5.0, 1.5, oa, col * (0.9 + 0.35 * t), shade=False)
    return img, al


def make_atlas():
    W, H = CELL * COLS, CELL * ROWS_
    rgba = np.zeros((H, W, 4), np.float32)
    for k, kind in enumerate(CELLS):
        img, al = leaf_cell(kind)
        r, c = k // COLS, k % COLS
        rgba[r * CELL:(r + 1) * CELL, c * CELL:(c + 1) * CELL, :3] = img
        rgba[r * CELL:(r + 1) * CELL, c * CELL:(c + 1) * CELL, 3] = al
    # bleed colour into transparent texels so mip-mapping does not halo the cut-outs
    col = rgba[:, :, :3].copy()
    for _ in range(6):
        m = rgba[:, :, 3:4] > 0
        acc = np.zeros_like(col)
        cnt = np.zeros(col.shape[:2] + (1,), np.float32)
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            acc += np.roll(np.roll(col * m, dy, 0), dx, 1)
            cnt += np.roll(np.roll(m.astype(np.float32), dy, 0), dx, 1)
        fill = (cnt > 0) & ~m
        col = np.where(fill, acc / np.maximum(cnt, 1), col)
        rgba[:, :, 3:4] = np.where(fill, 1e-3, rgba[:, :, 3:4])
    rgba[:, :, :3] = col
    rgba[:, :, 3] = (rgba[:, :, 3] > 0.5).astype(np.float32)
    img = bpy.data.images.new('T_Leaves', W, H, alpha=True)
    img.pixels.foreach_set(np.flipud(rgba).ravel())
    path = os.path.join(ROOT, 'textures', 'T_Leaves.png')
    img.filepath_raw = path
    img.file_format = 'PNG'
    img.save()
    return img


def cell_uv(kind):
    k = CELLS.index(kind)
    r, c = k // COLS, k % COLS
    e = 0.004
    u0, u1 = c / COLS + e, (c + 1) / COLS - e
    v1, v0 = 1 - r / ROWS_ - e, 1 - (r + 1) / ROWS_ + e
    return [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]


# ---------------------------------------------------------------- geometry
def S(p):
    return Vector(p)


def tube(mb, a, b, r0, r1, m, seg=6):
    a, b = Vector(a), Vector(b)
    ax = (b - a).normalized()
    u = ax.cross(Vector((0, 1, 0)) if abs(ax.y) < 0.95 else Vector((1, 0, 0))).normalized()
    v = ax.cross(u)   # u x v == ax, so the quads face outwards
    ring = lambda c, r: [c + (u * math.cos(2 * math.pi * i / seg) + v * math.sin(2 * math.pi * i / seg)) * r for i in range(seg)]  # noqa: E731
    R0, R1 = ring(a, r0), ring(b, r1)
    for i in range(seg):
        j = (i + 1) % seg
        mb.poly([R0[i], R0[j], R1[j], R1[i]], m)


def card(mb, c, n, size, uvs, m, up=Vector((0, 1, 0))):
    n = n.normalized()
    r = up.cross(n)
    if r.length < 1e-4:
        r = Vector((1, 0, 0))
    r.normalize()
    u = n.cross(r)
    h = size / 2
    mb.poly([c - r * h - u * h, c + r * h - u * h, c + r * h + u * h, c - r * h + u * h], m, uvs=uvs)


def rand_dir():
    z = prng.uniform(-1, 1)
    t = prng.uniform(0, 2 * math.pi)
    s = math.sqrt(1 - z * z)
    return Vector((s * math.cos(t), z, s * math.sin(t)))


def canopy_tree(mb, x, y0, z, H, R, kind, leaf, bark, young=False):
    lean = Vector((prng.uniform(-0.6, 0.6), 0, prng.uniform(-0.6, 0.6))) * (0.3 if young else 1.0)
    base, top = Vector((x, y0, z)), Vector((x, y0 + H * 0.42, z)) + lean
    tube(mb, base, top, 0.06 if young else 0.26 * R / 3.5 + 0.08, 0.04 if young else 0.15, bark, 7)
    centre = Vector((x, y0 + H - R * 0.75, z)) + lean * 1.3
    tips = []
    for i in range(prng.randint(4, 6)):
        d = Vector((math.cos(i * 1.3 + prng.random()), 0.0, math.sin(i * 1.3 + prng.random()))).normalized()
        tip = centre + d * R * prng.uniform(0.45, 0.7) + Vector((0, prng.uniform(-0.3, 0.6) * R * 0.5, 0))
        tube(mb, top, tip, 0.035 if young else 0.13, 0.015 if young else 0.05, bark, 5)
        tips.append(tip)
    n = int((11 if young else 34) * R)       # young trees: a few loose sprays of leaves (1990s photo)
    uvs = cell_uv(kind)
    for _ in range(n):
        d = rand_dir()
        d.y *= 1.1 if young else 0.72
        rf = 0.55 + 0.45 * math.sqrt(prng.random())
        p = centre + Vector((d.x * R, d.y * R, d.z * R)) * rf
        if p.y < top.y - 0.3:
            p.y = top.y - 0.3 + prng.random() * 0.4
        nrm = (d + rand_dir() * 0.7)
        if nrm.length < 0.1:
            nrm = Vector((0, 1, 0))
        size = prng.uniform(1.0, 1.5) if young else prng.uniform(1.8, 2.8) * (1.15 if kind == 'feathery' else 1.0)
        card(mb, p, nrm, size, uvs, leaf)


def palm(mb, x, y0, z, H, leaf, bark):
    lean = Vector((prng.uniform(-0.5, 0.5), 0, prng.uniform(-0.5, 0.5)))
    crown = Vector((x, y0 + H, z)) + lean
    tube(mb, Vector((x, y0, z)), crown, 0.22, 0.17, bark, 8)
    uvs = cell_uv('palm')
    for i in range(22):
        t = i * 2.4 + prng.random() * 0.3
        el = prng.uniform(-0.5, 0.75)          # leaf elevation: young leaves up, old ones drooping
        d = Vector((math.cos(t) * math.cos(el), math.sin(el), math.sin(t) * math.cos(el)))
        tip = crown + d * 1.3
        tube(mb, crown, tip, 0.04, 0.025, bark, 4)
        nrm = Vector((d.x, d.y + 1.2, d.z))
        card(mb, tip + d * 0.75, nrm, 2.1, uvs, leaf, up=d)


def bush(mb, p, s, kind, leaf):
    uvs = cell_uv(kind)
    c = Vector(p) + Vector((0, s * 0.55, 0))
    for _ in range(9):
        d = rand_dir()
        d.y = abs(d.y) * 0.8
        card(mb, c + d * s * 0.45, d + rand_dir() * 0.5, prng.uniform(0.6, 0.85) * s * 1.6, uvs, leaf)


def build(markers, collection):
    img = make_atlas()
    leaf = M('M_Leaves', '#ffffff', 0.8)
    bark = M('M_Bark', '#5d5146', 0.9)
    nt = leaf.node_tree
    tn = nt.nodes.new('ShaderNodeTexImage')
    tn.image = img
    b = nt.nodes.get('Principled BSDF')
    nt.links.new(tn.outputs['Color'], b.inputs['Base Color'])
    nt.links.new(tn.outputs['Alpha'], b.inputs['Alpha'])
    mb = MB('SM_Trees', collection)
    species = markers.get('species', [])
    for i, (x, z, r) in enumerate(markers['trees']):
        kind = species[i] if i < len(species) else 'broad'
        if r < 1.4:   # young courtyard trees standing in the planters (1990s photo): slim, open crowns
            H = 3.6 + 1.8 * r + prng.uniform(-0.3, 0.4)
            canopy_tree(mb, x, 0.7, z, H, r * 1.25, kind, leaf, bark, young=True)
            continue
        H = prng.uniform(8, 10) * (r / 2.4) ** 0.3
        if kind == 'palm':
            palm(mb, x, 0.05, z, H * 0.62, leaf, bark)
        else:
            canopy_tree(mb, x, 0.05, z, H, r * 1.6, kind, leaf, bark)
    for x, y0, z, r in markers.get('hill_trees', []):   # street trees on the raised ground by the hillside blocks
        canopy_tree(mb, x, y0 + 0.05, z, prng.uniform(8, 10) * (r / 2.4) ** 0.3, r * 1.6, 'broad', leaf, bark)
    sh = MB('SM_Shrubs', collection)
    for s in markers.get('shrubs', []):
        bush(sh, s['p'], s['s'] * 1.3, 'bouga' if s.get('bouga') else 'shrub', leaf)
    nfaces = mb.nfaces + sh.nfaces
    mb.finish()
    sh.finish()
    print('WEB_TREES', len(markers['trees']), 'trees', len(markers.get('shrubs', [])), 'shrubs', nfaces, 'faces')
