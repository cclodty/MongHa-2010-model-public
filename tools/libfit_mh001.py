"""Library shape and position from MH001 with the camera fixed (export/cams/mh001.json): column ring, eave octagon, apex.
Run: G:/Blender/5.2/python/bin/python.exe tools/libfit_mh001.py"""
import json
import math
import os

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
c = json.load(open(os.path.join(ROOT, 'export', 'cams', 'mh001.json')))
C, FWD, RIGHT, UP = (np.array(c[k]) for k in ('pos', 'fwd', 'right', 'up'))
OCT = math.pi / 8


def proj(P):
    v = np.asarray(P) - C
    zc = v @ FWD
    return np.array([c['cx'] + c['f_px'] * (v @ RIGHT) / zc, c['cy'] - c['f_px'] * (v @ UP) / zc])


ang = lambda k: OCT + k * math.pi / 4
# photo observations (orig px), read off the 4x gridded crop (origin 390, 540)
COL_BASE = {6: (467.5, 772.5), 7: (525.0, 781.0), 0: (576.0, 760.0)}
COL_TOP = {6: (462.0, 690.0), 7: (517.0, 700.0), 0: (574.0, 680.0)}      # top of the outer columns (terrace parapet level)
EAVE = {5: (405, 612), 4: (430, 577), 3: (481, 563), 2: (539, 570), 1: (565, 599), 0: (550, 630), 7: (495, 649), 6: (431, 639)}
APEX = (466.0, 591.0)
# eave corner k sits at angle ang(k)? the octagon's corners line up with the columns (model) -- test both phases
NAMES = ['x', 'z', 'rc', 'hc', 're', 'he', 'ha', 'dx', 'dz', 'ph']


def res(p, phase_free=True):
    x, z, rc, hc, re_, he, ha, dx, dz, ph = p
    r = []
    for k, q in COL_BASE.items():
        r.extend(proj((x + math.sin(ang(k)) * rc, 0.0, z + math.cos(ang(k)) * rc)) - q)
    for k, q in COL_TOP.items():
        r.extend(proj((x + math.sin(ang(k)) * rc, hc, z + math.cos(ang(k)) * rc)) - q)
    for k, q in EAVE.items():
        a = ang(k) + (ph if phase_free else 0.0)
        r.extend(proj((x + dx + math.sin(a) * re_, he, z + dz + math.cos(a) * re_)) - q)
    r.extend(proj((x + dx, ha, z + dz)) - APEX)
    return np.array(r, float)


def lm(p, free):
    p = np.array(p, float)
    lam = 1e-2
    for _ in range(400):
        r = res(p)
        J = np.zeros((len(r), len(p)))
        for j in range(len(p)):
            if not free[j]:
                continue
            h = 1e-5 * max(1, abs(p[j]))
            q = p.copy()
            q[j] += h
            J[:, j] = (res(q) - r) / h
        A, g = J.T @ J, J.T @ r
        for j in range(len(p)):
            if not free[j]:
                A[j, :] = 0
                A[:, j] = 0
                A[j, j] = 1
                g[j] = 0
        while True:
            dp = -np.linalg.solve(A + lam * np.diag(np.diag(A) + 1e-9), g)
            if (res(p + dp) ** 2).sum() < (r ** 2).sum():
                p = p + dp
                lam = max(lam / 3, 1e-9)
                break
            lam *= 4
            if lam > 1e9:
                return p
        if np.abs(dp).max() < 1e-8:
            break
    return p


p0 = [83.0, 74.0, 6.7, 9.4, 5.9, 12.0, 15.2, 0.0, 0.0, 0.0]
for label, free in (('concentric, octagons in phase', [1, 1, 1, 1, 1, 1, 1, 0, 0, 0]),
                    ('concentric, eave phase free', [1, 1, 1, 1, 1, 1, 1, 0, 0, 1]),
                    ('upper part offset allowed', [1, 1, 1, 1, 1, 1, 1, 1, 1, 1])):
    p = lm(p0, free)
    r = res(p)
    print(f'{label:32s} rms {math.sqrt((r ** 2).mean()):5.2f} px  ' + '  '.join(f'{n}={v:.2f}' for n, v in zip(NAMES, p) if n != 'ph')
          + f'  ph={math.degrees(p[9]):.1f}deg')

# ---- top floor: its corner columns (feet on the terrace) with the upper-part centre from the offset fit
p = lm(p0, [1, 1, 1, 1, 1, 1, 1, 1, 1, 1])
cx_, cz_ = p[0] + p[7], p[1] + p[8]
TF_FOOT = {6: (439.0, 671.0), 7: (490.0, 680.0), 0: (544.0, 665.0)}


def res_tf(q):
    rt, ht = q
    out = []
    for k, obs in TF_FOOT.items():
        out.extend(proj((cx_ + math.sin(ang(k)) * rt, ht, cz_ + math.cos(ang(k)) * rt)) - obs)
    return np.array(out)


best = None
for rt in np.linspace(3.0, 7.0, 81):
    for ht in np.linspace(7.0, 9.5, 26):
        e = float((res_tf((rt, ht)) ** 2).mean())
        if best is None or e < best[0]:
            best = (e, rt, ht)
print(f'top floor: corner radius {best[1]:.2f} m, feet at {best[2]:.2f} m, rms {math.sqrt(best[0]):.1f} px; '
      f'upper centre ({cx_:.2f}, {cz_:.2f}), column ring centre ({p[0]:.2f}, {p[1]:.2f})')
