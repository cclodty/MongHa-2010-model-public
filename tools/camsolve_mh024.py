"""Solve the camera of MH024 (the 1980s-90s courtyard photo, 849 x 642; the same picture as photo 14 in camsolve.py)
against the current model, and read the courtyard's seats and planters off it.

Fitted to model points that the photo shows clearly: the bridges' red posts at the gallery end, the near U-stairs'
landing posts, and the inner parapet lines of both side galleries and the far end gallery. Site coordinates (x along
the avenue, y up, z into the estate); unknowns: camera position, yaw, pitch, roll, focal length. Levenberg-Marquardt in
numpy. The library's near columns are only checked: the photo's octagon (an earlier design) stands ~5.7 m nearer the
camera than the model's ring. Writes export/camsolve_mh024.json (camera, ground points relative to the courtyard
centre LX, LZ).
Run: python tools/camsolve_mh024.py
"""
import json
import math
import os

import numpy as np

W, H = 849, 642
CX0, CY0 = W / 2, H / 2
GF = 3.8
LX, LZ = 90.0, 73.0
POINTS = {   # site (x, y, z) -> photo px
    'bridge_post_nw': ((72.4, 0.0, 74.65), (237.5, 279.0)),
    'bridge_post_se': ((107.6, 0.0, 74.65), (612.5, 287.5)),
    'stair_nw_near': ((77.4, 0.0, 104.825), (178.0, 545.0)),
    'stair_nw_far': ((77.4, 0.0, 101.35), (205.0, 490.0)),
    'stair_se_near': ((102.6, 0.0, 104.95), (648.0, 545.0)),
    'stair_se_far': ((102.6, 0.0, 101.475), (630.0, 490.0)),
}
CHECK = {   # not fitted: how well the rest of the model sits on the photo
    'bridge_post_nw_lib': ((77.3, 0.0, 74.65), (292.5, 286.0)),
    'bridge_post_se_lib': ((102.7, 0.0, 74.65), (557.5, 285.0)),
    'library_col_nw': ((87.49, 0.0, 79.06), (383.75, 342.5)),
    'library_col_se': ((92.51, 0.0, 79.06), (456.0, 342.5)),
}
LINES = {   # parapet top rails (y = GF + 1.32) and points on them
    'gallery_nw': (((72.0, GF + 1.32, 0.0), (0, 0, 1)),
                   [(95, 420), (147.5, 352.5), (185, 302.5), (247.5, 222.5), (262.5, 202.5), (277.5, 182.5), (295, 162.5), (307.5, 147.5)]),
    'gallery_se': (((108.0, GF + 1.32, 0.0), (0, 0, 1)),
                   [(731.5, 420), (689, 352.5), (656.5, 297.5), (614, 230), (594, 197.5), (581, 180), (570, 165), (560, 150)]),
    'gallery_front': (((0.0, GF + 1.32, 23.0), (1, 0, 0)), [(350, 117.5), (549, 112.5)]),
}
# photo px of the seats and planters (y: height of the point read, the stone benches' seats at 0.45)
FEATURES = {
    'L_nw_corner': ((345, 373), 0.0), 'L_nw_arm_a': ((305, 345), 0.0), 'L_nw_arm_b': ((382, 347), 0.0),
    'L_se_corner': ((495, 372), 0.0), 'L_se_arm_a': ((457, 345), 0.0), 'L_se_arm_b': ((535, 345), 0.0),
    'tree_planter_nw': ((243, 403), 0.0), 'tree_planter_se': ((598, 405), 0.0),
    'long_planter_a': ((374, 375), 0.0), 'long_planter_b': ((488, 455), 0.0),
    'disc_nw_far': ((288, 323), 0.0), 'disc_nw': ((332, 410), 0.0), 'disc_se': ((502, 411), 0.0), 'disc_se_far': ((560, 323), 0.0),
    'playground_w': ((257, 502), 0.0), 'playground_e': ((568, 505), 0.0),
    'planter_near_nw': ((170, 606), 0.0), 'planter_near_se': ((661, 598), 0.0),
    'bench_nw_out_near': ((270, 284), 0.45), 'bench_nw_in_near': ((322, 284), 0.45),
    'bench_se_in_near': ((527, 283), 0.45), 'bench_se_out_near': ((585, 283), 0.45),
    'bench_nw_out_far': ((280, 264), 0.45), 'bench_nw_in_far': ((325, 265), 0.45),
    'bench_se_in_far': ((528, 262), 0.45), 'bench_se_out_far': ((583, 261), 0.45),
}
NAMES = ['cx', 'cy', 'cz', 'yaw', 'pitch', 'roll', 'f']


def basis(p):
    ps, ph, rl = p['yaw'], p['pitch'], p['roll']
    fwd = np.array([math.sin(ps) * math.cos(ph), -math.sin(ph), -math.cos(ps) * math.cos(ph)])
    right0 = np.array([math.cos(ps), 0.0, math.sin(ps)])
    up0 = np.cross(right0, fwd)
    right = right0 * math.cos(rl) + up0 * math.sin(rl)
    return fwd, right, np.cross(right, fwd)


def project(p, P):
    fwd, right, up = basis(p)
    v = np.asarray(P, float) - np.array([p['cx'], p['cy'], p['cz']])
    zc = v @ fwd
    return np.array([CX0 + p['f'] * (v @ right) / zc, CY0 - p['f'] * (v @ up) / zc])


def residuals(x):
    p = dict(zip(NAMES, x))
    r = []
    for P, uv in POINTS.values():
        r.extend(project(p, P) - np.array(uv))
    for (o, d), obs in LINES.values():
        a, b = project(p, np.array(o) + 40 * np.array(d)), project(p, np.array(o) + 120 * np.array(d))
        n = np.array([-(b - a)[1], (b - a)[0]])
        n /= np.linalg.norm(n)
        r.extend((np.array(q) - a) @ n for q in obs)
    return np.array(r)


def lm(x, iters=400):
    lam = 1e-2
    for _ in range(iters):
        r = residuals(x)
        J = np.zeros((len(r), len(x)))
        for j in range(len(x)):
            h = 1e-6 * max(1.0, abs(x[j]))
            xp = x.copy()
            xp[j] += h
            J[:, j] = (residuals(xp) - r) / h
        A, g = J.T @ J, J.T @ r
        xn = x + np.linalg.solve(A + lam * np.diag(np.diag(A) + 1e-9), -g)
        if (residuals(xn) ** 2).sum() < (r ** 2).sum():
            x, lam = xn, lam * 0.4
        else:
            lam *= 4
    return x


def ground(p, uv, y=0.0):
    """Back-project a photo point onto the horizontal plane at height y."""
    fwd, right, up = basis(p)
    d = fwd + ((uv[0] - CX0) / p['f']) * right - ((uv[1] - CY0) / p['f']) * up
    C = np.array([p['cx'], p['cy'], p['cz']])
    return C + (y - C[1]) / d[1] * d


x = lm(np.array([91.0, 30.0, 150.0, 0.0, math.radians(25), 0.0, 800.0]))
p = dict(zip(NAMES, x))
r = residuals(x)
print('rms px', round(float(np.sqrt((r ** 2).mean())), 2), 'max', round(float(np.abs(r).max()), 1))
print({k: round(math.degrees(v) if k in ('yaw', 'pitch', 'roll') else v, 2) for k, v in p.items()})
for k, (P, uv) in CHECK.items():
    q = project(p, P)
    print(f'check {k:20s} off by {math.hypot(q[0] - uv[0], q[1] - uv[1]):5.1f} px')
out = {}
for k, (uv, y) in FEATURES.items():
    g = ground(p, uv, y)
    out[k] = (round(float(g[0] - LX), 2), round(float(g[2] - LZ), 2))
    print(f'{k:20s} x {out[k][0]:7.2f}  z {out[k][1]:7.2f}   (from the courtyard centre)')
json.dump(dict(camera={k: float(v) for k, v in p.items()}, features=out),
          open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'export', 'camsolve_mh024.json'), 'w'), indent=1)
