"""Solve the camera of the 1990s courtyard photo (photo 14, 849 x 642) and the courtyard dimensions it implies.

World frame: origin at the library centre on the ground, X = site +x, Y up, Z = site +z (towards the photographer).
Unknowns: camera position, yaw, pitch, focal length, gallery half-width Wg (inner parapet line), far gallery line Zf,
library-end bridge post offset Xb. Levenberg-Marquardt in numpy.
Run: py -3 tools/camsolve.py
"""
import json
import math
import os

import numpy as np

W_IMG, H_IMG = 849, 642
CX0, CY0 = W_IMG / 2, H_IMG / 2

# ---- observations (original pixel coordinates)
POINTS = [  # (world point or function of params, image point)
    ('A', lambda p: (-3.56, 0.0, 8.6), (383.75, 342.5)),
    ('B', lambda p: (3.56, 0.0, 8.6), (456.0, 342.5)),
    ('A_top', lambda p: (-3.56, 11.4, 8.6), (381.0, 187.5)),
    ('B_top', lambda p: (3.56, 11.4, 8.6), (455.0, 186.0)),
    ('eaveL', lambda p: (-9.29, 12.0, 3.85), (337.5, 167.5)),
    ('eaveR', lambda p: (9.29, 12.0, 3.85), (506.0, 166.0)),
    ('bridgeL_gal', lambda p: (-(p['Wg'] - 0.4), 0.0, 1.6), (240.0, 287.5)),
    ('bridgeR_gal', lambda p: ((p['Wg'] - 0.4), 0.0, 1.6), (612.5, 287.5)),
    ('bridgeL_lib', lambda p: (-p['Xb'], 0.0, 1.6), (295.0, 287.5)),
    ('bridgeR_lib', lambda p: (p['Xb'], 0.0, 1.6), (557.5, 285.0)),
]
LINES = [  # 3D line as (point at z=0, direction) built from params; observed image points lying on it
    ('galL', lambda p: ((-p['Wg'], 5.1, 0.0), (0, 0, 1)),
     [(95, 420), (147.5, 352.5), (185, 302.5), (247.5, 222.5), (262.5, 202.5), (277.5, 182.5), (295, 162.5), (307.5, 147.5)]),
    ('galR', lambda p: ((p['Wg'], 5.1, 0.0), (0, 0, 1)),
     [(731.5, 420), (689, 352.5), (656.5, 297.5), (614, 230), (594, 197.5), (581, 180), (570, 165), (560, 150)]),
    ('galFar', lambda p: ((0.0, 5.1, p['Zf']), (1, 0, 0)), [(350, 117.5), (549, 112.5)]),
]
NAMES = ['cx', 'cy', 'cz', 'yaw', 'pitch', 'f', 'Wg', 'Zf', 'Xb']
X0 = np.array([2.0, 22.0, 40.0, 0.0, math.radians(40), 700.0, 19.0, -40.0, 13.5])


def unpack(x):
    return dict(zip(NAMES, x))


def basis(p):
    ps, ph = p['yaw'], p['pitch']
    fwd = np.array([math.sin(ps) * math.cos(ph), -math.sin(ph), -math.cos(ps) * math.cos(ph)])
    right = np.array([math.cos(ps), 0.0, math.sin(ps)])
    up = np.cross(right, fwd)
    return fwd, right, up


def project(p, P):
    fwd, right, up = basis(p)
    v = np.asarray(P, float) - np.array([p['cx'], p['cy'], p['cz']])
    zc = v @ fwd
    return np.array([CX0 + p['f'] * (v @ right) / zc, CY0 - p['f'] * (v @ up) / zc])


def residuals(x):
    p = unpack(x)
    r = []
    for _, fn, obs in POINTS:
        r.extend(project(p, fn(p)) - np.array(obs))
    for _, fn, obs in LINES:
        o, d = fn(p)
        a = project(p, np.array(o) + 20 * np.array(d))
        b = project(p, np.array(o) - 20 * np.array(d))
        n = np.array([-(b - a)[1], (b - a)[0]])
        n /= np.linalg.norm(n)
        for q in obs:
            r.append((np.array(q) - a) @ n)
    return np.array(r)


def lm(x, iters=200):
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
        step = np.linalg.solve(A + lam * np.diag(np.diag(A) + 1e-9), -g)
        xn = x + step
        if (residuals(xn) ** 2).sum() < (r ** 2).sum():
            x, lam = xn, lam * 0.4
        else:
            lam *= 4
    return x


def ground(p, uv):
    """Back-project an image point onto the ground plane Y=0."""
    fwd, right, up = basis(p)
    d = fwd + ((uv[0] - CX0) / p['f']) * right - ((uv[1] - CY0) / p['f']) * up
    C = np.array([p['cx'], p['cy'], p['cz']])
    t = -C[1] / d[1]
    return C + t * d


x = lm(X0.copy())
p = unpack(x)
r = residuals(x)
print('rms px', round(float(np.sqrt((r ** 2).mean())), 2), 'max', round(float(np.abs(r).max()), 1))
for k in NAMES:
    v = p[k]
    print(f'{k:6s}', round(math.degrees(v), 2) if k in ('yaw', 'pitch') else round(v, 2))
print('gallery-to-gallery (inner parapets) m:', round(2 * p['Wg'], 1))
print('camera height m:', round(p['cy'], 1), ' fov_v deg:', round(math.degrees(2 * math.atan(H_IMG / 2 / p['f'])), 1))

# ---- ground features read off the photo (orig px) -> world (X, Z) relative to the library centre
FEATURES = {
    'L_planter_left': (343, 352), 'L_planter_right': (496, 352), 'planter_left_tree': (240, 407),
    'planter_right_tree': (598, 405), 'planter_centre': (430, 410), 'disc_left': (332, 410), 'disc_right': (502, 411),
    'disc_far_left': (287, 326), 'disc_far_right': (561, 325),
    'sandpit_N': (410, 450), 'sandpit_E': (460, 487.5), 'sandpit_S': (407.5, 525), 'sandpit_W': (357.5, 480),
    'swing_L': (460, 500), 'swing_R': (542, 522), 'tyres': (345, 485), 'play_diamond_W': (257.5, 502.5),
    'play_diamond_E': (567.5, 505), 'stairL_post_far': (95, 495), 'stairL_post_near': (52, 548),
    'stairR_post_far': (626, 492), 'stairR_post_near': (645, 550), 'stairL_gal_post': (95, 420),
    'planter_bottom_centre': (387, 600), 'planter_bottom_left': (165, 600), 'planter_bottom_right': (670, 600),
    'bench_L1': (270, 284), 'bench_L2': (324, 284), 'bench_R1': (525, 282), 'bench_R2': (583, 282),
}
out = {}
for k, uv in FEATURES.items():
    g = ground(p, uv)
    out[k] = (round(float(g[0]), 2), round(float(g[2]), 2))
    print(f'{k:22s} X {g[0]:7.2f}  Z {g[2]:7.2f}')
json.dump(dict(camera=p, features=out), open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'export', 'camsolve.json'), 'w'), indent=1)
