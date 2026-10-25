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


def Bi(n, color, passages=(), serr=False, rec=0.0):
    """color: one colour for the block, or a list with one colour per bay (2026-10-22 photo package: each block between
    the white stair towers is painted in sections of one or two bays, every bay with its own tile cap, MH002/MH005/MH068).
    rec: the whole block, every floor, stands this far back from the street (the estate's corner bays)."""
    cols = list(color) if isinstance(color, (list, tuple)) else [color] * n
    assert len(cols) == n, (n, cols)
    return {'t': 'b', 'n': n, 'color': cols[0], 'cols': cols, 'pass': list(passages), 'serr': serr, 'rec': rec}


def Ji():
    return {'t': 'j'}


def Gi(w):
    """w metres of the row left open: a passage from the street into the courtyard, no block."""
    return {'t': 'g', 'w': w}


# 16 blocks: the end rows run the full frontage and wrap the corners, the side rows sit between them
Y, G, K, R = 'yellow', 'green', 'brick', 'red'
# At three of the estate's four outer corners the end rows end in a bay that stands back from the street all the way up,
# after two full bays from the corner tower; not at the 利誠 corner (user, 2026-10-24, with photo 21, MH022 and MH007: the
# post office fills the one at the avenue's south-east end, a white side wall with the post office's board where the
# frontage steps back). Depth from photo 21 and MH022 (estimated). The estate's outline is not quite regular (user): half of
# each recessed bay lies within the side rows' outer walls and half stands out past them, so the rest of the end rows
# keeps its bays and towers; MH001 shows the avenue row's roof running ~2.3 m past the south-east row's outer wall.
CORNER_REC = 3.5
FRONT_BW = (EX1 - EX0 - 3 * JW) / 13     # avenue row: 13 bays within the side rows' outer walls, 4.88 m
BACK_BW = (EX1 - EX0 - 3 * JW) / 12.5    # back row: 12.5 bays from the 利誠 corner, 5.07 m (towers within ~1 m of MH001)
SIDE_PASS = 2 * (CZ1 - CZ0 - 3 * JW) / 24   # the corner passages at the side rows' ends: two of the first layout's bays
PASS_GAL_IN = 2.0   # the end galleries over the corner passages stop short of the street, at the end row's first window
#                     at least this far in (user, 2026-10-24: the gate fits; the corridor ends about at a window, pulled
#                     in at all four corners)
# the two hillside blocks up the steps from 利誠 (user, 2026-10-22: part of the estate). MH068 (2011-06-08, frontal), MH006
# (from the top of the steps) and the aerial MH001: they stand south-east of the 利誠 side street on the raised ground and
# face the level top of 馬交石斜坡 across a paved forecourt. Seen from the street, north-west first: block A green |
# yellow | yellow | yellow, a white stair tower with a breeze-block strip, block B green | red-brown. Bays ~5 m (MH068).
# Built in the estate's design all the same, its tower and bays like the estate's street faces (user, 2026-10-24).
HILL = dict(x0=EX1 + 7.5, x1=EX1 + 7.5 + 6 * 5.0 + JW, zf=EZ1 - 2.0, y0=3.0)   # x0/x1 NW / SE ends, zf street face (MH006 camera)
ROWS = [
    # per-bay colours, listed in each row's own direction. Back row's south-east end red-brown (MH033). Front row from photos (NW end red-brown then yellow, MH007 and
    # photo 21; red-brown over the post office corner, MH022); the back and south-east rows checked bay by bay against
    # MH001 (2026-10-24); the north-west row follows the same grammar (MH002, MH005), its ends from photos 1 and 2.
    # end rows (user, 2026-10-23, with MH001): a small block at either end and two big ones between, three stair towers
    # (the corner ones under a barrel vault, the middle one with a flat stair room), alike front and back. No passage into
    # the courtyard under the middle tower: its ground floor has the residents' doors like the others (user). The small
    # blocks are two bays and the recessed half bay at the corner (user, 2026-10-24), the 利誠 end two bays; bays the same
    # width along a row, so the front row has 13 (4.88 m) and the back row 12.5 (5.07 m; its towers then sit within ~1 m of
    # MH001's). Colours: the avenue's north-west end and big block from photo 21 (recess red-brown, two yellow; yellow,
    # red-brown, red-brown, green), its south-east end from MH001 and MH022 (two yellow, the post office's red-brown half
    # bay), the rest from MH002 (2011, the courtyard face), MH001 and MH007, which all agree. The back row, from the 利誠
    # end: red-brown (MH033, MH001), the south-east big block green, green, green, yellow and the north-west one all yellow
    # (MH001's back-street face; MH080 sees the two by the north-west tower yellow), the north-west end red-brown (MH080)
    # and its recessed corner bay yellow (photo 2).
    # 'draws_o' / 'draws_L': where the first layout stood (the full frontage between the side rows' outer walls)
    dict(id='front', o=(EX0 - FRONT_BW / 2, EZ0 + HZ), d=(1, 0), L=EX1 - EX0 + FRONT_BW, outer='street', gallery=True,
         items=[Bi(1, [K], rec=CORNER_REC), Bi(2, [Y, Y]), Ji(), Bi(4, [Y, K, K, G]), Ji(), Bi(4, [G, G, Y, Y]), Ji(),
                Bi(2, [Y, Y]), Bi(1, [K], rec=CORNER_REC)],
         draws=[Bi(4, [K, Y, Y, Y]), Ji(), Bi(5, [Y, K, K, G, G], [2]), Ji(), Bi(4, [Y, Y, K, K])],
         draws_o=(EX0, EZ0 + HZ), draws_L=EX1 - EX0),
    dict(id='back', o=(EX1, EZ1 - HZ), d=(-1, 0), L=EX1 - EX0 + BACK_BW / 2, outer='street', gallery=True,
         items=[Bi(2, [K, K]), Ji(), Bi(4, [G, G, G, Y]), Ji(), Bi(4, [Y, Y, Y, Y]), Ji(), Bi(2, [K, K]),
                Bi(1, [Y], rec=CORNER_REC)],   # the recessed corner bay over the nursery yellow (photo 2)
         draws=[Bi(4, [K, K, Y, Y]), Ji(), Bi(5, [Y, R, R, G, G], [2]), Ji(), Bi(4, [Y, Y, K, K])],   # 利誠 end first
         draws_L=EX1 - EX0),
    # side rows (user, 2026-10-23, photo 1 and MH001): no block at either end but a passage from the street into the
    # estate, alike at all four corners, 7.8 m long (two of the first layout's bays). Between the passages 2 | 4 | 4 | 2
    # bays of ~6.5 m and three towers, as MH001 measures the bays (its tile caps and fins; photo 1 alike) (user,
    # 2026-10-24); the towers nearest the ends then stand ~2.6 m nearer them than first laid out (MH001's towers within
    # ~1 m). Neither side row has a ground-floor passage through it (user, 2026-10-24: the south-east one a shuttered shop,
    # the north-west one plain wall on the lane, the towers' doors the only ways in from there). 'draws' is the first layout: the
    # shared random streams are tuned to it, so it is drawn into the scratch mesh before the row is built.
    # north-west row, from the back end: yellow, yellow | tower | yellow, brick, brick (photo 1), the rest inferred
    dict(id='nw', o=(EX0 + HZ, CZ1), d=(0, -1), L=CZ1 - CZ0, outer='street', gallery=True,
         items=[Gi(SIDE_PASS), Bi(2, [Y, Y]), Ji(), Bi(4, [Y, K, K, G]), Ji(), Bi(4, [K, G, Y, R]), Ji(),
                Bi(2, [Y, Y]), Gi(SIDE_PASS)],   # no passage through it either: plain wall on the lane (user, 2026-10-24)
         draws=[Bi(6, [Y, Y, G, G, K, K]), Ji(), Bi(6, [G, G, Y, Y, K, K], [3]), Ji(), Bi(6, [K, K, G, Y, Y, G]), Ji(),
                Bi(6, [R, R, Y, Y, G, G])]),
    # south-east row, from the avenue end (MH001, shadows lifted): yellow, red-brown | green, green, red-brown, red-brown |
    # red-brown, yellow, yellow, yellow | the 利誠 end yellow (photo 3, 2010; too dark in MH001)
    dict(id='se', o=(EX1 - HZ, CZ0), d=(0, 1), L=CZ1 - CZ0, outer='street', gallery=True,
         items=[Gi(SIDE_PASS), Bi(2, [Y, K]), Ji(), Bi(4, [G, G, K, K]), Ji(), Bi(4, [K, Y, Y, Y]), Ji(),
                Bi(2, [Y, Y]), Gi(SIDE_PASS)],   # no passage through the green bay: a shuttered shop (user, 2026-10-24)
         draws=[Bi(6, [K, K, Y, Y, G, G]), Ji(), Bi(6, [G, G, Y, Y, K, K], [2]), Ji(), Bi(6, [G, Y, Y, R, R, G]), Ji(),
                Bi(6, [G, G, K, K, Y, Y])]),
    dict(id='slope1', o=(HILL['x1'], HILL['zf'] - HZ), d=(-1, 0), L=HILL['x1'] - HILL['x0'], outer='street', gallery=None,
         y0=HILL['y0'], items=[Bi(2, [K, G]), Ji(), Bi(4, [Y, Y, Y, G])]),   # listed from the south-east end
]
for row in ROWS:
    for key in ('draws', 'items'):   # bay width of each layout ('bw' is the one built)
        if key not in row:
            continue
        items = row[key]
        L = row.get('draws_L', row['L']) if key == 'draws' else row['L']
        fixed = sum(JW if it['t'] == 'j' else it['w'] for it in items if it['t'] != 'b')
        bays = sum(it['n'] for it in items if it['t'] == 'b')
        bw = row['bw' if key == 'items' else 'draws_bw'] = (L - fixed) / bays
        x = 0.0
        for it in items:
            it['x0'] = x
            x += JW if it['t'] == 'j' else it['w'] if it['t'] == 'g' else it['n'] * bw
            it['x1'] = x
    dx, dz = row['d']
    for key, o in (('fr', row['o']), ('draws_fr', row.get('draws_o', row['o']))):
        row[key] = Fr((o[0], row.get('y0', 0.0), o[1]), (dx, 0, dz), (-dz, 0, dx))

_FJ = [it for it in ROWS[0]['items'] if it['t'] == 'j']
FX0 = ROWS[0]['o'][0]                              # site x of the avenue row's north-west end
PASS_X = FX0 + (_FJ[1]['x0'] + _FJ[1]['x1']) / 2   # the avenue row's middle tower (zebra crossing)
# (site x, z) near which the two trading shops stood (user, 2026-10-22): from the avenue's north-west corner (photo 21,
# user 2026-10-24): the recessed half bay, 鞋宜樂, the bay with the bus shelter in front, the stair tower; 利誠美食 in the
# south-east side street beside its last stair tower (top-left seen from the avenue), up the steps at its end 望廈飲食;
# sign atlas cells 11 and 10
SHOES_X = FX0 + ROWS[0]['items'][1]['x0'] + 0.5 * ROWS[0]['bw']
BUS_X = FX0 + ROWS[0]['items'][1]['x0'] + 1.5 * ROWS[0]['bw']
OPEN_SHOPS = {'shoes': (EX0 + ROWS[0]['draws'][2]['x0'] + 0.5 * ROWS[0]['draws_bw'], EZ0, 11),   # first layout's spot,
              'lisheng': (EX1, CZ1 - 0.5 * ROWS[3]['draws_bw'], 3),                               # for the scratch draw
              'lisheng2': (EX1, CZ1 - 1.5 * ROWS[3]['draws_bw'], None)}
ROWS[0]['shops'] = {'shoes': (SHOES_X, EZ0, 11)}
_SE_T3 = CZ1 - SIDE_PASS - 2 * ROWS[3]['bw'] - JW   # the avenue side of the south-east row's last stair tower
ROWS[3]['shops'] = {'lisheng': (EX1, _SE_T3 - 0.5 * ROWS[3]['bw'], 3),   # 利誠美食 in the bay beside the last tower (user,
                    'lisheng2': (EX1, _SE_T3 - 1.5 * ROWS[3]['bw'], None)}   # 2026-10-24), its green neighbour towards the avenue (MH013)
# the hillside shops, north-west first (MH068, MH006): 望廈飲食 and 金富美食 (black boards, red characters), an eatery with
# an unreadable pale board, a green canvas awning (MH033), a striped awning, Maria Beauty Center (purple board)
HILL_BW = ROWS[4]['bw']
HILL_SHOPS = ('mhfood', 'kamfu', 'hill3', 'hill4', 'hill5', 'maria')   # their boards and names taken off (user, 2026-10-24)
HX = [HILL['x0'] + (k + 0.5) * HILL_BW + (JW if k > 3 else 0) for k in range(6)]
OPEN_SHOPS.update({k: (HX[i], HILL['zf'], c) for i, (k, c) in enumerate((('mhfood', 0), ('kamfu', 1), ('hill3', None),
                                                                         ('hill4', None), ('hill5', None), ('maria', 2)))})
FRONT_TREES = [(EX0 + f * (EX1 - EX0), -1.5, r) for f, r in ((0.175, 2.0), (0.33, 3.0), (0.645, 1.9), (0.92, 2.0))]   # photos 21, 22;
# the first one past the bus shelter's end, in front of the tower (it stood in the shelter: user, 2026-10-24)
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


# the 利誠 steps (see build_ground): the short flight from its slanting gate (foot = middle of its first riser, ang = its
# heading from +x towards +z), the turn against the hillside's wall from za0 to za1, the long flight along the wall from
# xl0, up to the raised paving's old edge at zp; the store beside the gate under the paving (front at store_z); the side
# street ends at the store's front
LISHENG = dict(foot=(SIDE_X1 - 3.26, 0.0, CZ1 + 0.9), ang=math.radians(30), za0=CZ1 + 1.0, za1=CZ1 + 2.6, xl0=SIDE_X1 - 1.6,
               zp=CZ1 + 6.2, store_z=CZ1 + 1.6)
LISHENG_ZP = LISHENG['store_z']


def back_h(x):
    """Ground level of the back street at site x."""
    t = (x - BACK['x_lo']) / (BACK['x_hi'] - BACK['x_lo'])
    return BACK['H'] * min(1.0, max(0.0, t))
# library: three storeys (user, 2026-10-23, with MH034 = photo 24 and MH001): the ground and top floors share one octagon
# inside the red column ring, and the columns run from the ground to the roof. The first floor, level with the galleries,
# is a walkway behind a planter ring round the court side, reached by the two bridges; its reading room fills the back
# half, and its three back faces jut out ~4.6 m towards the back street over open ground, on four more red columns; the
# top of the jut is a balcony round the top floor, its middle part tiled in a different tone. Entrance under the
# north-west bridge (MH034). Radii are of octagon corners, before the plan scale.
# Position, jut and roof refitted to MH001 with this shape (2026-10-23): the four columns standing on the paving are the
# jut's, so the octagon sits ~4 m nearer the ball court than the earlier fit, which took them for the column ring
# (centre z 76.9, ring radius 6.54 m, jut 4.57 m, rms 4.3 px; eave ~11.2 m high, 7.1 m in radius).
# The estate is laid out symmetrically and the two bridges line up with the side rows' middle stair towers (user,
# 2026-10-24): the library stands on the courtyard's centre, ~4 m nearer the ball court than that fit (and 1 m off it
# across, which the fit also had).
LIB_X, LIB_Z = LX, LZ               # centre of the red column ring
LIB_S = 0.705                       # plan scale: column ring radius 9.3 * 0.705 = 6.56 m
# Heights from MH034, taken from the first-floor gallery (its horizon sits ~1.5 m above the first floor), scaled so the
# first floor is level with the galleries and bridges (GF); windows five to a face, ~0.96 m apart (user, 2026-10-23).
LIB = dict(col=9.3, slab=9.35, wall=8.9, inner=5.3, jut=6.5, bay=0.96,
           plinth=0.3, l1_win=(2.55, 3.42), l2_win=(4.05, 6.5), l3=(6.75, 7.1), band=8.0, l3_win=(8.05, 9.55),
           fascia=(9.6, 10.0), eave=10.1, apex=12.3)   # roof ~2.3 m from eaves to top (MH035; user, 2026-10-24: less flat)
BRIDGE_Z = LIB_Z
NWG, SEG = CX0 + GW, CX1 - GW          # inner edges of the side galleries
GZ0, GZ1 = CZ0 + GW, CZ1 - GW          # inner edges of the end galleries
# each of the four U-stairs stands in front of the side row's tower nearest its end, and the playground in front of the
# back pair (photo 1): all of them two bays nearer the ends than first laid out, like the towers (user, 2026-10-23);
# each stair, both flights, centred on its tower (user, 2026-10-24, with photo 10). With MH001's bays (2026-10-24) the
# towers, and so the stairs, stand only ~2.6 m nearer the ends than first laid out; the playground and the planters
# beside it stay two of the first layout's bays back, as the long planter MH001 has in front of the playground leaves no
# room to bring it forward
END_SHIFT = 2 * ROWS[2]['draws_bw']
STAIRS = sorted((CZ1 - (it['x0'] + it['x1']) / 2 for it in ROWS[2]['items'] if it['t'] == 'j'), reverse=True)
STAIRS = [STAIRS[0], STAIRS[-1]]
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
        if row.get('first'):   # the first layout (drawn only to keep the random streams in step): ground-floor recesses
            if xl < 3 * bw:
                return 'recess', int(xl // bw)
            if xl > row['L'] - 3 * bw:
                return 'post', int((row['L'] - xl) // bw)
        elif xl > row['L'] - row['bw']:   # the post office fills the recessed corner bay (user, 2026-10-24)
            return 'post', 0
    if row['id'] == 'nw' and row.get('first') and xl < 2 * bw:   # where the first layout had it (drawn for the streams only)
        return 'nursery', int(xl // bw)
    # the nursery's door is in the back row's recessed corner bay on the back street (user, 2026-10-24, photo 2), the
    # coloured glass-block windows beside it in the next bay (MH080)
    if row['id'] == 'back' and xl > row['L'] - 2 * bw:
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
    'pyellow': M('M_Play_Yellow', '#e3b62c', 0.45, 0.2),   # the playground's yellow rails and swing beam (MH024)
    'pred': M('M_Play_Red', '#b8473a', 0.5),
    'sand': M('M_Sand', '#d6c391', 1.0),
    'wood': M('M_Wood_Planter', '#9c7a4c', 0.8),
    'water': M('M_Water_Pond', '#3f5e57', 0.05),
    'rock': M('M_Rock', '#86837a', 0.9),
    'bench': M('M_Concrete_Bench', '#cfc9bc'),
    'lamp': M('M_Lamp_Globe', '#f6f1e0', 0.3, emit='#3a3528'),
    'hallw': M('M_Hall_White', '#e2dfd6'),
    'hallg': M('M_Hall_Grey', '#5a6062', 0.7),
    'stone': M('M_Hall_Stone', '#adada7', 0.7),      # grey granite cladding (lighter, MH017, MH027)
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
    'desporto': M('M_Sign_Desporto', '#ffffff', 0.5),   # 體育發展局 logo on the sports hall's gable (tools/make_sign_tex.py)
    'hallname': M('M_Sign_HallName', '#ffffff', 0.5),   # the hall's name lettered on its gable (tools/make_sign_tex.py)
    'photosigns': M('M_Sign_Photos', '#ffffff', 0.6),   # shop boards cut out of the photos (tools/make_sign_tex.py)
    'ctxglass': M('M_Context_Glass', '#55636a', 0.15),
    'fanglass': M('M_Glass_Fan', '#9aabb3', 0.12),   # the stair towers' fan lights: pale, the sky in them (MH005)
    'hallglass': M('M_Hall_Glass', '#93aab2', 0.1),   # the sports hall's pale window glass (MH017, MH030)
    'signs': [M(f'M_Sign_{n}', c, 0.5) for n, c in (('Red', '#b8282a'), ('Yellow', '#f2d23c'), ('Green', '#1f6f4a'), ('White', '#f5f1e6'), ('Blue', '#1d4e8f'), ('Orange', '#e06a1f'),
                                                          ('Black', '#1f1f1d'), ('Purple', '#3b2f6e'))],
    'cloth': [M(f'M_Cloth_{i}', c, 0.95) for i, c in enumerate(['#e8e2d6', '#c9473e', '#3f6ea8', '#e3c34d', '#f2f2ee', '#6c9a6c', '#d98cab', '#4b4b4b'])],
    'post': M('M_PostOffice_Red', '#b3201f', 0.5),
    'fanred': M('M_Frame_FanRed', '#8a3324', 0.5),
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
AC_HELD = None  # a list while a floor is drawn for the streams only: its units land here, to be hung on the floor built instead


def ac_mark(sf, kind, xc, y0, z0):
    """kind 'window' | 'split'; (xc, y0, z0) = bottom centre where the unit meets the wall, in frame sf (local +z = out)."""
    if AC_HELD is not None:
        AC_HELD.append((kind, xc, y0))
        return
    AC_MARKS.append(dict(kind=kind, p=[round(v, 4) for v in sf.p(xc, y0, z0)], out=[round(v, 5) for v in sf.ez]))


# the top floor has no balconies on either face: a flat wall with two windows a bay, standing a little behind the floors
# below and the white walls either side, a grey sunshade along its foot (user, 2026-10-24, MH002 = their photo, MH005)
YT = GF + FH * (NF - 1)   # its floor level
SB = 0.2                  # how far its wall stands behind the facade below on the courtyard side
SB_ST = 0.4               # and on the street side, where the pilasters are flush below (user, 2026-10-24: the other face too)
FIN_TOP = 0.15            # the courtyard pilasters' face up there, from the courtyard facade plane (0.85 below)


def held_floor(mb, f):
    """Where floor f is built: the top floor as it was goes to the scratch mesh (its random draws kept, its units held)."""
    global AC_HELD
    if f == NF - 1:
        AC_HELD = []
        return SCRATCH
    return mb


def top_units(mb, sf, z, street):
    """Hang the units the old top floor drew (held_floor) on the new wall at depth z."""
    global AC_HELD
    held, AC_HELD = AC_HELD or [], None
    for kind, xc, y0 in held:
        if kind == 'window':
            box(mb, sf, xc - 0.33, xc + 0.33, y0, y0 + 0.42, z, z + (0.42 if street else 0.4), MAT['ac'])
        else:
            box(mb, sf, xc - 0.38, xc + 0.38, y0, y0 + 0.53, z + 0.06, z + 0.34, MAT['ac'])
            for k in (-0.3, 0.3):
                box(mb, sf, xc + k - 0.02, xc + k + 0.02, y0 - 0.05, y0, z, z + 0.4, MAT['pole'])
        ac_mark(sf, kind, xc, y0, z)


def top_rng(sf, xa):
    """The new top floor's own stream, one per bay, so its windows leave the rest alone."""
    return random.Random('top %.2f %.2f %.2f' % tuple(sf.p(xa, 0, 0)))


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
# cut into the wall: their railings stand on thick slab bands that run unbroken across the bay (MH005, MH038, MH068). The
# top floor has no balcony (see YT)
ZW_OUT = 0.35       # the street facade stands this far in from the row's outer line
ZW = HZ - ZW_OUT    # street facade plane
ZR = HZ - LOG       # balcony back wall (the residential core face)
BALC = ZW + 0.06    # balcony front: railing just proud of the wall plane


def street_bay(mb, sf, xa, xb, ib, col, post=False):
    """post: the post office's bay, its first floor a band of red-framed windows across the bay (MH022). (The hillside
    blocks' green bays, one balcony across the bay in MH068, are the estate's like the rest: user, 2026-10-24.)"""
    global irng
    w, p = xb - xa, 0.18
    bwid = (w - 2 * p) * 0.5
    if ib % 2 == 0:
        bx0, bx1, wx0, wx1 = xa + p, xa + p + bwid, xa + p + bwid, xb - p
    else:
        bx0, bx1, wx0, wx1 = xb - p - bwid, xb - p, xa + p, xb - p - bwid
    tile, band = MAT['plaster'][col], MAT['slab'][col]
    rail = MAT['balrail'] if irng.random() < 0.7 else MAT['rail']
    ww = wx1 - wx0
    box(mb, sf, wx0, wx1, GF, YT, ZR, ZW, tile, skip=('nz',))
    cylv(mb, sf, xa, ZW + 0.2, GF - 0.3, ROOF + 0.3, 0.05, 8, MAT['white'])                     # drain pipe on the pilaster
    for f in range(NF):
        y = GF + FH * f
        mf = held_floor(mb, f)
        box(mf, sf, xa + p, xb - p, y - 0.18, y + 0.22, ZW - 0.02, ZW + 0.08, band)             # slab band, whole bay
        if post and f == 0:   # six panes, just above the post office's fascia (MH022)
            ga, gb = xa + p + 0.15, xb - p - 0.15
            box(mf, sf, xa + p, xb - p, y + 0.22, y + FH - 0.18, ZR, ZW + 0.03, MAT['white'], skip=('nz',))
            window(mf, sf, ga, gb, y + 0.6, y + 1.8, ZW + 0.03, mull=False, gm=MAT['shopglass'], cells=4, fm=MAT['post'])
            for t in POST_MULL1:
                xm = ga + (gb - ga) * t
                box(mf, sf, xm - 0.04, xm + 0.04, y + 0.6, y + 1.8, ZW + 0.03, ZW + 0.11, MAT['post'])
            continue
        box(mf, sf, bx0, bx1, y, y + 0.16, ZR, ZW - 0.02, {'py': MAT['deck'], '*': MAT['soffit']})
        railing_run(mf, sf, bx0 + 0.03, bx1 - 0.03, y + 0.16, BALC - 0.04, rail)
        window(mf, sf, bx0 + 0.15, bx1 - 0.15, y + 0.2, y + 2.35, ZR, mull=True)                 # balcony door
        window(mf, sf, wx0 + 0.2 * ww, wx1 - 0.2 * ww, y + 0.95, y + 2.25, ZW, bars=irng.random() < 0.3)
        r = irng.random()
        if r < 0.3:      # window-type air conditioner under the window
            xc = wx0 + 0.5 * ww
            box(mf, sf, xc - 0.33, xc + 0.33, y + 0.5, y + 0.92, ZW, ZW + 0.42, MAT['ac'])
            ac_mark(sf, 'window', xc, y + 0.5, ZW)
        elif r < 0.65:   # split unit on a wall bracket
            xc = wx0 + (0.18 if irng.random() < 0.5 else 0.82) * ww
            box(mf, sf, xc - 0.38, xc + 0.38, y + 0.35, y + 0.88, ZW + 0.06, ZW + 0.34, MAT['ac'])
            ac_mark(sf, 'split', xc, y + 0.35, ZW)
            for k in (-0.3, 0.3):
                box(mf, sf, xc + k - 0.02, xc + k + 0.02, y + 0.3, y + 0.35, ZW, ZW + 0.4, MAT['pole'])
        if irng.random() < 0.55:   # laundry inside the balcony front
            cylx(mf, sf, bx0 + 0.05, bx1 - 0.05, y + 2.45, BALC - 0.18, 0.02, 6, MAT['pole'])
            xx = bx0 + 0.1
            while xx < bx1 - 0.3:
                cell = CLOTH['cells'][irng.randrange(len(CLOTH['cells']))]
                k = irng.uniform(0.8, 1.0)
                if xx + cell['size'][0] * k > bx1 - 0.05:
                    break
                garment(mf, sf, xx, y + 2.42, BALC - 0.18, cell, k)
                xx += cell['size'][0] * k + 0.04 + 0.2 * irng.random()
        if (f == NF - 1 and irng.random() < 0.8) or irng.random() < 0.06:   # sheet-metal awning
            prism_x(mf, sf, [(ZR, y + FH - 0.13), (ZW + 0.65, y + FH - 0.6), (ZW + 0.65, y + FH - 0.55), (ZR, y + FH - 0.08)],
                    bx0 - 0.04, bx1 + 0.04, MAT['awning'])
    # the top floor (see YT): a wall across the bay a little behind the facade, a window over the balcony below and one over
    # the window, the sunshade at its foot
    zt = ZW - SB_ST
    box(mb, sf, xa + p, xb - p, YT, ROOF, ZR, zt, {'ny': MAT['soffit'], '*': tile}, skip=('nz', 'py'))
    box(mb, sf, xa + p, xb - p, YT - 0.08, YT + 0.02, zt, ZW + 0.12, {'py': MAT['screed'], '*': MAT['soffit']})
    keep, irng = irng, top_rng(sf, xa)
    for c in ((bx0 + bx1) / 2, (wx0 + wx1) / 2):
        window(mb, sf, c - 0.3 * ww, c + 0.3 * ww, YT + 0.95, YT + 2.25, zt, bars=irng.random() < 0.3)
    irng = keep
    top_units(mb, sf, zt, True)


def court_layout(xa, xb, ib):
    """A courtyard bay's loggia (lx0, lx1) and window (ox0, ox1) between its pilasters, on alternate sides bay by bay."""
    p = 0.17
    wi = xb - xa - 2 * p
    lw = 0.48 * wi
    if ib % 2 == 0:
        lx0, lx1 = xa + p, xa + p + lw
        return lx0, lx1, lx1 + 0.22 * (wi - lw), xb - p - 0.22 * (wi - lw)
    lx0, lx1 = xb - p - lw, xb - p
    return lx0, lx1, xa + p + 0.22 * (wi - lw), lx0 - 0.22 * (wi - lw)


def court_window_xs(row):
    """Site x of the middle of every courtyard-side window along an end row."""
    xs = []
    for it in row['items']:
        for i in range(it['n'] if it['t'] == 'b' else 0):
            _, _, ox0, ox1 = court_layout(it['x0'] + i * row['bw'], it['x0'] + (i + 1) * row['bw'], i)
            xs.append(row['fr'].p((ox0 + ox1) / 2, 0, 0)[0])
    return xs


def court_bay(mb, sf, xa, xb, ib, col):
    """Courtyard side (photo 14): flat wall between slim white pilasters, a recessed loggia and a window per bay
    on every floor from the gallery floor up to the one under the top floor (which has none: see YT), white floor bands,
    window air-conditioners, laundry in the loggias."""
    global irng
    p = 0.17
    lx0, lx1, ox0, ox1 = court_layout(xa, xb, ib)
    tile = MAT['plaster'][col]
    wallm = {'pz': tile, 'px': tile, 'nx': tile, 'ny': MAT['soffit'], '*': MAT['white']}
    rail = MAT['balrail'] if irng.random() < 0.4 else MAT['rail']
    for f in range(NF):
        y = GF + FH * f
        mf = held_floor(mb, f)
        segs = [(xa + p, lx0), (lx1, xb - p)]
        for a_, b_ in segs:
            if b_ - a_ > 0.02:
                box(mf, sf, a_, b_, y, y + FH, ZL, ZC, wallm, skip=('py', 'ny'))
        box(mf, sf, lx0, lx1, y + 2.45, y + FH, ZL, ZC, wallm, skip=('py',))           # lintel over the loggia
        box(mf, sf, lx0, lx1, y, y + 0.12, ZL, ZC + 0.03, {'py': MAT['deck'], '*': MAT['slab'][col]})
        box(mf, sf, lx0, lx1, y + 0.12, y + 0.55, ZC - 0.12, ZC, {'pz': tile, '*': MAT['white']})   # low wall
        box(mf, sf, lx0, lx1, y + 1.0, y + 1.05, ZC - 0.09, ZC - 0.03, rail)
        xv = lx0 + 0.12
        while xv < lx1 - 0.08:
            box(mf, sf, xv - 0.009, xv + 0.009, y + 0.55, y + 1.0, ZC - 0.07, ZC - 0.05, rail)
            xv += 0.13
        lwid = lx1 - lx0
        window(mf, sf, lx0 + 0.1 * lwid, lx0 + 0.45 * lwid, y + 0.95, y + 2.25, ZL, bars=irng.random() < 0.3)
        window(mf, sf, lx0 + 0.55 * lwid, lx0 + 0.9 * lwid, y + 0.15, y + 2.3, ZL, mull=True)
        window(mf, sf, ox0, ox1, y + 0.95, y + 2.25, ZC, bars=irng.random() < 0.2)
        if irng.random() < 0.45:                                                       # window air-conditioner
            xc = (ox0 + ox1) / 2
            box(mf, sf, xc - 0.33, xc + 0.33, y + 0.98, y + 1.4, ZC, ZC + 0.4, MAT['ac'])
            ac_mark(sf, 'window', xc, y + 0.98, ZC)
        if irng.random() < 0.55:                                                       # laundry inside the loggia
            cylx(mf, sf, lx0 + 0.05, lx1 - 0.05, y + 2.35, ZC - 0.35, 0.02, 6, MAT['pole'])
            xx = lx0 + 0.1
            while xx < lx1 - 0.3:
                cell = CLOTH['cells'][irng.randrange(len(CLOTH['cells']))]
                k = irng.uniform(0.75, 0.95)
                if xx + cell['size'][0] * k > lx1 - 0.05:
                    break
                garment(mf, sf, xx, y + 2.32, ZC - 0.35, cell, k)
                xx += cell['size'][0] * k + 0.05 + 0.2 * irng.random()
        box(mf, sf, xa + p, xb - p, y - 0.1, y + 0.08, ZC, ZC + 0.05, MAT['white'])       # floor band
    # the top floor (see YT): no loggia, a flat wall a little behind the facade and the pilasters, two windows, the sunshade
    # at its foot reaching the pilasters' face up there
    zt = ZC - SB
    box(mb, sf, xa + p, xb - p, YT, ROOF, ZL, zt, wallm, skip=('py', 'nz'))
    box(mb, sf, xa + p, xb - p, YT - 0.08, YT + 0.02, zt, ZC + FIN_TOP, {'py': MAT['screed'], '*': MAT['soffit']})
    keep, irng = irng, top_rng(sf, xa)
    ww = ox1 - ox0
    for c in ((lx0 + lx1) / 2, (ox0 + ox1) / 2):
        window(mb, sf, c - ww / 2, c + ww / 2, YT + 0.95, YT + 2.25, zt, bars=irng.random() < 0.2)
    irng = keep
    top_units(mb, sf, zt, False)


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


# shop boards cut out of the photos (user, 2026-10-24; 鞋宜樂's lettered board back, its photo too skewed): cells x0, y0,
# x1, y1 of tools/make_sign_tex.py's 2048 px atlas
PHOTO_SIGNS = {'lisheng': (0, 0, 2048, 253), 'nursery': (0, 650, 2048, 866), 'lisheng_blade': (0, 870, 640, 1311)}
POST_MULL = (0.155, 0.31, 0.44, 0.5, 0.618, 0.697, 0.848)   # the post office window's red frames across it (MH022)
POST_MULL1 = (0.135, 0.302, 0.481, 0.664, 0.832)            # and its first floor's


def photo_uv(name):
    """(bl, br, tr, tl) UVs of a photographed board."""
    x0, y0, x1, y1 = PHOTO_SIGNS[name]
    u0, u1, vb, vt = (x0 + 2) / 2048, (x1 - 2) / 2048, 1 - (y1 - 2) / 2048, 1 - (y0 + 2) / 2048
    return [(u0, vb), (u1, vb), (u1, vt), (u0, vt)]


def open_shop(mb, sf, shop, fa, fb):
    """Trading shops: glazed front, frames, signboard (the photographed board, else from the atlas when the name is
    known), awning (SHOP_LOOK)."""
    frame = MAT['shopgreen'] if shop == 'shoes' else MAT['frame']
    box(mb, sf, fa, fb, 0, 0.35, HZ - 0.3, HZ - 0.22, MAT['myellow'] if shop == 'shoes' else MAT['ground'])
    mb.poly([sf.p(fa, 0.35, HZ - 0.25), sf.p(fb, 0.35, HZ - 0.25), sf.p(fb, GF - 1.05, HZ - 0.25), sf.p(fa, GF - 1.05, HZ - 0.25)],
            MAT['shopglass'], uvs=atlas_uv(4, (fb - fa) / (GF - 1.4)))
    for xm in (fa + 0.04, fa + (fb - fa) * 0.5, fb - 0.04):
        box(mb, sf, xm - 0.04, xm + 0.04, 0.35, GF - 1.05, HZ - 0.28, HZ - 0.18, frame)
    box(mb, sf, fa, fb, 1.9, 1.96, HZ - 0.28, HZ - 0.18, frame)
    zf = HZ + 0.135
    board, awn = SHOP_LOOK[shop]
    if shop not in HILL_SHOPS:   # the hillside row's boards and names taken off (user, 2026-10-24)
        box(mb, sf, fa + 0.05, fb - 0.05, GF - 1.05, GF - 0.3, HZ, HZ + 0.12, MAT['signs'][board])
        quad = [sf.p(fa + 0.05, GF - 1.05, zf), sf.p(fb - 0.05, GF - 1.05, zf), sf.p(fb - 0.05, GF - 0.3, zf), sf.p(fa + 0.05, GF - 0.3, zf)]
        if shop in PHOTO_SIGNS:
            mb.poly(quad, MAT['photosigns'], uvs=photo_uv(shop))
        elif OPEN_SHOPS[shop][2] is not None:
            mb.poly(quad, MAT['signatlas'], uvs=sign_uv(OPEN_SHOPS[shop][2]))
    if awn:   # canvas awning (利誠 grey, its neighbour green, photo 3; hillside: white and striped, MH068)
        prism_x(mb, sf, [(HZ, GF - 1.2), (HZ + 1.4, GF - 1.65), (HZ + 1.4, GF - 1.6), (HZ, GF - 1.15)], fa, fb, MAT[awn])
    if shop == 'lisheng':   # yellow blade sign standing out from the wall on a bracket (photo 3), at the back-street end
        xs, yl, yh, zi, zo = fa + 0.3, GF + 0.15, GF + 1.25, HZ + 0.45, HZ + 2.05   # its proportions as in MH013
        box(mb, sf, xs - 0.04, xs + 0.04, yl, yh, zi, zo, MAT['signs'][1])
        uv = photo_uv('lisheng_blade')
        mb.poly([sf.p(xs + 0.055, yl, zo), sf.p(xs + 0.055, yl, zi), sf.p(xs + 0.055, yh, zi), sf.p(xs + 0.055, yh, zo)], MAT['photosigns'], uvs=uv)
        mb.poly([sf.p(xs - 0.055, yl, zi), sf.p(xs - 0.055, yl, zo), sf.p(xs - 0.055, yh, zo), sf.p(xs - 0.055, yh, zi)], MAT['photosigns'], uvs=uv)
        box(mb, sf, xs - 0.025, xs + 0.025, yh, yh + 0.05, HZ, zo, MAT['steel'])                # bracket
        beam(mb, sf.p(xs, yh + 0.05, HZ), sf.p(xs, yh + 0.7, HZ), 0.05, MAT['steel'])
        beam(mb, sf.p(xs, yh + 0.7, HZ), sf.p(xs, yh + 0.05, zo - 0.1), 0.03, MAT['steel'])


def special_front(mb, sf, kind, fa, fb, i, depth=REC, col=Y):
    """Ground floor of the recessed end blocks: post office (red frames, 郵政 Correios) or the nursery (glass block),
    depth behind the piers; col the bay's colour."""
    zw = HZ - depth
    if kind == 'post':   # as MH022: the window up to ~3.25 m, its red frames where the photo's are; the fascia over it
        yg = GF - 0.55   # ~3.3-4.35 m, up across the first floor's slab, lettered 郵政 Correios (tools/make_sign_tex.py)
        box(mb, sf, fa, fb, 0, 0.3, zw, zw + 0.1, MAT['hallg'])
        mb.poly([sf.p(fa, 0.3, zw + 0.05), sf.p(fb, 0.3, zw + 0.05), sf.p(fb, yg, zw + 0.05), sf.p(fa, yg, zw + 0.05)],
                MAT['shopglass'], uvs=atlas_uv(4, (fb - fa) / (yg - 0.3)))
        for xm in [fa, fb] + [fa + (fb - fa) * t for t in POST_MULL]:
            box(mb, sf, xm - 0.04, xm + 0.04, 0.3, yg, zw + 0.02, zw + 0.12, MAT['post'])
        box(mb, sf, fa, fb, 1.72, 1.79, zw + 0.02, zw + 0.12, MAT['post'])
        box(mb, sf, fa, fb, yg - 0.07, yg, zw + 0.02, zw + 0.12, MAT['post'])
        box(mb, sf, fa - 0.02, fb + 0.02, GF - 0.5, GF + 0.55, HZ - 0.05, HZ + 0.35, MAT['post'])
        zf = HZ + 0.36
        mb.poly([sf.p(fa + 0.1, GF - 0.47, zf), sf.p(fb - 0.1, GF - 0.47, zf), sf.p(fb - 0.1, GF + 0.52, zf), sf.p(fa + 0.1, GF + 0.52, zf)],
                MAT['postsign'], uvs=[(0.01, 0.02), (0.99, 0.02), (0.99, 0.98), (0.01, 0.98)])
    elif i == 2:   # 望廈托兒所 in the recessed corner bay (photo 2): a glazed door between two strips of glass block, the
        gb = 0.55  # yellow name board over them, a row of clerestory panes, the bay's mosaic above and a sheet-metal awning
        for a, b in ((fa, fa + gb), (fb - gb, fb)):
            box(mb, sf, a, b, 0, 2.45, zw, zw + 0.12, MAT['glassblock'])
        box(mb, sf, fa + gb, fb - gb, 0, 2.45, zw - 0.05, zw, MAT['void'])
        window(mb, sf, fa + gb + 0.12, fb - gb - 0.12, 0.02, 2.33, zw + 0.02, mull=True, gm=MAT['shopglass'], cells=4)
        box(mb, sf, fa, fb, 2.45, 2.95, zw, zw + 0.14, MAT['signs'][1])
        mb.poly([sf.p(fa, 2.45, zw + 0.145), sf.p(fb, 2.45, zw + 0.145), sf.p(fb, 2.95, zw + 0.145), sf.p(fa, 2.95, zw + 0.145)],
                MAT['photosigns'], uvs=photo_uv('nursery'))   # the board in photo 2
        box(mb, sf, fa, fb, 2.95, 3.4, zw - 0.05, zw, MAT['void'])
        np_ = 6
        for k in range(np_ + 1):   # clerestory: six panes in white frames
            xm = fa + (fb - fa) * k / np_
            box(mb, sf, xm - 0.04, xm + 0.04, 2.95, 3.4, zw, zw + 0.08, MAT['frame'])
        mb.poly([sf.p(fa, 2.98, zw + 0.03), sf.p(fb, 2.98, zw + 0.03), sf.p(fb, 3.37, zw + 0.03), sf.p(fa, 3.37, zw + 0.03)],
                MAT['shopglass'], uvs=atlas_uv(4, (fb - fa) / 0.4))
        box(mb, sf, fa - 0.32, fb, 3.4, GF, zw, HZ, MAT['plaster'][col])
        prism_x(mb, sf, [(HZ - 0.02, GF + 0.12), (HZ + 0.65, GF - 0.18), (HZ + 0.65, GF - 0.14), (HZ - 0.02, GF + 0.17)],
                fa - 0.3, fb, MAT['awning'])
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


WELL = (2.62, 2.52, -0.8)       # light well of the big blocks (inside its parapet): half width along the row, half depth,
                                # centre across the block; parapet ~5.6 m square fitted to MH001 (the first model had 3.2)
WELL_RNG = random.Random(2071)  # its windows draw from their own stream


def light_well(mb, fr, xm):
    """The open square enclosure in the middle of a big block's roof (MH001) is the top of a light well (user, 2026-10-23):
    a parapet with posts at the corners round a shaft down to the first floor, a partition across it (MH001), one small
    window a floor in each half."""
    global irng
    hx, hz, zc_ = WELL
    wa, wb, za, zb = xm - hx, xm + hx, zc_ - hz, zc_ + hz
    t, hw = 0.18, RFS + 1.25
    for xa_, xb_, za_, zb_ in ((wa - t, wb + t, za - t, za), (wa - t, wb + t, zb, zb + t), (wa - t, wa, za, zb), (wb, wb + t, za, zb)):
        box(mb, fr, xa_, xb_, RFS, hw, za_, zb_, MAT['white'])                                     # parapet
    for xq in (wa - t / 2, wb + t / 2):
        for zq in (za - t / 2, zb + t / 2):
            box(mb, fr, xq - 0.2, xq + 0.2, RFS, hw + 0.45, zq - 0.2, zq + 0.2, MAT['white'])    # corner posts
    for xa_, xb_, za_, zb_ in ((wa - 0.05, wa, za, zb), (wb, wb + 0.05, za, zb), (wa, wb, za - 0.05, za), (wa, wb, zb, zb + 0.05)):
        box(mb, fr, xa_, xb_, GF, ROOF, za_, zb_, MAT['white'])   # shaft walls, up to the roof slab round the well (they
        #                                                            ran on into it, and both baked black there)
    box(mb, fr, wa, wb, GF, GF + 0.02, za, zb, MAT['screed'])
    box(mb, fr, xm - 0.09, xm + 0.09, GF, RFS + 0.95, za, zb, MAT['white'])                       # partition
    keep, irng = irng, WELL_RNG
    for f in range(NF):
        y = GF + FH * f
        for xh in ((wa + xm - 0.09) / 2, (xm + 0.09 + wb) / 2):
            if WELL_RNG.random() < 0.5:
                window(mb, fr, xh - 0.3, xh + 0.3, y + 1.2, y + 2.0, za, mull=False, cells=4)
            else:
                window(mb, fr.sub(rot=math.pi), -xh - 0.3, -xh + 0.3, y + 1.2, y + 2.0, -zb, mull=False, cells=4)
    irng = keep


PIL_DONE = set()   # courtyard pilasters built: (row, first layout, row-local x)


def build_block(mb, row, it):
    fr, bw = row['fr'], row['bw']
    x0, x1, n = it['x0'], it['x1'], it['n']
    cols = it['cols']
    rec = it.get('rec', 0.0)   # a recessed corner bay: everything on the street side stands back by rec
    gal = bool(row.get('gallery'))
    sides = {-1: row['outer'], 1: 'court' if gal else 'street'}
    k_it = next(k for k, j in enumerate(row['items']) if j is it)   # ends not against a tower or another block
    open0 = k_it == 0 or row['items'][k_it - 1]['t'] == 'g'
    open1 = k_it == len(row['items']) - 1 or row['items'][k_it + 1]['t'] == 'g'
    zA = (-HZ + 0.3 if sides[-1] == 'street' else -(HZ - ARC)) + rec
    zB = HZ - 0.3 if sides[1] == 'street' else HZ - ARC
    spd = 0.6 if rec else REC  # how far the post office's and the nursery's fronts sit behind their piers

    def side(s):
        sf = side_frame(fr, s)
        return sf.sub(0, 0, -rec) if (s < 0 and rec) else sf
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
            box(mb, fr, x0 + i * bw, x0 + (i + 1) * bw, 0, GF - 0.3, -HZ + rec + spd if sp else zA, zB,
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
        sf = side(s)
        lane = row['id'] == 'nw' and not row.get('first')   # the lane by the sports hall: no shops, plain wall but for the
        #                                                    towers' doors (user, 2026-10-24); the first layout as it was
        for i in range(n):
            xa, xb = X(x0 + i * bw, s), X(x0 + (i + 1) * bw, s)
            xa, xb = min(xa, xb), max(xa, xb)
            sp, sj = special_bay(row, x0 + (i + 0.5) * bw, bw) if s < 0 else (None, None)
            if lane:   # its shutters drawn, not built, so the row's random stream stays in step; no canopy, so no units on it
                box(mb, sf, xa, xb, 0.45, GF - 0.3, HZ - 0.3, HZ - 0.02, MAT['ground'])
                box(mb, sf, xa, xb, 0, 0.45, HZ - 0.3, HZ + 0.02, MAT['hallg'])
                shutter_bay(SCRATCH, sf, xa + 0.32, xb)
                for _ in range(LEDGE_RNG.choice((0, 0, 1, 2, 3))):
                    LEDGE_RNG.uniform(-0.15, 0.15)
                continue
            if sp:
                cm = MAT['hallg'] if sp == 'post' else MAT['white']
                yp = GF - 0.5 if sp == 'post' and rec else GF - 1.05   # the post office's piers run up to its fascia
                box(mb, sf, xa, xa + 0.4, 0, yp, HZ - 0.4, HZ, cm)
                box(mb, sf, xb - 0.4, xb, 0, yp, HZ - 0.4, HZ, cm)
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
                special_front(mb, sf, sp, fa, fb, sj, spd, cols[i])
            elif shop:
                open_shop(mb, sf, shop, fa, fb)
            else:
                shutter_bay(mb, sf, fa, fb)
            door = rec and sp == 'nursery' and sj == 2   # the nursery's own name board and clerestory under its awning
            if not door and not (rec and sp == 'post'):   # the post office's window runs up behind its fascia (MH022)
                box(mb, sf, xa, xb, GF - 1.05, GF - 0.3, HZ - 0.3, HZ, MAT['ground'])
            if rec and sp == 'post' or door:   # the post office: its red fascia, no canopy over it (MH022); the nursery: its awning
                continue
            box(mb, sf, xa, xb, GF - 0.3, GF - 0.14, HZ, HZ + 0.9, MAT['white'])                # canopy ledge
            if row['id'] == 'front':   # globe lamp under the canopy at the pier (photo 22)
                cylv(mb, sf, xa + 0.16, HZ + 0.55, GF - 0.62, GF - 0.3, 0.015, 6, MAT['pole'])
                globe(mb, sf.p(xa + 0.16, GF - 0.78, HZ + 0.55), 0.16, MAT['lamp'])
            nac = LEDGE_RNG.choice((0, 0, 1, 2, 3))
            for k in range(nac):
                xc = xa + (xb - xa) * (k + 0.5 + LEDGE_RNG.uniform(-0.15, 0.15)) / max(nac, 1)
                box(mb, sf, xc - 0.38, xc + 0.38, GF - 0.14, GF + 0.42, HZ - 0.02, HZ + 0.3, MAT['ac'])
                ac_mark(sf, 'split', xc, GF - 0.14, HZ - 0.02)
    # --- courtyard arcade (beam, dado, doors; no red columns under the gallery, user 2026-10-24)
    if sides[1] == 'court':
        box(mb, fr, x0, x1, GF - 0.75, GF - 0.3, HZ - 0.75, HZ - 0.05, MAT['ground'])
        for a, b in segs:
            sx0, sx1 = x0 + a * bw, x0 + b * bw
            box(mb, fr, sx0, sx1, 0, 1.1, zB, zB + 0.03, MAT['dado'])
            for i in range(a, b):
                if rnd.random() < 0.5 and in_court(row, x0 + (i + 0.5) * bw):
                    xm = x0 + (i + 0.5) * bw
                    box(mb, fr, xm - 0.55, xm + 0.55, 0, 2.2, zB, zB + 0.06, MAT['door'])
    # --- first-floor structural slab and roof slab (round the light well's shaft on the big blocks)
    box(mb, fr, x0, x1, GF - 0.3, GF, -HZ + rec, HZ, {'py': MAT['soffit'], 'ny': MAT['soffit'], '*': MAT['white']})
    xm = (x0 + x1) / 2
    well = n >= 4
    wa, wb, wza, wzb = xm - WELL[0], xm + WELL[0], WELL[2] - WELL[1], WELL[2] + WELL[1]
    zs = -HZ + rec
    for a, b, c, d in (((x0, wa, zs, HZ), (wb, x1, zs, HZ), (wa, wb, zs, wza), (wa, wb, wzb, HZ)) if well else ((x0, x1, zs, HZ),)):
        box(mb, fr, a, b, ROOF, RFS, c, d, {'py': MAT['screed'], '*': MAT['white']})
    # --- residential core (back wall of the loggias)
    for i in range(n):
        pm = MAT['plaster'][cols[i]]
        box(mb, fr, x0 + i * bw, x0 + (i + 1) * bw, GF, ROOF, -(HZ - LOG) + rec, ZL if gal else HZ - LOG,
            {'pz': pm, 'nz': pm, '*': pm if row['id'] == 'front' else MAT['white']}, skip=('py', 'ny'))   # avenue row's ends in mosaic (MH022)
    for s in (-1, 1):
        sf = side(s)
        street = sides[s] == 'street'
        f0 = 1 if (gal and s > 0) else 0
        for i in range(n):
            xa, xb = sorted((X(x0 + i * bw, s), X(x0 + (i + 1) * bw, s)))
            w = xb - xa
            if street:
                post_ = bool(rec) and s < 0 and special_bay(row, x0 + (i + 0.5) * bw, bw)[0] == 'post'
                street_bay(mb, sf, xa, xb, i, cols[i], post=post_)
                continue
            if in_court(row, x0 + (i + 0.5) * bw):
                court_bay(mb, sf, xa, xb, i, cols[i])
            elif not row.get('first'):   # (the first layout, drawn for its streams only, had a white wall here)
                passage_bay(mb, sf, xa, xb, i, cols[i])
        if street:   # flush white pilasters between bays instead of the courtyard fins
            for i in range(n + 1):
                xi = X(x0 + i * bw, s)
                box(mb, sf, xi - 0.18, xi + 0.18, GF - 0.3, ROOF + 0.3, ZR, ZW + 0.12, MAT['white'])
        else:        # slim white pilasters standing off the courtyard wall, gallery deck to roof (the end ones within the row),
            #          stepping back above the railing under the top floor to stand only a little proud of it (MH002)
            for i in range(n + 1):
                key = (row['id'], bool(row.get('first')), round(x0 + i * bw, 3))   # once where two blocks meet (a corner
                if (in_court(row, x0 + i * bw) or not row.get('first')) and key not in PIL_DONE:   # bay): built twice, both
                    PIL_DONE.add(key)                                                               # baked black
                    xi = X(x0 + i * bw, s)
                    pa, pb, yh = max(xi - 0.17, 0.01), min(xi + 0.17, row['L'] - 0.01), YT - 1.85
                    box(mb, sf, pa, pb, GF - 0.3, yh, ZL + 0.2, ZC + 0.85, MAT['white'], skip=('py',))
                    prism_x(mb, sf, [(ZL + 0.2, yh), (ZC + 0.85, yh), (ZC + FIN_TOP, YT), (ZL + 0.2, YT)], pa, pb, MAT['white'])
                    box(mb, sf, pa, pb, YT, ROOF + 0.3, ZL + 0.2, ZC + FIN_TOP, MAT['white'], skip=('ny',))   # (MH002)
        # sloped terracotta tile band and its white cap; at an open end the band stops a hair short (the roof slab's end
        # lay in its end's plane and both baked black, user 2026-10-24)
        xa, xb = sorted((X(x0 + 0.01 * open0, s), X(x1 - 0.01 * open1, s)))
        prism_x(mb, sf, [(ZC, ROOF + 0.3), (HZ + 0.95, ROOF + 0.3), (HZ + 0.5, TOP), (ZC, TOP)], xa, xb, MAT['rooftile'])
        xa, xb = sorted((X(x0, s), X(x1, s)))
        box(mb, sf, xa, xb, RFS, TOP, ZC - 0.17, ZC - 0.01, MAT['white'])               # white inner face of the parapet (MH001)
        box(mb, sf, xa, xb, TOP, TOP + 0.12, ZC - 0.17, HZ + 0.6, MAT['white'])
        post = sides[s] == 'court'   # every bay has its own tile cap; the white pilasters run up through the band and, on the
        for i in range(1, n):        # courtyard side only, stand above the parapet as short posts (MH002, MH001)
            xi = X(x0 + i * bw, s)
            box(mb, sf, xi - 0.2, xi + 0.2, ROOF + 0.31, TOP + (0.55 if post else 0.14), ZC - 0.2, HZ + 0.98, MAT['white'])
            #   (their feet just inside the band: in the plane of its underside both baked black)
    # roof (MH001): chunky white vent posts, one per bay near the courtyard side and most bays one near the street side,
    # set at odd places along the bay; a thin red line runs along the roof towards the street side
    vr = random.Random(ROW_SEED[row['id']] * 1000 + int(x0 * 10))
    for i in range(n):
        xa_, xb_ = x0 + i * bw + 0.7, x0 + (i + 1) * bw - 0.7
        posts = [(vr.uniform(xa_, xb_), HZ - 2.4 + vr.uniform(-0.45, 0.3))]                 # courtyard side
        if vr.random() < 0.4:
            posts.append((vr.uniform(xa_, xb_), vr.uniform(0.3, 1.6)))                      # middle
        if vr.random() < 0.3:
            posts.append((vr.uniform(xa_, xb_), -(HZ - 2.4) + rec + vr.uniform(-0.3, 0.45)))     # street side
        for xp, zp in posts:
            if well and wa - 0.5 < xp < wb + 0.5 and wza - 0.5 < zp < wzb + 0.5:
                vr.uniform(1.0, 1.3)   # over the light well: drawn, not built
                continue
            box(mb, fr, xp - 0.28, xp + 0.28, RFS, RFS + vr.uniform(1.0, 1.3), zp - 0.28, zp + 0.28, MAT['white'])
    zl = -0.3 * HZ   # the red line stops at the light well's parapet
    for a, b in ((x0, wa - 0.18), (wb + 0.18, x1)) if well and wza - 0.25 < zl < wzb + 0.25 else ((x0, x1),):
        box(mb, fr, a, b, RFS, RFS + 0.03, zl - 0.06, zl + 0.06, MAT['mred'])
    if well:
        light_well(mb, fr, xm)
    for _ in range(max(1, int((x1 - x0) / 12))):
        xr, zr = irng.uniform(x0 + 1, x1 - 1), irng.uniform(-HZ + 1.2, HZ - 1.2)
        zr = max(zr, -HZ + rec + 1.2)
        if irng.random() < 0.6 and not (well and wa - 0.5 < xr < wb + 0.5 and wza - 0.5 < zr < wzb + 0.5):   # TV aerial mast
            cylv(mb, fr, xr, zr, RFS, RFS + 3.3, 0.03, 6, MAT['pole'])
            for hh, ln in ((RFS + 3.1, 1.2), (RFS + 2.6, 0.9), (RFS + 2.1, 0.7)):
                cylx(mb, fr, xr - ln / 2, xr + ln / 2, hh, zr, 0.012, 4, MAT['pole'])
        # (no stainless tanks: the roofs carry concrete tanks beside the stair towers, MH001; the draw above is kept)
    if rec:   # the street floor runs into the recess; the next bay's white side wall where the frontage steps back
        box(mb, fr, x0, x1, 0, 0.15 if row['id'] == 'front' else 0.05, -HZ, -HZ + rec, {'py': MAT['sidewalk'], '*': MAT['curb']},
            skip=('ny',))
        dn = 1 if x0 < 0.01 else -1   # the recessed bay at the start of the row: its neighbour lies towards +x
        step_wall(mb, fr, x1 if dn > 0 else x0, dn, rec, poster=row['id'] == 'front' and dn < 0)
        xi = x1 if dn > 0 else x0   # its own tile cap: a white post on the courtyard side where it meets the next block (MH001)
        box(mb, fr, xi - 0.2, xi + 0.2, ROOF + 0.31, TOP + 0.55, ZC - 0.2, HZ + 0.98, MAT['white'])
        xe = sorted(((EX0 - fr.o.x) * fr.ex.x, (EX1 - fr.o.x) * fr.ex.x))   # row-local x of the side rows' outer walls
        for a, b in ((x0, min(x1, xe[0])), (max(x0, xe[1]), x1)):          # the part standing out past them: its upper
            if b - a > 0.05:                                                 # floors in the bay's colour (passage_bay),
                box(mb, fr, a + 0.01, b - 0.01, 0, GF - 0.3, HZ - 0.2, HZ + 0.01, MAT['white'])   # the ground floor closed
                #   in white, a hair proud of the arcade's closing block, which lies in its planes (baked black)
                side_cap(SCRATCH, fr, a, b)                                  # (the white cap it had, for STEP_RNG)


STEP_RNG = random.Random(2091)   # the step walls' windows draw from their own stream
PASS_RNG = random.Random(2101)   # and the end rows' faces on the corner passages from theirs


def passage_bay(mb, sf, xa, xb, ib, col):
    """Courtyard-side face of an end-row bay beside a corner passage, or standing out past the side rows: the same as the
    courtyard bays, in the bay's own colour (user, 2026-10-24, with MH001), not the white end wall it had."""
    global irng
    keep, irng = irng, PASS_RNG
    court_bay(mb, sf, xa, xb, ib, col)
    irng = keep


def side_cap(mb, fr, xa, xb):
    """The white cap first built on the part of a corner bay standing out past the side rows (now drawn, not built)."""
    global irng
    box(mb, fr, xa, xb, 0, ROOF + 0.3, HZ - 0.2, HZ, MAT['white'])
    keep, irng = irng, STEP_RNG
    for f in range(NF):
        y = GF + FH * f
        window(mb, fr, (xa + xb) / 2 - 0.3, (xa + xb) / 2 + 0.3, y + 1.15, y + 2.15, HZ, mull=False, cells=4)
    irng = keep


def step_wall(mb, fr, xi, dn, rec, poster=False):
    """White side wall where the street face steps back to a recessed corner bay (photo 21, MH022), at row-local x = xi,
    the recessed bay towards -dn: street line to the recessed face, ground to parapet, a small window on every floor.
    poster: the post office's board on it (MH022)."""
    global irng
    box(mb, fr, xi - 0.2, xi + 0.2, 0, TOP + 0.12, -HZ - 0.05, -HZ + rec, MAT['white'])
    wf = fr.sub(xi - 0.2 * dn, 0, -HZ + rec / 2, rot=-dn * math.pi / 2)   # local z towards the recessed bay
    keep, irng = irng, STEP_RNG
    for f in range(NF):
        y = GF + FH * f
        window(mb, wf, -0.3, 0.3, y + 1.15, y + 2.15, 0.0, mull=False, cells=4)
    irng = keep
    if poster:
        box(mb, wf, -1.2, 1.2, 1.2, 3.0, 0.0, 0.06, MAT['post'])
        box(mb, wf, -1.1, 1.1, 1.3, 2.9, 0.06, 0.08, MAT['signs'][3])


# ------------------------------------------------------------------ stair towers, gables, corners
def end_wall(mb, o, ez, gap=None):
    """White wall across a passage between blocks, facing ez, centred on site point o at ground level: small windows and floor
    bands on every floor (MH001). gap: local x range left open (the slot in front of a corner stair tower)."""
    ez = Vector(ez)
    ef = Fr(Vector(o) + ez * 0.02, tuple(Vector((0, 1, 0)).cross(ez)), tuple(ez))   # 2 cm proud of the block's end face: in
    spans = [(-HZ, gap[0]), (gap[1], HZ)] if gap else [(-HZ, HZ)]                    # its plane both baked black (user, 2026-10-24)
    for a, b in spans:
        box(mb, ef, a, b, GF - 0.3, ROOF, -0.22, 0.0, MAT['white'], skip=('ny',))   # (its back where it was: the end
        #   pilaster's side at -0.18; no underside, which lay in the first-floor slab's)
    for f in range(NF):
        y = GF + FH * f
        for xw in [-(HZ - 1.6) + k * (2 * HZ - 3.2) / 4 for k in range(5)]:
            bars = irng.random() < 0.3
            if gap and gap[0] - 0.7 < xw < gap[1] + 0.7:
                atlas_uv(8)   # in the slot: drawn, not built
                continue
            window(mb, ef, xw - 0.6, xw + 0.6, y + 0.95, y + 2.25, 0.0, bars=bars)
        for a, b in spans:
            box(mb, ef, a, b, y - 0.1, y + 0.08, 0.0, 0.05, MAT['white'])


def gable(mb, fr, w, base):
    """Arched gable facing local +z, front face at z=0, with the fan-light."""
    r = w / 2
    gr = 1.0
    prof = [(-r, base), (r, base), (r, base + gr)] + [(x, y) for x, y in arc(0, base + gr, r, 0, math.pi, 20)[1:-1]] + [(-r, base + gr)]
    prism_z(mb, fr, prof, -0.35, 0.0, MAT['white'])
    rf = r * 0.78
    half = [(x, y) for x, y in arc(0, base + gr, rf, 0, math.pi, 20)]
    mb.poly([fr.p(x, y, 0.01) for x, y in half], MAT['fanglass'])   # glazed (MH005); the dark void baked black (user, 2026-10-24)
    m = MAT['fanred']   # its bars, arcs and frame red-brown (user, 2026-10-24; MH001, MH002, MH005)
    for i in range(11):
        a = math.pi * i / 10
        p0 = fr.p(math.cos(a) * rf * 0.28, base + gr + math.sin(a) * rf * 0.28, 0.05)
        p1 = fr.p(math.cos(a) * rf, base + gr + math.sin(a) * rf, 0.05)
        beam(mb, p0, p1, 0.07, m, up=tuple(fr.ez))
    for k, rr in ((12, rf * 0.6), (20, rf)):   # the middle arc and the frame round the fan
        pts = arc(0, base + gr, rr, 0, math.pi, k)
        for a, b in zip(pts, pts[1:]):
            beam(mb, fr.p(a[0], a[1], 0.05), fr.p(b[0], b[1], 0.05), 0.07 if rr < rf else 0.1, m, up=tuple(fr.ez))
    beam(mb, fr.p(-rf, base + gr, 0.05), fr.p(rf, base + gr, 0.05), 0.1, m, up=tuple(fr.ez))   # and its sill
    hub = [(x, y) for x, y in arc(0, base + gr, rf * 0.28, 0, math.pi, 8)]
    mb.poly([fr.p(x, y, 0.06) for x, y in hub], m)


# 馬交石 (MH078, MH079): a granite boulder carved RAMPA DOS CAVALLEIROS 1847 under a crowned shield, in a niche of dressed
# granite behind and on its left and rubble on its right, fronted by a curved low granite wall with brick coping on its
# right end, red-grey brick paving. First set at the lane's end by the sports hall; it stands in the sunken strip behind
# the back row's 利誠 end instead, against the back street's retaining wall, the 利誠 steps' granite side on its left,
# facing the back of the block (user, 2026-10-24, with a screenshot of the spot): photo 2 sees the lane's end open.
# Given in its own frame (x along the wall, z out of it towards the block)
MKS_FR = Fr((EX1 - 3.45, 0, EZ1 + 3.95), (-1, 0, 0), (0, 0, -1))
MKS = dict(x0=-3.4, x1=3.4, zb=0.0, zf=2.1)


def rock_lobe(mb, c, r, rng, m, zcut=None, seg=14, rings=9, fr=None):
    """Weathered boulder lobe: an ellipsoid with lumpy radii, cut flat at the ground and, if zcut, at a carved front face
    (in frame fr when given)."""
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
            z = min(z, zcut) if zcut is not None else z
            row.append(fr.p(x, y, z) if fr else Vector((x, y, z)))
        pts.append(row)
    for i in range(rings):
        for j in range(seg):
            a, b, cc, d = pts[i][j], pts[i][(j + 1) % seg], pts[i + 1][(j + 1) % seg], pts[i + 1][j]
            mb.poly([a, cc, d] if i == 0 else [a, b, cc] if i == rings - 1 else [a, b, cc, d], m)


def build_makau_stone(mb, f0):
    k = MKS
    x0, x1, zb, zf = k['x0'], k['x1'], k['zb'], k['zf']
    box(mb, f0, x0, x1, 0, 3.6, zb - 0.6, zb, MAT['stone'])                       # dressed granite behind
    box(mb, f0, x0 - 0.6, x0, 0, 3.2, zb - 0.6, zf, MAT['stone'])                 # return on its left
    box(mb, f0, x1, x1 + 0.6, 0, 2.6, zb - 0.6, zf, MAT['rock'])                  # rubble wall on its right
    flat_ = lambda xa, za, xb, zz, y, m: mb.poly([f0.p(xa, y, zz), f0.p(xb, y, zz), f0.p(xb, y, za), f0.p(xa, y, za)], m)
    flat_(x0, zb, x1, zf + 2.6, 0.17, MAT['brickpave'])                           # red-grey brick paving
    flat_(x0 + 0.2, zf + 1.9, x0 + 1.6, zf + 2.25, 0.175, MAT['steel'])            # drain grate
    rng = random.Random(1847)
    xc = (x0 + x1) / 2
    zcut = zf - 0.45
    rock_lobe(mb, (xc + 0.7, -0.3, zb + 0.95), (2.5, 2.7, 1.25), rng, MAT['stone'], zcut=zcut, fr=f0)   # main block, carved
    rock_lobe(mb, (xc - 1.9, -0.4, zb + 1.0), (1.35, 1.9, 1.1), rng, MAT['stone'], fr=f0)              # split-off lobe (MH078)
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
            beam(mb, tuple(f0.p(pa[0], (y0 + y1) / 2, pa[1])), tuple(f0.p(pb[0], (y0 + y1) / 2, pb[1])), 0.34 if m is top_m else 0.3, m,
                 h=y1 - y0)


def joint_kind(row, it):
    """'F' or 'V' (see build_joint): in a row of three towers the middle one is F, the outer two V (side rows, MH001; end
    rows, user 2026-10-23 with MH001); a row with fewer towers has F."""
    js = [i for i in row['items'] if i['t'] == 'j']
    if len(js) == 3 and js.index(it) != 1:
        return 'V'
    return 'F'


TOWER_OUT = 1.15   # how far the street stair towers' side walls stand out past HZ (photo 21 sees them deep, with windows)
# A galleried tower's stair core stands in the middle of the block's depth, with an open slot between the two blocks on
# either side of it, alike in size: a platform at gallery level in each, open to the sky (user, 2026-10-23). The courtyard
# platform, floored in cream and green bands, runs on into the gallery (MH010); the street one ends in a black railing
# above the residents' gated door under its half-round hood (MH005, MH007, photo 21, user photo). Small windows in the
# slot walls (MH018). Core ~8.5 m deep, like the stair rooms on the roofs in MH001. The barrel vaults' fan windows face the
# courtyard in the side rows and the street in the end rows (MH001). The hillside row's tower is the estate's too, a street
# one on both its faces (user, 2026-10-24: the same design as the estate; MH068 sees a plainer white wall there)
PLAT = 4.25
SLOT_RNG = random.Random(2061)   # the slot walls' windows draw from their own stream


PLAT_EDGE = 0.35   # the green strip along both walls of a platform (MH010)


def platform(mb, sf, ia, ib, za, zb):
    """Gallery-level platform from za to zb (side frame), floored in cream and green cross bands inside a green strip
    along both walls (MH010; user, 2026-10-24)."""
    box(mb, sf, ia, ib, GF - 0.3, GF - 0.02, za, zb, {'ny': MAT['soffit'], '*': MAT['white']}, skip=('py',))
    e = PLAT_EDGE
    for a, b in ((ia, ia + e), (ib - e, ib)):
        box(mb, sf, a, b, GF - 0.02, GF, za, zb, {'py': MAT['tilegreen']}, skip=('ny',))
    z, k = za, 0
    while z < zb - 0.01:
        dz = min(1.1 if k % 2 == 0 else 0.55, zb - z)
        box(mb, sf, ia + e, ib - e, GF - 0.02, GF, z, z + dz, {'py': MAT['tilecream'] if k % 2 == 0 else MAT['tilegreen']},
            skip=('ny',))
        z, k = z + dz, k + 1


def slot_windows(mb, sf, ia, ib, zs):
    """Small windows in both walls of a slot, at the depths zs (side frame), drawn from SLOT_RNG."""
    global irng
    keep, irng = irng, SLOT_RNG
    for f in range(NF):
        y = GF + FH * f
        for xw, rot in ((ia, math.pi / 2), (ib, -math.pi / 2)):
            for zw in zs:
                if SLOT_RNG.random() < 0.6:
                    window(mb, sf.sub(xw, 0, zw, rot=rot), -0.3, 0.3, y + 1.15, y + 2.15, 0.0, mull=False, cells=4)
    irng = keep


def build_joint(mb, row, it):
    fr = row['fr']
    x0, x1 = it['x0'], it['x1']
    w, xc, zr = x1 - x0, (it['x0'] + it['x1']) / 2, HZ - 0.6
    zk = HZ - PLAT   # either face of the stair core (side frames)
    jsides = {-1: row['outer'], 1: 'court' if row.get('gallery') else 'street'}
    box(mb, fr, x0, x1, 0, GF - 0.3, -zr, zr, MAT['white'], skip=('py',))
    for s in (-1, 1):   # lobby entrance with metal gate, the residents' door (user photo)
        sf = side_frame(fr, s)
        xl = X(xc, s)
        low = jsides[s] == 'street'   # under the street platform: its hood just below it, the number beside it
        gh = 2.0 if low else 2.6
        box(mb, sf, xl - 1.1, xl + 1.1, 0, gh, zr, zr + 0.02, MAT['void'])
        for k in range(12):
            xx = xl - 1.05 + k * 0.19
            box(mb, sf, xx - 0.015, xx + 0.015, 0, gh, zr + 0.05, zr + 0.08, MAT['gate'])
        box(mb, sf, xl - 1.1, xl + 1.1, gh - 1.1, gh - 1.04, zr + 0.04, zr + 0.09, MAT['gate'])
        if low:
            box(mb, sf, xl + 1.15, xl + 1.55, 1.7, 2.1, zr, zr + 0.05, MAT['signs'][4])
        else:
            box(mb, sf, xl - 0.5, xl + 0.5, 2.85, 3.25, zr, zr + 0.05, MAT['signs'][4])
    zwell = zk - 1.6   # back of the open courtyard stair well
    box(mb, fr, x0 + 0.4, x1 - 0.4, GF - 0.3, TOP - 0.3, -(zk - 1.88), zwell if jsides[1] == 'court' else zk - 1.88,
        MAT['void'], skip=('ny', 'py'))
    box(mb, fr, x0 + 0.4, x1 - 0.4, TOP - 0.3, TOP, -zk, zk, {'py': MAT['screed'], '*': MAT['white']})   # between the side
    for s in (-1, 1):                                       # walls (in their planes it baked black, user 2026-10-24); the
        sf = side_frame(fr, s)                              # bands under it at either face stop at its underside
        xa, xb = sorted((X(x0, s), X(x1, s)))
        if jsides[s] == 'street':
            prism_z(mb, sf, arc(X(xc, s), GF - 1.75, 1.45, 0, math.pi, 16), HZ - 0.4, HZ + TOWER_OUT + 0.25,
                    MAT['white'])                                                                    # lobby hood
            ia, ib = xa + 0.55, xb - 0.55   # white side walls well proud of the facade, the slot between them
            zt = HZ + TOWER_OUT
            for wa, wb in ((xa - 0.05, ia), (ib, xb + 0.05)):
                box(mb, sf, wa, wb, GF - 0.3, TOP + 0.6, zk, zt, MAT['whitetile'])
            for f in range(NF):   # small windows in the side walls where they stand out of the facade (photo 21, MH018)
                y = GF + FH * f
                for xw, rot in ((xa - 0.05, -math.pi / 2), (xb + 0.05, math.pi / 2)):
                    window(mb, sf.sub(xw, 0, zt - 0.55, rot=rot), -0.22, 0.22, y + 1.5, y + 2.1, 0.0, mull=False, cells=4)
            box(mb, sf, ia, ib, GF - 0.3, ROOF - 0.1, zk - 1.9, zk - 1.86, MAT['soffit'])         # back of the stair well
            for f in range(NF):   # the core's street face: half landings behind breeze-block screens (MH005, MH007)
                yl = GF + FH * f + FH / 2   # half landing
                box(mb, sf, ia, ib, yl - 0.15, yl, zk - 1.86, zk, MAT['white'])                    # landing slab edge
                box(mb, sf, ia, ib, yl, min(yl + 1.35, ROOF - 0.1), zk - 0.1, zk - 0.02, MAT['breeze'])   # breeze screen
                prism_z(mb, sf, [(ia + 0.05, yl - FH / 2 - 0.3), (ib - 0.05, yl - 0.2), (ib - 0.05, yl - 0.02), (ia + 0.05, yl - FH / 2 - 0.12)],
                        zk - 1.86, zk - 0.2, MAT['soffit'])                                         # flight up to it
            box(mb, sf, ia, ib, ROOF - 0.1, TOP - 0.3, zk - 0.4, zk, MAT['white'])
            platform(mb, sf, ia, ib, zk, zt)
            platform(mb, sf, ia, ib, zk - 1.86, zk)   # and the floor of the stair behind it, which was missing (user, 2026-10-24)
            railing_run(mb, sf, ia, ib, GF, zt - 0.1, MAT['bars'])
            slot_windows(mb, sf, ia, ib, (zk + 1.2, HZ - 0.6))
            continue
        ia, ib = xa + 0.4, xb - 0.4
        for f in range(NF):   # the core's courtyard face: open landings onto the platform
            y = GF + FH * f
            box(mb, sf, ia, ib, y - 0.3, y + 0.02, zwell, zk + 0.06, {'py': MAT['deck'], '*': MAT['white']})   # landing
            if f > 0:   # the first-floor landing runs on into the platform
                for hh in (0.6, 1.02):
                    cylx(mb, sf, ia, ib, y + hh, zk - 0.02, 0.03, 8, MAT['creampipe'])
                for xp in (ia + 0.05, (ia + ib) / 2, ib - 0.05):
                    cylv(mb, sf, xp, zk - 0.02, y + 0.02, y + 1.04, 0.025, 6, MAT['creampipe'])
            if f < NF - 1:
                box(mb, sf, ia + 0.5, ib - 0.5, y + 0.45, y + FH - 0.45, zwell, zwell + 0.06, MAT['breeze'])   # back wall
                prism_z(mb, sf, [(ia + 0.05, y - 0.15), (ib - 0.05, y + FH - 0.45), (ib - 0.05, y + FH - 0.3), (ia + 0.05, y + 0.02)],
                        zwell + 0.08, zk - 0.6, MAT['soffit'])                                      # flight
        for xp in (ia + 0.15, ib - 0.15):   # downpipes on the walls beside the landings
            cylv(mb, sf, xp, zk + 0.3, GF, ROOF, 0.05, 8, MAT['white'])
        box(mb, sf, ia, ib, ROOF - 0.1, TOP - 0.3, zk - 0.4, zk + 0.06, MAT['white'])
        platform(mb, sf, ia, ib, zk + 0.06, HZ)
        slot_windows(mb, sf, ia, ib, (zk + 1.2, HZ - 1.2))
    for xe in (x0, x1 - 0.4):
        box(mb, fr, xe, xe + 0.4, 0, TOP, -(HZ + 0.15), HZ + 0.15, MAT['whitetile'])
    zh = zk - 0.35   # ends of the stair room (behind the gables)
    kind = joint_kind(row, it)
    vface = -1 if row['id'] in ('front', 'back') else 1   # side of a barrel vault's fan window
    if kind == 'V':
        za_, zb_ = (-zk + 0.02, zh) if vface > 0 else (-zh, zk - 0.02)   # its plain end just behind the low wall's face
        box(mb, fr, xc - 1.5, xc + 1.5, TOP, TOP + 1.0, za_, zb_, MAT['white'], skip=('py',))
        prism_z(mb, fr, arc(xc, TOP + 1.0, 1.5, 0, math.pi, 16), za_, zb_, MAT['white'])   # barrel vault across the core
        zm = (za_ + zb_) / 2
        for sx in (-1, 1):
            wf = fr.sub(xc + sx * 1.5, 0, 0, rot=sx * math.pi / 2)
            box(mb, wf, -sx * zm - 0.4, -sx * zm + 0.4, TOP, TOP + 1.9, 0.0, 0.03, MAT['void'])   # doorway onto the roof
        za_w, zb_w = (zk - 0.2, zk) if vface < 0 else (-zk, -zk + 0.2)   # low wall across the top at the vault's plain end
        box(mb, fr, x0 + 0.1, x1 - 0.1, TOP, TOP + 0.8, za_w, zb_w, MAT['white'])
    else:
        box(mb, fr, xc - 1.6, xc + 1.6, TOP, TOP + 2.3, -zh, zh, {'py': MAT['screed'], '*': MAT['white']})   # flat stair room
        box(mb, fr, xc - 1.7, xc + 1.7, TOP + 2.3, TOP + 2.42, -zh - 0.05, zh + 0.05, MAT['white'], skip=('ny',))
        for sx in (-1, 1):
            wf = fr.sub(xc + sx * 1.6, 0, 0, rot=sx * math.pi / 2)                            # faces +-x
            for zw in (-zh + 0.7, zh - 0.7):
                box(mb, wf, -sx * zw - 0.25, -sx * zw + 0.25, TOP + 1.25, TOP + 1.85, 0.0, 0.03, MAT['void'])   # small windows
            box(mb, wf, -0.4, 0.4, TOP, TOP + 1.95, 0.0, 0.03, MAT['void'])                     # doorway
    for xw in (x0 + 0.1, x1 - 0.3):   # low white walls along the tower top, posts standing above them
        box(mb, fr, xw, xw + 0.2, TOP, TOP + 0.8, -zk, zk, MAT['white'])
        zp = -zk + 0.15
        while zp < zk:
            box(mb, fr, xw - 0.08, xw + 0.28, TOP, TOP + 1.3, zp - 0.18, zp + 0.18, MAT['white'])
            zp += 1.55
    for s in (-1, 1):
        if kind == 'V' and s != vface:   # the vault ends plain on its other side
            continue
        sf = side_frame(fr, s)
        gable(mb, sf.sub(X(xc, s), 0, zk), w, TOP)


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
    for xg, side in ((NWG - 0.11, 1), (SEG + 0.11, -1)):   # gaps for the bridge and the stairs' upper flights
        zrun(mb, xg, GZ0, GZ1, GF, [(BRIDGE_Z - 2.0, BRIDGE_Z + 2.0)] + [stair_flight_z(z, side) for z in STAIRS])
    for x in (NWG - 0.4, SEG + 0.4):   # the gallery is cantilevered: red columns down to the ground only at its inner
        for z in (GZ0 - 0.4, GZ1 + 0.4):   # corners, the bridges and the stairs (user, 2026-10-24; MH024, photo 10)
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


def stair_flight_z(zc, side):
    """z range of the upper flight (the one that meets the gallery deck). The four stairs are one design turned to face
    the courtyard: seen from it, the upper flight is on the left, so towards the back street on the north-west side
    (side = +1) and towards the avenue on the south-east side (photo 14's back pair, photo 10's front stair, user
    2026-10-24)."""
    d = side
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
    ua, ub = stair_flight_z(zc, side)                   # upper flight
    d = -side                                           # lower flight sits on the other side of zc
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
    # the inner rails joined up, no post at the foot (user, 2026-10-24): a bar down to the bottom tread, and round the
    # turn at the landing from one flight's rails to the other's
    beam(mb, (x_edge + side * 0.6, 0.16, zm + d * 0.1), (x_edge + side * 0.6, 1.33, zm + d * 0.1), 0.04, MAT['creampipe'])
    beam(mb, (x_land, GF / 2, zm - d * 0.1), (x_land, GF / 2 + 1.07, zm - d * 0.1), 0.04, MAT['creampipe'])
    beam(mb, (x_land, GF / 2, zm + d * 0.1), (x_land, GF / 2 + 1.07, zm + d * 0.1), 0.04, MAT['creampipe'])
    for h in (0.3, 0.55, 0.8, 1.05):
        beam(mb, (x_land, GF / 2 + h, zm - 0.12), (x_land, GF / 2 + h, zm + 0.12), 0.04, MAT['creampipe'])
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


def lib_window(mb, fr, xa, xb, ya, yb, tiers=None):
    """One library pane in a dark aluminium frame. tiers = (top, bottom) shares of a three-part window: a short top light,
    one tall middle pane and a short bottom pane, split by two transoms only (user, 2026-10-23: the bright line across
    the middle of the panes in MH034 is the reading-room lighting, not a frame). None: a single pane."""
    t, d, m = 0.05, 0.08, MAT['bars']
    box(mb, fr, xa, xb, ya - t, ya, 0.0, d, m)
    box(mb, fr, xa, xb, yb, yb + t, 0.0, d, m)
    box(mb, fr, xa, xa + t, ya, yb, 0.0, d, m)
    box(mb, fr, xb - t, xb, ya, yb, 0.0, d, m)
    if tiers:
        for yt in (yb - (yb - ya) * tiers[0], ya + (yb - ya) * tiers[1]):
            box(mb, fr, xa + t, xb - t, yt - t / 2, yt + t / 2, 0.0, d * 0.8, m)
    mb.poly([fr.p(xa, ya, 0.02), fr.p(xb, ya, 0.02), fr.p(xb, yb, 0.02), fr.p(xa, yb, 0.02)], MAT['lglass'],
            uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])


def lib_glass(mb, fr, ln, y0, y1, ya, yb, tiers=None, door=None):
    """Glazed wall from y0 to y1 along a frame of (pre-scale) length ln: panes ~LIB['bay'] apart from ya to yb on a cream
    sill, a cream strip above. door: index of the pane (from the left, seen from outside) that is a glass door down to
    y0, under the same top light."""
    n = max(1, round(ln * LIB_S / LIB['bay']))
    w = ln / n
    for j in range(n):
        xa, xb = -ln / 2 + j * w, -ln / 2 + (j + 1) * w
        if j == door:
            yt = yb - (yb - ya) * tiers[0]
            lib_window(mb, fr, xa, xb, yt, yb)
            lib_window(mb, fr, xa, xb, y0 + 0.02, yt - 0.05)
            continue
        box(mb, fr, xa, xb, y0, ya, -0.15, 0.0, MAT['lcream'])
        lib_window(mb, fr, xa, xb, ya, yb, tiers)
    box(mb, fr, -ln / 2, ln / 2, yb, y1, -0.15, 0.0, MAT['lcream'])


def lib_band_panel(mb, fr, ln, y0, y1):
    """The sunk panel outline on the cream band (MH034): grooves down both ends and along the bottom, stepped at the
    bottom corners; the top runs out at the band's upper edge."""
    m, g, d = MAT['soffit'], 0.04, 0.012
    xa, xb, ya, yt = -ln / 2 + 0.3, ln / 2 - 0.3, y0 + 0.2, y1 - 0.12
    for s_, x_ in ((1, xa), (-1, xb)):
        box(mb, fr, min(x_, x_ + s_ * g), max(x_, x_ + s_ * g), ya + 0.14, yt, 0.0, d, m)
        x2 = x_ + s_ * 0.16
        box(mb, fr, min(x_, x2), max(x_, x2), ya + 0.14, ya + 0.14 + g, 0.0, d, m)
        box(mb, fr, min(x2, x2 + s_ * g), max(x2, x2 + s_ * g), ya, ya + 0.14 + g, 0.0, d, m)
    box(mb, fr, xa + 0.16, xb - 0.16, ya, ya + g, 0.0, d, m)


def build_library(mb):
    lf = Fr((LIB_X, 0, LIB_Z))
    L = LIB
    f0_, f1_ = L['fascia']
    l2, (l3a, l3) = GF, L['l3']           # first floor level with the galleries and bridges; top floor slab
    T3 = (0.15, 0.19)                     # three-part windows: shares of the top light and the bottom pane (MH034)

    def jut(p):   # the three back faces are moved this far towards the back street
        return p[0], p[1] + L['jut']
    slab = [oct_corner(L['slab'], k) for k in range(8)]
    outline = [jut(slab[6]), jut(slab[7]), jut(slab[0]), jut(slab[1])] + slab[1:7]   # octagon with the jut, from its NW end
    # ground floor: yellow tile on the octagon over a dark green plinth, a band of windows under the first-floor slab
    cylv(mb, lf, 0, 0, 0, L['plinth'], L['wall'] + 0.15, 8, MAT['lgreend'], phase=OCT)
    cylv(mb, lf, 0, 0, L['plinth'], l2 - 0.3, L['wall'], 8, MAT['lyellow'], phase=OCT, caps=False)
    for k in range(8):
        ff = face_frame(lf, k, L['wall'] * math.cos(OCT))
        ln = 2 * L['wall'] * math.sin(OCT)
        n = round(ln * LIB_S / L['bay'])
        for j in range(n):
            xa, xb = -ln / 2 + j * ln / n, -ln / 2 + (j + 1) * ln / n
            lib_window(mb, ff, xa + 0.04, xb - 0.04, *L['l1_win'])
            if k == 6 and 1 <= j <= 3:   # entrance under the north-west bridge (MH034): glazed, the doors in the middle
                lib_window(mb, ff, xa + 0.04, xb - 0.04, L['plinth'] + 0.02, 2.4, None if j == 2 else (0.0, 0.3))
        if k == 6:   # the dark board by the entrance (MH034)
            box(mb, ff, -ln / 2 + 0.45, -ln / 2 + 1.5, 1.4, 2.0, 0.0, 0.06, MAT['lsign'])
    # first floor: the slab with the jut, a walkway round the court side, the reading room on the back half and the jut
    lib_slab(mb, lf, outline, l2 - 0.3, l2, MAT['deck'], MAT['soffit'], MAT['lcream'])
    wall = [oct_corner(L['wall'], k) for k in range(8)]
    room = [jut(wall[6]), jut(wall[7]), jut(wall[0]), jut(wall[1]), wall[1]]
    room += [oct_corner(L['inner'], k) for k in range(1, 7)] + [wall[6]]
    for i, (a, b) in enumerate(zip(room, room[1:] + room[:1])):
        fr, ln = lib_seg(lf, a, b)
        if i in (4, 10):   # where the room steps in from the octagon to the walkway: solid
            box(mb, fr, -ln / 2, ln / 2, l2, l3a, -0.2, 0.0, MAT['lcream'])
        else:   # windows the top floor's size under the same head, wall below: the jut (user, 2026-10-24), and the faces
            yb = L['l2_win'][1]   # the bridges and the walkway look at as well (user, 2026-10-24: wall all round below them)
            lib_glass(mb, fr, ln, l2, l3a, yb - (L['l3_win'][1] - L['l3_win'][0]), yb, tiers=T3)
    # top floor: slab with the balcony, a cream band with a sunk panel round the slab edge (the balcony parapet round the
    # jut), the glass behind and above it
    lib_slab(mb, lf, outline, l3a, l3, MAT['deck'], MAT['soffit'], MAT['lcream'])
    for i, (a, b) in enumerate(zip(outline, outline[1:] + outline[:1])):
        fr, ln = lib_seg(lf, a, b)
        box(mb, fr, -ln / 2, ln / 2, l3a + 0.015, L['band'], -0.25, 0.015, MAT['lcream'])   # a hair proud of the slab's edge and
        if ln * LIB_S > 2.0:                                                                   # up from its underside: in their
            lib_band_panel(mb, fr.sub(0, 0, 0.015), ln, l3a, L['band'])                        # planes both baked black (user)
        if i in (0, 1, 2, 3, 9):   # balcony railing round the jut (MH034)
            for y_ in (L['band'] + 0.32, L['band'] + 0.05):
                box(mb, fr, -ln / 2, ln / 2, y_, y_ + 0.05, -0.15, -0.1, MAT['creampipe'])
            for j in range(int(ln / 1.6) + 1):
                xp = -ln / 2 + 0.05 + j * (ln - 0.1) / int(ln / 1.6)
                box(mb, fr, xp - 0.04, xp + 0.04, L['band'], L['band'] + 0.37, -0.15, -0.1, MAT['creampipe'])
    xs0, xs1 = wall[7][0] + 0.1, wall[0][0] - 0.1   # the balcony's middle part: bands of paler and darker tile (MH001)
    zs0, zs1 = wall[0][1] + 0.02, jut(slab[0])[1] - 0.27
    for j in range(15):
        xa, xb = xs0 + j * (xs1 - xs0) / 15, xs0 + (j + 1) * (xs1 - xs0) / 15
        mb.poly([lf.p(xa, l3 + 0.01, zs1), lf.p(xb, l3 + 0.01, zs1), lf.p(xb, l3 + 0.01, zs0), lf.p(xa, l3 + 0.01, zs0)],
                MAT['tilecream'] if j % 2 == 0 else MAT['dado'])
    for k in range(8):   # the second pane from the left on the north-west back face is the balcony door (user)
        ff = face_frame(lf, k, L['wall'] * math.cos(OCT))
        lib_glass(mb, ff, 2 * L['wall'] * math.sin(OCT), l3, f0_, *L['l3_win'], tiers=T3, door=1 if k == 7 else None)
    # roof: octagonal pyramid (~18 degrees, MH035) with standing seams and ridge caps over the top floor and the column ring
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
    # first-floor planter ring along the walkway, a dark handrail on posts behind it (MH034); the shared random stream is
    # drawn as before (two planters fewer than the old ring, whose back faces are now the reading room)
    for k in range(8):
        if k in (2, 6):   # the bridges arrive here
            continue
        if k not in (3, 4, 5):
            for _ in range(20):
                rnd.random()
            continue
        fp = face_frame(lf, k, L['slab'] * math.cos(OCT) - 0.3)
        e = 2 * (L['slab'] * math.cos(OCT) - 0.3) * math.tan(OCT) - 0.75
        box(mb, fp, -e / 2, e / 2, l2, l2 + 0.55, -0.25, 0.25, MAT['lcream'])
        box(mb, fp, -e / 2 + 0.1, e / 2 - 0.1, l2 + 0.42, l2 + 0.5, -0.15, 0.15, MAT['soil'])
        box(mb, fp, -e / 2, e / 2, l2 + 1.0, l2 + 1.05, -0.32, -0.26, MAT['balrail'])
        for j in range(5):
            xp = -e / 2 + 0.1 + j * (e - 0.2) / 4
            box(mb, fp, xp - 0.03, xp + 0.03, l2 + 0.55, l2 + 1.0, -0.31, -0.27, MAT['balrail'])
        for j in range(10):
            t = (j / 9 - 0.5) * (e - 0.6)
            c = fp.p(t, l2 + 0.5, 0.05)
            SHRUBS.append(dict(p=[c[0], c[1], c[2]], s=0.45 + 0.2 * rnd.random(), bouga=rnd.random() < 0.45))
    # red mosaic columns: the ring from the ground to the fascia, and four under the jut's outer corners to its parapet
    for k in range(8):
        cylv(mb, lf, *oct_corner(L['col'], k), 0, f0_, 0.36, 16, MAT['mred'])
    for k in (6, 7, 0, 1):
        cylv(mb, lf, *jut(oct_corner(L['col'], k)), 0, L['band'] - 0.015, 0.36, 16, MAT['mred'])   # (tops under the band's)


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
    # 龜池 (residents' memory) between the cage and the library, 3 m nearer the bridge than first put (user, 2026-10-24)
    pond = (LX - 12, LZ - 11)
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
    for i, spec in enumerate(PLANTERS):
        if i in PLANTERS_GONE:
            n_sh, n_tr = len(SHRUBS), len(YOUNG_TREES)
            planter_seat(SCRATCH, *spec)
            del SHRUBS[n_sh:]
            YOUNG_TREES[n_tr:] = [None] * (len(YOUNG_TREES) - n_tr)   # keeps the other trees' species
            continue
        planter_seat(mb, *spec)
    planter_seat(mb, *BEHIND_PLAY, rng=random.Random(4401))
    for (x, z) in DISCS:
        dfr = Fr((LX + x, 0, LZ + z))
        cylv(mb, dfr, 0, 0, 0, 0.06, 0.85, 20, MAT['bench'])
        cylv(mb, dfr, 0, 0, 0.06, 0.08, 0.72, 20, MAT['disc'], caps=True)
        for k in range(5):
            a = k * 1.256
            SHRUBS.append(dict(p=[LX + x + math.cos(a) * 0.4, 0.08, LZ + z + math.sin(a) * 0.4], s=0.28, bouga=False))
    # big four-legged stone benches under the bridges (photo 14), the only ones in the courtyard (user, 2026-10-24)
    for xs in (-1, 1):   # four per side: two rows of two under each bridge (user)
        for dx, dz in ((10.2, -1.9), (15.5, -1.9), (10.2, 1.9), (15.5, 1.9)):   # at the bridge's edges (MH024)
            bf = Fr((LX + xs * dx, 0, BRIDGE_Z + dz))
            box(mb, bf, -1.15, 1.15, 0.34, 0.46, -0.35, 0.35, MAT['bench'])
            for ex in (-0.9, 0.9):
                for ez in (-0.22, 0.22):
                    box(mb, bf, ex - 0.1, ex + 0.1, 0, 0.34, ez - 0.1, ez + 0.1, MAT['bench'])
    for (x, z) in LAMPS:
        lp = Fr((LX + x, 0, LZ + z))
        cylv(mb, lp, 0, 0, 0, 3.2, 0.07, 10, MAT['steel'], r1=0.05)
        sphere(mb, lp.p(0, 3.45, 0), 0.26, MAT['lamp'])


# planter seats: (x, z from the courtyard centre LX, LZ, kind, length, width, rotation deg about y, tree?, second
# length) — 'L': two arms from its outer corner at (x, z), along local x (length) and local z (second length), a stone
# seat along both inner sides; 'R': a box centred there. Every seat is the same L, but for the long one in front of the
# playground (and the one behind its sandpit, gone by 2010), one arm longer (user, 2026-10-24, with MH024). The half on
# the playground's side as MH024 has it (tools/camsolve_mh024.py, 2026-10-24): the two chevrons behind the library at
# +-5.8 m; the tree planters either side, their corner towards the side gallery and open towards the middle, the second
# arm at the end the user marked; the long one's short arm at its library end, open the same way. The ball court's half
# is the same turned about the library, less what the cage stands on (user, 2026-10-24: the estate is symmetric; the
# court was laid over that half's middle); a seat reaching into the cage would be pushed out sideways (none does).
# Kept from the user's 2010 account (2026-10-23, MH001): the chevrons turned round to open away from the library, the
# long planter where MH001 has it, the planters either side of the playground's far end gone back with it (END_SHIFT),
# the one behind its sandpit gone (left out, drawn into the scratch mesh so the random stream stays in step)
_BACK = [(-5.8, 11.8, 'L', 4.4, 1.6, 315, True, 4.4), (5.8, 11.8, 'L', 4.4, 1.6, 315, True, 4.4),   # behind the library
         (-15.25, 20.6, 'L', 4.4, 1.6, 45, True, 4.4), (15.25, 20.6, 'L', 4.4, 1.6, 225, True, 4.4),   # tree planters
         (-4.46, 22.58, 'L', 4.4, 1.6, 48, True, 7.6),                            # in front of the playground, the long one
         (-2.6, 37.0, 'R', 6.8, 2.6, 45, True, 6.8),                              # behind its sandpit (gone by 2010)
         (-14.43, 34.76 + END_SHIFT, 'L', 4.4, 1.6, 45, True, 4.4), (14.43, 34.76 + END_SHIFT, 'L', 4.4, 1.6, 225, True, 4.4)]


def under_cage(x, z):
    """True if the point (from the courtyard centre) lies inside the ball court's cage."""
    return CAGE['x0'] < LX + x < CAGE['x1'] and CAGE['z0'] < LZ + z < CAGE['z1']


def seat_outline(x, z, kind, ln, w, rot, tree, ln2):
    """Plan corners (from the courtyard centre) of a planter seat's boxes."""
    c, s_ = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    arms = [(-ln / 2, ln / 2, -w / 2, w / 2)] if kind == 'R' else [(0.0, ln, 0.0, w), (0.0, w, 0.0, ln2)]
    return [(x + u * c + v * s_, z - u * s_ + v * c) for (a, b, c0, d) in arms for u in (a, b) for v in (c0, d)]


def mirrored(spec):
    """The seat turned about the library onto the ball court's half, pushed out sideways clear of the cage."""
    x, z, k, ln, w, r, t, ln2 = spec
    m = (x, -z, k, ln2, w, 90 - r, t, ln) if k == 'L' else (x, -z, k, ln, w, -r, t, ln2)
    if under_cage(m[0], m[1]):
        return None
    while any(under_cage(px, pz) for px, pz in seat_outline(*m)):
        m = (m[0] + (0.25 if m[0] > 0 else -0.25),) + m[1:]
    return m


PLANTERS = _BACK + [m for m in map(mirrored, _BACK) if m]
PLANTERS_GONE = {5}
# and one more long L behind the playground (user, 2026-10-24: part of it under the corridor, no column there), turned
# 90 degrees from the first try (user, 2026-10-24): its corner under the back gallery, both arms out towards the
# playground and the seats in its crook facing it; set aside from the middle tower's door and the tree planter beside it,
# clear of the rubber, no tree; its plants on a stream of their own
BEHIND_PLAY = (-5.0, 51.3, 'L', 7.6, 1.6, 132, False, 4.4)
_DISCS = [(-6.0, 20.6), (6.0, 20.6), (-11.95, 8.6), (11.95, 8.6)]   # MH024
DISCS = _DISCS + [(x, -6.9 if z == 8.6 else -z) for x, z in _DISCS if not under_cage(x, -z)]   # (the pair by the pond 1.7 m nearer the bridge)
LAMPS = [(9.0, 13.0), (-6.4, -9.4), (-10.6, -25.0), (10.6, -25.0)]   # the one at (-1.5, 36.4) stood in the moved playground, gone by 2010


def planter_seat(mb, x, z, kind, ln, w, rot, tree, ln2=None, rng=None):
    """Raised planter (brown-red tile walls, soil, shrubs, a young tree) with a stone seat ledge: along one side of a box,
    along both inner sides of an L. rng: the stream its shrubs and tree draw from (the shared one by default)."""
    rng = rng or rnd
    fr = Fr((LX + x, 0, LZ + z)).sub(rot=math.radians(rot))
    ln2 = ln if ln2 is None else ln2
    arms = [(-ln / 2, ln / 2, -w / 2, w / 2)] if kind == 'R' else [(0.0, ln, 0.0, w), (0.0, w, 0.0, ln2)]
    for (a, b, c, d) in arms:
        box(mb, fr, a, b, 0, 0.62, c, d, {'py': MAT['soil'], '*': MAT['ptile']})
        box(mb, fr, a - 0.04, b + 0.04, 0.62, 0.68, c - 0.04, d + 0.04, MAT['bench'], skip=('ny',))
        box(mb, fr, a + 0.12, b - 0.12, 0.66, 0.7, c + 0.12, d - 0.12, MAT['soil'])
    if kind == 'R':
        a, b, c, d = arms[0]
        box(mb, fr, a, b, 0, 0.42, d, d + 0.45, {'py': MAT['bench'], '*': MAT['bench']})     # seat ledge
    else:
        box(mb, fr, w, ln, 0, 0.42, w, w + 0.45, MAT['bench'])                              # seat ledges in the inner corner
        box(mb, fr, w, w + 0.45, 0, 0.42, w + 0.45, ln2, MAT['bench'])
    for (a, b, c, d) in arms:   # shrubs along each arm
        along = (b - a) >= (d - c)
        nx = max(1, int(((b - a) if along else (d - c)) / 0.9))
        for k in range(nx):
            t = (k + 0.5) / nx
            c0 = fr.p(a + t * (b - a), 0.7, (c + d) / 2) if along else fr.p((a + b) / 2, 0.7, c + t * (d - c))
            SHRUBS.append(dict(p=[c0[0], c0[1], c0[2]], s=0.45 + 0.15 * rng.random(), bouga=rng.random() < 0.25))
    if tree:   # in the box's middle, an L's corner
        c0 = fr.p(0, 0.7, 0) if kind == 'R' else fr.p(w / 2, 0.7, w / 2)
        YOUNG_TREES.append((c0[0], c0[2], 0.9 + 0.3 * rng.random()))


YOUNG_TREES = []


def ladder_bars(mb, fr, prof, half=0.3, rung=0.3, m=None):
    """Climbing bars in fr's x-y plane: two rails half either side (local z) along the profile [(u, v), ...], rungs
    across them every rung metres along it."""
    m = m or MAT['lamppole']
    for side in (-half, half):
        for (u0, v0), (u1, v1) in zip(prof, prof[1:]):
            beam(mb, fr.p(u0, v0, side), fr.p(u1, v1, side), 0.03, m)
    run = 0.0
    for (u0, v0), (u1, v1) in zip(prof, prof[1:]):
        seg = math.hypot(u1 - u0, v1 - v0)
        while run <= seg:
            t = run / seg
            pa = fr.p(u0 + t * (u1 - u0), v0 + t * (v1 - v0), 0.0)
            beam(mb, pa - fr.ez * half, pa + fr.ez * half, 0.018, m)
            run += rung
        run -= seg


def build_playground(mb):
    """Playground: the frames of MH024 (1988; the user, 2026-10-24: model what that photo shows), still there in 2008-10
    (photo 1) but standing on black rubber safety tiles inside a timber edging, the sandpit tiled over too. Round the old
    sandpit (4.4 m, set square to the paving's diagonal grid) a rail on blue posts, its top rail yellow; at its left
    corner a stack of tyres on blue legs; on its library side a climbing frame (a ladder up, bars across, an arc down);
    from its right corner post a swing beam to an A-frame, a tyre swing and a seat; from its near corner a ladder that
    dips and climbs over a small arch. Placed as in MH024 about the sandpit (read off with tools/camsolve_mh024.py's
    camera), a little drawn in where a frame would stand off the rubber."""
    pz = LZ + END_SHIFT   # two bays further back than photo 14's sandpit (user, 2026-10-23, photo 1)
    pg = Fr((LX, 0, pz + 28.5)).sub(rot=math.pi / 4)
    for k in range(4):   # timber edging round the safety surface, 12 m side
        e = pg.sub(rot=k * math.pi / 2)
        box(mb, e, -6.0, 6.0, 0.0, 0.1, 5.8, 6.2, MAT['timber'])
    box(mb, pg, -5.8, 5.8, 0.04, 0.06, -5.8, 5.8, {'py': MAT['rubbertile']})   # black rubber tiles (photo 1)
    sp = pg.sub(-0.2, 0, 0)   # former sandpit 4.4 m, tiled over too
    box(mb, sp, -2.2, 2.2, 0, 0.07, -2.2, 2.2, {'py': MAT['rubbertile'], '*': MAT['timber']})
    for k in range(4):
        e = sp.sub(rot=k * math.pi / 2)
        box(mb, e, -2.3, 2.3, 0, 0.4, 2.2, 2.4, MAT['timber'])                       # kerb
        box(mb, e, -2.3, 2.3, 0.95, 1.07, 2.24, 2.36, MAT['pyellow'])                 # top rail
        box(mb, e, -2.3, 2.3, 0.62, 0.67, 2.27, 2.33, MAT['pblue'])                   # middle rail
        for xp in (-2.3, 0.0):                                                        # posts at the corners and halfway
            box(mb, e, xp - 0.05, xp + 0.05, 0, 1.12 if xp else 1.0, 2.25, 2.35, MAT['pblue'])
    S = sp.p(0, 0, 0)
    f0 = Fr((S[0], 0, S[2]))                         # site axes through the old sandpit's middle (MH024)
    # swing: the right corner's post carries the beam out to an A-frame; a tyre on three chains, a flat seat
    box(mb, f0, 3.2, 3.3, 0, 2.45, -0.05, 0.05, MAT['pblue'])
    beam(mb, f0.p(3.25, 2.4, 0), f0.p(7.45, 2.4, 0), 0.07, MAT['pyellow'])
    for ez in (-0.85, 0.85):
        beam(mb, f0.p(7.45, 0, ez), f0.p(7.45, 2.4, 0), 0.06, MAT['pblue'])
    tc = f0.p(4.4, 0.55, 0)
    cylv(mb, Fr(tc), 0, 0, -0.1, 0.1, 0.42, 14, MAT['rubber'])
    for k in range(3):
        a = k * 2 * math.pi / 3
        beam(mb, tc + Vector((math.cos(a) * 0.36, 0.1, math.sin(a) * 0.36)), f0.p(4.4, 2.38, 0), 0.012, MAT['pipe'])
    box(mb, f0, 6.05, 6.55, 0.45, 0.5, -0.12, 0.12, MAT['steel'])
    for kz in (-0.1, 0.1):
        beam(mb, f0.p(6.3, 0.5, kz), f0.p(6.3, 2.38, kz), 0.012, MAT['pipe'])
    # tyre stack on three blue legs, just out from the left corner
    ty = Fr(f0.p(-3.65, 0, 0.3))
    for k in range(4):
        cylv(mb, ty, 0, 0, 0.12 + k * 0.38, 0.47 + k * 0.38, 0.45, 14, MAT['rubber'])
    for a in range(3):
        ang = a * 2 * math.pi / 3 + 0.4
        cylv(mb, ty, 0.5 * math.cos(ang), 0.5 * math.sin(ang), 0, 1.9, 0.035, 6, MAT['pblue'])
    # climbing frame on the library side, along the avenue's direction: a ladder up at its left end, bars across at 2 m,
    # then an arc down to its right-hand posts
    cf = Fr(f0.p(-4.3, 0, -3.8))
    arc_pts = [(3.0 + 1.3 * math.sin(t * math.pi / 2), 0.8 + 1.2 * math.cos(t * math.pi / 2)) for t in [i / 6 for i in range(7)]]
    ladder_bars(mb, cf, [(0.0, 2.0), (3.0, 2.0)] + arc_pts[1:])
    ladder_bars(mb, cf, [(0.0, 0.3), (0.0, 1.95)], rung=0.32)                       # the ladder's rungs
    for u, v in ((0.0, 2.0), (1.5, 2.0), (3.0, 2.0), (4.3, 0.8)):                  # posts
        for side in (-0.3, 0.3):
            beam(mb, cf.p(u, 0, side), cf.p(u, v, side), 0.035, MAT['lamppole'])
    # from the near corner, bars that dip and climb over a small arch to the ground
    d = Vector((0.915, 0.0, 0.404))
    lf_ = Fr(f0.p(0.0, 0, 3.35), tuple(d), (-d[2], 0.0, d[0]))
    prof = [(0.0, 1.2), (0.6, 0.95), (1.2, 0.75), (1.8, 0.95), (2.3, 1.45), (2.7, 1.7), (3.1, 1.45), (3.45, 0.9)]
    ladder_bars(mb, lf_, prof)
    for u, v in ((0.0, 1.2), (3.45, 0.9)):
        for side in (-0.3, 0.3):
            beam(mb, lf_.p(u, 0, side), lf_.p(u, v, side), 0.035, MAT['lamppole'])


# ------------------------------------------------------------------ ground, streets, sports hall (simplified), context
GATE_H = 2.3   # head rail of the steel gates


def iron_gate(mb, fr, xa, xb, leaves, open_=(), out=False, h=GATE_H, posts=None, swing=80, lt=0.55):
    """Steel gate (MH038; user, 2026-10-24: the four passages into the estate all have this one): square posts, leaves
    of upright bars between flat rails, and over the head beam a grille leaning out towards the street, each of its bars
    ending in a hook turned down. Local x along the gate, +z out to the street, gate plane z = 0; open_: the leaves
    standing open, swung in by swing degrees on their hinges, the first half's on the left and the rest's on the right
    (out: swung out); posts: the divisions with a post (all by default)."""
    m = MAT['gate']
    w = (xb - xa) / leaves
    for k in (range(leaves + 1) if posts is None else posts):
        xp = xa + k * w
        box(mb, fr, xp - 0.05, xp + 0.05, 0, h + 0.12, -0.05, 0.05, m)
    box(mb, fr, xa, xb, h + 0.04, h + 0.12, -0.04, 0.04, m)
    for k in range(leaves):
        a, b = xa + k * w + 0.06, xa + (k + 1) * w - 0.06
        ln = b - a
        hinge, sgn = (a, 1) if k < leaves / 2 else (b, -1)
        ang = math.radians(swing) if k in open_ else 0.0
        d = fr.ex * (sgn * math.cos(ang)) + fr.ez * ((1 if out else -1) * math.sin(ang))
        lf = Fr(fr.p(hinge, 0, 0), tuple(d), tuple(d.cross(fr.ey)))
        for y0, y1 in ((0.08, 0.14), (1.0, 1.06), (h - 0.06, h)):
            box(mb, lf, 0, ln, y0, y1, -0.025, 0.025, m)
        for x0_ in (0.0, ln - 0.05):
            box(mb, lf, x0_, x0_ + 0.05, 0.08, h, -0.025, 0.025, m)
        for j in range(1, int(ln / 0.12)):
            xq = ln * j / int(ln / 0.12)
            box(mb, lf, xq - 0.011, xq + 0.011, 0.14, h - 0.06, -0.011, 0.011, m)
    ca, sa = math.cos(math.radians(35)), math.sin(math.radians(35))   # the leaning grille and its hooks
    up = tuple(fr.ex)
    beam(mb, fr.p(xa, h + 0.12 + lt * sa, lt * ca), fr.p(xb, h + 0.12 + lt * sa, lt * ca), 0.04, m)
    for j in range(int((xb - xa) / 0.13) + 1):
        xq = xa + (xb - xa) * j / int((xb - xa) / 0.13)
        tip = fr.p(xq, h + 0.12 + lt * sa, lt * ca)
        beam(mb, fr.p(xq, h + 0.12, 0.0), tip, 0.022, m, up=up)
        beam(mb, tip, fr.p(xq, h + 0.12 + lt * sa - 0.14, lt * ca + 0.03), 0.022, m, up=up)


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
    flat(EX0, EZ1, EX1, B['strip'], 0.03, MAT['soil'])                     # sunken planted strip behind the blocks
    # the 利誠 side street (ground level) and the raised ground to its east, where the hillside blocks stood
    flat(EX1 + 1.5, EZ0, SIDE_X1, LISHENG_ZP, 0.021, MAT['asphalt'])
    box(mb, f0, EX1, EX1 + 1.5, 0, 0.15, EZ0, LISHENG_ZP, {'py': MAT['sidewalk'], '*': MAT['curb']})
    # the post office's corner bay stands out into the side street (user, 2026-10-24): the pavement steps out round it, and
    # the roadway is widened on its far side, where there is room below the hillside's raised ground
    xp = ROWS[0]['fr'].p(ROWS[0]['L'], 0, 0)[0]   # the avenue row's south-east end
    box(mb, f0, EX1 + 1.5, xp + 1.5, 0, 0.15, EZ0, EZ0 + D + 1.5, {'py': MAT['sidewalk'], '*': MAT['curb']})
    flat(SIDE_X1, EZ0, SIDE_X1 + 2.0, SLOPE['z0'], 0.021, MAT['asphalt'])
    PZ0, PX1 = HILL['zf'] - D - 2.5, HILL['x1'] + 2.5                         # paved round the hillside blocks
    box(mb, f0, SIDE_X1, SLOPE['x1'], 0, B['H'], SLOPE['z0'], PZ0, {'py': MAT['grass'], '*': MAT['rock']}, skip=('pz',))
    box(mb, f0, SIDE_X1, PX1, 0, B['H'], PZ0, B['strip'], {'py': MAT['sidewalk'], '*': MAT['rock']}, skip=('nz', 'px'))
    box(mb, f0, PX1, SLOPE['x1'], 0, B['H'], PZ0, B['strip'], {'py': MAT['grass'], '*': MAT['rock']}, skip=('nz', 'nx'))
    # (no green grid lines on the forecourt: user, 2026-10-24)
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
    # the retaining wall along the planted strip starts at the nursery's corner bay: in front of its door the pavement runs
    # up to the building, with the inscribed stone post at the mouth of the lane (photo 2, MH030; user, 2026-10-24)
    WX0, WX1 = ROWS[1]['fr'].p(ROWS[1]['items'][-1]['x0'], 0, 0)[0], EX1
    flat(HALL['x1'], EZ1, WX0, B['strip'], 0.04, MAT['sidewalk'])
    box(mb, f0, 50.85, 51.55, 0.03, 1.1, EZ1 + 0.4, EZ1 + 1.1, MAT['rock'])
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
    xk = max(WX0 + 0.15, B['x_lo'])   # the rails bend where the street starts to climb
    for yo in (0.5, 0.95):
        for xa, xb in ((WX0 + 0.15, xk), (xk, WX1 - 0.1)):
            if xb - xa > 0.01:
                beam(mb, (xa, back_h(xa) + 0.9 + yo, zw), (xb, back_h(xb) + 0.9 + yo, zw), 0.05, MAT['creampipe'])
    xh = HALL['x1'] + 6.8                                                     # U-hoop barriers along the back kerb
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
    # steps from the end of the 利誠 side street up to the high end of the back street (and the 望廈飲食 spot beyond),
    # estimated from the user's account (2026-10-24, no photo of it): out of the passage gate, the MH038 gate is right
    # there, set at a slant; behind it a V of two flights, a short one up towards the hillside's wall, a turn, a long one
    # up along the wall (the blue line drawn on MH038); at the top a raised paving at the back street's level fills the
    # street's end, the block's end wall on the right. MH038: a cream face with a railing along it across the street's end,
    # the slanting gate, and a store with a grid window beside it. The paving fills the whole V up to the flights' sides,
    # the store under it (user, 2026-10-24)
    sx0, sx1 = EX1 + 0.6, EX1 + 4.1                                           # the gate at the back street (MH033)
    top = back_h((sx0 + sx1) / 2) + 0.15
    L = LISHENG
    rz, zA0, zA1, xl0, zP, zs = top / 20, L['za0'], L['za1'], L['xl0'], L['zp'], L['store_z']
    gm = {'py': MAT['sidewalk'], '*': MAT['rock']}
    cream = MAT['arcwall']
    d1 = Vector((math.cos(L['ang']), 0, math.sin(L['ang'])))                    # the short flight, up towards the wall
    n1 = d1.cross(Vector((0, 1, 0)))
    sf_ = Fr(L['foot'], tuple(d1), tuple(n1))
    for k in range(6):
        box(mb, sf_, 0.3 * k, 0.3 * (k + 1) if k < 5 else 2.2, 0, rz * (k + 1), -0.75, 0.75, gm)
    prism_z(mb, sf_, [(0.0, 0.0), (1.8, 0.0), (1.8, rz * 7 + 1.0), (0.0, rz + 1.0)], -0.9, -0.75, cream)   # its parapet
    yl = rz * 7
    box(mb, f0, xl0 - 0.6, SIDE_X1, 0, yl, zA0, zA1, gm, skip=('px',))            # the turn, against the wall
    en, ep = Vector(L['foot']) - n1 * 0.75, Vector(L['foot']) + n1 * 0.75      # the short flight's two sides
    xf = en.x + (zA0 - en.z) / d1.z * d1.x                                      # where they meet the turn's edges
    box(mb, f0, xf, SIDE_X1, yl, yl + 1.0, zA0 - 0.15, zA0, cream)               # its parapet
    for k in range(12):                                                       # the long flight, up along the wall
        box(mb, f0, xl0, SIDE_X1, 0, rz * (k + 8), zA1 + 0.3 * k, zA1 + 0.3 * (k + 1), gm, skip=('px',))
    # the raised paving: the store's front across the street's end, the short flight's side, its turn and the long flight's
    # side are its cream faces, a railing along their top (ec: where a line along the short flight, off its side by o,
    # crosses z = zq or x = xq)
    ec = lambda o, zq=None, xq=None: ((ep.x + n1.x * o + (zq - ep.z - n1.z * o) / d1.z * d1.x, zq) if xq is None else
                                      (xq, ep.z + n1.z * o + (xq - ep.x - n1.x * o) / d1.x * d1.z))
    prism_y(mb, f0, [(EX1, zs), ec(0.0, zq=zs), ec(0.0, zq=zA1), (xl0, zA1), (xl0, zP), (EX1, zP)], 0, top, cream,
            cap_m=MAT['sidewalk'])
    box(mb, f0, EX1, SIDE_X1, 0, top, zP, EZ1, {'py': MAT['sidewalk'], 'nz': cream, '*': MAT['rock']}, skip=('nx',))
    box(mb, f0, EX1, SIDE_X1, 0, top, EZ1, B['wall'], gm)                    # (its side the 馬交石's niche's left)
    rail = [(EX1 + 0.1, zs + 0.06), ec(0.06, zq=zs + 0.06), ec(0.06, xq=xl0 - 0.06), (xl0 - 0.06, zP)]
    for (xa, za), (xb, zb) in zip(rail, rail[1:]):
        dr = Vector((xb - xa, 0, zb - za))
        railing_run(mb, Fr((xa, top, za), tuple(dr.normalized()), tuple(dr.normalized().cross(Vector((0, 1, 0))))),
                    0.0, dr.length, 0.0, 0.0, MAT['creampipe'])
    railing_run(mb, Fr((EX1 + 0.06, top, 0), (0, 0, 1), (-1, 0, 0)), EZ1, B['wall'] - 0.5, 0.0, 0.0, MAT['creampipe'])
    beam(mb, (xl0 + 0.06, yl + 0.9, zA1), (xl0 + 0.06, top + 0.9, zP), 0.05, MAT['creampipe'])        # handrails
    beam(mb, tuple(sf_.p(0, rz + 1.05, -0.82)), tuple(sf_.p(1.8, yl + 1.05, -0.82)), 0.05, MAT['creampipe'])
    beam(mb, tuple(sf_.p(0.2, rz + 0.9, 0.69)), tuple(sf_.p(2.0, yl + 0.9, 0.69)), 0.05, MAT['creampipe'])
    iron_gate(mb, Fr(sf_.p(-0.12, 0, 0), tuple(n1), tuple(-d1)), -0.85, 0.85, 2, open_=(0,))           # the MH038 gate
    gx0, gx1, gy0, gy1 = EX1 + 0.5, EX1 + 1.9, 1.0, 2.0                       # the store's grid window, three by four
    box(mb, f0, gx0, gx1, gy0, gy1, zs - 0.02, zs, MAT['void'])
    for xq in [gx0 + k * (gx1 - gx0) / 4 for k in range(5)]:
        box(mb, f0, xq - 0.03, xq + 0.03, gy0, gy1, zs - 0.05, zs, MAT['frame'])
    for yq in [gy0 + k * (gy1 - gy0) / 3 for k in range(4)]:
        box(mb, f0, gx0, gx1, yq - 0.03, yq + 0.03, zs - 0.05, zs, MAT['frame'])
    zq = SLOPE['z0'] + 0.3                                                    # railing along the top of the 3 m wall
    while zq < zP - 0.1:
        cylv(mb, f0, SIDE_X1 + 0.15, zq, B['H'], B['H'] + 1.0, 0.03, 8, MAT['creampipe'])
        zq += 2.0
    for yo in (0.5, 1.0):
        cylz_y = B['H'] + yo
        beam(mb, (SIDE_X1 + 0.15, cylz_y, SLOPE['z0'] + 0.3), (SIDE_X1 + 0.15, cylz_y, zP), 0.05, MAT['creampipe'])
    build_makau_stone(mb, MKS_FR)
    # top of the steps (MH033 = photo 23): a granite pier with a plaque; no gate there (user, 2026-10-24)
    zg = B['wall'] - 0.3
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
    # dark-green U-hoop barriers along the kerb (gaps at the zebra crossing, junction and bus stop: photo 21 has none in front
    # of the shelter)
    zr = -2.7
    xbs = min(BUS_X, PASS_X - 8.3)
    for xa, xb in ((-40, -12), (2, xbs - 2.4), (xbs + 2.4, PASS_X - 5.4), (PASS_X + 13.0, 190)):
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
    bs = Fr((min(BUS_X, PASS_X - 8.3), 0.15, -1.6))   # in front of the bay on the far side of 鞋宜樂's tower, clear of the signal pole
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


def gallery_box(mb, fr, xc, w=3.2):
    """A box standing out of the cantilever gallery, its underside rounded into the gallery's bull-nose (MH016, MH029,
    MH039; photo 2 and the lane photo of 2026-10-24)."""
    d, y0, y1, r = 3.0, 6.6, 9.45, 1.1
    prof = [(0, y0), (d - r, y0)] + [(d - r + math.cos(t) * r, y0 + r + math.sin(t) * r)
                                     for t in [-math.pi / 2 + math.pi / 2 * k / 6 for k in range(1, 7)]] + [(d, y1), (0, y1)]
    prism_x(mb, fr, prof, xc - w / 2, xc + w / 2, MAT['hallg'])


HALL_AD, HALL_YA, HALL_FL = 2.4, 6.7, 0.75   # the 俾利喇街 arcade: depth to its back wall, ceiling, floor (MH025, MH029)


def arched_opening(mb, fr, xc, y0, w, ys, z, door=False):
    """Round-headed door or window in the arcade's back wall (MH025, MH029): dark glass behind upright bars, or two
    wooden leaves, in a white frame, a fan grille in the head. z: the wall plane (local; the wall faces +z)."""
    r = w / 2
    prism_z(mb, fr, [(xc - r, y0), (xc + r, y0), (xc + r, ys)] + arc(xc, ys, r, 0, math.pi, 12)[1:-1] + [(xc - r, ys)],
            z, z + 0.02, MAT['ctxglass'])
    if door:
        box(mb, fr, xc - r + 0.06, xc - 0.02, y0, ys - 0.05, z, z + 0.06, MAT['door'])
        box(mb, fr, xc + 0.02, xc + r - 0.06, y0, ys - 0.05, z, z + 0.06, MAT['door'])
    else:
        for k in range(1, 6):
            xq = xc - r + 2 * r * k / 6
            box(mb, fr, xq - 0.015, xq + 0.015, y0, ys, z + 0.02, z + 0.05, MAT['gate'])
    box(mb, fr, xc - r, xc + r, ys - 0.04, ys + 0.02, z + 0.02, z + 0.06, MAT['frame'])          # transom
    up = tuple(fr.ez)
    for k in range(1, 6):                                                                       # fan grille
        a = math.pi * k / 6
        beam(mb, fr.p(xc + 0.12 * math.cos(a), ys + 0.12 * math.sin(a), z + 0.04),
             fr.p(xc + r * math.cos(a), ys + r * math.sin(a), z + 0.04), 0.03, MAT['gate'], up=up)
    for rr, wd, m in ((r * 0.5, 0.03, MAT['gate']), (r + 0.06, 0.12, MAT['frame'])):           # its ring, the white frame
        pts = arc(xc, ys, rr, 0, math.pi, 12)
        for a, b in zip(pts, pts[1:]):
            beam(mb, fr.p(a[0], a[1], z + 0.04), fr.p(b[0], b[1], z + 0.04), wd, m, up=up, h=0.05)
    for s in (-1, 1):
        box(mb, fr, xc + s * (r + 0.06) - 0.06, xc + s * (r + 0.06) + 0.06, y0, ys, z, z + 0.06, MAT['frame'])


def hall_facade(mb, fr, xa, xb, lights, lane=False, boxes=(), ends=(False, False)):
    """One arcaded face of the hall in a frame whose +z points out of the wall (wall plane z = 0). 俾利喇街 (MH025, MH029,
    MH016, MH019): a deep arcade of tall round arches on thin piers, its floor four red-and-white steps up from the
    pavement, round-headed doors and barred windows with fan grilles in its back wall, railings between the piers;
    ends: the corner bay at that end is solid, one big arch with a glazed screen in it under the gallery's box. lane:
    the face on the lane by the estate (photo 2, the 2026-10-24 lane photos): narrow round-headed recesses between broad
    cream piers, a tall window in each, the same red and white steps along its foot (user, 2026-10-24). boxes: local x of
    the boxes standing out of the gallery."""
    CB = 6.0                                             # corner bay
    ca, cb = xa + (CB if ends[0] else 0.0), xb - (CB if ends[1] else 0.0)
    L = cb - ca
    n = int((L - 2.0) / 4.4) if lane else int(L / 4.4)
    x0 = ca + (L - n * 4.4) / 2
    if lane:
        aw, ys, yt, dep = 1.0, 5.2, 6.45, 0.45   # recess half width, springing, top of the piers, depth
        for i in range(n):
            xc = x0 + (i + 0.5) * 4.4
            box(mb, fr, xc - 0.5, xc + 0.5, 0.85, 4.75, 0.0, 0.04, MAT['frame'])
            box(mb, fr, xc - 0.42, xc + 0.42, 0.93, 4.67, 0.04, 0.06, MAT['ctxglass'])          # tall window in the recess
            prism_z(mb, fr, [(xc - aw, yt), (xc - aw, ys)] + arc(xc, ys, aw, math.pi, 0, 10)[1:-1] + [(xc + aw, ys), (xc + aw, yt)],
                    0.0, dep, MAT['hallw'])                                                     # over the round head
        for i in range(n + 1):                                                                  # the piers
            pa = xa if i == 0 else x0 + i * 4.4 - (2.2 - aw)
            pb = xb if i == n else x0 + i * 4.4 + (2.2 - aw)
            box(mb, fr, pa, pb, 0, yt, 0.0, dep, MAT['hallw'], skip=('ny',))
        for k in range(4):   # the same red and white steps along its foot as on 俾利喇街 (user, 2026-10-24), off the piers
            box(mb, fr, xa, xb, 0, 0.15 + (HALL_FL - 0.15) * (k + 1) / 4, 0.0, dep + 0.3 * (4 - k), {'py': MAT['hallw'], '*': MAT['hallred']})
    else:
        AD, YA, FL, PD, AW, YS = HALL_AD, HALL_YA, HALL_FL, 0.8, 1.7, 4.8   # the arch ring's depth, half width, springing
        for i in range(n):
            xc = x0 + (i + 0.5) * 4.4
            prism_z(mb, fr, [(xc - AW, YA), (xc - AW, YS)] + arc(xc, YS, AW, math.pi, 0, 12)[1:-1] + [(xc + AW, YS), (xc + AW, YA)],
                    -PD, 0.0, MAT['hallw'])                                                     # over the arch
            door = i % 3 == 1
            arched_opening(mb, fr, xc, FL, 1.7 if door else 1.5, 3.3 if door else 3.6, -AD, door)
            if not door:
                railing_run(mb, fr, xc - AW + 0.05, xc + AW - 0.05, FL, -0.45, MAT['gate'])
        for i in range(n + 1):                                                                  # the piers
            pa = ca if i == 0 else x0 + i * 4.4 - (2.2 - AW)
            pb = cb if i == n else x0 + i * 4.4 + (2.2 - AW)
            box(mb, fr, pa, pb, FL, YA, -PD, 0.0, MAT['hallw'])
        box(mb, fr, ca, cb, 0.0, FL, -AD, 0.0, {'py': MAT['sidewalk'], '*': MAT['hallw']})      # the arcade's floor
        for on, s0, s1 in ((ends[0], xa, ca), (ends[1], cb, xb)):                                # solid corner bays
            if not on:
                continue
            xc, r, ys = (s0 + s1) / 2, 1.6, 4.5
            box(mb, fr, s0, s1, 0.0, YA, -AD, -PD, MAT['hallw'])
            box(mb, fr, s0, s1, 0.0, FL, -PD, 0.0, MAT['hallw'])
            for pa, pb in ((s0, xc - r), (xc + r, s1)):
                box(mb, fr, pa, pb, FL, YA, -PD, 0.0, MAT['hallw'])
            prism_z(mb, fr, [(xc - r, YA), (xc - r, ys)] + arc(xc, ys, r, math.pi, 0, 12)[1:-1] + [(xc + r, ys), (xc + r, YA)],
                    -PD, 0.0, MAT['hallw'])
            prism_z(mb, fr, [(xc - r, FL), (xc + r, FL), (xc + r, ys)] + arc(xc, ys, r, 0, math.pi, 12)[1:-1] + [(xc - r, ys)],
                    -PD, -PD + 0.02, MAT['ctxglass'])                                           # glazed screen and doors
            for xq in (xc - r / 3, xc + r / 3, xc - r + 0.04, xc + r - 0.04):
                box(mb, fr, xq - 0.04, xq + 0.04, FL, ys + math.sqrt(max(0.0, r * r - (xq - xc) ** 2)), -PD, -PD + 0.07, MAT['frame'])
            for yq in (2.9, ys):
                box(mb, fr, xc - r, xc + r, yq - 0.04, yq + 0.04, -PD, -PD + 0.07, MAT['frame'])
        for k in range(4):                                             # four red and white steps up from the pavement
            box(mb, fr, xa, xb, 0, 0.15 + (FL - 0.15) * (k + 1) / 4, 0.0, 0.35 * (4 - k), {'py': MAT['hallw'], '*': MAT['hallred']})
    hall_band(mb, fr, xa, xb, 6.9, 2.4, 1.4, MAT['hallg'])                       # cantilever corridor
    for xc in boxes:
        gallery_box(mb, fr, xc)
    railing_run(mb, fr, xa + 0.3, xb - 0.3, 8.3, 2.15, MAT['steel'])
    for i in range(n):                                   # recessed upper windows
        xc = x0 + (i + 0.5) * 4.4
        box(mb, fr, xc - 1.4, xc + 1.4, 8.7, 10.1, 0.0, 0.03, MAT['ctxglass'])
    hall_band(mb, fr, xa - 1.5, xb + 1.5, 10.6, 3.3, 0.9, MAT['hallg'])          # overhanging roof slab
    for i in range(n + 1):
        xb_ = x0 + i * 4.4
        prism_x(mb, fr, [(0, 9.0), (2.7, 10.62), (0, 10.62)], xb_ - 0.15, xb_ + 0.15, MAT['hallg'])
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
    AD, YA = HALL_AD, HALL_YA
    zm = (Z0 + ZR) / 2
    EW = 7.0                                            # half width of the entrance bay
    box(mb, f0, X0, X1, YA, H, Z0, ZR, {'py': MAT['hallg'], '*': MAT['hallw']})               # main block (two halls)
    box(mb, f0, X0 + AD, X1, 0, YA, Z0, ZR, MAT['hallw'], skip=('py',))                       # behind the arcade
    for za, zb in ((Z0, Z0 + 1.0), (zm - EW, zm + EW), (ZR - 0.5, ZR)):   # solid at the avenue corner, entrance, back end
        box(mb, f0, X0, X0 + AD, 0, YA, za, zb, MAT['hallw'], skip=('px', 'py'))
    box(mb, f0, X0 + 3, X1 - 3, H, H + 1.6, Z0 + 4, ZR - 4, {'py': MAT['hallg'], '*': MAT['hallw']})   # raised hall roofs
    street = Fr((X0, 0, 0), (0, 0, 1), (-1, 0, 0))      # 俾利喇街 face: local x = world z, +z = -x (right-handed frames)
    lane = Fr((X1, 0, 0), (0, 0, -1), (1, 0, 0))       # lane face: local x = -world z, +z = +x
    ave = Fr((0, 0, Z0), (-1, 0, 0), (0, 0, -1))        # avenue end: +z = -z
    # the gallery's boxes: at the corners and either side of the entrance on 俾利喇街 (MH016, MH029, MH039, MH027); on the
    # lane at both ends and halfway (photo 2, the 2026-10-24 lane photo from the avenue end)
    hall_facade(mb, street, Z0 + 1.0, zm - EW, True, boxes=(Z0 + 3.6, zm - EW - 2.0), ends=(True, False))
    hall_facade(mb, street, zm + EW, ZR - 0.5, True, boxes=(zm + EW + 2.0, ZR - 3.0), ends=(False, True))
    hall_facade(mb, lane, -(ZR - 1.0), -(Z0 + 1.0), False, lane=True, boxes=(-(ZR - 3.4), -zm, -(Z0 + 3.6)))
    # entrance bay: raised gable with a low triangular top, three glazed arches, glass canopy, the 體育發展局 logo near the
    # apex and the name under the eaves, flagpoles (user, 2026-10-24, with a photo of the entrance)
    ent = Fr((X0, 0, zm), (0, 0, 1), (-1, 0, 0))
    ye, ya = H + 0.4, H + 2.1                           # eaves, apex
    prism_z(mb, ent, [(-EW, 0), (EW, 0), (EW, ye), (0, ya), (-EW, ye)], -0.2, 0.5, MAT['hallw'])
    mb.poly([ent.p(-0.72, ye - 0.07, 0.505), ent.p(0.72, ye - 0.07, 0.505), ent.p(0.72, ye + 1.37, 0.505), ent.p(-0.72, ye + 1.37, 0.505)],
            MAT['desporto'], uvs=[(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)])
    for k in (-1, 0, 1):
        xc = k * 4.3
        prism_z(mb, Fr(ent.p(xc, 0, 0), ent.ex, ent.ez), [(-1.8, 0.4), (1.8, 0.4), (1.8, 6.2)] + arc(0, 6.2, 1.8, 0, math.pi, 12)[1:-1]
                + [(-1.8, 6.2)], 0.5, 0.54, MAT['ctxglass'])
        box(mb, ent, xc - 1.8, xc + 1.8, 0.4, 3.0, 0.5, 0.56, MAT['frame'])
    box(mb, ent, -EW + 0.4, EW - 0.4, 3.2, 3.3, 0.5, 3.2, MAT['ctxglass'])                    # glass canopy
    for k in (-1, 1):
        box(mb, ent, k * (EW - 0.6) - 0.06, k * (EW - 0.6) + 0.06, 0, 3.2, 3.0, 3.12, MAT['steel'])
    mb.poly([ent.p(-2.93, ye - 1.8, 0.505), ent.p(2.93, ye - 1.8, 0.505), ent.p(2.93, ye - 0.5, 0.505), ent.p(-2.93, ye - 0.5, 0.505)],
            MAT['hallname'], uvs=[(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)])   # 望廈體育館 / Pavilhão de Mong-Há (MH064),
    #                                                    the letters on the wall itself (user, 2026-10-24, with a photo)
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
    # its corner on the lane rounded too, a tall window cut into it (MH017, MH030); there the block overhangs a recessed,
    # glazed ground floor reached up three steps from the lane, a rounded lip along the overhang (photo 2, MH030)
    R1, RS, YO = 6.0, 1.6, 4.4          # radius of the lane corner, how far its ground floor stands back, underside
    ZE = G0 + 4.0                       # along the lane: the granite pier, a slot of windows, then the recessed entrance
    c1x, c1z = X1 - R1, Z1 - R1
    # the back street face carries the drum's bands (image 28): its ground floor set back like the lane corner's
    YG = 3.6                            # the drum's and the back face's ground floor: lower than the lane corner's (image 28)
    box(mb, f0, X0 + R0, c1x, YG, 14.5, G0, Z1, {'py': MAT['hallg'], '*': MAT['stone']})
    box(mb, f0, X0 + R0, c1x, 0, YG, G0, Z1 - RS, MAT['stone'], skip=('py',))
    box(mb, f0, X0 + R0, c1x, 0.45, YG, Z1 - RS, Z1 - RS + 0.03, MAT['ctxglass'])
    for xq in [X0 + R0 + 0.3 + k * (c1x - X0 - R0 - 0.6) / 10 for k in range(11)]:
        box(mb, f0, xq - 0.04, xq + 0.04, 0.45, YG, Z1 - RS, Z1 - RS + 0.08, MAT['frame'])
    # on 俾利喇街, between the hall's corner bay and the drum, a lower granite block: a band of windows across it over a
    # glazed ground floor (MH019, MH027, image 28); the flat granite pier stands where the drum's curve begins
    HL, XL = 9.4, X0 + 4.0
    box(mb, f0, X0, XL, 0, HL, G0, cz, {'py': MAT['hallg'], '*': MAT['stone']}, skip=('px',))
    box(mb, f0, XL, X0 + R0, 0, 14.5, G0, cz, {'py': MAT['hallg'], '*': MAT['stone']})
    for y0, y1, za, zb in ((0.5, 3.8, G0 + 0.4, cz - 1.9), (5.3, 6.6, G0 + 0.4, cz - 1.9)):
        box(mb, f0, X0 - 0.03, X0, y0, y1, za, zb, MAT['ctxglass'])
        for zq in [za + k * (zb - za) / 6 for k in range(7)]:
            box(mb, f0, X0 - 0.08, X0, y0, y1, zq - 0.04, zq + 0.04, MAT['frame'])
    box(mb, f0, X0 - 1.0, X0 + 0.8, 0, 14.9, cz - 1.8, cz + 0.4, {'py': MAT['hallg'], '*': MAT['stone']})
    box(mb, f0, c1x, X1, YO, 14.5, G0, c1z, {'py': MAT['hallg'], '*': MAT['stone']})
    box(mb, f0, c1x, X1, 0, YO, G0, ZE, MAT['stone'], skip=('py',))
    box(mb, f0, c1x, X1 - RS, 0, YO, ZE, c1z, MAT['stone'], skip=('py',))
    box(mb, f0, X1 - RS, X1 - RS + 0.03, 0.45, YO - 0.25, ZE + 1.0, c1z - 0.3, MAT['ctxglass'])      # entrance glazing
    for zq in [ZE + 1.0 + k * (c1z - 1.3 - ZE) / 5 for k in range(6)]:
        box(mb, f0, X1 - RS, X1 - RS + 0.08, 0.45, YO - 0.25, zq - 0.04, zq + 0.04, MAT['frame'])
    lip = Fr((X1 - RS, 0, 0), (0, 0, -1), (1, 0, 0))
    hall_band(mb, lip, -c1z, -ZE, YO - 0.55, RS, 0.55, MAT['stone'])
    nose = [(RS - 0.275 + math.cos(t) * 0.275, YO - 0.275 + math.sin(t) * 0.275) for t in [-math.pi / 2 + math.pi * k / 8 for k in range(9)]]
    nose = [(0.0, YO - 0.55)] + nose + [(0.0, YO)]
    ring1 = [(math.cos(t), math.sin(t)) for t in [math.pi / 2 * k / 12 for k in range(13)]]   # +x .. +z quarter
    for (c0, s0), (c1, s1) in zip(ring1, ring1[1:]):
        for y0, y1, rr, m in ((YO, 14.5, R1, MAT['stone']), (0.0, 0.45, R1 - RS, MAT['stone']), (0.45, YO, R1 - RS, MAT['ctxglass'])):
            a, b = (c1x + c0 * rr, c1z + s0 * rr), (c1x + c1 * rr, c1z + s1 * rr)
            mb.poly([(a[0], y0, a[1]), (a[0], y1, a[1]), (b[0], y1, b[1]), (b[0], y0, b[1])], m)
        a, b = (c1x + c0 * R1, c1z + s0 * R1), (c1x + c1 * R1, c1z + s1 * R1)
        mb.poly([(c1x, 14.5, c1z), (b[0], 14.5, b[1]), (a[0], 14.5, a[1])], MAT['hallg'])
        ai, bi = (c1x + c0 * (R1 - RS), c1z + s0 * (R1 - RS)), (c1x + c1 * (R1 - RS), c1z + s1 * (R1 - RS))
        mb.poly([(a[0], YO, a[1]), (b[0], YO, b[1]), (bi[0], YO, bi[1]), (ai[0], YO, ai[1])], MAT['stone'])
        for (d0, y0), (d1, y1) in zip(nose, nose[1:]):   # the lip swept round the corner (both faces, as its winding varies)
            r0, r1_ = R1 - RS + d0, R1 - RS + d1
            q = [(c1x + c0 * r0, y0, c1z + s0 * r0), (c1x + c1 * r0, y0, c1z + s1 * r0),
                 (c1x + c1 * r1_, y1, c1z + s1 * r1_), (c1x + c0 * r1_, y1, c1z + s0 * r1_)]
            mb.poly(q, MAT['stone'])
            mb.poly(q[::-1], MAT['stone'])
    # the window on the corner (MH017, MH030): a tall strip of glass on the side towards the back street, a great disc
    # cut out of it from the lane side, so the glass narrows to a sliver halfway up; its frame follows the disc's edge
    se_, sw, rc, yc, hh_ = 6.4, 1.5, 3.6, 9.4, 3.7   # strip edge and width (along the face), disc radius, centre height, half height
    sc = se_ - rc - 0.15                             # disc centre (along the face)

    def cpt(sv, y, out=0.03):
        t = sv / R1
        return (c1x + (R1 + out) * math.cos(t), y, c1z + (R1 + out) * math.sin(t))
    ys_ = [yc - hh_ + 2 * hh_ * k / 24 for k in range(25)]
    for y0, y1 in zip(ys_, ys_[1:]):
        lo = [max(se_ - sw, sc + math.sqrt(max(0.0, rc ** 2 - (y - yc) ** 2))) if abs(y - yc) < rc else se_ - sw for y in (y0, y1)]
        for j in range(3):   # three strips across, so the panes follow the curve
            f0_, f1_ = j / 3, (j + 1) / 3
            sa = [lo[i] + (se_ - lo[i]) * f0_ for i in (0, 1)]
            sb = [lo[i] + (se_ - lo[i]) * f1_ for i in (0, 1)]
            mb.poly([cpt(sa[0], y0), cpt(sb[0], y0), cpt(sb[1], y1), cpt(sa[1], y1)][::-1], MAT['hallglass'])
        for (a0, a1), (b0, b1) in (((lo[0] - 0.05, lo[1] - 0.05), (lo[0] + 0.03, lo[1] + 0.03)),
                                   ((se_ - 0.04, se_ - 0.04), (se_ + 0.04, se_ + 0.04))):   # frame along the disc, the strip's edge
            mb.poly([cpt(a0, y0, 0.05), cpt(b0, y0, 0.05), cpt(b1, y1, 0.05), cpt(a1, y1, 0.05)][::-1], MAT['frame'])
    for y in (yc - hh_, yc + hh_):
        mb.poly([cpt(se_ - sw, y - 0.04, 0.05), cpt(se_, y - 0.04, 0.05), cpt(se_, y + 0.04, 0.05), cpt(se_ - sw, y + 0.04, 0.05)][::-1],
                MAT['frame'])
    for k, (xs, hh) in enumerate(((X1 + 0.6, 0.15), (X1 + 0.2, 0.3), (X1 - 0.2, 0.45))):   # three steps up from the lane
        box(mb, f0, X1 - RS, xs, 0, hh, G0 + 2.6, c1z, {'py': MAT['hallw'], '*': MAT['stone']}, skip=('nx',))
    box(mb, f0, X1 - 0.02, X1 + 0.02, 0.5, 13.8, G0 + 2.75, G0 + 3.85, MAT['ctxglass'])           # slot of windows
    box(mb, f0, X1 - 0.5, X1 + 1.8, 0, 15.2, G0 - 1.0, G0 + 2.6, {'py': MAT['hallg'], '*': MAT['stone']})   # the lane's pier
    box(mb, f0, X1 + 0.8, X1 + 1.2, 15.2, 15.5, G0 + 0.6, G0 + 1.0, MAT['tlbox'])
    # the drum (image 28 of 2026-10-24, MH019, MH027): its glazed ground floor set back under a fascia like the lane
    # corner's, the lower ribbon window and a lip over it, a plain band, the upper ribbon window under a deep parapet with
    # a thin cap, a low dome on the roof; two dark raking struts in the recess towards the back street
    ts = [math.pi * (0.5 + 0.5 * k / 16) for k in range(17)]   # +z .. -x quarter
    RG = 2.6                                                   # how far the drum's ground floor stands back

    def band(t0, t1, r, y0, y1, m):   # a strip of the drum's face at radius r, facing out
        a, b = (cx + math.cos(t0) * r, cz + math.sin(t0) * r), (cx + math.cos(t1) * r, cz + math.sin(t1) * r)
        mb.poly([(a[0], y0, a[1]), (a[0], y1, a[1]), (b[0], y1, b[1]), (b[0], y0, b[1])], m)

    def ledge(t0, t1, r0, r1, y, m, up=True):   # a flat ring strip between radii r0 < r1 at height y
        q = [(cx + math.cos(t) * r, y, cz + math.sin(t) * r) for t, r in ((t0, r1), (t1, r1), (t1, r0), (t0, r0))]
        mb.poly(q[::-1] if up else q, m)

    BANDS = ((YG, 5.1, 0.15), (6.9, 7.1, 0.3), (14.25, 14.5, 0.12))   # fascia, lip, cap: heights and projection
    RIBBONS = ((5.3, 6.6), (10.2, 12.2))
    for t0, t1 in zip(ts, ts[1:]):
        band(t0, t1, R0, YG, 14.25, MAT['stone'])
        band(t0, t1, R0 - RG, 0.0, 0.45, MAT['stone'])
        band(t0, t1, R0 - RG, 0.45, YG, MAT['ctxglass'])
        ledge(t0, t1, R0 - RG, R0, YG, MAT['stone'], up=False)                   # soffit over the recess
        for y0, y1, d in BANDS:
            band(t0, t1, R0 + d, y0, y1, MAT['stone'])
            ledge(t0, t1, R0, R0 + d, y1, MAT['stone'])
            ledge(t0, t1, R0, R0 + d, y0, MAT['stone'], up=False)
        for y0, y1 in RIBBONS:
            band(t0, t1, R0 + 0.03, y0, y1, MAT['hallglass'])
        a, b = (cx + math.cos(t0) * R0, cz + math.sin(t0) * R0), (cx + math.cos(t1) * R0, cz + math.sin(t1) * R0)
        mb.poly([(cx, 14.5, cz), (b[0], 14.5, b[1]), (a[0], 14.5, a[1])], MAT['hallg'])          # roof
    for t in ts[1:-1]:                                                                          # mullions
        for (y0, y1), r in ((RIBBONS[0], R0 + 0.05), (RIBBONS[1], R0 + 0.05), ((0.45, YG), R0 - RG + 0.05)):
            q = (cx + math.cos(t) * r, cz + math.sin(t) * r)
            beam(mb, (q[0], y0, q[1]), (q[0], y1, q[1]), 0.07, MAT['frame'])
    for t in (0.6 * math.pi, 0.67 * math.pi):                                                   # raking struts
        lo = (cx + math.cos(t - 0.03) * (R0 - RG + 0.4), 0.0, cz + math.sin(t - 0.03) * (R0 - RG + 0.4))
        hi = (cx + math.cos(t + 0.03) * (R0 - 0.25), YG, cz + math.sin(t + 0.03) * (R0 - 0.25))
        beam(mb, lo, hi, 0.38, MAT['tlbox'])
    RD, HD = 8.0, 2.6                                                                           # the low dome
    Rs = (RD * RD + HD * HD) / (2 * HD)
    yc, ph0 = 14.5 + HD - Rs, math.asin(RD / Rs)
    seg = 32
    dome = [[(cx + Rs * math.sin(ph0 * i / 6) * math.cos(2 * math.pi * j / seg), yc + Rs * math.cos(ph0 * i / 6),
              cz + Rs * math.sin(ph0 * i / 6) * math.sin(2 * math.pi * j / seg)) for j in range(seg)] for i in range(7)]
    for i in range(6):
        for j in range(seg):
            a, b, c_, d = dome[i][j], dome[i][(j + 1) % seg], dome[i + 1][(j + 1) % seg], dome[i + 1][j]
            mb.poly([a, c_, d] if i == 0 else [a, b, c_, d], MAT['stone'])
    xa_, xb_ = X0 + R0, c1x                                                                     # the bands on the back face
    for y0, y1, d in BANDS:
        box(mb, f0, xa_, xb_, y0, y1, Z1, Z1 + d, MAT['stone'], skip=('nx',))
    for y0, y1 in RIBBONS:
        box(mb, f0, xa_, xb_, y0, y1, Z1, Z1 + 0.03, MAT['hallglass'])
        for xq in [xa_ + k * (xb_ - xa_) / 16 for k in range(1, 16)]:
            box(mb, f0, xq - 0.035, xq + 0.035, y0, y1, Z1, Z1 + 0.05, MAT['frame'])
    for (fx, fz) in ((X1 - 4.0, Z1 - 3.0), (X1 - 6.2, Z1 - 2.2)):                              # black flues with masts
        cylv(mb, Fr((fx, 0, fz)), 0, 0, 14.5, 19.0, 0.45, 16, MAT['steel'])
        cylv(mb, Fr((fx, 0, fz)), 0, 0, 19.0, 24.0, 0.05, 6, MAT['lamppole'])
    for k in range(5):                                                                         # floodlights on the parapet
        t = math.pi * (0.55 + 0.4 * k / 4)
        lx, lz = cx + math.cos(t) * (R0 - 0.3), cz + math.sin(t) * (R0 - 0.3)
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
for ri, row in enumerate(ROWS):
    mb = slope if row['id'].startswith('slope') else ROW_MB[row['id']]
    irng = random.Random(2011) if mb is slope else _irng_main   # hillside edits leave the estate's draws alone
    if 'draws' in row:   # keep the shared streams where the first layout left them (its air-conditioner marks dropped)
        n_ac, first = len(AC_MARKS), dict(row, items=row['draws'], bw=row['draws_bw'], first=True,
                                          L=row.get('draws_L', row['L']), fr=row['draws_fr'])
        for it in first['items']:
            (build_block if it['t'] == 'b' else build_joint)(SCRATCH, first, it)
        del AC_MARKS[n_ac:]
        streams = rnd, irng, REC_RNG, LEDGE_RNG
        rnd, irng, REC_RNG, LEDGE_RNG = (random.Random(2023 + 10 * (ri - 2) + k) for k in range(4))
        shops = {k: OPEN_SHOPS[k] for k in row.get('shops', {})}
        OPEN_SHOPS.update(row.get('shops', {}))
    for it in row['items']:
        if it['t'] == 'b':
            build_block(mb, row, it)
        elif it['t'] == 'j':
            build_joint(mb, row, it)
    if 'draws' in row:
        OPEN_SHOPS.update(shops)
        rnd, irng, REC_RNG, LEDGE_RNG = streams
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
irng = _irng_main
for rid in ('front', 'back'):   # the end rows' outer ends face the side streets: windows and floor bands
    row = next(r for r in ROWS if r['id'] == rid)
    fr = row['fr']
    for xl, sgn in ((0.0, -1), (row['L'], 1)):
        ez = fr.ex * sgn
        ex = Vector((0, 1, 0)).cross(ez)
        ef = Fr(fr.p(xl, 0, 0), tuple(ex), tuple(ez))
        rec = (row['items'][0] if sgn < 0 else row['items'][-1]).get('rec', 0.0)   # a recessed corner bay ends here
        lo, hi = (-HZ + rec, HZ) if sgn < 0 else (-HZ, HZ - rec)   # the end wall's span (its street edge at sgn * HZ)
        post = rid == 'front' and sgn == 1
        for f in range(NF):
            y = GF + FH * f
            nwin = max(3, int((2 * HZ - 2.4) / 2.6) + 1)
            for zl in [-(HZ - 1.6) + k * (2 * HZ - 3.2) / (nwin - 1) for k in range(nwin)]:
                xw = zl * (1 if ex.dot(fr.ez) > 0 else -1)
                inside = lo + 0.7 < xw < hi - 0.7   # windows where the corner bay stands back are drawn, not built
                window(ROW_MB[rid] if inside else SCRATCH, ef, xw - 0.6, xw + 0.6, y + 0.95, y + 2.25, 0.0, bars=irng.random() < 0.3)
            if post and f == 0:   # the red-framed band of the post office's first floor faces the avenue now (MH022)
                window(SCRATCH, ef, HZ - REC - 5.4, HZ - 0.5, y + 0.45, y + 2.2, 0.0, mull=False, gm=MAT['shopglass'], cells=4,
                       fm=MAT['post'])
            ecol = row['items'][0]['cols'][0] if sgn < 0 else row['items'][-1]['cols'][-1]
            box(ROW_MB[rid], ef, lo, hi, y - 0.1, y + 0.08, 0.0, 0.05, MAT['slab'][ecol] if rid == 'front' and f > 0 else MAT['white'])
        if rid == 'front':   # the avenue row's end walls: mosaic of the end bay from the second floor up, rendered white below (MH022)
            box(ROW_MB[rid], ef, lo, hi, GF - 0.3, GF + FH - 0.1, 0.0, 0.015, MAT['white'], skip=('nz',))
        if post:   # the post office's frontage turning onto the side street (MH022: glazing behind grey piers, two signs) was
            atlas_uv(4)   # not there in 2010, only the avenue face (user, 2026-10-24): its glazing drawn, not built
_irng_keep, irng = irng, random.Random(2051)   # the passages at the side rows' ends (user): the side row's white end wall
for row in (ROWS[2], ROWS[3]):                  # with small windows and floor bands (MH001), on a stream of their own; the
    fr = row['fr']                              # end row across the passage shows its bays (passage_bay), so its white wall
    for k, it in enumerate(row['items']):       # is drawn, not built
        if it['t'] == 'g':
            s_ = -1 if k == 0 else 1   # along the row, from the block to the passage
            end_wall(ROW_MB[row['id']], fr.p(it['x1'] if k == 0 else it['x0'], 0, 0), fr.ex * s_)
            xe = it['x0'] if k == 0 else it['x1']
            end_row = 'back' if abs(fr.p(xe, 0, 0)[2] - CZ1) < 0.5 else 'front'
            o, er, gap = fr.p(xe, 0, 0), next(r for r in ROWS if r['id'] == end_row), None
            ex_ = Vector((0, 1, 0)).cross(Vector(fr.ex * -s_))
            for jt in er['items']:   # the end row's corner tower: its slot opens onto this passage
                ends = [(er['fr'].p(xx, 0, 0) - o).dot(ex_) for xx in (jt['x0'] + 0.4, jt['x1'] - 0.4)]
                if jt['t'] == 'j' and all(abs(e) < HZ for e in ends):
                    gap = (min(ends), max(ends))
            end_wall(SCRATCH, o, fr.ex * -s_, gap)
irng = _irng_keep
gal = MB('SM_Galleries_Bridges', C_EST)
build_galleries(gal)
for row, xg in ((ROWS[2], CX0), (ROWS[3], CX1)):   # the gallery crosses each passage (user): parapet on its open side, posts
    sx, xs = (1, EX0) if xg == CX0 else (-1, EX1)  # under it; and the end gallery runs on over the passage along the end row's
    for it in row['items']:                        # face out to the street, past the corner tower's platform (user, 2026-10-23,
        if it['t'] == 'g':                         # at all four corners)
            za, zb = sorted((row['fr'].p(it['x0'], 0, 0)[2], row['fr'].p(it['x1'], 0, 0)[2]))
            back = zb > LZ
            wa, wb = (GZ1, CZ1) if back else (CZ0, GZ0)   # the walkway's z range
            zrun(gal, xg + sx * 0.11, za if back else wb, wa if back else zb, GF)
            for zq in (za + 0.5, zb - 0.5):
                cylv(gal, Fr(), xg + sx * 0.4, zq, 0, GF - 0.3, 0.3, 16, MAT['mred'], caps=False)
            xe = min((x for x in court_window_xs(ROWS[1] if back else ROWS[0]) if sx * (x - xs) >= PASS_GAL_IN),
                     key=lambda x: sx * (x - xs))          # it stops short of the street, at a window (user, 2026-10-24)
            xa_, xb_ = sorted((xe, xg))
            box(gal, Fr(), xa_, xb_, GF - 0.3, GF, wa, wb, {'py': MAT['deck'], 'ny': MAT['soffit'], '*': MAT['white']})
            ze = wa + 0.11 if back else wb - 0.11
            parapet_run(gal, Fr(), xa_, xb_, ze, GF)                       # its open side
            zrun(gal, xe + sx * 0.11, wa, wb, GF)                          # and across its end
            xq = xe + sx * 0.5
            while sx * (xg - xq) > 1.5:
                cylv(gal, Fr(), xq, ze + (0.3 if back else -0.3), 0, GF - 0.3, 0.3, 16, MAT['mred'], caps=False)
                xq += sx * 4.0
for row, xs, s_ in ((ROWS[2], EX0, -1), (ROWS[3], EX1, 1)):   # the steel gate across each passage's street end, from
    for it in row['items']:                                    # wall to wall in the side row's street wall: four
        if it['t'] == 'g':                                     # leaves, the middle two the doors, open by day (MH038; user)
            za, zb = sorted((row['fr'].p(it['x0'], 0, 0)[2], row['fr'].p(it['x1'], 0, 0)[2]))
            xw = xs - s_ * (ZW_OUT + 0.05)
            if s_ > 0:
                fr_, ga, gb = Fr((xw, 0, 0), (0, 0, -1), (1, 0, 0)), -zb - 0.02, -za + 0.02
            else:
                fr_, ga, gb = Fr((xw, 0, 0), (0, 0, 1), (-1, 0, 0)), za - 0.02, zb + 0.02
            iron_gate(gal, fr_, ga, gb, 4, open_=(1, 2), posts=(0, 1, 3, 4), swing=90, lt=0.4)
            # the end row's courtyard arcade runs on past the gate to the row's end: closed there, from just inside the gate
            # to the end, as part of the block (user, 2026-10-24)
            back = zb > LZ
            er = ROWS[1] if back else ROWS[0]
            xr = (max if s_ > 0 else min)(er['fr'].p(0, 0, 0)[0], er['fr'].p(er['L'], 0, 0)[0])
            za_, zb_ = (CZ1, CZ1 + ARC) if back else (CZ0 - ARC, CZ0)
            box(ROW_MB[er['id']], Fr(), xw - s_ * 0.3, xr, 0, GF - 0.3, za_, zb_,
                {'nz' if back else 'pz': MAT['arcwall'], 'px' if s_ > 0 else 'nx': MAT['ground'], '*': MAT['arcwall']},
                skip=('py', 'ny', 'pz' if back else 'nz'))
            box(ROW_MB[er['id']], Fr(), xw - s_ * 0.3, xr, 0, 1.1, *((CZ1 - 0.03, CZ1) if back else (CZ0, CZ0 + 0.03)), MAT['dado'])
            box(ROW_MB[er['id']], Fr(), xw - s_ * 0.33, xw - s_ * 0.3, 0, 1.1, za_, zb_, MAT['dado'])   # (and in the arcade)
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
trees = [t for t in YOUNG_TREES if t]
SPECIES = [('feathery', 'broad', 'bauhinia')[i % 3] for i, t in enumerate(YOUNG_TREES) if t]
trees += [(x, -1.2, 2.2) for x in (-30, -18, 12, 26, 40, 150, 176) if not EX0 - 2 < x < EX1 + 2]
trees += [(2.4, z, 2.0) for z in range(50, int(HALL['zr']) - 4, 9)]   # along the arcade, none before the drum (MH019, image 28)
for _ in range(78):   # 26 garden trees used to stand where the full-length hall now is; keep the shared stream in step
    rnd.random()
for _ in range(66):   # the old back-garden trees used 66 draws; keep the shared stream where it was
    rnd.random()
_brng = random.Random(129)
_strip = [(EX0 + 5 + 7.4 * k + _brng.uniform(-1.2, 1.2), EZ1 + 2.0 + _brng.uniform(-0.4, 0.4), 2.0 + _brng.random() * 0.7)
          for k in range(int((EX1 - EX0 - 8) / 7.4) + 1)]   # trees in the sunken strip behind the blocks, growing up past the wall (street photo)
_mks_x = sorted(MKS_FR.p(x, 0, 0)[0] for x in (MKS['x0'] - 0.6, MKS['x1'] + 0.6))
trees += [t for t in _strip if not _mks_x[0] - 1.0 < t[0] < _mks_x[1] + 1.0]   # (but not where the 馬交石's niche is)
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
_t = MKS_FR.p(MKS['x1'] + 1.4, 0, MKS['zf'] + 0.4)
trees += [(_t[0], _t[2], 1.8)]   # the young tree beside the 馬交石, on its right (MH078)
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
