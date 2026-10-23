"""Builds the 2010 (pre-demolition) Bairro Social de Mong-Ha as detailed meshes for Unreal.

Run:  blender -b --factory-startup -P build_estate.py -- [--render] [--export]
Layout mirrors G:/Claude/mongha-1988/index.html (site metres; see mh_geom for axes).
"""
import json
import math
import os
import random
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from mh_geom import (B, MB, Fr, M, arc, box, cylv, cylx, prism_x, prism_y,  # noqa: E402
                     prism_z, quad_bezier)

ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
ROOT = os.path.dirname(HERE)
EXPORT = os.path.join(ROOT, 'export')
os.makedirs(EXPORT, exist_ok=True)
rnd = random.Random(2010)
CLOTH = json.load(open(os.path.join(ROOT, 'export', 'cloth_cells.json'), encoding='utf-8'))
SIGN_FH, SIGN_P = 228, 2048    # T_Signs_BC layout (make_signs.py): 2 x 7 fascia cells on top, 8 blade cells below


def sign_uv(k):
    """(bl, br, tr, tl) UVs of fascia sign k (0..13)."""
    u0, u1 = (k % 2) * 0.5 + 0.002, (k % 2) * 0.5 + 0.498
    vt = 1 - (k // 2) * SIGN_FH / SIGN_P - 0.002
    vb = vt - SIGN_FH / SIGN_P + 0.004
    return [(u0, vb), (u1, vb), (u1, vt), (u0, vt)]


def blade_uv(k):
    u0, u1 = k * 256 / SIGN_P + 0.002, (k + 1) * 256 / SIGN_P - 0.002
    vt, vb = 1 - (7 * SIGN_FH + 4) / SIGN_P - 0.002, 0.002
    return [(u0, vb), (u1, vb), (u1, vt), (u0, vt)]


def garment(mb, fr, x0, ytop, z, cell, k=1.0):
    """A draped garment hanging from a laundry pole: 4x3 grid with folds, cut out by the atlas mask."""
    w, h = cell['size'][0] * k, cell['size'][1] * k
    n, e = CLOTH['n'], 0.004
    u0, u1 = cell['i'] / n + e, (cell['i'] + 1) / n - e
    vt, vb = 1 - cell['j'] / n - e, 1 - (cell['j'] + 1) / n + e
    nx, ny = 4, 3
    ph, fold, sway = irng.uniform(0, 6.3), irng.uniform(1.5, 3.0), irng.uniform(-0.06, 0.08)

    def pt(i, j):
        t, d = i / nx, j / ny
        return fr.p(x0 + w * t, ytop - h * d, z + 0.03 * math.sin(math.pi * t * fold + ph) * (0.3 + 0.7 * d) + sway * d * d)

    def uv(i, j):
        return (u0 + (u1 - u0) * i / nx, vt - (vt - vb) * j / ny)
    for j in range(ny):
        for i in range(nx):
            mb.poly([pt(i, j + 1), pt(i + 1, j + 1), pt(i + 1, j), pt(i, j)], MAT['clothatlas'],
                    uvs=[uv(i, j + 1), uv(i + 1, j + 1), uv(i + 1, j), uv(i, j)])


SHRUBS = []                  # planter plants: placed in Unreal from Fab foliage, not modelled here
irng = random.Random(1988)   # interior-atlas picks; separate so layout randomness stays unchanged


def atlas_uv(n, aspect=1.0):
    """UVs (bl, br, tr, tl) of a random n x n interior-atlas cell, cropped to the pane's width/height aspect."""
    i, j = irng.randrange(n), irng.randrange(n)
    c, e = 1 / n, 0.03 / n
    uw, vh = c - 2 * e, c - 2 * e
    if aspect < 1:
        uw *= aspect
    else:
        vh /= aspect
    u0 = i * c + e + irng.random() * (c - 2 * e - uw)
    v0 = 1 - (j + 1) * c + e
    u1, v1 = u0 + uw, v0 + vh
    if irng.random() < 0.5:
        u0, u1 = u1, u0
    return [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]


bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1.0

# ------------------------------------------------------------------ dimensions & layout (same as the web model)
D, HZ, GF, FH, NF = 17.0, 8.5, 3.8, 2.9, 6   # block depth: MH001 camera solve (2026-10-23), was 10 m
ROOF = GF + FH * NF
PAR = 1.4
TOP = ROOF + PAR
RFS = TOP - 0.6     # finished roof surface: the parapet stands 0.6 m above it (MH001)
JW, ARC, GW, SAW, LOG = 4.2, 2.6, 3.0, 1.3, 1.1
COURT_W, COURT_L = 42.0, 106.0                  # courtyard face to face (photo 14 camera solve + OSM lot)
EX0, EZ0 = 52.0, 3.0                            # lane by the sports hall; avenue building line
EX1, EZ1 = EX0 + 2 * D + COURT_W, EZ0 + 2 * D + COURT_L
CX0, CX1, CZ0, CZ1 = EX0 + D, EX1 - D, EZ0 + D, EZ1 - D


def Bi(n, color, passages=(), serr=False):
    """color: one colour for the block, or a list with one colour per bay (2026-10-22 photo package: each block between
    the white stair towers is painted in sections of one or two bays, every bay with its own tile cap, MH002/MH005/MH068)."""
    cols = list(color) if isinstance(color, (list, tuple)) else [color] * n
    assert len(cols) == n, (n, cols)
    return {'t': 'b', 'n': n, 'color': cols[0], 'cols': cols, 'pass': list(passages), 'serr': serr}


def Ji():
    return {'t': 'j'}


# 14 blocks: the end rows run the full frontage and wrap the corners, the side rows sit between them
Y, G, K, R = 'yellow', 'green', 'brick', 'red'
# the two hillside blocks up the steps from 利誠 (user, 2026-10-22: part of the estate). MH068 (2011-06-08, frontal), MH006
# (from the top of the steps) and the aerial MH001: they stand south-east of the 利誠 side street on the raised ground and
# face the level top of 馬交石斜坡 across a paved forecourt. Seen from the street, north-west first: block A green |
# yellow | yellow | yellow, a white stair tower with a breeze-block strip, block B green | red-brown. Bays ~5 m (MH068).
HILL = dict(x0=EX1 + 7.5, x1=EX1 + 7.5 + 6 * 5.0 + JW, zf=EZ1 - 2.0, y0=3.0)   # x0/x1 NW / SE ends, zf street face (MH006 camera)
ROWS = [
    # per-bay colours, listed in each row's own direction. Back row's south-east end red-brown (MH033). Front row from photos (NW end red-brown then yellow, MH007 and
    # photo 21; red-brown over the post office corner, MH022); the other rows follow the same grammar (MH002, MH005, MH080),
    # keeping each block's main colour, but their exact sequences are inferred.
    dict(id='front', o=(EX0, EZ0 + HZ), d=(1, 0), L=EX1 - EX0, outer='street', gallery=True,
         items=[Bi(4, [K, Y, Y, Y]), Ji(), Bi(5, [Y, K, K, G, G], [2]), Ji(), Bi(4, [Y, Y, K, K])]),
    dict(id='back', o=(EX1, EZ1 - HZ), d=(-1, 0), L=EX1 - EX0, outer='street', gallery=True,
         items=[Bi(4, [K, K, Y, Y]), Ji(), Bi(5, [Y, R, R, G, G], [2]), Ji(), Bi(4, [Y, Y, K, K])]),
    dict(id='nw', o=(EX0 + HZ, CZ1), d=(0, -1), L=CZ1 - CZ0, outer='street', gallery=True,
         items=[Bi(6, [Y, Y, G, G, K, K]), Ji(), Bi(6, [G, G, Y, Y, K, K], [3]), Ji(), Bi(6, [K, K, G, Y, Y, G]), Ji(),
                Bi(6, [R, R, Y, Y, G, G])]),
    dict(id='se', o=(EX1 - HZ, CZ0), d=(0, 1), L=CZ1 - CZ0, outer='street', gallery=True,
         items=[Bi(6, [K, K, Y, Y, G, G]), Ji(), Bi(6, [G, G, Y, Y, K, K], [2]), Ji(), Bi(6, [G, Y, Y, R, R, G]), Ji(),
                Bi(6, [G, G, K, K, Y, Y])]),
    dict(id='slope1', o=(HILL['x1'], HILL['zf'] - HZ), d=(-1, 0), L=HILL['x1'] - HILL['x0'], outer='street', gallery=None,
         y0=HILL['y0'], items=[Bi(2, [K, G]), Ji(), Bi(4, [Y, Y, Y, G])]),   # listed from the south-east end
]
for row in ROWS:
    fixed = sum(JW for it in row['items'] if it['t'] == 'j')
    bays = sum(it['n'] for it in row['items'] if it['t'] == 'b')
    row['bw'] = (row['L'] - fixed) / bays
    x = 0.0
    for it in row['items']:
        it['x0'] = x
        x += it['n'] * row['bw'] if it['t'] == 'b' else JW
        it['x1'] = x
    dx, dz = row['d']
    row['fr'] = Fr((row['o'][0], row.get('y0', 0.0), row['o'][1]), (dx, 0, dz), (-dz, 0, dx))

PASS_X = EX0 + ROWS[0]['items'][2]['x0'] + 2.5 * ROWS[0]['bw']
# (site x, z) near which the two trading shops stood (user, 2026-10-22): 鞋宜樂 in the north-west bay of the middle avenue
# block, beside the stair tower, bus stop in front of the next bay (photo 21); 利誠美食 at the back end of the south-east side
# street (top-left seen from the avenue), up the steps from there is the 望廈飲食 spot; sign atlas cells 11 and 10
SHOES_X = EX0 + ROWS[0]['items'][2]['x0'] + 0.5 * ROWS[0]['bw']
OPEN_SHOPS = {'shoes': (SHOES_X, EZ0, 11), 'lisheng': (EX1, CZ1 - 0.5 * ROWS[3]['bw'], 3),
              'lisheng2': (EX1, CZ1 - 1.5 * ROWS[3]['bw'], None)}
# the hillside shops, north-west first (MH068, MH006): 望廈飲食 and 金富美食 (black boards, red characters), an eatery with
# an unreadable pale board, a green canvas awning (MH033), a striped awning, Maria Beauty Center (purple board)
HILL_BW = ROWS[4]['bw']
HX = [HILL['x0'] + (k + 0.5) * HILL_BW + (JW if k > 3 else 0) for k in range(6)]
OPEN_SHOPS.update({k: (HX[i], HILL['zf'], c) for i, (k, c) in enumerate((('mhfood', 0), ('kamfu', 1), ('hill3', None),
                                                                         ('hill4', None), ('hill5', None), ('maria', 2)))})
FRONT_TREES = [(EX0 + f * (EX1 - EX0), -1.5, r) for f, r in ((0.145, 2.0), (0.33, 3.0), (0.645, 1.9), (0.92, 2.0))]   # photos 21, 22
SHOP_LOOK = {'shoes': (1, None), 'lisheng': (3, 'canvas'), 'lisheng2': (3, 'awninggreen'), 'mhfood': (6, 'awning'), 'kamfu': (6, None), 'hill3': (3, None),
             'hill4': (3, 'awninggreen'), 'hill5': (3, 'canvasred'), 'maria': (7, None)}   # board colour (MAT['signs'] index), awning
REC = 1.6   # depth of the covered recess at the two ends of the frontage
LX, LZ = (CX0 + CX1) / 2, (CZ0 + CZ1) / 2
CAGE = dict(x0=LX - 9, x1=LX + 9, z0=CZ0 + GW + 3.5, z1=CZ0 + GW + 29.5, h=6.0)   # long axis along z (user, round 4)
HALL = dict(x0=6.0, x1=EX0 - 8.0, z0=EZ0 + 2.0, zr=EZ1 - 18.0, z1=EZ1 + 2.5, h=11.4)   # 2026-10-22 photos, see build_hall
SLOPE = dict(x0=EX1 + 2.0, x1=EX1 + 58.0, z0=EZ1 - 33.0, z1=EZ1 + 12.0)
SIDE_X1 = EX1 + 7.0   # the 利誠 side street runs between the south-east row (x = EX1) and the raised ground at x = SIDE_X1
# back street (user, 2026-10-22, street photo): it climbs from the north-west back corner (by the nursery) to the south-east
# back corner (by 利誠), where steps lead down to the 利誠 side street. A granite retaining wall with a railing runs between
# the pavement and a sunken planted strip along the back of the blocks, so the rising street hides their lower floors.
BACK = dict(x_lo=EX0 - 2.0, x_hi=SIDE_X1, H=HILL['y0'], strip=EZ1 + 4.0, wall=EZ1 + 4.6, kerb=EZ1 + 7.5, far=EZ1 + 15.5,
            far_kerb=EZ1 + 18.5, end=EZ1 + 31.0)


def back_h(x):
    """Ground level of the back street at site x."""
    t = (x - BACK['x_lo']) / (BACK['x_hi'] - BACK['x_lo'])
    return BACK['H'] * min(1.0, max(0.0, t))
# library (MH001 solved against the courtyard width, 2026-10-23): its centre stands 0.58 of the courtyard length from the
# avenue side, ~8 m behind the middle, and its column ring is ~6.7 m in radius; heights match. Photo 14's solve also put
# it well behind the middle. The courtyard furniture stays where MH001 and photo 14 show it (relative to LZ).
LIB_X, LIB_Z = LX - 1.0, LZ + 8.2   # centre of the red column ring (tools/libfit_mh001.py: 82.0, 74.2)
LIB_S = 0.705                       # plan scale: column ring radius 9.3 * 0.705 = 6.56 m (fit 6.55)
# three storeys (user, 2026-10-23, with MH034 = photo 24 and MH001): the ground and top floors share one octagon inside the
# red column ring, and the columns run from the ground to the roof. The first floor, level with the galleries, is a walkway
# behind a planter ring round the court side, reached by the two bridges; its reading room fills the back half and juts
# out on the side away from the ball court, one face wide and ~3.5 m deep, over open ground on two more red columns; the
# top of the jut is a balcony off the top floor. The entrance is under the north-west bridge (MH034).
# Radii are of octagon corners, before the plan scale.
LIB = dict(col=9.3, slab=9.35, wall=8.9, inner=5.3, jut=5.0, band=8.8, fascia=(12.0, 12.9), eave=10.3, apex=14.4)
BRIDGE_Z = LIB_Z
NWG, SEG = CX0 + GW, CX1 - GW          # inner edges of the side galleries
GZ0, GZ1 = CZ0 + GW, CZ1 - GW          # inner edges of the end galleries
STAIRS = [LZ + 29.0, LZ - 29.0]       # four U-stairs (photo 14: back pair 29 m behind the library)
ZC = HZ - 0.3                          # courtyard facade plane (row-local z)
ZL = ZC - 1.3                          # back wall of the courtyard loggias


def in_court(row, xl):
    """True if row-local x lies along the courtyard (end rows also run past the corners)."""
    if row['id'] not in ('front', 'back'):
        return True
    x = row['fr'].p(xl, 0, 0)[0]
    return CX0 + 0.05 < x < CX1 - 0.05


def special_bay(row, xl, bw):
    """Covered recesses (user, round 3) and where the post office and nursery really were (user, 2026-10-22, seen from
    the avenue: post office in the bottom-left = south-east recess of the frontage; nursery top-right = back end of the
    north-west row, facing the lane by the sports hall, photo 2). The north-west avenue recess holds shuttered shops."""
    if row['id'] == 'front':
        if xl < 3 * bw:
            return 'recess', int(xl // bw)
        if xl > row['L'] - 3 * bw:
            return 'post', int((row['L'] - xl) // bw)
    if row['id'] == 'nw' and xl < 2 * bw:   # the NW row starts at the back corner
        return 'nursery', int(xl // bw)
    if row['id'] == 'back' and xl > row['L'] - 2 * bw:   # and its glass-block windows turn the corner onto the back street (MH080)
        return 'nursery', 2 + int((row['L'] - xl) // bw)
    return None, None

# ------------------------------------------------------------------ materials (names are what Unreal maps to real materials)
def hexmix(a, b, t):
    A = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    Bc = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return '#' + ''.join(f'{round(A[k] + (Bc[k] - A[k]) * t):02x}' for k in range(3))


def hexscale(h, k):
    return '#' + ''.join(f'{max(0, min(255, round(int(h[i:i + 2], 16) * k))):02x}' for i in (1, 3, 5))


def weather(h):
    return hexmix(hexscale(h, 0.92), '#8d877a', 0.22)


PAL = {k: weather(v) for k, v in dict(red='#c46c52', green='#86a98a', yellow='#dfba67', brick='#a65842').items()}
MAT = {
    'plaster': {k: M(f'M_Plaster_{k.capitalize()}', v) for k, v in PAL.items()},
    'slab': {k: M(f'M_SlabEdge_{k.capitalize()}', hexscale(v, 1.06)) for k, v in PAL.items()},
    'white': M('M_Plaster_White', '#dcd6c9'),
    'ground': M('M_Plaster_Ground', '#c9bea8'),
    'soffit': M('M_Concrete_Soffit', '#bdb5a5'),
    'rooftile': M('M_RoofTile_Terracotta', '#d4732f', 0.7),          # orange in every photo
    'screed': M('M_Roof_Screed', '#bcb8ae'),
    'breeze': M('M_BreezeBlock', '#b9b4a8'),
    'void': M('M_Dark_Void', '#262725', 1.0),
    'frame': M('M_WindowFrame', '#d9d4c8', 0.5),
    'glass': M('M_Glass_Residential', '#3a4c55', 0.08, transmission=0.0),
    'bars': M('M_Metal_WindowBars', '#3c3f3e', 0.45, 0.6),
    'rail': M('M_Metal_Railing', '#d0ccc2', 0.45, 0.4),
    'ac': M('M_AC_Unit', '#e1dfd8', 0.5),
    'pole': M('M_Laundry_Pole', '#8f8a7c', 0.5, 0.5),
    'shutter': M('M_Shop_Shutter', '#8f918c', 0.45, 0.7),
    'shopglass': M('M_Shop_Glass', '#33424a', 0.08),
    'shopin': M('M_Shop_Interior', '#2a2e2c'),
    'mred': M('M_Mosaic_Red', '#b5372e', 0.4),
    'myellow': M('M_Mosaic_Yellow', '#e2d39a', 0.45),
    'deck': M('M_Tile_Deck', '#bdb7a6', 0.7),
    'pipe': M('M_Metal_Pipe', '#3a3d3c', 0.4, 0.8),
    'dado': M('M_Tile_Dado', '#b9a98c', 0.5),
    'arcwall': M('M_Plaster_Arcade', '#d2c8b3'),
    'door': M('M_Wood_Door', '#5a4632', 0.6),
    'gate': M('M_Metal_Gate', '#6d716c', 0.4, 0.8),
    'paving': M('M_Paving_Courtyard', '#a7a59d', 0.9),
    'sidewalk': M('M_Paving_Sidewalk', '#bdb7aa', 0.9),
    'asphalt': M('M_Asphalt', '#5d5f5f', 0.95),
    'paint': M('M_Road_Paint', '#e8e6dc', 0.7),
    'curb': M('M_Concrete_Curb', '#a7a296'),
    'ground0': M('M_Ground_Dirt', '#8d8b83', 1.0),
    'grass': M('M_Grass', '#6f8a55', 1.0),
    'lcream': M('M_Lib_Cream', '#dccfb2'),
    'lgreen': M('M_Lib_GreenMetal', '#3a634d', 0.45, 0.6),
    'lgreend': M('M_Lib_GreenPlinth', '#35574a', 0.8),
    'lglass': M('M_Glass_Library', '#b9c6c2', 0.35),   # frosted (user: nothing visible from outside)
    'lmull': M('M_Lib_Mullion', '#f1ede4', 0.4),
    'lsign': M('M_Lib_Sign', '#2f5d48', 0.5),
    'soil': M('M_Soil', '#4a3b2c', 1.0),
    'shrub': M('M_Foliage_Shrub', '#4f7a3d', 0.9),
    'bouga': M('M_Foliage_Bougainvillea', '#c2357a', 0.8),
    'steel': M('M_Steel_Black', '#222524', 0.5, 0.6),
    'chain': M('M_ChainLink', '#1d1f1e', 0.5, 0.6),
    'court': M('M_Court_Surface', '#8f9389', 0.9),
    'cline': M('M_Court_Line', '#e9e5d6', 0.8),
    'pblue': M('M_Play_Blue', '#3a679f', 0.4, 0.3),
    'pred': M('M_Play_Red', '#b8473a', 0.5),
    'sand': M('M_Sand', '#d6c391', 1.0),
    'wood': M('M_Wood_Planter', '#9c7a4c', 0.8),
    'water': M('M_Water_Pond', '#3f5e57', 0.05),
    'rock': M('M_Rock', '#86837a', 0.9),
    'bench': M('M_Concrete_Bench', '#cfc9bc'),
    'lamp': M('M_Lamp_Globe', '#f6f1e0', 0.3, emit='#3a3528'),
    'hallw': M('M_Hall_White', '#e2dfd6'),
    'hallg': M('M_Hall_Grey', '#5a6062', 0.7),
    'stone': M('M_Hall_Stone', '#9c9d98', 0.7),      # grey granite cladding
    'ctx': M('M_Context_Concrete', '#cfc9bd'),
    'ctxB': M('M_Context_Facade_B', '#d6c3b8'),
    'ctxC': M('M_Context_Facade_C', '#bfc6c8'),
    'ctxroof': M('M_Context_Roof', '#8e8b84'),
    'signatlas': M('M_Sign_Atlas', '#d8d0c0', 0.5),
    'clothatlas': M('M_Cloth_Atlas', '#d9d4c8', 0.95),
    'kerbrail': M('M_Metal_KerbRail', '#24483b', 0.45, 0.5),         # Macau dark-green barriers
    'lamppole': M('M_Metal_StreetPole', '#8a8f8c', 0.5, 0.7),
    'tlbox': M('M_TrafficLight_Box', '#1c1d1d', 0.5),
    'tlgreen': M('M_TrafficLight_Green', '#3fe08a', 0.3, emit='#2fd27a'),
    'tlred': M('M_TrafficLight_Red', '#5a1512', 0.3),
    'tank': M('M_Roof_Tank', '#cfd2d0', 0.35, 0.8),
    'ptile': M('M_Planter_Tile', '#8a4a35', 0.6),          # brown-red tiled planter walls (photo 14)
    'disc': M('M_Grass', '#6f8a55', 1.0),
    'shutter2': M('M_Shop_Shutter_Green', '#56705f', 0.45, 0.6),
    'shutter3': M('M_Shop_Shutter_Pale', '#b8bab3', 0.45, 0.6),
    'shopgreen': M('M_Frame_Green', '#2f8a45', 0.4, 0.3),
    'awninggreen': M('M_Awning_Green', '#2f6b4a', 0.8),
    'canvas': M('M_Awning_Canvas', '#d8d4c8', 0.9),
    'canvasred': M('M_Awning_Stripe', '#b26a5c', 0.9),
    'paintgreen': M('M_Paint_Green', '#4f8a66', 0.8),
    'tilecream': M('M_Tile_Cream', '#d6cdb0', 0.45),
    'hydrant': M('M_Hydrant_Red', '#b3261e', 0.5),
    'billboard': M('M_Billboard', '#ffffff', 0.6),
    'brickpave': M('M_Paving_Brick', '#8d6457', 0.85),
    'brickcap': M('M_Brick_Coping', '#9a5442', 0.8),
    'rubbertile': M('M_Rubber_Tiles', '#262827', 0.9),
    'tilegreen': M('M_Tile_Green', '#3f6f52', 0.45),
    'glassblock': M('M_GlassBlock', '#b9cfcc', 0.2),
    'whitetile': M('M_Tile_White', '#e4e1d8', 0.5),        # stair towers are white mosaic (photos 8, 18)
    'lyellow': M('M_Lib_YellowTile', '#d6b45f', 0.5),      # library ground floor (photo 24)
    'hallred': M('M_Hall_RedTile', '#a8362c', 0.5),
    'balrail': M('M_Metal_BalconyRail', '#2b3632', 0.5, 0.6),
    'awning': M('M_Metal_Awning', '#8a8f8a', 0.5, 0.6),
    'pilaster': M('M_Tile_Maroon', '#6a2b26', 0.5),
    'creampipe': M('M_Metal_CreamRail', '#e4ddcc', 0.45, 0.3),
    'rubber': M('M_Play_Rubber', '#2f3231', 0.95),
    'timber': M('M_Play_Timber', '#8a6440', 0.8),
    'shelter': M('M_BusShelter_Metal', '#a3a8a6', 0.45, 0.7),
    'postsign': M('M_PostOffice_Sign', '#b3201f', 0.5),
    'ctxglass': M('M_Context_Glass', '#55636a', 0.15),
    'signs': [M(f'M_Sign_{n}', c, 0.5) for n, c in (('Red', '#b8282a'), ('Yellow', '#f2d23c'), ('Green', '#1f6f4a'), ('White', '#f5f1e6'), ('Blue', '#1d4e8f'), ('Orange', '#e06a1f'),
                                                          ('Black', '#1f1f1d'), ('Purple', '#3b2f6e'))],
    'cloth': [M(f'M_Cloth_{i}', c, 0.95) for i, c in enumerate(['#e8e2d6', '#c9473e', '#3f6ea8', '#e3c34d', '#f2f2ee', '#6c9a6c', '#d98cab', '#4b4b4b'])],
    'post': M('M_PostOffice_Red', '#b3201f', 0.5),
}

# ------------------------------------------------------------------ collections
def coll(name):
    c = bpy.data.collections.new(name)
    scene.collection.children.link(c)
    return c


C_EST, C_SLOPE, C_COURT, C_LIB, C_GROUND, C_HALL, C_CTX, C_MARK = (coll(n) for n in (
    'Estate', 'SlopeBlocks', 'Courtyard', 'Library', 'Ground', 'SportsHall', 'Context', 'Markers'))

# ------------------------------------------------------------------ generic helpers
def beam(mb, a, b, w, m, up=(0, 1, 0), h=None):
    """Box of width w (height h) between site points a and b."""
    a, b = Vector(a), Vector(b)
    u = (b - a)
    L = u.length
    if L < 1e-6:
        return
    u.normalize()
    v = Vector(up) - u * Vector(up).dot(u)
    if v.length < 1e-6:
        v = Vector((1, 0, 0)) - u * u.x
    v.normalize()
    wv = u.cross(v)
    hh = (h or w) / 2
    ww = w / 2
    c = [a + u * x + v * y + wv * z for z in (-ww, ww) for y in (-hh, hh) for x in (0, L)]
    from mh_geom import BOX_FACES
    for idx in BOX_FACES.values():
        mb.poly([c[i] for i in idx], m)


def blob(mb, c, r, m, sy=1.0):
    """Low-poly icosahedron (shrubs, rocks)."""
    t = (1 + 5 ** 0.5) / 2
    vs = [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t), (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]
    k = r / math.sqrt(1 + t * t)
    P = [Vector((c[0] + x * k * (0.85 + 0.3 * rnd.random()), c[1] + y * k * sy, c[2] + z * k * (0.85 + 0.3 * rnd.random()))) for x, y, z in vs]
    F = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6), (7, 1, 8),
         (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1)]
    for f in F:
        mb.poly([P[i] for i in reversed(f)], m)


AC_MARKS = []   # every air-conditioner box, so the Unreal export can swap in scanned units (blender/ue_export.py, tools/ue_09_props.py)


def ac_mark(sf, kind, xc, y0, z0):
    """kind 'window' | 'split'; (xc, y0, z0) = bottom centre where the unit meets the wall, in frame sf (local +z = out)."""
    AC_MARKS.append(dict(kind=kind, p=[round(v, 4) for v in sf.p(xc, y0, z0)], out=[round(v, 5) for v in sf.ez]))


def sphere(mb, c, r, m, seg=32, rings=16):
    """Smooth globe (lamp shades); burns blob()'s 24 random draws so the rest of the layout stays identical."""
    for _ in range(24):
        rnd.random()
    globe(mb, c, r, m, seg, rings)


def globe(mb, c, r, m, seg=20, rings=10):
    pts = [[Vector((c[0] + r * math.sin(math.pi * i / rings) * math.cos(2 * math.pi * j / seg), c[1] + r * math.cos(math.pi * i / rings),
                    c[2] + r * math.sin(math.pi * i / rings) * math.sin(2 * math.pi * j / seg))) for j in range(seg)] for i in range(rings + 1)]
    for i in range(rings):
        for j in range(seg):
            a, b, cc, d = pts[i][j], pts[i][(j + 1) % seg], pts[i + 1][(j + 1) % seg], pts[i + 1][j]
            mb.poly([a, cc, d] if i == 0 else [a, b, cc] if i == rings - 1 else [a, b, cc, d], m)   # poles collapse a=b / cc=d


def side_frame(fr, s):
    return fr if s > 0 else fr.sub(rot=math.pi)


def X(x, s):
    return x if s > 0 else -x


# ------------------------------------------------------------------ residential block (one coloured building of n bays)
def railing_run(mb, fr, xa, xb, y, z, m=None):
    """Balcony railing along local x at depth z, floor level y."""
    m = m or MAT['rail']
    box(mb, fr, xa, xb, y + 0.98, y + 1.05, z - 0.03, z + 0.03, m)
    box(mb, fr, xa, xb, y + 0.2, y + 0.24, z - 0.02, z + 0.02, m)
    n = max(1, int((xb - xa) / 0.11))
    for i in range(1, n):
        x = xa + (xb - xa) * i / n
        box(mb, fr, x - 0.01, x + 0.01, y + 0.24, y + 0.98, z - 0.01, z + 0.01, m)


# street side (photos 21, 23): flat mosaic wall, each bay half window + half balcony, slab bands, awnings. The balconies are
# cut into the wall: their railings stand on thick slab bands that run unbroken across the bay (MH005, MH038, MH068)
ZW = HZ - 0.35      # street facade plane
ZR = HZ - LOG       # balcony back wall (the residential core face)
BALC = ZW + 0.06    # balcony front: railing just proud of the wall plane


def street_bay(mb, sf, xa, xb, ib, col, full=False):
    """full: one balcony across the whole bay, no window wall (the hillside blocks' green bays, MH068)."""
    w, p = xb - xa, 0.18
    bwid = (w - 2 * p) * (1.0 if full else 0.5)
    if ib % 2 == 0:
        bx0, bx1, wx0, wx1 = xa + p, xa + p + bwid, xa + p + bwid, xb - p
    else:
        bx0, bx1, wx0, wx1 = xb - p - bwid, xb - p, xa + p, xb - p - bwid
    tile, band = MAT['plaster'][col], MAT['slab'][col]
    rail = MAT['balrail'] if irng.random() < 0.7 else MAT['rail']
    ww = wx1 - wx0
    if not full:
        box(mb, sf, wx0, wx1, GF, ROOF, ZR, ZW, tile, skip=('nz',))
    cylv(mb, sf, xa, ZW + 0.2, GF - 0.3, ROOF + 0.3, 0.05, 8, MAT['white'])                     # drain pipe on the pilaster
    for f in range(NF):
        y = GF + FH * f
        box(mb, sf, xa + p, xb - p, y - 0.18, y + 0.22, ZW - 0.02, ZW + 0.08, band)             # slab band, whole bay
        box(mb, sf, bx0, bx1, y, y + 0.16, ZR, ZW - 0.02, {'py': MAT['deck'], '*': MAT['soffit']})
        railing_run(mb, sf, bx0 + 0.03, bx1 - 0.03, y + 0.16, BALC - 0.04, rail)
        if full:   # balcony door and a window in the back wall of the loggia
            xm = (bx0 + bx1) / 2
            window(mb, sf, bx0 + 0.2, xm - 0.15, y + 0.2, y + 2.35, ZR, mull=True)
            window(mb, sf, xm + 0.3, bx1 - 0.3, y + 0.95, y + 2.25, ZR, bars=irng.random() < 0.3)
            continue
        window(mb, sf, bx0 + 0.15, bx1 - 0.15, y + 0.2, y + 2.35, ZR, mull=True)                 # balcony door
        window(mb, sf, wx0 + 0.2 * ww, wx1 - 0.2 * ww, y + 0.95, y + 2.25, ZW, bars=irng.random() < 0.3)
        r = irng.random()
        if r < 0.3:      # window-type air conditioner under the window
            xc = wx0 + 0.5 * ww
            box(mb, sf, xc - 0.33, xc + 0.33, y + 0.5, y + 0.92, ZW, ZW + 0.42, MAT['ac'])
            ac_mark(sf, 'window', xc, y + 0.5, ZW)
        elif r < 0.65:   # split unit on a wall bracket
            xc = wx0 + (0.18 if irng.random() < 0.5 else 0.82) * ww
            box(mb, sf, xc - 0.38, xc + 0.38, y + 0.35, y + 0.88, ZW + 0.06, ZW + 0.34, MAT['ac'])
            ac_mark(sf, 'split', xc, y + 0.35, ZW)
            for k in (-0.3, 0.3):
                box(mb, sf, xc + k - 0.02, xc + k + 0.02, y + 0.3, y + 0.35, ZW, ZW + 0.4, MAT['pole'])
        if irng.random() < 0.55:   # laundry inside the balcony front
            cylx(mb, sf, bx0 + 0.05, bx1 - 0.05, y + 2.45, BALC - 0.18, 0.02, 6, MAT['pole'])
            xx = bx0 + 0.1
            while xx < bx1 - 0.3:
                cell = CLOTH['cells'][irng.randrange(len(CLOTH['cells']))]
                k = irng.uniform(0.8, 1.0)
                if xx + cell['size'][0] * k > bx1 - 0.05:
                    break
                garment(mb, sf, xx, y + 2.42, BALC - 0.18, cell, k)
                xx += cell['size'][0] * k + 0.04 + 0.2 * irng.random()
        if (f == NF - 1 and irng.random() < 0.8) or irng.random() < 0.06:   # sheet-metal awning
            prism_x(mb, sf, [(ZR, y + FH - 0.13), (ZW + 0.65, y + FH - 0.6), (ZW + 0.65, y + FH - 0.55), (ZR, y + FH - 0.08)],
                    bx0 - 0.04, bx1 + 0.04, MAT['awning'])


def court_bay(mb, sf, xa, xb, ib, col):
    """Courtyard side (photo 14): flat wall between slim white pilasters, a recessed loggia and a window per bay
    on every floor including the gallery floor, white floor bands, window air-conditioners, laundry in the loggias."""
    p = 0.17
    wi = xb - xa - 2 * p
    lw = 0.48 * wi
    if ib % 2 == 0:
        lx0, lx1 = xa + p, xa + p + lw
        ox0, ox1 = lx1 + 0.22 * (wi - lw), xb - p - 0.22 * (wi - lw)
    else:
        lx0, lx1 = xb - p - lw, xb - p
        ox0, ox1 = xa + p + 0.22 * (wi - lw), lx0 - 0.22 * (wi - lw)
    tile = MAT['plaster'][col]
    wallm = {'pz': tile, 'px': tile, 'nx': tile, 'ny': MAT['soffit'], '*': MAT['white']}
    rail = MAT['balrail'] if irng.random() < 0.4 else MAT['rail']
    for f in range(NF):
        y = GF + FH * f
        segs = [(xa + p, lx0), (lx1, xb - p)]
        for a_, b_ in segs:
            if b_ - a_ > 0.02:
                box(mb, sf, a_, b_, y, y + FH, ZL, ZC, wallm, skip=('py', 'ny'))
        box(mb, sf, lx0, lx1, y + 2.45, y + FH, ZL, ZC, wallm, skip=('py',))           # lintel over the loggia
        box(mb, sf, lx0, lx1, y, y + 0.12, ZL, ZC + 0.03, {'py': MAT['deck'], '*': MAT['slab'][col]})
        box(mb, sf, lx0, lx1, y + 0.12, y + 0.55, ZC - 0.12, ZC, {'pz': tile, '*': MAT['white']})   # low wall
        box(mb, sf, lx0, lx1, y + 1.0, y + 1.05, ZC - 0.09, ZC - 0.03, rail)
        xv = lx0 + 0.12
        while xv < lx1 - 0.08:
            box(mb, sf, xv - 0.009, xv + 0.009, y + 0.55, y + 1.0, ZC - 0.07, ZC - 0.05, rail)
            xv += 0.13
        lwid = lx1 - lx0
        window(mb, sf, lx0 + 0.1 * lwid, lx0 + 0.45 * lwid, y + 0.95, y + 2.25, ZL, bars=irng.random() < 0.3)
        window(mb, sf, lx0 + 0.55 * lwid, lx0 + 0.9 * lwid, y + 0.15, y + 2.3, ZL, mull=True)
        window(mb, sf, ox0, ox1, y + 0.95, y + 2.25, ZC, bars=irng.random() < 0.2)
        if irng.random() < 0.45:                                                       # window air-conditioner
            xc = (ox0 + ox1) / 2
            box(mb, sf, xc - 0.33, xc + 0.33, y + 0.98, y + 1.4, ZC, ZC + 0.4, MAT['ac'])
            ac_mark(sf, 'window', xc, y + 0.98, ZC)
        if irng.random() < 0.55:                                                       # laundry inside the loggia
            cylx(mb, sf, lx0 + 0.05, lx1 - 0.05, y + 2.35, ZC - 0.35, 0.02, 6, MAT['pole'])
            xx = lx0 + 0.1
            while xx < lx1 - 0.3:
                cell = CLOTH['cells'][irng.randrange(len(CLOTH['cells']))]
                k = irng.uniform(0.75, 0.95)
                if xx + cell['size'][0] * k > lx1 - 0.05:
                    break
                garment(mb, sf, xx, y + 2.32, ZC - 0.35, cell, k)
                xx += cell['size'][0] * k + 0.05 + 0.2 * irng.random()
        box(mb, sf, xa + p, xb - p, y - 0.1, y + 0.08, ZC, ZC + 0.05, MAT['white'])       # floor band


def window(mb, fr, xa, xb, ya, yb, z, bars=False, mull=True, gm=None, cells=8, fm=None):
    """Framed window on a wall facing +z at depth z."""
    t, d = 0.06, 0.07
    m = fm or MAT['frame']
    box(mb, fr, xa - t, xb + t, ya - t, ya, z, z + d, m)
    box(mb, fr, xa - t, xb + t, yb, yb + t, z, z + d, m)
    box(mb, fr, xa - t, xa, ya, yb, z, z + d, m)
    box(mb, fr, xb, xb + t, ya, yb, z, z + d, m)
    if mull:
        xm = (xa + xb) / 2
        box(mb, fr, xm - 0.025, xm + 0.025, ya, yb, z, z + d * 0.8, m)
        yt = ya + (yb - ya) * 0.7
        box(mb, fr, xa, xb, yt - 0.025, yt + 0.025, z, z + d * 0.8, m)
    mb.poly([fr.p(xa, ya, z + 0.02), fr.p(xb, ya, z + 0.02), fr.p(xb, yb, z + 0.02), fr.p(xa, yb, z + 0.02)], gm or MAT['glass'], uvs=atlas_uv(cells, (xb - xa) / (yb - ya)))
    if bars:
        n = max(2, int((xb - xa) / 0.13))
        for i in range(1, n):
            x = xa + (xb - xa) * i / n
            box(mb, fr, x - 0.008, x + 0.008, ya, yb, z + d + 0.03, z + d + 0.046, MAT['bars'])
        for yy in (ya + 0.05, yb - 0.05):
            box(mb, fr, xa, xb, yy - 0.012, yy + 0.012, z + d + 0.03, z + d + 0.05, MAT['bars'])


ROW_SEED = {'front': 1, 'back': 2, 'nw': 3, 'se': 4, 'slope1': 5}   # per-row seeds for the roof furniture
REC_RNG = random.Random(1021)   # recess shutters draw from their own stream so the rest of the layout (and markers) stays put
LEDGE_RNG = random.Random(733)  # air-conditioner units on the shop canopies, likewise


def shutter_bay(mb, sf, fa, fb, r=None):
    """Closed rolling shutter set back behind the pilasters: slatted curtain, housing box, guide rails, bottom bar."""
    rg = r or irng
    zs = HZ - 0.42
    m = MAT['shutter'] if rg.random() < 0.7 else (MAT['shutter2'] if rg.random() < 0.5 else MAT['shutter3'])
    box(mb, sf, fa, fb, 0.05, GF - 1.4, zs, zs + 0.04, m)
    box(mb, sf, fa, fb, GF - 1.4, GF - 1.05, HZ - 0.5, HZ - 0.1, m)                  # roller housing
    for xg in (fa + 0.02, fb - 0.07):                                                  # guide channels
        box(mb, sf, xg, xg + 0.05, 0, GF - 1.4, zs - 0.02, zs + 0.1, MAT['steel'])
    box(mb, sf, fa, fb, 0.0, 0.1, zs, zs + 0.09, MAT['steel'])                        # bottom bar
    box(mb, sf, fa, fb, 0.0, 0.03, zs + 0.09, HZ - 0.02, MAT['ground'])               # worn threshold
    if rg.random() < 0.5:                                                            # padlocked hasp
        xc = (fa + fb) / 2 + rg.uniform(-0.3, 0.3)
        box(mb, sf, xc - 0.05, xc + 0.05, 0.1, 0.25, zs + 0.04, zs + 0.09, MAT['steel'])


def open_shop(mb, sf, shop, fa, fb):
    """Trading shops: glazed front, frames, signboard (from the atlas when the name is known), awning (SHOP_LOOK)."""
    frame = MAT['shopgreen'] if shop == 'shoes' else MAT['frame']
    box(mb, sf, fa, fb, 0, 0.35, HZ - 0.3, HZ - 0.22, MAT['myellow'] if shop == 'shoes' else MAT['ground'])
    mb.poly([sf.p(fa, 0.35, HZ - 0.25), sf.p(fb, 0.35, HZ - 0.25), sf.p(fb, GF - 1.05, HZ - 0.25), sf.p(fa, GF - 1.05, HZ - 0.25)],
            MAT['shopglass'], uvs=atlas_uv(4, (fb - fa) / (GF - 1.4)))
    for xm in (fa + 0.04, fa + (fb - fa) * 0.5, fb - 0.04):
        box(mb, sf, xm - 0.04, xm + 0.04, 0.35, GF - 1.05, HZ - 0.28, HZ - 0.18, frame)
    box(mb, sf, fa, fb, 1.9, 1.96, HZ - 0.28, HZ - 0.18, frame)
    zf = HZ + 0.135
    board, awn = SHOP_LOOK[shop]
    box(mb, sf, fa + 0.05, fb - 0.05, GF - 1.05, GF - 0.3, HZ, HZ + 0.12, MAT['signs'][board])
    if OPEN_SHOPS[shop][2] is not None:
        mb.poly([sf.p(fa + 0.05, GF - 1.05, zf), sf.p(fb - 0.05, GF - 1.05, zf), sf.p(fb - 0.05, GF - 0.3, zf), sf.p(fa + 0.05, GF - 0.3, zf)],
                MAT['signatlas'], uvs=sign_uv(OPEN_SHOPS[shop][2]))
    if awn:   # canvas awning (利誠 grey, its neighbour green, photo 3; hillside: white and striped, MH068)
        prism_x(mb, sf, [(HZ, GF - 1.2), (HZ + 1.4, GF - 1.65), (HZ + 1.4, GF - 1.6), (HZ, GF - 1.15)], fa, fb, MAT[awn])
    if shop == 'lisheng':   # yellow blade sign standing out from the wall on a bracket (photo 3), at the back-street end
        xs, yl, yh, zi, zo = fa + 0.3, GF + 0.15, GF + 1.25, HZ + 0.45, HZ + 2.6
        box(mb, sf, xs - 0.04, xs + 0.04, yl, yh, zi, zo, MAT['signs'][1])
        uv = sign_uv(10)
        mb.poly([sf.p(xs + 0.055, yl, zo), sf.p(xs + 0.055, yl, zi), sf.p(xs + 0.055, yh, zi), sf.p(xs + 0.055, yh, zo)], MAT['signatlas'], uvs=uv)
        mb.poly([sf.p(xs - 0.055, yl, zi), sf.p(xs - 0.055, yl, zo), sf.p(xs - 0.055, yh, zo), sf.p(xs - 0.055, yh, zi)], MAT['signatlas'], uvs=uv)
        box(mb, sf, xs - 0.025, xs + 0.025, yh, yh + 0.05, HZ, zo, MAT['steel'])                # bracket
        beam(mb, sf.p(xs, yh + 0.05, HZ), sf.p(xs, yh + 0.7, HZ), 0.05, MAT['steel'])
        beam(mb, sf.p(xs, yh + 0.7, HZ), sf.p(xs, yh + 0.05, zo - 0.1), 0.03, MAT['steel'])


def special_front(mb, sf, kind, fa, fb, i):
    """Ground floor of the recessed end blocks: post office (red frames, 郵政 Correios) or the nursery (glass block)."""
    zw = HZ - REC
    if kind == 'post':
        box(mb, sf, fa, fb, 0, 0.3, zw, zw + 0.1, MAT['hallg'])
        mb.poly([sf.p(fa, 0.3, zw + 0.05), sf.p(fb, 0.3, zw + 0.05), sf.p(fb, GF - 1.05, zw + 0.05), sf.p(fa, GF - 1.05, zw + 0.05)],
                MAT['shopglass'], uvs=atlas_uv(4, (fb - fa) / (GF - 1.4)))
        for xm in [fa + k * (fb - fa) / 3 for k in range(4)]:
            box(mb, sf, xm - 0.05, xm + 0.05, 0.3, GF - 1.05, zw + 0.02, zw + 0.14, MAT['post'])
        box(mb, sf, fa, fb, 1.95, 2.02, zw + 0.02, zw + 0.14, MAT['post'])
        box(mb, sf, fa - 0.02, fb + 0.02, GF - 1.15, GF - 0.25, HZ - 0.05, HZ + 0.35, MAT['post'])
        zf = HZ + 0.36
        mb.poly([sf.p(fa + 0.1, GF - 1.12, zf), sf.p(fb - 0.1, GF - 1.12, zf), sf.p(fb - 0.1, GF - 0.28, zf), sf.p(fa + 0.1, GF - 0.28, zf)],
                MAT['postsign'], uvs=[(0.01, 0.02), (0.99, 0.02), (0.99, 0.98), (0.01, 0.98)])
    else:   # 望廈托兒所: glass-block wall, a glazed door in the middle bay, yellow sign
        box(mb, sf, fa, fb, 0, GF - 1.05, zw, zw + 0.12, MAT['glassblock'] if i != 1 else MAT['void'])
        if i == 1:
            window(mb, sf, fa + 0.4, fb - 0.4, 0.02, 2.4, zw + 0.12, mull=True, gm=MAT['shopglass'], cells=4)
        zf = HZ + 0.135
        box(mb, sf, fa + 0.05, fb - 0.05, GF - 1.05, GF - 0.3, HZ, HZ + 0.12, MAT['signs'][1])
        if i == 1:
            mb.poly([sf.p(fa + 0.05, GF - 1.05, zf), sf.p(fb - 0.05, GF - 1.05, zf), sf.p(fb - 0.05, GF - 0.3, zf), sf.p(fa + 0.05, GF - 0.3, zf)],
                    MAT['signatlas'], uvs=sign_uv(8))


def fin_profile(dep, flare, y0, y1, z_back):
    h = y1 - y0
    pts = [(z_back, y0), (HZ, y0)]
    pts += quad_bezier((HZ, y0), (HZ + dep * 0.15, y0 + 0.55), (HZ + dep, y0 + 0.95), 5)
    pts.append((HZ + dep, y1 - 2.6))
    pts += quad_bezier((HZ + dep, y1 - 2.6), (HZ + dep * 1.02, y1 - 0.9), (HZ + flare, y1), 6)
    pts.append((z_back, y1))
    return pts


def build_block(mb, row, it):
    fr, bw = row['fr'], row['bw']
    x0, x1, n = it['x0'], it['x1'], it['n']
    cols = it['cols']
    gal = bool(row.get('gallery'))
    sides = {-1: row['outer'], 1: 'court' if gal else 'street'}
    zA = -HZ + 0.3 if sides[-1] == 'street' else -(HZ - ARC)
    zB = HZ - 0.3 if sides[1] == 'street' else HZ - ARC
    # --- ground floor cores (broken at through-passages)
    segs, s0 = [], 0
    for i in range(n + 1):
        if i == n or i in it['pass']:
            if i > s0:
                segs.append((s0, i))
            s0 = i + 1
    for a, b in segs:
        for i in range(a, b):   # per bay: the two end recesses of the frontage are deeper
            sp, _ = special_bay(row, x0 + (i + 0.5) * bw, bw)
            box(mb, fr, x0 + i * bw, x0 + (i + 1) * bw, 0, GF - 0.3, -HZ + REC if sp else zA, zB,
                {'pz': MAT['arcwall'] if sides[1] == 'court' else MAT['shopin'], 'nz': MAT['shopin'], '*': MAT['ground']}, skip=('py',))
    for p in it['pass']:
        for xe in (x0 + p * bw, x0 + (p + 1) * bw - 0.3):
            box(mb, fr, xe, xe + 0.3, 0, GF - 0.3, zA, zB, MAT['ground'])
        z, k = -HZ, 0   # floor in cross bands of cream and green tiles (MH010)
        while z < HZ - 0.01:
            dz = min(1.1 if k % 2 == 0 else 0.55, HZ - z)
            box(mb, fr, x0 + p * bw + 0.3, x0 + (p + 1) * bw - 0.3, 0.04, 0.06, z, z + dz,
                {'py': MAT['tilecream'] if k % 2 == 0 else MAT['tilegreen']}, skip=('ny',))
            z, k = z + dz, k + 1
    # --- street-side shopfronts, pilasters, fascia and signboards
    for s in (-1, 1):
        if sides[s] != 'street':
            continue
        sf = side_frame(fr, s)
        for i in range(n):
            xa, xb = X(x0 + i * bw, s), X(x0 + (i + 1) * bw, s)
            xa, xb = min(xa, xb), max(xa, xb)
            sp, sj = special_bay(row, x0 + (i + 0.5) * bw, bw) if s < 0 else (None, None)
            if sp:
                cm = MAT['hallg'] if sp == 'post' else MAT['white']
                box(mb, sf, xa, xa + 0.4, 0, GF - 1.05, HZ - 0.4, HZ, cm)
                box(mb, sf, xb - 0.4, xb, 0, GF - 1.05, HZ - 0.4, HZ, cm)
            else:
                box(mb, sf, xa, xa + 0.32, 0.45, GF - 1.05, HZ - 0.3, HZ + 0.04, MAT['pilaster'])
                box(mb, sf, xa - 0.02, xa + 0.34, 0, 0.45, HZ - 0.3, HZ + 0.06, MAT['hallg'])
            if i in it['pass']:
                continue
            fa, fb = xa + 0.32, xb
            centre = sf.p((fa + fb) / 2, 0, HZ)
            shop = next((k for k, (sx, sz, _) in OPEN_SHOPS.items() if abs(centre[0] - sx) < bw / 2 and abs(centre[2] - sz) < bw / 2), None)
            if sp == 'recess':   # shuttered shop at the back of the end recess: curtain 3 cm proud of the recess wall
                shutter_bay(mb, sf.sub(0, 0, -(REC - 0.45)), fa, fb, r=REC_RNG)
            elif sp:
                special_front(mb, sf, sp, fa, fb, sj)
            elif shop:
                open_shop(mb, sf, shop, fa, fb)
            else:
                shutter_bay(mb, sf, fa, fb)
            box(mb, sf, xa, xb, GF - 1.05, GF - 0.3, HZ - 0.3, HZ, MAT['ground'])
            box(mb, sf, xa, xb, GF - 0.3, GF - 0.14, HZ, HZ + 0.9, MAT['white'])                # canopy ledge
            if row['id'] == 'front':   # globe lamp under the canopy at the pier (photo 22)
                cylv(mb, sf, xa + 0.16, HZ + 0.55, GF - 0.62, GF - 0.3, 0.015, 6, MAT['pole'])
                globe(mb, sf.p(xa + 0.16, GF - 0.78, HZ + 0.55), 0.16, MAT['lamp'])
            nac = LEDGE_RNG.choice((0, 0, 1, 2, 3))
            for k in range(nac):
                xc = xa + (xb - xa) * (k + 0.5 + LEDGE_RNG.uniform(-0.15, 0.15)) / max(nac, 1)
                box(mb, sf, xc - 0.38, xc + 0.38, GF - 0.14, GF + 0.42, HZ - 0.02, HZ + 0.3, MAT['ac'])
                ac_mark(sf, 'split', xc, GF - 0.14, HZ - 0.02)
    # --- courtyard arcade (columns, beam, dado, doors)
    if sides[1] == 'court':
        for i in range(n + 1):
            x = x0 + i * bw + (0.4 if i == 0 else -0.4 if i == n else 0)
            if in_court(row, x):
                cylv(mb, fr, x, HZ - 0.4, 0, GF - 0.3, 0.3, 16, MAT['mred'], caps=False)
        box(mb, fr, x0, x1, GF - 0.75, GF - 0.3, HZ - 0.75, HZ - 0.05, MAT['ground'])
        for a, b in segs:
            sx0, sx1 = x0 + a * bw, x0 + b * bw
            box(mb, fr, sx0, sx1, 0, 1.1, zB, zB + 0.03, MAT['dado'])
            for i in range(a, b):
                if rnd.random() < 0.5 and in_court(row, x0 + (i + 0.5) * bw):
                    xm = x0 + (i + 0.5) * bw
                    box(mb, fr, xm - 0.55, xm + 0.55, 0, 2.2, zB, zB + 0.06, MAT['door'])
    # --- first-floor structural slab and roof slab
    box(mb, fr, x0, x1, GF - 0.3, GF, -HZ, HZ, {'py': MAT['soffit'], 'ny': MAT['soffit'], '*': MAT['white']})
    box(mb, fr, x0, x1, ROOF, RFS, -HZ, HZ, {'py': MAT['screed'], '*': MAT['white']})
    # --- residential core (back wall of the loggias)
    for i in range(n):
        pm = MAT['plaster'][cols[i]]
        box(mb, fr, x0 + i * bw, x0 + (i + 1) * bw, GF, ROOF, -(HZ - LOG), ZL if gal else HZ - LOG,
            {'pz': pm, 'nz': pm, '*': pm if row['id'] == 'front' else MAT['white']}, skip=('py', 'ny'))   # avenue row's ends in mosaic (MH022)
    for s in (-1, 1):
        sf = side_frame(fr, s)
        street = sides[s] == 'street'
        f0 = 1 if (gal and s > 0) else 0
        for i in range(n):
            xa, xb = sorted((X(x0 + i * bw, s), X(x0 + (i + 1) * bw, s)))
            w = xb - xa
            if street:
                street_bay(mb, sf, xa, xb, i, cols[i], full=row['id'] == 'slope1' and cols[i] == G)
                continue
            if in_court(row, x0 + (i + 0.5) * bw):
                court_bay(mb, sf, xa, xb, i, cols[i])
        if street:   # flush white pilasters between bays instead of the courtyard fins
            for i in range(n + 1):
                xi = X(x0 + i * bw, s)
                box(mb, sf, xi - 0.18, xi + 0.18, GF - 0.3, ROOF + 0.3, ZR, ZW + 0.12, MAT['white'])
        else:        # slim white pilasters standing off the courtyard wall, gallery deck to roof
            for i in range(n + 1):
                if in_court(row, x0 + i * bw):
                    xi = X(x0 + i * bw, s)
                    box(mb, sf, xi - 0.17, xi + 0.17, GF - 0.3, ROOF + 0.3, ZL + 0.2, ZC + 0.85, MAT['white'])
        # sloped terracotta tile band and its white cap
        xa, xb = sorted((X(x0, s), X(x1, s)))
        prism_x(mb, sf, [(ZC, ROOF + 0.3), (HZ + 0.95, ROOF + 0.3), (HZ + 0.5, TOP), (ZC, TOP)], xa, xb, MAT['rooftile'])
        box(mb, sf, xa, xb, RFS, TOP, ZC - 0.17, ZC - 0.01, MAT['white'])               # white inner face of the parapet (MH001)
        box(mb, sf, xa, xb, TOP, TOP + 0.12, ZC - 0.17, HZ + 0.6, MAT['white'])
        post = sides[s] == 'court'   # every bay has its own tile cap; the white pilasters run up through the band and, on the
        for i in range(1, n):        # courtyard side only, stand above the parapet as short posts (MH002, MH001)
            xi = X(x0 + i * bw, s)
            box(mb, sf, xi - 0.2, xi + 0.2, ROOF + 0.3, TOP + (0.55 if post else 0.14), ZC - 0.2, HZ + 0.98, MAT['white'])
    # roof (MH001): chunky white vent posts, one per bay near the courtyard side and most bays one near the street side,
    # set at odd places along the bay; a thin red line runs along the roof towards the street side
    vr = random.Random(ROW_SEED[row['id']] * 1000 + int(x0 * 10))
    for i in range(n):
        xa_, xb_ = x0 + i * bw + 0.7, x0 + (i + 1) * bw - 0.7
        posts = [(vr.uniform(xa_, xb_), HZ - 2.4 + vr.uniform(-0.45, 0.3))]                 # courtyard side
        if vr.random() < 0.4:
            posts.append((vr.uniform(xa_, xb_), vr.uniform(0.3, 1.6)))                      # middle
        if vr.random() < 0.3:
            posts.append((vr.uniform(xa_, xb_), -(HZ - 2.4) + vr.uniform(-0.3, 0.45)))     # street side
        for xp, zp in posts:
            box(mb, fr, xp - 0.28, xp + 0.28, RFS, RFS + vr.uniform(1.0, 1.3), zp - 0.28, zp + 0.28, MAT['white'])
    box(mb, fr, x0, x1, RFS, RFS + 0.03, -0.3 * HZ - 0.06, -0.3 * HZ + 0.06, MAT['mred'])
    # open-topped square enclosure in the middle of each block, walls with posts at the corners and a cross wall (MH001)
    xm, ex, ez, zc_, hw = (x0 + x1) / 2, 1.6, 1.45, -0.5, RFS + 1.25
    for xa_, xb_, za_, zb_ in ((xm - ex, xm + ex, zc_ - ez, zc_ - ez + 0.18), (xm - ex, xm + ex, zc_ + ez - 0.18, zc_ + ez),
                               (xm - ex, xm - ex + 0.18, zc_ - ez, zc_ + ez), (xm + ex - 0.18, xm + ex, zc_ - ez, zc_ - 0.45),
                               (xm + ex - 0.18, xm + ex, zc_ + 0.45, zc_ + ez)):   # doorway in the +x wall
        box(mb, fr, xa_, xb_, RFS, hw, za_, zb_, MAT['white'])
    box(mb, fr, xm - 0.09, xm + 0.09, RFS, RFS + 0.95, zc_ - ez, zc_ + ez, MAT['white'])   # cross wall
    for xq in (xm - ex + 0.09, xm + ex - 0.09):
        for zq in (zc_ - ez + 0.09, zc_ + ez - 0.09):
            box(mb, fr, xq - 0.2, xq + 0.2, RFS, hw + 0.45, zq - 0.2, zq + 0.2, MAT['white'])
    for _ in range(max(1, int((x1 - x0) / 12))):
        xr, zr = irng.uniform(x0 + 1, x1 - 1), irng.uniform(-HZ + 1.2, HZ - 1.2)
        if irng.random() < 0.6:   # TV aerial mast
            cylv(mb, fr, xr, zr, RFS, RFS + 3.3, 0.03, 6, MAT['pole'])
            for hh, ln in ((RFS + 3.1, 1.2), (RFS + 2.6, 0.9), (RFS + 2.1, 0.7)):
                cylx(mb, fr, xr - ln / 2, xr + ln / 2, hh, zr, 0.012, 4, MAT['pole'])
        # (no stainless tanks: the roofs carry concrete tanks beside the stair towers, MH001; the draw above is kept)


# ------------------------------------------------------------------ stair towers, gables, corners
def gable(mb, fr, w, base):
    """Arched gable facing local +z, front face at z=0, with the fan-light."""
    r = w / 2
    gr = 1.0
    prof = [(-r, base), (r, base), (r, base + gr)] + [(x, y) for x, y in arc(0, base + gr, r, 0, math.pi, 20)[1:-1]] + [(-r, base + gr)]
    prism_z(mb, fr, prof, -0.35, 0.0, MAT['white'])
    rf = r * 0.78
    half = [(x, y) for x, y in arc(0, base + gr, rf, 0, math.pi, 20)]
    mb.poly([fr.p(x, y, 0.01) for x, y in half], MAT['void'])
    for i in range(11):
        a = math.pi * i / 10
        p0 = fr.p(math.cos(a) * rf * 0.28, base + gr + math.sin(a) * rf * 0.28, 0.05)
        p1 = fr.p(math.cos(a) * rf, base + gr + math.sin(a) * rf, 0.05)
        beam(mb, p0, p1, 0.07, MAT['white'], up=tuple(fr.ez))
    pts = arc(0, base + gr, rf * 0.6, 0, math.pi, 12)
    for a, b in zip(pts, pts[1:]):
        beam(mb, fr.p(a[0], a[1], 0.05), fr.p(b[0], b[1], 0.05), 0.07, MAT['white'], up=tuple(fr.ez))
    hub = [(x, y) for x, y in arc(0, base + gr, rf * 0.28, 0, math.pi, 8)]
    mb.poly([fr.p(x, y, 0.06) for x, y in hub], MAT['white'])


# 馬交石 (user, 2026-10-22: at the foot of 馬交石斜坡 between the sports hall and the estate; MH078, MH079): a granite boulder
# carved RAMPA DOS CAVALLEIROS 1847 under a crowned shield, in a niche of dressed granite (the hall's side) and rubble
# (the estate's side), fronted by a curved low granite wall with brick coping on its east end, red-grey brick paving
MKS = dict(x0=HALL['x1'] - 0.6, x1=HALL['x1'] + 6.2, zb=HALL['z1'], zf=HALL['z1'] + 2.1)


def rock_lobe(mb, c, r, rng, m, zcut=None, seg=14, rings=9):
    """Weathered boulder lobe: an ellipsoid with lumpy radii, cut flat at the ground and, if zcut, at a carved front face."""
    jit = [[0.86 + 0.26 * rng.random() for _ in range(seg)] for _ in range(rings + 1)]
    pts = []
    for i in range(rings + 1):
        ph = math.pi * i / rings
        row = []
        for j in range(seg):
            th = 2 * math.pi * j / seg
            k = jit[i][j] if 0 < i < rings else 1.0
            x = c[0] + r[0] * k * math.sin(ph) * math.cos(th)
            y = max(0.0, c[1] + r[1] * k * math.cos(ph))
            z = c[2] + r[2] * k * math.sin(ph) * math.sin(th)
            row.append(Vector((x, y, min(z, zcut) if zcut is not None else z)))
        pts.append(row)
    for i in range(rings):
        for j in range(seg):
            a, b, cc, d = pts[i][j], pts[i][(j + 1) % seg], pts[i + 1][(j + 1) % seg], pts[i + 1][j]
            mb.poly([a, cc, d] if i == 0 else [a, b, cc] if i == rings - 1 else [a, b, cc, d], m)


def build_makau_stone(mb, f0):
    k = MKS
    x0, x1, zb, zf = k['x0'], k['x1'], k['zb'], k['zf']
    box(mb, f0, x0, x1, 0, 3.6, zb - 0.6, zb, MAT['stone'])                       # dressed granite behind (the hall's)
    box(mb, f0, x0 - 0.6, x0, 0, 3.2, zb - 0.6, zf, MAT['stone'])                 # return on the hall side
    box(mb, f0, x1, x1 + 0.6, 0, 2.6, zb - 0.6, zf, MAT['rock'])                  # rubble wall on the estate side
    flat_ = lambda xa, za, xb, zz, y, m: mb.poly([f0.p(xa, y, zz), f0.p(xb, y, zz), f0.p(xb, y, za), f0.p(xa, y, za)], m)
    flat_(x0, zb, x1, zf + 2.6, 0.17, MAT['brickpave'])                           # red-grey brick paving
    flat_(x0 + 0.2, zf + 1.9, x0 + 1.6, zf + 2.25, 0.175, MAT['steel'])            # drain grate
    rng = random.Random(1847)
    xc = (x0 + x1) / 2
    zcut = zf - 0.45
    rock_lobe(mb, (xc + 0.7, -0.3, zb + 0.95), (2.5, 2.7, 1.25), rng, MAT['stone'], zcut=zcut)   # main block, carved face
    rock_lobe(mb, (xc - 1.9, -0.4, zb + 1.0), (1.35, 1.9, 1.1), rng, MAT['stone'])              # split-off lobe (MH078)
    px0, px1, py0, py1 = xc + 0.27, xc + 1.13, 0.4, 1.9                          # carved panel (MH079), blade atlas cell 0
    mb.poly([f0.p(px0, py0, zcut + 0.012), f0.p(px1, py0, zcut + 0.012), f0.p(px1, py1, zcut + 0.012), f0.p(px0, py1, zcut + 0.012)],
            MAT['signatlas'], uvs=blade_uv(0))
    cz, R = zb + 0.6, (x1 - x0) / 2 + 0.1                                          # curved low wall round the front
    n = 14
    for i in range(n):
        a0, a1 = math.pi * i / n, math.pi * (i + 1) / n
        pa = (xc + R * math.cos(a0), cz + R * 0.75 * math.sin(a0))
        pb = (xc + R * math.cos(a1), cz + R * 0.75 * math.sin(a1))
        top_m = MAT['brickcap'] if i < 4 else MAT['rock']                          # brick coping on the east end
        for y0, y1, m in ((0.0, 0.58, MAT['rock']), (0.58, 0.68, top_m)):
            beam(mb, (pa[0], (y0 + y1) / 2, pa[1]), (pb[0], (y0 + y1) / 2, pb[1]), 0.34 if m is top_m else 0.3, m, h=y1 - y0)


def joint_kind(row, it):
    """'F' or 'V' (see build_joint): the side rows' middle tower is F, their outer two V; the end rows' towers are F."""
    js = [i for i in row['items'] if i['t'] == 'j']
    if row['id'] in ('nw', 'se') and len(js) == 3 and js.index(it) != 1:
        return 'V'
    return 'F'


TOWER_OUT = 1.15   # how far the street stair towers' side walls stand out past HZ (photo 21 sees them deep, with windows)


def build_joint(mb, row, it):
    fr = row['fr']
    x0, x1 = it['x0'], it['x1']
    w, xc, zr = x1 - x0, (it['x0'] + it['x1']) / 2, HZ - 0.6
    box(mb, fr, x0, x1, 0, GF - 0.3, -zr, zr, MAT['white'], skip=('py',))
    for s in (-1, 1):   # lobby entrance with metal gate
        sf = side_frame(fr, s)
        xl = X(xc, s)
        box(mb, sf, xl - 1.1, xl + 1.1, 0, 2.6, zr, zr + 0.02, MAT['void'])
        for k in range(12):
            xx = xl - 1.05 + k * 0.19
            box(mb, sf, xx - 0.015, xx + 0.015, 0, 2.6, zr + 0.05, zr + 0.08, MAT['gate'])
        box(mb, sf, xl - 1.1, xl + 1.1, 1.5, 1.56, zr + 0.04, zr + 0.09, MAT['gate'])
        box(mb, sf, xl - 0.5, xl + 0.5, 2.85, 3.25, zr, zr + 0.05, MAT['signs'][4])
    gal = bool(row.get('gallery'))
    zwell = zr - 1.6   # back of the open courtyard stair well
    box(mb, fr, x0 + 0.4, x1 - 0.4, GF - 0.3, TOP - 0.3, -(zr - 0.4), zwell if gal else zr - 0.4, MAT['void'], skip=('ny', 'py'))
    box(mb, fr, x0, x1, TOP - 0.3, TOP, -(zr + 0.06), zr + 0.06, {'py': MAT['screed'], '*': MAT['white']})
    jsides = {-1: row['outer'], 1: 'court' if gal else 'street'}
    for s in (-1, 1):
        sf = side_frame(fr, s)
        xa, xb = sorted((X(x0, s), X(x1, s)))
        if jsides[s] == 'street':
            prism_z(mb, sf, arc(X(xc, s), 2.75, 1.45, 0, math.pi, 16), HZ - 0.4,
                    HZ + (0.95 if row['id'] == 'slope1' else TOWER_OUT + 0.25), MAT['white'])          # lobby hood
            if row['id'] == 'slope1':   # hillside tower: plain white wall standing proud of the facade (MH068)
                box(mb, sf, xa - 0.05, xb + 0.05, GF - 0.3, TOP + 0.6, zr - 0.4, HZ + 0.75, MAT['whitetile'])
                for f in range(1, NF, 2):
                    y = GF + FH * f
                    window(mb, sf, X(xc, s) - 0.3, X(xc, s) + 0.3, y + 1.2, y + 2.0, HZ + 0.75, mull=False)
                continue
            ia, ib = xa + 0.55, xb - 0.55   # white side walls well proud of the facade, open stairs between them
            zt = HZ + TOWER_OUT
            for wa, wb in ((xa - 0.05, ia), (ib, xb + 0.05)):
                box(mb, sf, wa, wb, GF - 0.3, TOP + 0.6, zr - 0.4, zt, MAT['whitetile'])
            for f in range(NF):   # small windows in the side walls where they stand out of the facade (photo 21, MH018)
                y = GF + FH * f
                for xw, rot in ((xa - 0.05, -math.pi / 2), (xb + 0.05, math.pi / 2)):
                    window(mb, sf.sub(xw, 0, zt - 0.55, rot=rot), -0.22, 0.22, y + 1.5, y + 2.1, 0.0, mull=False, cells=4)
            box(mb, sf, ia, ib, ROOF - 0.1, TOP + 0.6, zr - 0.4, zt, MAT['whitetile'])             # solid head
            box(mb, sf, ia, ib, GF - 0.3, ROOF - 0.1, zr - 0.42, zr - 0.38, MAT['soffit'])         # back of the stair well
            for f in range(NF):
                yl = GF + FH * f + FH / 2   # half landing
                box(mb, sf, ia, ib, yl - 0.15, yl, zr - 0.38, zt - 0.25, MAT['white'])             # landing slab edge
                box(mb, sf, ia, ib, yl, min(yl + 1.35, ROOF - 0.1), zt - 0.35, zt - 0.27, MAT['breeze'])   # breeze screen
                prism_z(mb, sf, [(ia + 0.05, yl - FH / 2 - 0.3), (ib - 0.05, yl - 0.2), (ib - 0.05, yl - 0.02), (ia + 0.05, yl - FH / 2 - 0.12)],
                        zr - 0.38, zt - 0.45, MAT['soffit'])                                        # flight up to it
            continue
        ia, ib = xa + 0.4, xb - 0.4
        for f in range(NF):
            y = GF + FH * f
            box(mb, sf, ia, ib, y - 0.3, y + 0.02, zwell, zr + 0.06, {'py': MAT['deck'], '*': MAT['white']})   # landing
            for hh in (0.6, 1.02):
                cylx(mb, sf, ia, ib, y + hh, zr - 0.02, 0.03, 8, MAT['creampipe'])
            for xp in (ia + 0.05, (ia + ib) / 2, ib - 0.05):
                cylv(mb, sf, xp, zr - 0.02, y + 0.02, y + 1.04, 0.025, 6, MAT['creampipe'])
            if f < NF - 1:
                box(mb, sf, ia + 0.5, ib - 0.5, y + 0.45, y + FH - 0.45, zwell, zwell + 0.06, MAT['breeze'])   # back wall
                prism_z(mb, sf, [(ia + 0.05, y - 0.15), (ib - 0.05, y + FH - 0.45), (ib - 0.05, y + FH - 0.3), (ia + 0.05, y + 0.02)],
                        zwell + 0.08, zr - 0.6, MAT['soffit'])                                      # flight
        for xp in (ia + 0.15, ib - 0.15):   # downpipes on the side walls of the well
            cylv(mb, sf, xp, zr - 0.3, GF - 0.3, ROOF, 0.05, 8, MAT['white'])
        box(mb, sf, ia, ib, ROOF - 0.1, TOP, zr - 0.4, zr + 0.06, MAT['white'])
    for xe in (x0, x1 - 0.4):
        box(mb, fr, xe, xe + 0.4, 0, TOP, -(HZ + 0.15), HZ + 0.15, MAT['whitetile'])
    zg = zr - 1.15                   # inner face of the gables
    kind = joint_kind(row, it)
    if kind == 'V':
        box(mb, fr, xc - 1.5, xc + 1.5, TOP, TOP + 1.0, -zg - 0.6, zg, MAT['white'], skip=('py',))
        prism_z(mb, fr, arc(xc, TOP + 1.0, 1.5, 0, math.pi, 16), -zg - 0.6, zg, MAT['white'])   # barrel vault across the block
        for sx in (-1, 1):
            wf = fr.sub(xc + sx * 1.5, 0, 0, rot=sx * math.pi / 2)
            box(mb, wf, -sx * 0.2 - 0.4, -sx * 0.2 + 0.4, TOP, TOP + 1.9, 0.0, 0.03, MAT['void'])   # doorway onto the roof
    else:
        box(mb, fr, xc - 1.6, xc + 1.6, TOP, TOP + 2.3, -zg, zg, {'py': MAT['screed'], '*': MAT['white']})   # flat stair room
        box(mb, fr, xc - 1.7, xc + 1.7, TOP + 2.3, TOP + 2.42, -zg - 0.05, zg + 0.05, MAT['white'], skip=('ny',))
        for sx in (-1, 1):
            wf = fr.sub(xc + sx * 1.6, 0, 0, rot=sx * math.pi / 2)                            # faces +-x
            for zw in (-zg + 0.7, zg - 0.7):
                box(mb, wf, -sx * zw - 0.25, -sx * zw + 0.25, TOP + 1.25, TOP + 1.85, 0.0, 0.03, MAT['void'])   # small windows
            box(mb, wf, -0.4, 0.4, TOP, TOP + 1.95, 0.0, 0.03, MAT['void'])                     # doorway
    for xw in (x0 + 0.1, x1 - 0.3):    # low white walls along the tower top, posts standing above them
        box(mb, fr, xw, xw + 0.2, TOP, TOP + 0.8, -zg, zg, MAT['white'])
        zp = -zg + 0.15
        while zp < zg:
            box(mb, fr, xw - 0.08, xw + 0.28, TOP, TOP + 1.3, zp - 0.18, zp + 0.18, MAT['white'])
            zp += 1.55
    for s in (-1, 1):
        if kind == 'V' and jsides[s] == 'street':   # the vault meets the tower's plain head on the street side
            continue
        sf = side_frame(fr, s)
        gable(mb, sf.sub(X(xc, s), 0, zr - 0.8), w, TOP)


def build_corner(mb, cx, cz, gable_side):
    fr = Fr((cx, 0, cz))
    box(mb, fr, -HZ, HZ, 0, GF - 0.3, -HZ, HZ, MAT['white'], skip=('py',))
    box(mb, fr, -HZ + 0.4, HZ - 0.4, GF - 0.3, TOP - 0.3, -HZ + 0.4, HZ - 0.4, MAT['void'], skip=('py',))
    box(mb, fr, -HZ, HZ, TOP - 0.3, TOP, -HZ, HZ, {'py': MAT['screed'], '*': MAT['white']})
    for rot in (0, math.pi / 2, math.pi, -math.pi / 2):
        sf = fr.sub(rot=rot)
        for f in range(NF):
            y = GF + FH * f
            box(mb, sf, -HZ + 0.4, HZ - 0.4, y - 0.1, y + 0.18, HZ - 0.4, HZ + 0.06, MAT['white'])
            box(mb, sf, -HZ + 0.4, HZ - 0.4, y + 0.18, y + FH - 0.1, HZ - 0.18, HZ - 0.03, MAT['breeze'])
        box(mb, sf, -HZ + 0.4, HZ - 0.4, ROOF - 0.1, TOP, HZ - 0.4, HZ + 0.06, MAT['white'])
        box(mb, sf, -HZ, -HZ + 0.6, 0, TOP + 0.2, HZ - 0.6, HZ + 0.1, MAT['white'])
    box(mb, fr, -2.4, 2.4, TOP, TOP + 2.4, -2.2, 2.2, {'py': MAT['screed'], '*': MAT['white']})   # flat-roofed head (MH001)
    box(mb, fr, -2.5, 2.5, TOP + 2.4, TOP + 2.52, -2.3, 2.3, MAT['white'], skip=('ny',))
    for rot in (math.pi / 2, -math.pi / 2):
        wf = fr.sub(0, 0, 0, rot=rot).sub(0, 0, 2.4)
        for xw in (-1.2, 1.2):
            box(mb, wf, xw - 0.25, xw + 0.25, TOP + 1.25, TOP + 1.85, 0.0, 0.03, MAT['void'])
    gable(mb, fr.sub(rot=0 if gable_side > 0 else math.pi).sub(0, 0, 2.2), 5.0, TOP)


# ------------------------------------------------------------------ galleries, bridges, stairs (黃色紙皮石 + 紅色紙皮石)
def parapet_run(mb, fr, xa, xb, z, y):
    L = xb - xa
    if L <= 0.3:
        return
    box(mb, fr, xa, xb, y, y + 0.85, z - 0.11, z + 0.11, MAT['myellow'])
    box(mb, fr, xa, xb, y + 0.85, y + 0.9, z - 0.13, z + 0.13, MAT['myellow'])
    n = max(1, round(L / 4.4))
    for i in range(n + 1):
        xp = xa + L * i / n
        box(mb, fr, xp - 0.17, xp + 0.17, y, y + 1.3, z - 0.17, z + 0.17, MAT['mred'])
    k = max(1, round(L / 1.5))
    for i in range(k + 1):
        cylv(mb, fr, xa + L * i / k, z, y + 0.9, y + 1.32, 0.025, 6, MAT['creampipe'])
    for h in (1.32, 1.1):
        cylx(mb, fr, xa, xb, y + h, z, 0.03, 8, MAT['creampipe'])


def zrun(mb, x, za, zb, y, gaps=()):
    """Parapet along z at x (inner gallery edge), with gaps (z ranges) for the bridge and stairs."""
    fz = Fr((x, 0, 0), (0, 0, 1), (-1, 0, 0))
    cur = za
    for a, b in sorted(gaps) + [(zb, zb)]:
        parapet_run(mb, fz, cur, min(a, zb), 0.0, y)
        cur = max(cur, b)


def build_galleries(mb):
    """First-floor gallery all round the courtyard (photo 14): decks, inner parapet ring, columns beneath."""
    deck = {'py': MAT['deck'], 'ny': MAT['soffit'], '*': MAT['white']}
    f0 = Fr()
    box(mb, f0, CX0, CX1, GF - 0.3, GF, CZ0, GZ0, deck)
    box(mb, f0, CX0, CX1, GF - 0.3, GF, GZ1, CZ1, deck)
    box(mb, f0, CX0, NWG, GF - 0.3, GF, GZ0, GZ1, deck)
    box(mb, f0, SEG, CX1, GF - 0.3, GF, GZ0, GZ1, deck)
    parapet_run(mb, f0, NWG, SEG, GZ0 - 0.11, GF)
    parapet_run(mb, Fr((0, 0, 0), (-1, 0, 0), (0, 0, -1)), -SEG, -NWG, -(GZ1 + 0.11), GF)
    gaps = [(BRIDGE_Z - 2.0, BRIDGE_Z + 2.0)] + [(stair_flight_z(z)[0], stair_flight_z(z)[1]) for z in STAIRS]
    zrun(mb, NWG - 0.11, GZ0, GZ1, GF, gaps)
    zrun(mb, SEG + 0.11, GZ0, GZ1, GF, gaps)
    for x in [NWG + 0.5 + k * 4.4 for k in range(int((SEG - NWG) / 4.4) + 1)]:
        for z in (GZ0 - 0.4, GZ1 + 0.4):
            cylv(mb, f0, x, z, 0, GF - 0.3, 0.3, 16, MAT['mred'], caps=False)
    for z in [GZ0 + 2.2 + k * 4.4 for k in range(int((GZ1 - GZ0) / 4.4))]:
        if all(abs(z - c) > 2.6 for c in [BRIDGE_Z] + STAIRS):
            for x in (NWG - 0.4, SEG + 0.4):
                cylv(mb, f0, x, z, 0, GF - 0.3, 0.3, 16, MAT['mred'], caps=False)
    for (x, z) in ((CX0, CZ0), (CX1, CZ0), (CX0, CZ1), (CX1, CZ1)):   # inner corners: close the facade slot
        sx, sz = (1 if x == CX0 else -1), (1 if z == CZ0 else -1)
        box(mb, f0, x - sx * 0.65, x + sx * 0.08, GF - 0.3, ROOF + 0.3, z - sz * 0.65, z + sz * 0.08, MAT['white'])


def build_bridge(mb, xa, xb, z):
    """Library bridge, 4 m wide, on red posts at the gallery end and ~12.7 m from the library centre (photo 14)."""
    fr = Fr(((xa + xb) / 2, 0, z))
    L, hw = xb - xa, 2.0
    box(mb, fr, -L / 2, L / 2, GF - 0.3, GF, -hw, hw, {'py': MAT['deck'], 'ny': MAT['soffit'], '*': MAT['white']})
    for s in (-1, 1):
        parapet_run(mb, fr, -L / 2, L / 2, s * (hw - 0.11), GF)
    for xs in (xa + 0.4 if xa < LIB_X else xb - 0.4, LIB_X + (12.7 if xa > LIB_X else -12.7)):
        for s in (-1, 1):
            cylv(mb, Fr(), xs, z + s * (hw - 0.35), 0, GF - 0.3, 0.3, 16, MAT['mred'], caps=False)


STEPS_HALF, RUN, FLW, LAND, GAP = 12, 0.30, 1.5, 1.8, 0.25   # per flight: risers, tread; flight width; landing; gap


def stair_flight_z(zc):
    """z range of the upper flight (the one that meets the gallery deck), towards the library."""
    d = -1 if zc > LZ else 1
    a, b = zc + d * GAP / 2, zc + d * (GAP / 2 + FLW)
    return min(a, b), max(a, b)


def stair_rail(mb, a, b):
    """Cream pipe railing, four rails, between site points a and b (heights above the walking line)."""
    for h in (0.3, 0.55, 0.8, 1.05):
        beam(mb, (a[0], a[1] + h, a[2]), (b[0], b[1] + h, b[2]), 0.04, MAT['creampipe'])


def hollow_flight(mb, x_foot, dirx, za, zb, y0):
    """A flight on an inclined slab (open underneath): bottom step at x_foot, climbing along dirx from y0."""
    rise = GF / (2 * STEPS_HALF)
    n, T = STEPS_HALF, 0.28
    prof = [(x_foot, y0)]
    for i in range(n):
        x1 = x_foot + dirx * i * RUN
        prof += [(x1, y0 + rise * (i + 1)), (x1 + dirx * RUN, y0 + rise * (i + 1))]
    xh = x_foot + dirx * n * RUN
    prof += [(xh, y0 + rise * n - T), (x_foot + dirx * 0.45, y0)]
    area = sum(prof[i][0] * prof[(i + 1) % len(prof)][1] - prof[(i + 1) % len(prof)][0] * prof[i][1] for i in range(len(prof)))
    if area < 0:
        prof = prof[::-1]
    prism_z(mb, Fr(), prof, za, zb, MAT['white'])
    for i in range(n):   # tread finish
        x1 = x_foot + dirx * i * RUN
        xa_, xb_ = sorted((x1, x1 + dirx * RUN))
        box(mb, Fr(), xa_, xb_, y0 + rise * (i + 1), y0 + rise * (i + 1) + 0.015, za + 0.02, zb - 0.02, MAT['deck'])


def build_stair_u(mb, x_edge, zc, side):
    """Dog-leg stair standing out from a gallery (photos 14, user crop): the upper flight leaves the deck flush and
    runs out into the courtyard to a landing on red posts; the lower flight returns to the ground beside the gallery.
    Both flights are open underneath. side = +1 when the courtyard is towards +x."""
    ua, ub = stair_flight_z(zc)                         # upper flight
    d = 1 if zc > LZ else -1                            # lower flight sits on the far side of zc
    la, lb = sorted((zc + d * GAP / 2, zc + d * (GAP / 2 + FLW)))
    L = STEPS_HALF * RUN
    x_land = x_edge + side * L
    x_far = x_land + side * LAND
    hollow_flight(mb, x_land, -side, ua, ub, GF / 2)    # landing -> deck
    hollow_flight(mb, x_edge, side, la, lb, 0.0)        # ground -> landing
    lx0, lx1 = sorted((x_land, x_far))
    za_all, zb_all = min(ua, la), max(ub, lb)
    box(mb, Fr(), lx0, lx1, GF / 2 - 0.25, GF / 2, za_all, zb_all, {'py': MAT['deck'], '*': MAT['white']})
    # railings: outer sides, round the landing, between the flights
    zo_u = ub + 0.05 if d < 0 else ua - 0.05            # outer edge of the upper flight
    zo_l = la - 0.05 if d < 0 else lb + 0.05
    zm = zc
    stair_rail(mb, (x_edge, GF, zo_u), (x_land, GF / 2, zo_u))
    stair_rail(mb, (x_land, GF / 2, zo_u), (x_far, GF / 2, zo_u))
    stair_rail(mb, (x_far, GF / 2, zo_u), (x_far, GF / 2, zo_l))
    stair_rail(mb, (x_far, GF / 2, zo_l), (x_land, GF / 2, zo_l))
    stair_rail(mb, (x_land, GF / 2, zo_l), (x_edge + side * 0.3, 0.1, zo_l))
    stair_rail(mb, (x_edge + side * 0.6, 0.25, zm + d * 0.1), (x_land, GF / 2, zm + d * 0.1))
    stair_rail(mb, (x_land, GF / 2, zm - d * 0.1), (x_edge, GF, zm - d * 0.1))
    for (px, pz, h) in ((x_edge + side * 0.25, zo_l, 1.4), (x_far, zo_u, GF / 2 + 1.4), (x_far, zo_l, GF / 2 + 1.4)):
        cylv(mb, Fr(), px, pz, 0, h, 0.22, 16, MAT['mred'])
        cylv(mb, Fr(), px, pz, h, h + 0.08, 0.27, 16, MAT['mred'])


# ------------------------------------------------------------------ library (three-storey octagon, 1988–2011)
OCT = math.pi / 8


def face_frame(fr, k, apo, y=0.0):
    a = k * math.pi / 4
    return fr.sub(math.sin(a) * apo, y, math.cos(a) * apo, rot=a)


def oct_corner(r, k):
    """Plan corner k (local x, z) of an octagon with corner radius r; corner k sits between faces k and k + 1."""
    return math.sin(OCT + k * math.pi / 4) * r, math.cos(OCT + k * math.pi / 4) * r


def lib_seg(lf, a, b):
    """Frame on the library plan segment a -> b (local x, z): x along it from its middle, z outward when the plan runs
    clockwise seen from above (as face_frame does); returns the frame and the segment length."""
    pa, pb = lf.p(a[0], 0, a[1]), lf.p(b[0], 0, b[1])
    ex = (pb - pa).normalized()
    return Fr((pa + pb) / 2, tuple(ex), (-ex.z, 0, ex.x)), (pb - pa).length


def lib_slab(mb, lf, pts, y0, y1, top, bottom, side):
    """Flat slab on a convex plan outline (local x, z, clockwise seen from above)."""
    mb.poly([lf.p(x, y1, z) for x, z in pts], top)
    mb.poly([lf.p(x, y0, z) for x, z in reversed(pts)], bottom)
    for a, b in zip(pts, pts[1:] + pts[:1]):
        mb.poly([lf.p(a[0], y0, a[1]), lf.p(b[0], y0, b[1]), lf.p(b[0], y1, b[1]), lf.p(a[0], y1, a[1])], side)


def lib_glass(mb, fr, ln, y0, y1, ya, yb, panel=2.2):
    """Glazed wall between y0 and y1: cream sill and head strips, framed panes from ya to yb."""
    box(mb, fr, -ln / 2, ln / 2, y0, ya, -0.15, 0.0, MAT['lcream'])
    box(mb, fr, -ln / 2, ln / 2, yb, y1, -0.15, 0.0, MAT['lcream'])
    n = max(1, round(ln / panel))
    for j in range(n):
        xa = -ln / 2 + j * ln / n
        window(mb, fr, xa + 0.07, xa + ln / n - 0.07, ya, yb, 0.0, mull=True, gm=MAT['lglass'], cells=4)


def build_library(mb):
    lf = Fr((LIB_X, 0, LIB_Z))
    L = LIB
    f0_, f1_ = L['fascia']
    l2, l3 = GF, 7.95                     # first floor level with the galleries and bridges; top floor
    jx, jz = oct_corner(L['col'], 0)[0], oct_corner(L['col'], 0)[1] + L['jut']   # the jut's outer columns
    sx = oct_corner(L['slab'], 0)[0]
    outline = [(-sx, jz + 0.06), (sx, jz + 0.06)] + [oct_corner(L['slab'], k) for k in range(8)]   # slab: octagon + jut
    # ground floor: yellow tile on the octagon, a dark green plinth
    cylv(mb, lf, 0, 0, 0, 0.45, L['wall'] + 0.3, 8, MAT['lgreend'], phase=OCT)
    cylv(mb, lf, 0, 0, 0.45, l2 - 0.4, L['wall'], 8, MAT['lyellow'], phase=OCT, caps=False)
    for k in range(8):
        ff = face_frame(lf, k, L['wall'] * math.cos(OCT))
        hw = L['wall'] * math.sin(OCT) - 0.35
        if k == 6:   # entrance under the north-west bridge (MH034): glazed doors and side lights, the name board above
            window(mb, ff, -1.5, 1.5, 0.45, 2.75, 0.0, mull=True, gm=MAT['lglass'], cells=4)
            for xm in (-2.75, 2.75):
                window(mb, ff, xm - 0.45, xm + 0.45, 0.45, 2.75, 0.0, mull=False, gm=MAT['lglass'], cells=4)
            box(mb, ff, -1.9, 1.9, 2.9, 3.3, 0.0, 0.08, MAT['lsign'])
            continue
        for j in range(4):   # a band of windows under the first-floor slab
            xa = -hw + j * hw / 2
            window(mb, ff, xa + 0.05, xa + hw / 2 - 0.05, 1.7, 3.1, 0.0, mull=False, gm=MAT['lglass'], cells=4)
    # first floor: the slab with the jut, a walkway round the court side, the reading room on the back half and the jut
    lib_slab(mb, lf, outline, l2 - 0.4, l2, MAT['deck'], MAT['soffit'], MAT['lcream'])
    room = [(-sx + 0.17, jz - 0.25), (sx - 0.17, jz - 0.25), oct_corner(L['wall'], 0), oct_corner(L['wall'], 1)]
    room += [oct_corner(L['inner'], k) for k in range(1, 7)] + [oct_corner(L['wall'], 6), oct_corner(L['wall'], 7)]
    for i, (a, b) in enumerate(zip(room, room[1:] + room[:1])):
        fr, ln = lib_seg(lf, a, b)
        if i in (3, 9):   # where the room steps in from the octagon to the walkway: solid
            box(mb, fr, -ln / 2, ln / 2, l2, l3 - 0.35, -0.2, 0.0, MAT['lcream'])
        else:
            lib_glass(mb, fr, ln, l2, l3 - 0.35, l2 + 0.35, l3 - 0.65)
    # top floor: slab with the balcony, a cream band round the slab edge (the balcony parapet over the jut), glass above
    lib_slab(mb, lf, outline, l3 - 0.35, l3, MAT['deck'], MAT['soffit'], MAT['lcream'])
    for i, (a, b) in enumerate(zip(outline, outline[1:] + outline[:1])):
        fr, ln = lib_seg(lf, a, b)
        box(mb, fr, -ln / 2, ln / 2, l3 - 0.35, L['band'], -0.25, 0.0, MAT['lcream'])
        if i in (0, 1, 9):   # balcony railing on the jut's three sides (MH034)
            for y_ in (L['band'] + 0.32, L['band'] + 0.05):
                box(mb, fr, -ln / 2, ln / 2, y_, y_ + 0.05, -0.15, -0.1, MAT['creampipe'])
            for j in range(int(ln / 1.6) + 1):
                xp = -ln / 2 + 0.05 + j * (ln - 0.1) / int(ln / 1.6)
                box(mb, fr, xp - 0.04, xp + 0.04, L['band'], L['band'] + 0.37, -0.15, -0.1, MAT['creampipe'])
    for k in range(8):
        ff = face_frame(lf, k, L['wall'] * math.cos(OCT))
        hw = L['wall'] * math.sin(OCT)
        if k == 0:   # glazed full height onto the balcony
            lib_glass(mb, ff, 2 * hw, l3, f0_, l3 + 0.05, f0_ - 0.35, panel=1.8)
        else:
            lib_glass(mb, ff, 2 * hw, l3, f0_, L['band'] + 0.05, f0_ - 0.35)
    # roof: low octagonal pyramid with standing seams and ridge caps over the top floor and the column ring
    cylv(mb, lf, 0, 0, f0_, f1_, L['col'] + 0.5, 8, MAT['lgreen'], phase=OCT)       # deep dark fascia (MH034)
    eave_r, apex = L['eave'], L['apex']
    ang = [OCT + 2 * math.pi * i / 8 for i in range(8)]
    base = [lf.p(eave_r * math.sin(a), f1_, eave_r * math.cos(a)) for a in ang]
    top = lf.p(0, apex, 0)
    for i in range(8):
        mb.poly([base[i], base[(i + 1) % 8], top], MAT['lgreen'])
        beam(mb, base[i], top, 0.2, MAT['lgreen'])
        for t in (0.2, 0.4, 0.6, 0.8):
            pa = base[i].lerp(base[(i + 1) % 8], t)
            beam(mb, pa, pa.lerp(top, 0.92), 0.05, MAT['lgreen'])
    mb.poly(list(reversed(base)), MAT['soffit'])
    # first-floor planter ring along the walkway; the shared random stream is drawn as before (two planters fewer than
    # the old ring, whose back faces are now the reading room)
    for k in range(8):
        if k in (2, 6):   # the bridges arrive here
            continue
        if k not in (3, 4, 5):
            for _ in range(20):
                rnd.random()
            continue
        fp = face_frame(lf, k, L['slab'] * math.cos(OCT) - 0.3)
        e = 2 * (L['slab'] * math.cos(OCT) - 0.3) * math.tan(OCT) - 0.75
        box(mb, fp, -e / 2, e / 2, l2, l2 + 0.95, -0.25, 0.25, MAT['lcream'])
        box(mb, fp, -e / 2 + 0.1, e / 2 - 0.1, l2 + 0.75, l2 + 0.85, -0.15, 0.15, MAT['soil'])
        for j in range(10):
            t = (j / 9 - 0.5) * (e - 0.6)
            c = fp.p(t, l2 + 0.85, 0.05)
            SHRUBS.append(dict(p=[c[0], c[1], c[2]], s=0.45 + 0.2 * rnd.random(), bouga=rnd.random() < 0.45))
    # red mosaic columns: the ring from the ground to the fascia, and two under the jut's outer corners to the parapet
    for k in range(8):
        cx_, cz_ = oct_corner(L['col'], k)
        cylv(mb, lf, cx_, cz_, 0, f0_, 0.36, 16, MAT['mred'])
    for s_ in (-1, 1):
        cylv(mb, lf, s_ * jx, jz, 0, L['band'], 0.36, 16, MAT['mred'])


# ------------------------------------------------------------------ courtyard furniture
def build_courtyard(mb):
    f0 = Fr()
    # 鐵籠球場 — caged ball court
    c = CAGE
    w, d, h = c['x1'] - c['x0'], c['z1'] - c['z0'], c['h']
    mb.poly([f0.p(c['x0'], 0.06, c['z1']), f0.p(c['x1'], 0.06, c['z1']), f0.p(c['x1'], 0.06, c['z0']), f0.p(c['x0'], 0.06, c['z0'])], MAT['court'])
    zmid = (c['z0'] + c['z1']) / 2
    for (xa, za, xb, zb) in ((c['x0'] + 0.5, c['z0'] + 0.5, c['x1'] - 0.5, c['z0'] + 0.58), (c['x0'] + 0.5, c['z1'] - 0.58, c['x1'] - 0.5, c['z1'] - 0.5),
                             (c['x0'] + 0.5, c['z0'] + 0.5, c['x0'] + 0.58, c['z1'] - 0.5), (c['x1'] - 0.58, c['z0'] + 0.5, c['x1'] - 0.5, c['z1'] - 0.5),
                             (c['x0'] + 0.5, zmid - 0.04, c['x1'] - 0.5, zmid + 0.04)):
        box(mb, f0, xa, xb, 0.06, 0.075, za, zb, MAT['cline'])
    for i in range(7):
        for z in (c['z0'], c['z1']):
            x = c['x0'] + w * i / 6
            box(mb, f0, x - 0.08, x + 0.08, 0, h, z - 0.08, z + 0.08, MAT['steel'])
    for i in range(1, 9):
        for x in (c['x0'], c['x1']):
            z = c['z0'] + d * i / 9
            box(mb, f0, x - 0.08, x + 0.08, 0, h, z - 0.08, z + 0.08, MAT['steel'])
    for y in (h - 0.07, 2.4):
        box(mb, f0, c['x0'], c['x1'], y - 0.05, y + 0.05, c['z0'] - 0.06, c['z0'] + 0.06, MAT['steel'])
        box(mb, f0, c['x0'], c['x1'], y - 0.05, y + 0.05, c['z1'] - 0.06, c['z1'] + 0.06, MAT['steel'])
        box(mb, f0, c['x0'] - 0.06, c['x0'] + 0.06, y - 0.05, y + 0.05, c['z0'], c['z1'], MAT['steel'])
        box(mb, f0, c['x1'] - 0.06, c['x1'] + 0.06, y - 0.05, y + 0.05, c['z0'], c['z1'], MAT['steel'])
    for (pa, pb) in (((c['x0'], c['z0']), (c['x1'], c['z0'])), ((c['x1'], c['z1']), (c['x0'], c['z1'])), ((c['x0'], c['z1']), (c['x0'], c['z0'])), ((c['x1'], c['z0']), (c['x1'], c['z1']))):
        for side in (1, -1):   # chain-link both faces so it reads from inside and out
            p = [f0.p(pa[0], 0.05, pa[1]), f0.p(pb[0], 0.05, pb[1]), f0.p(pb[0], h, pb[1]), f0.p(pa[0], h, pa[1])]
            mb.poly(p if side > 0 else list(reversed(p)), MAT['chain'])
    for z in (c['z0'] + 1.4, c['z1'] - 1.4):   # hoops at the two short ends
        xc = LX
        box(mb, f0, xc - 0.07, xc + 0.07, 0, 3.6, z - 0.07, z + 0.07, MAT['steel'])
        box(mb, f0, xc - 0.9, xc + 0.9, 2.9, 3.95, z - 0.05, z + 0.05, MAT['cline'])
        zr = z + (0.35 if z < zmid else -0.35)
        pts = [(xc + a, zr + b) for a, b in arc(0, 0, 0.23, 0, 2 * math.pi, 12)]
        for a, b in zip(pts, pts[1:]):
            beam(mb, f0.p(a[0], 3.05, a[1]), f0.p(b[0], 3.05, b[1]), 0.025, MAT['pred'])
    build_playground(mb)
    # 龜池 (residents' memory) between the cage and the library
    pond = (LX - 12, LZ - 14)
    pf = Fr((pond[0], 0, pond[1]))
    cylv(mb, pf, 0, 0, 0, 0.55, 2.7, 24, MAT['rock'], caps=False)
    ring = arc(0, 0, 2.7, 0, 2 * math.pi, 24)
    ring_in = arc(0, 0, 2.35, 0, 2 * math.pi, 24)
    for i in range(24):
        a, b = ring[i], ring[i + 1]
        ai, bi = ring_in[i], ring_in[i + 1]
        mb.poly([pf.p(ai[0], 0.55, ai[1]), pf.p(bi[0], 0.55, bi[1]), pf.p(b[0], 0.55, b[1]), pf.p(a[0], 0.55, a[1])], MAT['rock'])
        mb.poly([pf.p(ai[0], 0.3, ai[1]), pf.p(ai[0], 0.55, ai[1]), pf.p(bi[0], 0.55, bi[1]), pf.p(bi[0], 0.3, bi[1])], MAT['rock'])
    mb.poly([pf.p(x, 0.45, z) for x, z in reversed(ring_in[:-1])], MAT['water'])
    for k in range(4):
        blob(mb, pf.p(math.cos(k * 1.7) * 1.2, 0.55, math.sin(k * 1.7) * 1.2), 0.45 + 0.3 * rnd.random(), MAT['rock'], sy=0.7)
    # planter seats (positions read off photo 14 with the solved camera; mirrored for the front half)
    for spec in PLANTERS:
        planter_seat(mb, *spec)
    for (x, z) in DISCS:
        dfr = Fr((LX + x, 0, LZ + z))
        cylv(mb, dfr, 0, 0, 0, 0.06, 0.85, 20, MAT['bench'])
        cylv(mb, dfr, 0, 0, 0.06, 0.08, 0.72, 20, MAT['disc'], caps=True)
        for k in range(5):
            a = k * 1.256
            SHRUBS.append(dict(p=[LX + x + math.cos(a) * 0.4, 0.08, LZ + z + math.sin(a) * 0.4], s=0.28, bouga=False))
    # big four-legged stone benches under the bridges (photo 14)
    for xs in (-1, 1):   # four per side: two rows of two under each bridge (user)
        for dx, dz in ((11.0, -1.0), (15.0, -1.0), (11.0, 1.0), (15.0, 1.0)):
            bf = Fr((LX + xs * dx, 0, BRIDGE_Z + dz))
            box(mb, bf, -1.15, 1.15, 0.34, 0.46, -0.35, 0.35, MAT['bench'])
            for ex in (-0.9, 0.9):
                for ez in (-0.22, 0.22):
                    box(mb, bf, ex - 0.1, ex + 0.1, 0, 0.34, ez - 0.1, ez + 0.1, MAT['bench'])
    # slab benches under the side gallery overhangs, just outside the column line, where residents sat and played chess
    # (YOLIVING recreation the user confirmed for the surroundings, 2026-10-22); kept clear of the stairs and bridge posts
    for xb in (CX0 + 1.3, CX1 - 1.3):
        for zb in (LZ - 18, LZ - 8, LZ + 8, LZ + 18):
            bf = Fr((xb, 0, zb), ex=(0, 0, 1), ez=(-1, 0, 0))
            box(mb, bf, -1.0, 1.0, 0.36, 0.46, -0.24, 0.24, MAT['bench'])
            for ex in (-0.8, 0.8):
                box(mb, bf, ex - 0.09, ex + 0.09, 0, 0.36, -0.19, 0.19, MAT['bench'])
    for (x, z) in LAMPS:
        lp = Fr((LX + x, 0, LZ + z))
        cylv(mb, lp, 0, 0, 0, 3.2, 0.07, 10, MAT['steel'], r1=0.05)
        sphere(mb, lp.p(0, 3.45, 0), 0.26, MAT['lamp'])


# planter seats: (x, z rel. library, kind, length, width, rotation deg about y, tree?) — 'L' = chevron of two arms
_BACK = [(-5.8, 15.6, 'L', 4.4, 1.6, 0, True), (5.9, 15.4, 'L', 4.4, 1.6, 0, True),
         (-12.6, 20.2, 'R', 4.6, 2.6, 45, True), (12.8, 19.3, 'R', 4.6, 2.6, -45, True),
         (0.6, 19.4, 'R', 7.6, 2.2, 34, True), (-2.6, 37.0, 'R', 6.8, 2.6, 45, True),
         (-12.4, 35.2, 'R', 4.2, 2.4, -45, True), (12.5, 35.0, 'R', 4.2, 2.4, 45, True)]
PLANTERS = _BACK + [(x, -z, k, ln, w, -r, t) for (x, z, k, ln, w, r, t) in _BACK if abs(x) > 5 or z < 15]
DISCS = [(-5.9, 20.5), (5.9, 20.5), (-11.7, 9.3), (12.0, 8.4), (-11.7, -9.3), (12.0, -8.4)]
LAMPS = [(9.0, 13.0), (-1.5, 36.4), (-6.4, -9.4), (-10.6, -25.0), (10.6, -25.0)]


def planter_seat(mb, x, z, kind, ln, w, rot, tree):
    """Raised planter (brown-red tile walls, soil, shrubs, a young tree) with a stone seat ledge along one side."""
    fr = Fr((LX + x, 0, LZ + z)).sub(rot=math.radians(rot))
    arms = [(-ln / 2, ln / 2, -w / 2, w / 2)] if kind == 'R' else [(0.0, ln, 0.0, w), (0.0, w, 0.0, ln)]
    if kind == 'L':   # chevron: corner towards the library, arms spreading diagonally away from it
        fr = Fr((LX + x, 0, LZ + z)).sub(rot=math.radians(135 if z > 0 else -45))
    for (a, b, c, d) in arms:
        box(mb, fr, a, b, 0, 0.62, c, d, {'py': MAT['soil'], '*': MAT['ptile']})
        box(mb, fr, a - 0.04, b + 0.04, 0.62, 0.68, c - 0.04, d + 0.04, MAT['bench'], skip=('ny',))
        box(mb, fr, a + 0.12, b - 0.12, 0.66, 0.7, c + 0.12, d - 0.12, MAT['soil'])
    a, b, c, d = arms[0]
    box(mb, fr, a, b, 0, 0.42, d, d + 0.45, {'py': MAT['bench'], '*': MAT['bench']})     # seat ledge
    for (a, b, c, d) in arms:
        nx = max(1, int((b - a) / 0.9))
        for k in range(nx):
            t = a + (k + 0.5) * (b - a) / nx
            c0 = fr.p(t, 0.7, (c + d) / 2)
            SHRUBS.append(dict(p=[c0[0], c0[1], c0[2]], s=0.45 + 0.15 * rnd.random(), bouga=rnd.random() < 0.25))
    if tree:
        a, b, c, d = arms[-1]
        c0 = fr.p((a + b) / 2, 0.7, (c + d) / 2)
        YOUNG_TREES.append((c0[0], c0[2], 0.9 + 0.3 * rnd.random()))


YOUNG_TREES = []


def build_playground(mb):
    """Playground (photo 14, 1990s): sandpit with a yellow timber rail, tyre climber, two arched monkey bars, a double
    swing. By 2008-10 (photo 1) the same frames stand on black rubber safety tiles inside a timber edging, sandpit included."""
    pg = Fr((LX, 0, LZ + 28.5)).sub(rot=math.pi / 4)
    f0 = Fr()
    for k in range(4):   # timber edging round the safety surface, 12 m side
        e = pg.sub(rot=k * math.pi / 2)
        box(mb, e, -6.0, 6.0, 0.0, 0.1, 5.8, 6.2, MAT['timber'])
    box(mb, pg, -5.8, 5.8, 0.04, 0.06, -5.8, 5.8, {'py': MAT['rubbertile']})   # black rubber tiles (photo 1)
    sp = pg.sub(-0.2, 0, 0)   # former sandpit 4.4 m, tiled over too
    box(mb, sp, -2.2, 2.2, 0, 0.07, -2.2, 2.2, {'py': MAT['rubbertile'], '*': MAT['timber']})
    for k in range(4):
        e = sp.sub(rot=k * math.pi / 2)
        box(mb, e, -2.3, 2.3, 0, 0.4, 2.2, 2.4, MAT['timber'])
        box(mb, e, -2.3, 2.3, 0.95, 1.05, 2.25, 2.35, MAT['myellow'])
        box(mb, e, 2.2, 2.4, 0, 1.05, 2.2, 2.4, MAT['myellow'])
    sw = Fr((LX + 5.0, 0, LZ + 29.3)).sub(rot=math.radians(-17))   # double swing
    for ex in (-2.3, 2.3):
        for ez in (-0.8, 0.8):
            beam(mb, sw.p(ex, 0, ez), sw.p(ex, 2.4, 0), 0.08, MAT['pblue'])
    beam(mb, sw.p(-2.4, 2.4, 0), sw.p(2.4, 2.4, 0), 0.1, MAT['myellow'])
    for ex in (-1.0, 1.0):
        box(mb, sw, ex - 0.25, ex + 0.25, 0.45, 0.5, -0.12, 0.12, MAT['steel'])
        for kx in (-0.22, 0.22):
            beam(mb, sw.p(ex + kx, 0.5, 0), sw.p(ex + kx, 2.38, 0), 0.02, MAT['pipe'])
    ty = Fr((LX - 4.0, 0, LZ + 27.6))   # tyre climber
    for k in range(4):
        cylv(mb, ty, 0, 0, 0.1 + k * 0.38, 0.38 + k * 0.38, 0.45, 14, MAT['rubber'])
    for a in range(4):
        ang = a * math.pi / 2
        cylv(mb, ty, 0.5 * math.cos(ang), 0.5 * math.sin(ang), 0, 1.75, 0.03, 6, MAT['pblue'])
    for (xa, za, xb, zb) in ((-5.9, 22.2, -0.5, 23.2), (0.6, 30.1, 3.6, 32.9)):   # arched monkey bars
        a3, b3 = (LX + xa, LZ + za), (LX + xb, LZ + zb)
        L = math.hypot(b3[0] - a3[0], b3[1] - a3[1])
        mfr = Fr((a3[0], 0, a3[1]), ((b3[0] - a3[0]) / L, 0, (b3[1] - a3[1]) / L), (-(b3[1] - a3[1]) / L, 0, (b3[0] - a3[0]) / L))
        pts = [(L * t, 0.4 + 1.7 * math.sin(math.pi * t)) for t in [i / 10 for i in range(11)]]
        for side in (-0.35, 0.35):
            for (u0, v0), (u1, v1) in zip(pts, pts[1:]):
                beam(mb, mfr.p(u0, v0, side), mfr.p(u1, v1, side), 0.04, MAT['steel'])
            beam(mb, mfr.p(0, 0, side), mfr.p(0, 0.4, side), 0.04, MAT['steel'])
            beam(mb, mfr.p(L, 0, side), mfr.p(L, 0.4, side), 0.04, MAT['steel'])
        for (u0, v0) in pts[1:-1]:
            cylx(mb, Fr(mfr.p(0, 0, 0), mfr.ez, (-mfr.ex[0], 0, -mfr.ex[2])), -0.35, 0.35, v0, -u0, 0.02, 5, MAT['steel'])

# ------------------------------------------------------------------ ground, streets, sports hall (simplified), context
def build_ground(mb):
    f0 = Fr()

    def flat(x0, z0, x1, z1, y, m):
        mb.poly([f0.p(x0, y, z1), f0.p(x1, y, z1), f0.p(x1, y, z0), f0.p(x0, y, z0)], m)

    flat(-250, -250, 350, 400, 0.0, MAT['ground0'])
    flat(EX0, EZ0, EX1, EZ1, 0.04, MAT['paving'])
    flat(-250, -21, 350, -3, 0.02, MAT['asphalt'])
    box(mb, f0, -250, 350, 0, 0.25, -12.8, -11.2, MAT['curb'])
    box(mb, f0, -250, 350, 0, 0.15, -3, EZ0, {'py': MAT['sidewalk'], '*': MAT['curb']})
    B = BACK
    flat(-10, -3, 0, B['kerb'], 0.021, MAT['asphalt'])
    box(mb, f0, 0, HALL['x0'], 0, 0.15, EZ0, B['strip'], {'py': MAT['sidewalk'], '*': MAT['curb']})
    flat(HALL['x0'], HALL['z1'], EX0, B['strip'], 0.03, MAT['grass'])
    flat(HALL['x1'], EZ0, EX0, HALL['z1'], 0.035, MAT['sidewalk'])
    flat(0, EZ0, HALL['x1'], HALL['z0'], 0.035, MAT['sidewalk'])                # hall forecourt on the avenue
    box(mb, f0, EX0 - 1.2, EX0 - 0.6, 0.03, 1.05, EZ0 + 0.5, EZ0 + 1.1, MAT['rock'])
    flat(EX0, EZ1, EX1, B['strip'], 0.03, MAT['soil'])                     # sunken planted strip behind the blocks
    # the 利誠 side street (ground level) and the raised ground to its east, where the hillside blocks stood
    flat(EX1 + 1.5, EZ0, SIDE_X1, B['strip'] - 6.5, 0.021, MAT['asphalt'])
    box(mb, f0, EX1, EX1 + 1.5, 0, 0.15, EZ0, B['strip'] - 6.5, {'py': MAT['sidewalk'], '*': MAT['curb']})
    PZ0, PX1 = HILL['zf'] - D - 2.5, HILL['x1'] + 2.5                         # paved round the hillside blocks
    box(mb, f0, SIDE_X1, SLOPE['x1'], 0, B['H'], SLOPE['z0'], PZ0, {'py': MAT['grass'], '*': MAT['rock']}, skip=('pz',))
    box(mb, f0, SIDE_X1, PX1, 0, B['H'], PZ0, B['strip'], {'py': MAT['sidewalk'], '*': MAT['rock']}, skip=('nz', 'px'))
    box(mb, f0, PX1, SLOPE['x1'], 0, B['H'], PZ0, B['strip'], {'py': MAT['grass'], '*': MAT['rock']}, skip=('nz', 'nx'))
    za, zb, xa_, xb_ = HILL['zf'] + 0.45, B['strip'] - 0.05, SIDE_X1 + 0.05, PX1   # green grid lines of the forecourt
    for sgn in (1, -1):
        for k in range(-80, 80):
            c = k * 5.0   # line x - sgn * z = c, clipped to the rectangle
            ts = sorted(t for t in (za, zb, (xa_ - c) * sgn, (xb_ - c) * sgn) if za - 1e-6 <= t <= zb + 1e-6
                        and xa_ - 1e-6 <= c + sgn * t <= xb_ + 1e-6)
            if len(ts) < 2 or ts[-1] - ts[0] < 0.4:
                continue
            a, b = (c + sgn * ts[0], ts[0]), (c + sgn * ts[-1], ts[-1])
            dx, dz = b[0] - a[0], b[1] - a[1]
            ln = math.hypot(dx, dz)
            nx, nz = -dz / ln * 0.2, dx / ln * 0.2
            q = [(a[0] - nx, a[1] - nz), (a[0] + nx, a[1] + nz), (b[0] + nx, b[1] + nz), (b[0] - nx, b[1] - nz)]
            if sum(q[i][0] * q[(i + 1) % 4][1] - q[(i + 1) % 4][0] * q[i][1] for i in range(4)) > 0:
                q.reverse()   # upward faces run clockwise in (x, z)
            mb.poly([f0.p(x, B['H'] + 0.006, z) for x, z in q], MAT['paintgreen'])
    px0, px1, pz0, pz1, ph = HILL['x1'] - 2 * HILL_BW - JW - 0.3, HILL['x1'] - HILL_BW - 0.3, B['strip'] - 2.0, B['strip'] - 0.4, 0.75
    box(mb, f0, px0, px1, B['H'], B['H'] + ph, pz0, pz1, {'py': MAT['soil'], 'ny': None, '*': MAT['rock']})   # planter (MH068)
    xq = px0 + 0.1
    while xq < px1:
        cylv(mb, f0, xq, pz1 - 0.08, B['H'] + ph, B['H'] + ph + 0.8, 0.025, 6, MAT['kerbrail'])
        xq += 1.5
    for hh in (0.4, 0.78):
        cylx(mb, f0, px0 + 0.1, px1 - 0.1, B['H'] + ph + hh, pz1 - 0.08, 0.025, 6, MAT['kerbrail'])
    xq = px0 + 0.8
    while xq < px1 - 0.5:
        SHRUBS.append(dict(p=[xq, B['H'] + ph, (pz0 + pz1) / 2], s=0.55, bouga=False))
        xq += 1.7
    for k in range(6):   # short dark bollards along the forecourt's street edge (MH006)
        cylv(mb, f0, HILL['x0'] + 3.0 + 2.4 * k, B['strip'] - 0.45, B['H'], B['H'] + 0.75, 0.07, 10, MAT['steel'], r1=0.055)
    hx, hz = HILL['x0'] + 18.5, B['strip'] - 0.5   # fire hydrant (MH006): red barrel, domed cap, two outlets
    cylv(mb, f0, hx, hz, B['H'], B['H'] + 0.12, 0.17, 12, MAT['hydrant'])
    cylv(mb, f0, hx, hz, B['H'] + 0.12, B['H'] + 0.62, 0.12, 12, MAT['hydrant'])
    cylv(mb, f0, hx, hz, B['H'] + 0.62, B['H'] + 0.74, 0.14, 12, MAT['hydrant'], r1=0.06)
    cylx(mb, f0, hx - 0.22, hx + 0.22, B['H'] + 0.45, hz, 0.045, 8, MAT['hydrant'])
    XS = [-10.0, B['x_lo'], B['x_hi'], 260.0]

    def slope_top(x0, x1, z0, z1, dy, m):
        """Surface following the back street's rise, between x0 and x1."""
        xs = [x0] + [x for x in XS if x0 < x < x1] + [x1]
        for xa, xb in zip(xs, xs[1:]):
            mb.poly([f0.p(xa, back_h(xa) + dy, z1), f0.p(xb, back_h(xb) + dy, z1),
                     f0.p(xb, back_h(xb) + dy, z0), f0.p(xa, back_h(xa) + dy, z0)], m)

    def slope_face(x0, x1, z, lo, hi, m, facing):
        """Vertical face at z between y = lo(x) and hi(x); facing -1 (towards the estate) or +1."""
        xs = [x0] + [x for x in XS if x0 < x < x1] + [x1]
        for xa, xb in zip(xs, xs[1:]):
            q = [f0.p(xa, lo(xa), z), f0.p(xa, hi(xa), z), f0.p(xb, hi(xb), z), f0.p(xb, lo(xb), z)]
            mb.poly(q if facing < 0 else list(reversed(q)), m)
    WX0, WX1 = MKS['x1'] + 0.6, EX1                                             # retaining wall along the planted strip
    slope_top(WX0, WX1, B['strip'], B['wall'], 0.9, MAT['rock'])
    slope_face(WX0, WX1, B['strip'], lambda x: 0.0, lambda x: back_h(x) + 0.9, MAT['rock'], -1)
    slope_face(WX0, WX1, B['wall'], lambda x: back_h(x) + 0.15, lambda x: back_h(x) + 0.9, MAT['rock'], 1)
    for xe, sgn in ((WX0, -1), (WX1, 1)):
        hh = back_h(xe) + 0.9
        q = [f0.p(xe, 0, B['strip']), f0.p(xe, 0, B['wall']), f0.p(xe, hh, B['wall']), f0.p(xe, hh, B['strip'])]
        mb.poly(q if sgn > 0 else list(reversed(q)), MAT['rock'])
    for xa, xb in ((-10.0, WX0), (WX1, 260.0)):                               # elsewhere the pavement reaches the strip line
        slope_top(xa, xb, B['strip'], B['wall'], 0.15, MAT['sidewalk'])
        slope_face(xa, xb, B['strip'], lambda x: 0.0, lambda x: back_h(x) + 0.15, MAT['curb'], -1)
    slope_top(-10.0, 260.0, B['wall'], B['kerb'], 0.15, MAT['sidewalk'])
    slope_face(-10.0, 260.0, B['kerb'], lambda x: back_h(x) + 0.02, lambda x: back_h(x) + 0.15, MAT['curb'], 1)
    slope_top(-10.0, 260.0, B['kerb'], B['far'], 0.02, MAT['asphalt'])
    slope_face(-10.0, 260.0, B['far'], lambda x: back_h(x) + 0.02, lambda x: back_h(x) + 0.15, MAT['curb'], -1)
    slope_top(-10.0, 260.0, B['far'], B['far_kerb'], 0.15, MAT['sidewalk'])
    slope_top(-10.0, 260.0, B['far_kerb'], B['end'], 0.15, MAT['grass'])
    slope_face(-10.0, 260.0, B['end'], lambda x: 0.0, lambda x: back_h(x) + 0.15, MAT['curb'], 1)
    zw = (B['strip'] + B['wall']) / 2
    xp = WX0 + 0.15                                                           # pipe railing on the wall
    while xp < WX1 - 0.1:
        y0 = back_h(xp) + 0.9
        cylv(mb, f0, xp, zw, y0, y0 + 0.95, 0.03, 8, MAT['creampipe'])
        xp += 2.0
    for yo in (0.5, 0.95):
        for xa, xb in ((WX0 + 0.15, B['x_lo']), (B['x_lo'], WX1 - 0.1)):
            beam(mb, (xa, back_h(xa) + 0.9 + yo, zw), (xb, back_h(xb) + 0.9 + yo, zw), 0.05, MAT['creampipe'])
    xh = WX0                                                                  # U-hoop barriers along the back kerb
    zr = B['kerb'] - 0.25
    while xh + 1.2 <= 200:
        for xq in (xh, xh + 1.2):
            cylv(mb, f0, xq, zr, back_h(xq) + 0.15, back_h(xq) + 1.0, 0.03, 8, MAT['kerbrail'])
        ym = back_h(xh + 0.6)
        cylx(mb, f0, xh, xh + 1.2, ym + 0.98, zr, 0.03, 8, MAT['kerbrail'])
        cylx(mb, f0, xh, xh + 1.2, ym + 0.55, zr, 0.025, 8, MAT['kerbrail'])
        xh += 1.65
    for xl in [EX0 + 14.0 + 30.0 * k for k in range(int((EX1 - EX0 - 10) / 30) + 1)]:   # street lamps, back pavement
        yb = back_h(xl) + 0.15
        zl = B['wall'] + 0.4
        cylv(mb, f0, xl, zl, yb, yb + 8.8, 0.1, 10, MAT['lamppole'], r1=0.065)
        beam(mb, (xl, yb + 8.7, zl), (xl, yb + 9.1, zl + 1.9), 0.07, MAT['lamppole'])
        box(mb, f0, xl - 0.17, xl + 0.17, yb + 9.0, yb + 9.18, zl + 1.5, zl + 2.3, MAT['lamppole'])
    # steps from the end of the 利誠 side street up to the high end of the back street (and the 望廈飲食 spot beyond)
    sx0, sx1 = EX1 + 0.6, EX1 + 4.1
    top = back_h((sx0 + sx1) / 2) + 0.15
    n = 19
    z0 = B['strip'] - 6.5
    for k in range(n):
        box(mb, f0, sx0, sx1, 0, top * (k + 1) / n, z0 + k * 0.3, z0 + (k + 1) * 0.3,
            {'py': MAT['sidewalk'], 'nz': MAT['curb'], 'pz': MAT['curb'], '*': MAT['rock']})   # granite sides (MH006)
    box(mb, f0, sx0, sx1, 0, top, z0 + n * 0.3, B['wall'], {'py': MAT['sidewalk'], '*': MAT['rock']})
    box(mb, f0, sx1, SIDE_X1, 0, top, z0, B['wall'], {'py': MAT['sidewalk'], '*': MAT['rock']})
    beam(mb, (sx0 + 0.05, 0.9, z0), (sx0 + 0.05, top + 0.9, z0 + n * 0.3), 0.05, MAT['creampipe'])   # handrail, open side
    zq = SLOPE['z0'] + 0.3                                                    # railing along the top of the 3 m wall
    while zq < z0 - 0.1:
        cylv(mb, f0, SIDE_X1 + 0.15, zq, B['H'], B['H'] + 1.0, 0.03, 8, MAT['creampipe'])
        zq += 2.0
    for yo in (0.5, 1.0):
        cylz_y = B['H'] + yo
        beam(mb, (SIDE_X1 + 0.15, cylz_y, SLOPE['z0'] + 0.3), (SIDE_X1 + 0.15, cylz_y, z0), 0.05, MAT['creampipe'])
    for k in range(0, n + 1, 4):
        yk = top * k / n
        cylv(mb, f0, sx0 + 0.05, z0 + k * 0.3, yk, yk + 0.9, 0.03, 8, MAT['creampipe'])
    build_makau_stone(mb, f0)
    # top of the steps (MH033 = photo 23): steel gate portal with a sheet canopy, leaves standing open, granite pier with a plaque
    zg = B['wall'] - 0.3
    for xg in (sx0 + 0.05, sx1 - 0.05):
        box(mb, f0, xg - 0.06, xg + 0.06, top, top + 2.7, zg - 0.06, zg + 0.06, MAT['steel'])
    box(mb, f0, sx0, sx1, top + 2.55, top + 2.7, zg - 0.06, zg + 0.06, MAT['steel'])
    box(mb, f0, sx0 - 0.1, sx1 + 0.1, top + 2.7, top + 2.76, zg - 0.5, zg + 0.6, MAT['awning'])
    for xh, sgn in ((sx0 + 0.11, 1), (sx1 - 0.11, -1)):   # two leaves swung out towards the street
        lf = Fr((xh, top, zg), (sgn * math.cos(math.radians(65)), 0, math.sin(math.radians(65))),
                (-math.sin(math.radians(65)), 0, sgn * math.cos(math.radians(65))))
        wl = (sx1 - sx0) / 2 - 0.15
        for yb in (0.08, 1.15, 2.3):
            box(mb, lf, 0, wl, yb, yb + 0.05, -0.02, 0.02, MAT['steel'])
        k = 0.0
        while k <= wl + 1e-6:
            box(mb, lf, k - 0.012, k + 0.012, 0.08, 2.35, -0.012, 0.012, MAT['steel'])
            k += 0.12
    box(mb, f0, sx0 - 1.3, sx0 - 0.05, 0, top + 3.0, zg - 0.45, zg + 0.45, MAT['rock'])          # granite pier
    box(mb, f0, sx0 - 1.05, sx0 - 0.3, top + 1.3, top + 2.3, zg + 0.45, zg + 0.49, MAT['steel'])   # dark plaque
    x = -245.0
    while x < 345:
        for z in (-17, -7):
            box(mb, f0, x, x + 4.2, 0.02, 0.035, z - 0.08, z + 0.08, MAT['paint'])
        x += 9
    for k in range(9):
        for z in (-5.6, -18.4):
            xx = PASS_X + k * 1.1 - 4.4
            box(mb, f0, xx - 0.27, xx + 0.27, 0.02, 0.036, z - 2.3, z + 2.3, MAT['paint'])
    # dark-green U-hoop barriers along the kerb (gaps at the zebra crossing, junction and bus stop)
    zr = -2.7
    for xa, xb in ((-40, -12), (2, PASS_X - 5.4), (PASS_X + 13.0, 190)):
        xh = xa
        while xh + 1.2 <= xb:
            for xp in (xh, xh + 1.2):
                cylv(mb, f0, xp, zr, 0.15, 1.0, 0.03, 8, MAT['kerbrail'])
            cylx(mb, f0, xh, xh + 1.2, 0.98, zr, 0.03, 8, MAT['kerbrail'])
            cylx(mb, f0, xh, xh + 1.2, 0.55, zr, 0.025, 8, MAT['kerbrail'])
            xh += 1.65
    # single-arm grey street lamps on both pavements
    for xl, zl, sgn in [(x, -2.3, -1) for x in range(-36, 192, 30)] + [(x + 15, -21.7, 1) for x in range(-36, 192, 30)]:
        cylv(mb, f0, xl, zl, 0.15, 9.0, 0.1, 10, MAT['lamppole'], r1=0.065)
        beam(mb, (xl, 8.9, zl), (xl, 9.3, zl + sgn * 1.9), 0.07, MAT['lamppole'])
        box(mb, f0, xl - 0.17, xl + 0.17, 9.2, 9.38, zl + sgn * 1.8 - 0.38, zl + sgn * 1.8 + 0.38, MAT['lamppole'])
    for tx, tz, _ in FRONT_TREES:   # raised concrete tree planters on the avenue pavement (photo 22)
        box(mb, f0, tx - 0.85, tx + 0.85, 0.15, 0.62, tz - 0.55, tz + 0.55, {'py': MAT['soil'], 'ny': None, '*': MAT['curb']})
    # bus shelter (photos 21, 22): steel frame, glass back, flat roof, bench
    bs = Fr((min(SHOES_X + ROWS[0]['bw'] + 0.7, PASS_X - 8.3), 0.15, -1.6))   # in front of the bay south-east of 鞋宜樂, clear of the signal pole
    for ex in (-1.9, 1.9):
        for ez in (-0.65, 0.65):
            box(mb, bs, ex - 0.05, ex + 0.05, 0, 2.45, ez - 0.05, ez + 0.05, MAT['shelter'])
    box(mb, bs, -2.1, 2.1, 2.45, 2.6, -0.95, 0.85, MAT['shelter'])
    mb.poly([bs.p(-1.85, 0.25, 0.66), bs.p(1.85, 0.25, 0.66), bs.p(1.85, 2.4, 0.66), bs.p(-1.85, 2.4, 0.66)], MAT['ctxglass'])
    mb.poly(list(reversed([bs.p(-1.85, 0.25, 0.66), bs.p(1.85, 0.25, 0.66), bs.p(1.85, 2.4, 0.66), bs.p(-1.85, 2.4, 0.66)])), MAT['ctxglass'])
    box(mb, bs, -1.6, 1.6, 0.45, 0.5, 0.25, 0.6, MAT['shelter'])
    # traffic signals at the crossing
    for (xs, zs, face) in ((PASS_X - 5.9, -2.45, 1), (PASS_X + 5.9, -21.55, -1), (PASS_X - 1.2, -12.0, -1), (PASS_X + 1.2, -12.0, 1)):
        cylv(mb, f0, xs, zs, 0.1, 4.3, 0.07, 8, MAT['tlbox'])
        hx = xs + face * 0.18
        box(mb, f0, hx - 0.12, hx + 0.12, 3.2, 4.15, zs - 0.16, zs + 0.16, MAT['tlbox'])
        for k, m in enumerate((MAT['tlred'], MAT['tlbox'], MAT['tlgreen'])):
            yy = 3.95 - k * 0.3
            box(mb, f0, hx + face * 0.12 - 0.01, hx + face * 0.12 + 0.01, yy - 0.1, yy + 0.1, zs - 0.1, zs + 0.1, m)
        box(mb, f0, xs - 0.13, xs + 0.13, 2.2, 2.8, zs - 0.12, zs + 0.12, MAT['tlbox'])   # pedestrian head


def hall_band(mb, fr, xa, xb, y, depth, thick, m):
    """Bull-nosed concrete band along local x, projecting 'depth' from the wall plane z = 0."""
    r = thick / 2
    prof = [(0, y), (depth - r, y)] + [(depth - r + math.cos(t) * r, y + r + math.sin(t) * r)
                                       for t in [-math.pi / 2 + math.pi * k / 8 for k in range(1, 8)]] + [(depth - r, y + thick), (0, y + thick)]
    prism_x(mb, fr, prof, xa, xb, m)


def hall_facade(mb, fr, xa, xb, lights):
    """One arcaded face of the hall in a frame whose +z points out of the wall (wall plane z = 0)."""
    L = xb - xa
    n = int((L - 2.0) / 4.4)
    x0 = xa + (L - n * 4.4) / 2
    for i in range(n):                                   # tall arches, some glazed doors
        xc = x0 + (i + 0.5) * 4.4
        prism_z(mb, Fr(fr.p(xc, 0, 0), fr.ex, fr.ez), [(-1.7, 0.6), (1.7, 0.6), (1.7, 4.8)] + arc(0, 4.8, 1.7, 0, math.pi, 12)[1:-1] + [(-1.7, 4.8)],
                0.0, 0.03, MAT['ctxglass'] if i % 3 == 1 else MAT['void'])
    hall_band(mb, fr, xa, xb, 6.9, 2.4, 1.4, MAT['hallg'])                       # cantilever corridor
    railing_run(mb, fr, xa + 0.3, xb - 0.3, 8.3, 2.15, MAT['steel'])
    for i in range(n):                                   # recessed upper windows
        xc = x0 + (i + 0.5) * 4.4
        box(mb, fr, xc - 1.4, xc + 1.4, 8.7, 10.1, 0.0, 0.03, MAT['ctxglass'])
    hall_band(mb, fr, xa - 1.5, xb + 1.5, 10.6, 3.3, 0.9, MAT['hallg'])          # overhanging roof slab
    for i in range(n + 1):
        xb_ = x0 + i * 4.4
        prism_x(mb, fr, [(0, 9.0), (2.7, 10.62), (0, 10.62)], xb_ - 0.15, xb_ + 0.15, MAT['hallg'])
    box(mb, fr, xa, xb, 0, 0.3, 0, 1.6, {'py': MAT['hallw'], '*': MAT['hallred']})   # stepped base, red/white tiles
    box(mb, fr, xa, xb, 0.3, 0.6, 0, 0.8, {'py': MAT['hallw'], '*': MAT['hallred']})
    if lights:                                           # floodlight posts in front
        for i in range(0, n + 1, 2):
            xp = x0 + i * 4.4
            cylv(mb, fr, xp, 3.4, 0.15, 3.2, 0.07, 8, MAT['lamppole'])
            box(mb, fr, xp - 0.6, xp + 0.6, 3.15, 3.25, 3.35, 3.45, MAT['lamppole'])
            for k in (-0.45, 0.45):
                box(mb, fr, xp + k - 0.2, xp + k + 0.2, 3.25, 3.6, 3.25, 3.55, MAT['tlbox'])


def build_hall(mb):
    """Old Mong-Ha Sports Pavilion (1983-2011), from the 2026-10-22 photo package. It runs the whole length of 俾利喇街
    beside the estate: a flat white end with a tall arched window faces the avenue (MH008, MH041); both long sides have the
    white arcade, the dark bull-nosed cantilever gallery and the deep roof slab (MH029, MH040; lane side in photo 2); the
    central entrance on 俾利喇街 has three glazed arches under a raised gable with the name board and flagpoles (MH039,
    MH064); the back end at the 馬交石斜坡 junction is the granite block with the curved corner, ribbon window, recessed glazed
    ground floor, flat granite pier and two black flues (MH027, MH042). Halls A/B were 32 x 18.7 and 33.1 x 20.25 m, 9 m
    high (2009 季刊), so the shell is 38 m wide and ~12 m to the roof slab."""
    h = HALL
    f0 = Fr()
    X0, X1, Z0, ZR, Z1, H = h['x0'], h['x1'], h['z0'], h['zr'], h['z1'], h['h']
    box(mb, f0, X0, X1, 0, H, Z0, ZR, {'py': MAT['hallg'], '*': MAT['hallw']})                # main block (two halls)
    box(mb, f0, X0 + 3, X1 - 3, H, H + 1.6, Z0 + 4, ZR - 4, {'py': MAT['hallg'], '*': MAT['hallw']})   # raised hall roofs
    street = Fr((X0, 0, 0), (0, 0, 1), (-1, 0, 0))      # 俾利喇街 face: local x = world z, +z = -x (right-handed frames)
    lane = Fr((X1, 0, 0), (0, 0, -1), (1, 0, 0))       # lane face: local x = -world z, +z = +x
    ave = Fr((0, 0, Z0), (-1, 0, 0), (0, 0, -1))        # avenue end: +z = -z
    zm = (Z0 + ZR) / 2
    EW = 7.0                                            # half width of the entrance bay
    hall_facade(mb, street, Z0 + 1.0, zm - EW, True)
    hall_facade(mb, street, zm + EW, ZR - 0.5, True)
    hall_facade(mb, lane, -(ZR - 0.5), -(Z0 + 1.0), False)
    # entrance bay: raised gable with a curved top, three glazed arches, glass canopy, name board, flagpoles
    ent = Fr((X0, 0, zm), (0, 0, 1), (-1, 0, 0))
    prof = [(-EW, 0), (EW, 0), (EW, H + 0.4)] + [(EW * math.cos(math.pi * k / 16), H + 0.4 + 2.4 * math.sin(math.pi * k / 16))
                                                 for k in range(1, 16)] + [(-EW, H + 0.4)]
    prism_z(mb, ent, prof, -0.2, 0.5, MAT['hallw'])
    for k in (-1, 0, 1):
        xc = k * 4.3
        prism_z(mb, Fr(ent.p(xc, 0, 0), ent.ex, ent.ez), [(-1.8, 0.4), (1.8, 0.4), (1.8, 6.2)] + arc(0, 6.2, 1.8, 0, math.pi, 12)[1:-1]
                + [(-1.8, 6.2)], 0.5, 0.54, MAT['ctxglass'])
        box(mb, ent, xc - 1.8, xc + 1.8, 0.4, 3.0, 0.5, 0.56, MAT['frame'])
    box(mb, ent, -EW + 0.4, EW - 0.4, 3.2, 3.3, 0.5, 3.2, MAT['ctxglass'])                    # glass canopy
    for k in (-1, 1):
        box(mb, ent, k * (EW - 0.6) - 0.06, k * (EW - 0.6) + 0.06, 0, 3.2, 3.0, 3.12, MAT['steel'])
    mb.poly([ent.p(-3.6, 7.9, 0.505), ent.p(3.6, 7.9, 0.505), ent.p(3.6, 9.5, 0.505), ent.p(-3.6, 9.5, 0.505)],
            MAT['signatlas'], uvs=sign_uv(4))   # name lettered on the gable: 望廈體育館 / Pavilhão de Mong-Há (MH064)
    for k in range(5):
        cylv(mb, ent, -3.0 + k * 1.5, 0.2, H + 1.2, H + 6.0, 0.035, 6, MAT['lamppole'])         # flagpoles
    for k in range(4):                                                                         # red/white steps
        box(mb, ent, -EW, EW, 0, 0.15 * (k + 1), 0.5 + (3 - k) * 0.35, 0.5 + (4 - k) * 0.35, {'py': MAT['hallw'], '*': MAT['hallred']})
    # avenue end: flat white wall, tall arched window, the cantilever gallery and roof slab wrap round from both sides
    prism_z(mb, Fr(ave.p(-(X0 + X1) / 2, 0, 0), ave.ex, ave.ez), [(-1.6, 1.0), (1.6, 1.0), (1.6, 6.6)] + arc(0, 6.6, 1.6, 0, math.pi, 12)[1:-1]
            + [(-1.6, 6.6)], 0.0, 0.04, MAT['ctxglass'])
    for xa, xb in ((-X1, -X1 + 7.0), (-X0 - 7.0, -X0)):
        hall_band(mb, ave, xa, xb, 6.9, 2.4, 1.4, MAT['hallg'])
        railing_run(mb, ave, xa + 0.3, xb - 0.3, 8.3, 2.15, MAT['steel'])
    hall_band(mb, ave, -X1 - 1.5, -X0 + 1.5, 10.6, 3.3, 0.9, MAT['hallg'])
    bx0, bx1, by0, by1 = -40.5, -31.1, 1.9, 6.6   # 2010 sports-for-all billboard on a steel frame (MH008; MH041 shows a 2011 one)
    box(mb, ave, bx0 - 0.15, bx1 + 0.15, by0 - 0.15, by1 + 0.15, 0.0, 0.25, MAT['steel'])
    mb.poly([ave.p(bx0, by0, 0.27), ave.p(bx1, by0, 0.27), ave.p(bx1, by1, 0.27), ave.p(bx0, by1, 0.27)], MAT['billboard'],
            uvs=[(0.002, 0.002), (0.998, 0.002), (0.998, 0.998), (0.002, 0.998)])
    for k in range(6):                                                                         # steel fire stair on the end
        box(mb, ave, -X0 - 9.0 + k * 0.8, -X0 - 8.2 + k * 0.8, 0.9 + k * 1.0, 1.0 + k * 1.0, 0.1, 1.2, MAT['steel'])
    # back end: granite block with a curved corner on the 俾利喇街 junction
    G0 = ZR
    R0 = 12.0
    cx, cz = X0 + R0, Z1 - R0
    box(mb, f0, X0 + R0, X1, 0, 14.5, G0, Z1, {'py': MAT['hallg'], '*': MAT['stone']})
    box(mb, f0, X0, X0 + R0, 0, 14.5, G0, cz, {'py': MAT['hallg'], '*': MAT['stone']})
    ring = [(math.cos(t), math.sin(t)) for t in [math.pi * (0.5 + 0.5 * k / 12) for k in range(13)]]   # +z .. -x quarter
    for (c0, s0), (c1, s1) in zip(ring, ring[1:]):
        a = (cx + c0 * R0, cz + s0 * R0)
        b = (cx + c1 * R0, cz + s1 * R0)
        mb.poly([(a[0], 0, a[1]), (a[0], 14.5, a[1]), (b[0], 14.5, b[1]), (b[0], 0, b[1])], MAT['stone'])    # curved wall
        mb.poly([(cx, 14.5, cz), (b[0], 14.5, b[1]), (a[0], 14.5, a[1])], MAT['hallg'])                        # roof wedge
        for y0, y1, rr, m in ((9.2, 10.5, R0 + 0.03, MAT['ctxglass']), (0.0, 4.4, R0 + 0.03, MAT['ctxglass'])):
            mb.poly([(cx + c0 * rr, y0, cz + s0 * rr), (cx + c0 * rr, y1, cz + s0 * rr),
                     (cx + c1 * rr, y1, cz + s1 * rr), (cx + c1 * rr, y0, cz + s1 * rr)], m)
        for y0, y1, r1 in ((4.4, 5.9, R0 + 2.0), (12.6, 13.2, R0 + 0.6)):     # curved canopy over the glazing, upper band
            o0, o1 = (cx + c0 * r1, cz + s0 * r1), (cx + c1 * r1, cz + s1 * r1)
            mb.poly([(o0[0], y0, o0[1]), (o0[0], y1, o0[1]), (o1[0], y1, o1[1]), (o1[0], y0, o1[1])], MAT['stone'])
            mb.poly([(a[0], y0, a[1]), (b[0], y0, b[1]), (o1[0], y0, o1[1]), (o0[0], y0, o0[1])][::-1], MAT['stone'])
            mb.poly([(a[0], y1, a[1]), (b[0], y1, b[1]), (o1[0], y1, o1[1]), (o0[0], y1, o0[1])], MAT['stone'])
    box(mb, f0, X0 + R0, X1, 9.2, 10.5, Z1, Z1 + 0.03, MAT['ctxglass'])                       # ribbon window, back face
    box(mb, f0, X0 + R0, X1 - 3.0, 0.0, 4.4, Z1, Z1 + 0.03, MAT['ctxglass'])
    box(mb, f0, X0 + R0, X1, 4.4, 5.9, Z1, Z1 + 2.0, MAT['stone'])
    box(mb, f0, X0 - 1.0, X0 + 0.6, 0, 13.2, G0 - 0.8, G0 + 0.8, MAT['stone'])                 # flat granite pier at the joint
    box(mb, f0, X0 - 0.6, X0 + 0.02, 5.6, 8.6, G0 + 1.0, cz, MAT['ctxglass'])                  # upper window, street side
    for (fx, fz) in ((X1 - 4.0, Z1 - 3.0), (X1 - 6.2, Z1 - 2.2)):                              # black flues with masts
        cylv(mb, Fr((fx, 0, fz)), 0, 0, 14.5, 19.0, 0.45, 16, MAT['steel'])
        cylv(mb, Fr((fx, 0, fz)), 0, 0, 19.0, 24.0, 0.05, 6, MAT['lamppole'])
    for k in range(5):                                                                         # floodlights on the parapet
        t = math.pi * (0.55 + 0.4 * k / 4)
        lx, lz = cx + math.cos(t) * (R0 + 0.4), cz + math.sin(t) * (R0 + 0.4)
        box(mb, f0, lx - 0.2, lx + 0.2, 14.5, 14.8, lz - 0.2, lz + 0.2, MAT['tlbox'])


def build_context(mb):
    f0 = Fr()
    for (x, w, d, hgt) in ((-70, 40, 30, 30), (-20, 36, 34, 42), (30, 44, 30, 36), (84, 40, 36, 48), (134, 36, 30, 32), (182, 40, 34, 40), (232, 44, 30, 28)):
        box(mb, f0, x, x + w, 0, hgt, -27 - d, -27, {'py': MAT['ctxroof'], '*': MAT[irng.choice(['ctx', 'ctxB', 'ctxC'])]})
    box(mb, f0, -37, -11, 0, 84, 1, 27, {'py': MAT['ctxroof'], '*': MAT['ctxB']})                       # 龍園
    box(mb, f0, SIDE_X1 + 2, EX1 + 49, 0, 14, 4, 67, {'py': MAT['ctxroof'], '*': MAT['ctx']})            # 望善樓 podium
    for (x, z, w, d) in ((EX1 + 26, 22, 34, 14), (EX1 + 25, 50, 30, 14)):
        box(mb, f0, x - w / 2, x + w / 2, 14, 100, z - d / 2, z + d / 2, {'py': MAT['ctxroof'], '*': MAT['ctxC']})
    for (x, z) in ((LX - 5, EZ1 + 43), (LX + 28, EZ1 + 41), (LX + 29, EZ1 + 76), (LX - 3, EZ1 + 78)):   # 新益花園
        cylv(mb, Fr((x, 0, z)), 0, 0, 0, 76, 12, 8, MAT['ctx'], phase=OCT)


# ------------------------------------------------------------------ build everything
ROW_MB = {r: MB(f'SM_Estate_{r.upper()}', C_EST) for r in ('front', 'back', 'nw', 'se')}
SCRATCH = MB('_scratch', C_MARK)   # never finished: geometry drawn here only keeps the random streams in step
slope = MB('SM_Estate_SlopeBlocks', C_SLOPE)
_irng_main = irng
for row in ROWS:
    mb = slope if row['id'].startswith('slope') else ROW_MB[row['id']]
    irng = random.Random(2011) if mb is slope else _irng_main   # hillside edits leave the estate's draws alone
    for it in row['items']:
        if it['t'] == 'b':
            build_block(mb, row, it)
        else:
            build_joint(mb, row, it)
hrow = ROWS[4]
fr = hrow['fr']
for xl, sgn in ((0.0, -1), (hrow['L'], 1)):   # white end walls with small windows (MH001), floor bands
    ez = fr.ex * sgn
    ex = Vector((0, 1, 0)).cross(ez)
    ef = Fr(fr.p(xl, 0, 0), tuple(ex), tuple(ez))
    for f in range(NF):
        y = GF + FH * f
        for xw in (-2.4, 2.4):
            window(slope, ef, xw - 0.45, xw + 0.45, y + 1.05, y + 2.15, 0.0, bars=irng.random() < 0.3)
        box(slope, ef, -HZ, HZ, y - 0.1, y + 0.08, 0.0, 0.05, MAT['white'])
jt = hrow['items'][1]
sf = side_frame(fr, -1)
xl = X((jt['x0'] + jt['x1']) / 2, -1)
box(slope, sf, xl - 1.95, xl - 1.0, GF, ROOF - 0.4, HZ + 0.75, HZ + 0.78, MAT['breeze'])         # breeze-block strip (MH068)
irng = _irng_main
for rid in ('front', 'back'):   # the end rows' outer ends face the side streets: windows and floor bands
    row = next(r for r in ROWS if r['id'] == rid)
    fr = row['fr']
    for xl, sgn in ((0.0, -1), (row['L'], 1)):
        ez = fr.ex * sgn
        ex = Vector((0, 1, 0)).cross(ez)
        ef = Fr(fr.p(xl, 0, 0), tuple(ex), tuple(ez))
        for f in range(NF):
            y = GF + FH * f
            ribbon = rid == 'front' and sgn == 1 and f == 0   # post office's first floor (MH022)
            nwin = max(3, int((2 * HZ - 2.4) / 2.6) + 1)
            for zl in [-(HZ - 1.6) + k * (2 * HZ - 3.2) / (nwin - 1) for k in range(nwin)]:
                xw = zl * (1 if ex.dot(fr.ez) > 0 else -1)
                window(SCRATCH if ribbon else ROW_MB[rid], ef, xw - 0.6, xw + 0.6, y + 0.95, y + 2.25, 0.0, bars=irng.random() < 0.3)
            if ribbon:   # red-framed band of windows over the post office, same span as its glazing below
                ga, gb = HZ - REC - 5.4, HZ - 0.5
                window(ROW_MB[rid], ef, ga, gb, y + 0.45, y + 2.2, 0.0, mull=False, gm=MAT['shopglass'], cells=4, fm=MAT['post'])
                for k in range(1, 6):
                    xm = ga + (gb - ga) * k / 6
                    box(ROW_MB[rid], ef, xm - 0.04, xm + 0.04, y + 0.45, y + 2.2, 0.0, 0.08, MAT['post'])
            ecol = row['items'][0]['cols'][0] if sgn < 0 else row['items'][-1]['cols'][-1]
            box(ROW_MB[rid], ef, -HZ, HZ, y - 0.1, y + 0.08, 0.0, 0.05, MAT['slab'][ecol] if rid == 'front' and f > 0 else MAT['white'])
        if rid == 'front':   # the avenue row's end walls: mosaic of the end bay from the second floor up, rendered white below (MH022)
            box(ROW_MB[rid], ef, -HZ, HZ, GF - 0.3, GF + FH - 0.1, 0.0, 0.015, MAT['white'], skip=('nz',))
        if rid == 'front' and sgn == 1:   # post office corner: local +x runs to the avenue corner
            ga, gb = HZ - REC - 5.4, HZ - REC
            box(ROW_MB[rid], ef, ga, gb, 0, 0.3, 0.0, 0.1, MAT['hallg'])
            mb_ = ROW_MB[rid]
            mb_.poly([ef.p(ga, 0.3, 0.05), ef.p(gb, 0.3, 0.05), ef.p(gb, GF - 1.05, 0.05), ef.p(ga, GF - 1.05, 0.05)],
                     MAT['shopglass'], uvs=atlas_uv(4, (gb - ga) / (GF - 1.4)))
            for xm in [ga + k * (gb - ga) / 4 for k in range(5)]:
                box(mb_, ef, xm - 0.05, xm + 0.05, 0.3, GF - 1.05, 0.02, 0.14, MAT['post'])
            box(mb_, ef, ga, gb, 1.95, 2.02, 0.02, 0.14, MAT['post'])
            box(mb_, ef, ga - 0.2, HZ + 0.02, GF - 1.15, GF - 0.25, -0.05, 0.35, MAT['post'])
            mb_.poly([ef.p(ga, GF - 1.12, 0.36), ef.p(HZ - 0.2, GF - 1.12, 0.36), ef.p(HZ - 0.2, GF - 0.28, 0.36), ef.p(ga, GF - 0.28, 0.36)],
                     MAT['postsign'], uvs=[(0.01, 0.02), (0.99, 0.02), (0.99, 0.98), (0.01, 0.98)])
gal = MB('SM_Galleries_Bridges', C_EST)
build_galleries(gal)
APO = 9.35 * math.cos(OCT) * LIB_S
build_bridge(gal, NWG, LIB_X - APO, BRIDGE_Z)
build_bridge(gal, LIB_X + APO, SEG, BRIDGE_Z)
for z in STAIRS:
    build_stair_u(gal, NWG, z, 1)
    build_stair_u(gal, SEG, z, -1)
lib = MB('SM_Library', C_LIB)
_n_shrubs = len(SHRUBS)
build_library(lib)
for sh in SHRUBS[_n_shrubs:]:
    sh['p'][0] = LIB_X + (sh['p'][0] - LIB_X) * LIB_S
    sh['p'][2] = LIB_Z + (sh['p'][2] - LIB_Z) * LIB_S
court = MB('SM_Courtyard', C_COURT)
build_courtyard(court)
grd = MB('SM_Ground_Streets', C_GROUND)
build_ground(grd)
hall = MB('SM_SportsHall_Simple', C_HALL)
build_hall(hall)
ctx = MB('SM_Context_Massing', C_CTX)
build_context(ctx)
stats = {}
for mb in (*ROW_MB.values(), slope, gal, lib, court, grd, hall, ctx):
    stats[mb.name] = mb.nfaces
    ob = mb.finish()
    if mb is lib:   # shrink the library in plan about its centre (Blender: x = site x, y = -site z)
        for v in ob.data.vertices:
            v.co.x = LIB_X + (v.co.x - LIB_X) * LIB_S
            v.co.y = -LIB_Z + (v.co.y + LIB_Z) * LIB_S
print('FACES', json.dumps(stats))

# ------------------------------------------------------------------ markers for Unreal (trees, cameras, sun) in site metres
# courtyard: young trees in the planters (1990s photo); the big canopy of the 2000s is left out on purpose
trees = list(YOUNG_TREES)
SPECIES = [('feathery', 'broad', 'bauhinia')[i % 3] for i in range(len(trees))]
trees += [(x, -1.2, 2.2) for x in (-30, -18, 12, 26, 40, 150, 176) if not EX0 - 2 < x < EX1 + 2]
trees += [(2.4, z, 2.0) for z in range(50, int(EZ1) + 8, 9)]
for _ in range(78):   # 26 garden trees used to stand where the full-length hall now is; keep the shared stream in step
    rnd.random()
for _ in range(66):   # the old back-garden trees used 66 draws; keep the shared stream where it was
    rnd.random()
_brng = random.Random(129)
trees += [(EX0 + 5 + 7.4 * k + _brng.uniform(-1.2, 1.2), EZ1 + 2.0 + _brng.uniform(-0.4, 0.4), 2.0 + _brng.random() * 0.7)
          for k in range(int((EX1 - EX0 - 8) / 7.4) + 1)]   # trees in the sunken strip behind the blocks, growing up past the wall (street photo)
views = {
    'courtyard_aerial': dict(p=(LX - 8, 125, CZ1 + 48), t=(LX, 0, CZ0 + 42), fov=46),
    'court_1990': dict(p=(LX + 1.4, 26.2, LZ + 53.1), t=(LX + 0.7, 11.1, LZ + 27.2), fov=56.7),   # solved camera of photo 14
    'avenue_2008': dict(p=(PASS_X - 8, 1.7, -24), t=(PASS_X - 8, 10, 8), fov=66),
    'library': dict(p=(LIB_X - 15, 1.7, LIB_Z - 10.2), t=(LIB_X, 5.5, LIB_Z), fov=62),   # MH034: the entrance under the NW bridge
    'gallery_deck': dict(p=(CX1 - 1.5, GF + 1.6, LZ + 40), t=(LX, GF + 2, LZ + 5), fov=62),
    'hall_corner': dict(p=(-14, 1.7, -16), t=(22, 7, 14), fov=62),
    'hill_food': dict(p=(HILL['x0'] - 1.5, 4.7, HILL['zf'] + 7.8), t=(HILL['x0'] + 10.5, 8.5, HILL['zf'] - 3.0), fov=64),   # MH006
}
trees += FRONT_TREES
trees += [(MKS['x1'] + 1.4, MKS['zf'] + 0.4, 1.8)]   # the young tree beside the 馬交石 (MH078)
SPECIES += ['broad'] * (len(trees) - len(SPECIES))
hill_trees = [(HILL['x1'] + 2.4, HILL['y0'], HILL['zf'] + 3.2, 2.6), (HILL['x1'] + 10.5, HILL['y0'], HILL['zf'] + 2.0, 2.3)]
markers = dict(site_to_blender='blender=(x,-z,y)', ac=AC_MARKS, trees=trees, hill_trees=hill_trees, species=SPECIES, shrubs=SHRUBS, views=views, library=(LIB_X, LIB_Z), cage=CAGE, passage_x=PASS_X,
               sun_dir_site=(0.357, 0.896, -0.266))
with open(os.path.join(EXPORT, 'markers.json'), 'w', encoding='utf-8') as fh:
    json.dump(markers, fh, ensure_ascii=False, indent=1)

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(EXPORT, 'MongHa_2010.blend'))


# ------------------------------------------------------------------ optional: preview renders (Cycles, GPU)
def look_at(cam, p, t):
    pv, tv = B(p), B(t)
    cam.location = pv
    cam.rotation_euler = (tv - pv).to_track_quat('-Z', 'Y').to_euler()


if '--render' in ARGS:
    prefs = bpy.context.preferences.addons['cycles'].preferences
    for dev in ('OPTIX', 'CUDA'):
        try:
            prefs.compute_device_type = dev
            prefs.get_devices()
            for d in prefs.devices:
                d.use = True
            break
        except Exception:
            continue
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'GPU'
    scene.cycles.samples = int(next((a.split('=')[1] for a in ARGS if a.startswith('--samples=')), 96))
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = 1600, 900
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.exposure = -0.9
    world = bpy.data.worlds.new('Sky')
    scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    bg = nt.nodes.get('Background')
    try:
        sky = nt.nodes.new('ShaderNodeTexSky')
        for t in ('MULTIPLE_SCATTERING', 'NISHITA', 'PREETHAM'):
            try:
                sky.sky_type = t
                break
            except Exception:
                continue
        sky.sun_elevation = math.radians(48)
        sky.sun_rotation = math.radians(150)
        nt.links.new(sky.outputs['Color'], bg.inputs['Color'])
        bg.inputs['Strength'].default_value = 0.25
    except Exception as e:
        print('sky fallback', e)
        bg.inputs['Color'].default_value = (0.55, 0.65, 0.78, 1)
    sd = Vector(B((0.55, 0.7, -0.45))).normalized()
    sun = bpy.data.lights.new('Sun', 'SUN')
    sun.energy = 3.6
    sun.angle = math.radians(0.6)
    so = bpy.data.objects.new('Sun', sun)
    so.rotation_euler = (-sd).to_track_quat('-Z', 'Y').to_euler()
    scene.collection.objects.link(so)
    camd = bpy.data.cameras.new('Cam')
    cam = bpy.data.objects.new('Cam', camd)
    scene.collection.objects.link(cam)
    scene.camera = cam
    which = next((a.split('=')[1] for a in ARGS if a.startswith('--views=')), 'courtyard_aerial,avenue_2008,library')
    for name in which.split(','):
        v = views[name]
        look_at(cam, v['p'], v['t'])
        camd.sensor_fit = 'VERTICAL'
        camd.angle = math.radians(v['fov'])
        scene.render.filepath = os.path.join(EXPORT, f'preview_{name}.png')
        bpy.ops.render.render(write_still=True)
        print('RENDERED', name)

if '--export' in ARGS:
    bpy.ops.export_scene.fbx(filepath=os.path.join(EXPORT, 'MongHa_2010.fbx'), use_selection=False, object_types={'MESH'},
                             apply_unit_scale=True, apply_scale_options='FBX_SCALE_UNITS', mesh_smooth_type='FACE',
                             use_mesh_modifiers=True, path_mode='AUTO', batch_mode='OFF')
    bpy.ops.export_scene.gltf(filepath=os.path.join(EXPORT, 'MongHa_2010.glb'), export_format='GLB', export_apply=True)
    print('EXPORTED')
