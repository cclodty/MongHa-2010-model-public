"""Camera of MH001 (the architect's aerial of the estate, 1445 x 1180) solved against the model, and overlays to check it.

Site frame: x along 慕拉士大馬路 (NW -> SE), y up, z into the estate. Camera: position, yaw (0 = looking towards -z, i.e. at
the avenue; + turns towards +x), pitch (+ looks down), focal length in px, principal point at the image centre.
Correspondences are listed in POINTS (3D point -> pixel) and LINES (3D line -> pixels on it).

Run with Blender's Python image IO:
  blender -b --factory-startup -P tools/camsolve_mh001.py -- [--solve] [--overlay=out.png] [--x0=cx,cy,cz,yaw,pitch,f]
--solve runs Levenberg-Marquardt from X0 and writes export/cams/mh001.json (read by blender/preview_render.py --cam=...).
--overlay draws the model's key outlines with the current/solved camera over the photo.
"""
import json
import math
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PHOTO = os.path.join(os.path.dirname(ROOT), 'mongha', '望廈舊相_整理交付_2026-10-22', '照片', '01_屋邨外觀與街景',
                     'MH001_CBMoreno建築師作品集：舊望廈平民屋全景俯瞰.jpg')
W_IMG, H_IMG = 1445, 1180
CX0, CY0 = W_IMG / 2, H_IMG / 2
ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
opt = {a.split('=', 1)[0]: (a.split('=', 1)[1] if '=' in a else True) for a in ARGS}

# ---- model constants (blender/build_estate.py)
EX0, EX1, EZ0, EZ1, HZ = 52.0, 128.0, 3.0, 143.0, 8.5   # 17 m deep blocks since 2026-10-23
TOPC = 22.72                      # top of the parapet cap
CAP = HZ + 0.6                    # cap edge, out from a row's centre line
LX, LZ = 90.0, 73.0
CI0, CI1 = EX0 + 2 * HZ + 0.6, EX1 - 2 * HZ - 0.6   # courtyard-side cap edges of the side rows
OCT = math.pi / 8
LIB_S = 0.705

# ---- correspondences (pixel coordinates in the original 1445 x 1180 photo)
# library column bases (k = 6, 7, 0 face the camera), apex (roof height less certain)
_rc = 9.3 * LIB_S
_col = lambda k: (LX + math.sin(OCT + k * math.pi / 4) * _rc, 0.0, LZ + math.cos(OCT + k * math.pi / 4) * _rc)
POINTS = [(_col(6), (467.5, 772.5), 1.0), (_col(7), (525.0, 781.0), 1.0), (_col(0), (576.0, 760.0), 1.0),
          ((LX, 15.2, LZ), (482.0, 594.0), 0.4)]
_ci0, _ci1, _cz0, _cz1 = EX0 + 2 * HZ + 0.6, EX1 - 2 * HZ - 0.6, EZ0 + 2 * HZ + 0.6, EZ1 - 2 * HZ - 0.6
FREE_DEPTH = bool(opt.get('--depth'))   # also solve the side rows' (x[9]) and end rows' (x[10]) block depth


def _dS(x):
    return x[9] if FREE_DEPTH else 2 * HZ


def _dE(x):
    return x[10] if FREE_DEPTH else 2 * HZ


LINES = [  # roof cap edges: courtyard sides of the four rows, and the back row's street side (read off 1.4-1.7x crops)
    (lambda x: ((LX, TOPC, EZ0 + _dE(x) + 0.6), (1, 0, 0)), [(44, 321), (106, 309), (171, 297), (218, 288), (300, 274), (382, 259), (471, 242)], 1.0),
    (lambda x: ((EX1 - _dS(x) - 0.6, TOPC, LZ), (0, 0, 1)), [(476, 259), (560, 322), (654, 391)], 0.7),   # SE, far segment
    (lambda x: ((LX, TOPC, EZ1 - _dE(x) - 0.6), (1, 0, 0)), [(460, 973), (630, 900), (800, 827)], 1.0),   # back
    (lambda x: ((EX0 + _dS(x) + 0.6, TOPC, LZ), (0, 0, 1)), [(150, 413), (200, 480), (250, 547), (300, 620), (343, 693), (393, 773), (433, 840),
                                     (457, 873)], 1.0),                                                 # NW
    (((LX, TOPC, EZ1 + 0.6), (1, 0, 0)), [(1082, 995), (1150, 962), (1223, 925), (1300, 889)], 1.0),    # back, street side
]
NAMES = ['cx', 'cy', 'cz', 'yaw', 'pitch', 'f', 'ppx', 'ppy', 'roll']
X0 = np.array([float(v) for v in opt['--x0'].split(',')]) if '--x0' in opt else np.array([50.0, 66.0, 166.0, 0.46, 0.48, 1460.0, CX0, CY0, 0.0])
if len(X0) == 6:
    X0 = np.concatenate([X0, [CX0, CY0, 0.0]])
if opt.get('--depth') and len(X0) == 9:
    X0 = np.concatenate([X0, [10.0, 10.0]])
    NAMES += ['depth_side', 'depth_end']
PP_PRIOR = float(opt.get("--pp", 0.08))    # the photo may be cropped from a larger frame: the principal point may move, at a small cost


def basis(p):
    ps, ph, rl = p[3], p[4], p[8]
    fwd = np.array([math.sin(ps) * math.cos(ph), -math.sin(ph), -math.cos(ps) * math.cos(ph)])
    right0 = np.array([math.cos(ps), 0.0, math.sin(ps)])
    up0 = np.cross(right0, fwd)
    right = right0 * math.cos(rl) + up0 * math.sin(rl)
    up = up0 * math.cos(rl) - right0 * math.sin(rl)
    return fwd, right, up


def project(p, P):
    fwd, right, up = basis(p)
    v = np.asarray(P, float) - p[:3]
    zc = v @ fwd
    return np.array([p[6] + p[5] * (v @ right) / zc, p[7] - p[5] * (v @ up) / zc]), zc


def residuals(x):
    r = [(x[6] - CX0) * PP_PRIOR, (x[7] - CY0) * PP_PRIOR]
    for P, q, wgt in POINTS:
        uv, _ = project(x, P(x) if callable(P) else P)
        r.extend((uv - np.array(q)) * wgt)
    for ln, qs, wgt in LINES:
        o, d = ln(x) if callable(ln) else ln
        a, _ = project(x, np.array(o) + 30 * np.array(d))
        b, _ = project(x, np.array(o) - 30 * np.array(d))
        n = np.array([-(b - a)[1], (b - a)[0]])
        n /= np.linalg.norm(n)
        for q in qs:
            r.append(((np.array(q) - a) @ n) * wgt)
    return np.array(r)


def lm(x, iters=300):
    lam = 1e-2
    for _ in range(iters):
        r = residuals(x)
        J = np.zeros((len(r), len(x)))
        for j in range(len(x)):
            h = 1e-5 * max(1.0, abs(x[j]))
            xp = x.copy()
            xp[j] += h
            J[:, j] = (residuals(xp) - r) / h
        A = J.T @ J
        g = J.T @ r
        while True:
            dx = -np.linalg.solve(A + lam * np.diag(np.diag(A) + 1e-9), g)
            if (residuals(x + dx) ** 2).sum() < (r ** 2).sum():
                x = x + dx
                lam = max(lam / 3, 1e-9)
                break
            lam *= 4
            if lam > 1e9:
                return x
        if np.abs(dx).max() < 1e-9:
            break
    return x


# ---- model outlines to draw: list of (polyline of 3D points, colour)
def outlines():
    segs = []
    Y = TOPC
    # estate outer roof edge and courtyard inner roof edge
    segs.append(([(EX0 - 0.6, Y, EZ0 - 0.6), (EX1 + 0.6, Y, EZ0 - 0.6), (EX1 + 0.6, Y, EZ1 + 0.6), (EX0 - 0.6, Y, EZ1 + 0.6),
                  (EX0 - 0.6, Y, EZ0 - 0.6)], (1, 0.15, 0.1)))
    cx0, cx1, cz0, cz1 = EX0 + 2 * HZ + 0.6, EX1 - 2 * HZ - 0.6, EZ0 + 2 * HZ + 0.6, EZ1 - 2 * HZ - 0.6
    segs.append(([(cx0, Y, cz0), (cx1, Y, cz0), (cx1, Y, cz1), (cx0, Y, cz1), (cx0, Y, cz0)], (1, 0.9, 0.1)))
    # courtyard floor outline (faces of the rows at ground level)
    segs.append(([(cx0 - 0.6, 0, cz0 - 0.6), (cx1 + 0.6, 0, cz0 - 0.6), (cx1 + 0.6, 0, cz1 + 0.6), (cx0 - 0.6, 0, cz1 + 0.6),
                  (cx0 - 0.6, 0, cz0 - 0.6)], (0.2, 1, 0.3)))
    # vertical corner edges of the courtyard
    for x, z in ((cx0, cz0), (cx1, cz0), (cx1, cz1), (cx0, cz1)):
        segs.append(([(x, 0, z), (x, Y, z)], (0.2, 1, 0.3)))
    # stair towers (joints): a cross on the roof at each one
    bw_end = (EX1 - EX0 - 2 * 4.2) / 13
    for xc in (EX0 + 4 * bw_end + 2.1, EX1 - 4 * bw_end - 2.1):
        for zc in (EZ0 + HZ, EZ1 - HZ):
            segs.append(([(xc, Y + 2.5, zc - HZ), (xc, Y + 2.5, zc + HZ)], (0.2, 0.6, 1)))
    bw_side = (EZ1 - EZ0 - 4 * HZ - 3 * 4.2) / 24
    for k in range(1, 4):
        zc = EZ0 + 2 * HZ + k * 6 * bw_side + (k - 0.5) * 4.2
        for xc in (EX0 + HZ, EX1 - HZ):
            segs.append(([(xc - HZ, Y + 2.5, zc), (xc + HZ, Y + 2.5, zc)], (0.2, 0.6, 1)))
    # library: column lines, eave octagon, apex
    r_col, r_eave = 9.3 * LIB_S, 9.2 * LIB_S
    lx, lz = LX - 1.0, LZ + 8.2                       # library ring centre (build_estate LIB_X, LIB_Z)
    ux, uz = lx - 2.0 * LIB_S, lz - 3.0 * LIB_S       # top floor and roof, off-centre (LIB_UP)
    for k in range(8):
        a = OCT + k * math.pi / 4
        x, z = lx + math.sin(a) * r_col, lz + math.cos(a) * r_col
        segs.append(([(x, 0, z), (x, 9.25, z)], (1, 0.3, 1)))
    ring = [(ux + math.sin(OCT + k * math.pi / 4) * r_eave, 12.9, uz + math.cos(OCT + k * math.pi / 4) * r_eave) for k in range(9)]
    segs.append((ring, (1, 0.3, 1)))
    for k in range(8):
        segs.append(([ring[k], (ux, 14.4, uz)], (1, 0.3, 1)))
    # caged court
    cz0 = EZ0 + 2 * HZ + 3
    c = (LX - 9, LX + 9, cz0 + 3.5, cz0 + 29.5)
    segs.append(([(c[0], 0, c[2]), (c[1], 0, c[2]), (c[1], 0, c[3]), (c[0], 0, c[3]), (c[0], 0, c[2])], (0.3, 1, 1)))
    return segs


def draw(x, path):
    import bpy
    img = bpy.data.images.load(PHOTO)
    w, h = img.size
    px = np.array(img.pixels[:], np.float32).reshape(h, w, 4)[::-1].copy()   # top-left origin
    for poly, col in outlines():
        for P, Q in zip(poly, poly[1:]):
            a, za = project(x, P)
            b, zb = project(x, Q)
            if za <= 0 or zb <= 0:
                continue
            n = int(max(abs(b[0] - a[0]), abs(b[1] - a[1])) * 2) + 1
            for t in np.linspace(0, 1, n):
                u, v = a + (b - a) * t
                iu, iv = int(round(u)), int(round(v))
                if 1 <= iu < w - 1 and 1 <= iv < h - 1:
                    px[iv - 1:iv + 1, iu - 1:iu + 1, :3] = col
    for P, q, _ in POINTS:   # observed point (white ring) and its projection (cyan dot)
        uv, _ = project(x, P(x) if callable(P) else P)
        for ang in np.linspace(0, 2 * math.pi, 40):
            iu, iv = int(q[0] + 6 * math.cos(ang)), int(q[1] + 6 * math.sin(ang))
            if 0 <= iu < w and 0 <= iv < h:
                px[iv, iu, :3] = (1, 1, 1)
        iu, iv = int(round(uv[0])), int(round(uv[1]))
        if 2 <= iu < w - 2 and 2 <= iv < h - 2:
            px[iv - 2:iv + 3, iu - 2:iu + 3, :3] = (0, 1, 1)
    out = bpy.data.images.new('ov', w, h, alpha=True)
    out.pixels[:] = px[::-1].ravel()
    out.filepath_raw = path
    out.file_format = 'PNG'
    out.save()
    print('OVERLAY', path)


def save_cam(x, path):
    fwd, right, up = basis(x)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(dict(name='mh001', w=W_IMG, h=H_IMG, f_px=float(x[5]), cx=float(x[6]), cy=float(x[7]), pos=[float(v) for v in x[:3]],
                   fwd=[float(v) for v in fwd], right=[float(v) for v in right], up=[float(v) for v in up],
                   yaw_deg=math.degrees(x[3]), pitch_deg=math.degrees(x[4])), open(path, 'w'), indent=1)
    print('CAMERA', path)


SHAPE = bool(opt.get('--shape'))
if SHAPE:
    # Scale anchored on the courtyard width (inner cap edges x 62.6 .. 103.4, from photo 14's solve); free: the end rows'
    # inner edges z0c, z1c, the back row's street edge z_out, the library centre and column radius. x[9:15]
    NAMES += ['z0c', 'z1c', 'z_out', 'lib_x', 'lib_z', 'lib_r']
    if len(X0) == 9:
        X0 = np.concatenate([X0, [EZ0 + 2 * HZ + 0.6, EZ1 - 2 * HZ - 0.6, EZ1 + 0.6, LX, LZ + 8.2, 9.3 * LIB_S]])
    _colS = lambda x, k: (x[12] + math.sin(OCT + k * math.pi / 4) * x[14], 0.0, x[13] + math.cos(OCT + k * math.pi / 4) * x[14])
    POINTS[:] = [(lambda x, k=k: _colS(x, k), q, 1.0) for k, q in ((6, (467.5, 772.5)), (7, (525.0, 781.0)), (0, (576.0, 760.0)))]
    LINES[0] = (lambda x: ((LX, TOPC, x[9]), (1, 0, 0)), LINES[0][1], LINES[0][2])
    LINES[1] = (lambda x: ((CI1, TOPC, LZ), (0, 0, 1)), LINES[1][1], LINES[1][2])
    BACK_DY = float(opt.get('--backdy', 0.0))   # test: back row taller (+2.9 = one more floor)
    LINES[2] = (lambda x: ((LX, TOPC + BACK_DY, x[10]), (1, 0, 0)), LINES[2][1], LINES[2][2])
    LINES[3] = (lambda x: ((CI0, TOPC, LZ), (0, 0, 1)), LINES[3][1], LINES[3][2])
    LINES[4] = (lambda x: ((LX, TOPC + BACK_DY, x[11]), (1, 0, 0)), LINES[4][1], LINES[4][2])
    if opt.get('--outer'):   # outer (street-side) cap edges of the side rows, free x: x[15] NW, x[16] SE
        NAMES += ['x_nw_out', 'x_se_out']
        if len(X0) == 15:
            X0 = np.concatenate([X0, [EX0 - 0.6, EX1 + 0.6]])
        LINES.append((lambda x: ((x[16], TOPC, LZ), (0, 0, 1)), [(633, 238), (808, 346), (867, 375), (1033, 488), (1067, 508),
                                                                  (1183, 575)], 1.0))
        LINES.append((lambda x: ((x[15], TOPC, LZ), (0, 0, 1)), [(40, 600), (65, 700), (90, 800), (140, 1000)], 0.6))

x = X0.copy()
if opt.get('--solve'):
    x = lm(x)
    r = residuals(x)
    print('RMS px', float(np.sqrt((r ** 2).mean())), 'max', float(np.abs(r).max()))
    print('SOLVED', ' '.join(f'{n}={v:.4f}' for n, v in zip(NAMES, x)), 'yaw_deg', math.degrees(x[3]), 'pitch_deg', math.degrees(x[4]),
          'roll_deg', math.degrees(x[8]))
    k = 2
    for P, q, wgt in POINTS:
        print('  pt', [round(float(v), 2) for v in (P(x) if callable(P) else P)], 'res', [round(float(v), 1) for v in r[k:k + 2] / wgt])
        k += 2
    for ln, qs, wgt in LINES:
        o, d = ln(x) if callable(ln) else ln
        print('  line', [round(float(v), 2) for v in o], d, 'res', [round(float(v), 1) for v in r[k:k + len(qs)] / wgt])
        k += len(qs)
    save_cam(x, os.path.join(ROOT, 'export', 'cams', 'mh001.json'))
if opt.get('--overlay'):
    draw(x, opt['--overlay'])
