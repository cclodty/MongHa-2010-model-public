"""Turn the Poly Haven HDRI (CC0, kloofendal_48d_partly_cloudy_puresky) into the estate's sky.

- finds the sun in the HDRI, removes it (the bake uses a matching sun lamp for crisp shadows) and measures its irradiance
- rotates the sky so the sun sits at the estate's morning azimuth (south-east of the courtyard axis, as before)
- replaces the mirrored lower half with a dull ground colour
- writes textures/sky_bake.exr (Blender equirect, sun removed, scaled so the sun's irradiance is SUN_E)
  and web/tex/sky.jpg (three.js equirect, LDR = value / K) + export/sky.json (sun direction, strength, colour, K)

Run:  blender -b --factory-startup -P make_sky.py
"""
import json
import math
import os

import bpy
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'cc0', 'hdri', 'kloofendal_48d_partly_cloudy_puresky_4k.hdr')
SUN_E = 5.0                                   # sun irradiance in Blender units (same as earlier bakes)
SITE_SUN_HORIZ = np.array([0.802, -0.598])    # morning sun direction projected on the ground, site (x, z)

img = bpy.data.images.load(SRC)
W, H = img.size
src = np.array(img.pixels[:], np.float32).reshape(H, W, 4)[:, :, :3]   # row 0 = bottom (v = 0)
lum = src @ np.array([0.2126, 0.7152, 0.0722], np.float32)
vv = (np.arange(H) + 0.5) / H
elev = (vv - 0.5) * math.pi                                             # per row
upper = elev > 0.02

# ---------------------------------------------------------------- sun: brightest blob in the upper half
med = float(np.median(lum[upper]))
mask = (lum > 60 * med) & upper[:, None]
ys, xs = np.nonzero(mask)
wts = lum[ys, xs]
cy, cx = float((ys * wts).sum() / wts.sum()), float((xs * wts).sum() / wts.sum())
sun_u, sun_v = (cx + 0.5) / W, (cy + 0.5) / H
phi, theta = (sun_u - 0.5) * 2 * math.pi, (sun_v - 0.5) * math.pi
sun_b = np.array([-math.cos(phi) * math.cos(theta), math.sin(phi) * math.cos(theta), math.sin(theta)])   # Blender dir
# fill the sun with the surrounding sky and measure what was removed
grow = mask.copy()
for _ in range(3):
    grow = grow | np.roll(grow, 1, 0) | np.roll(grow, -1, 0) | np.roll(grow, 1, 1) | np.roll(grow, -1, 1)
ring = grow & ~mask
for _ in range(6):
    ring = ring | np.roll(ring, 1, 0) | np.roll(ring, 1, 1)
ring &= ~grow
fill = np.median(src[ring], axis=0)
domega = (2 * math.pi / W) * (math.pi / H) * np.cos(elev)                # solid angle per pixel, per row
excess = np.clip(src[grow] - fill, 0, None)
E_rgb = (excess * domega[np.nonzero(grow)[0]][:, None]).sum(0)
sky = src.copy()
sky[grow] = fill
E_lum = float(E_rgb @ np.array([0.2126, 0.7152, 0.0722]))
scale = SUN_E / E_lum
sun_col = (E_rgb / E_rgb.max()).tolist()
print('SUN uv', round(sun_u, 4), round(sun_v, 4), 'elev deg', round(math.degrees(theta), 1), 'pixels', int(mask.sum()), 'E', round(E_lum, 2), 'scale', round(scale, 4))

# ---------------------------------------------------------------- rotation about the vertical so the sun matches the site
want_b = np.array([SITE_SUN_HORIZ[0], -SITE_SUN_HORIZ[1]])               # site (x, z) -> Blender (x, -z)
gamma = math.atan2(want_b[1], want_b[0]) - math.atan2(sun_b[1], sun_b[0])
cg, sg = math.cos(-gamma), math.sin(-gamma)

# ground colour for the lower half (the puresky mirrors the sky there)
horizon = np.median(sky[(elev > 0.0) & (elev < 0.08)].reshape(-1, 3), axis=0)
ground = horizon * np.array([0.30, 0.28, 0.25]) / max(horizon.mean(), 1e-6) * horizon.mean()


def sample_blender(d):
    """Radiance of the rotated, sun-free sky for Blender-space directions d (N x 3)."""
    x = d[:, 0] * cg - d[:, 1] * sg
    y = d[:, 0] * sg + d[:, 1] * cg
    z = d[:, 2]
    u = np.arctan2(y, -x) / (2 * math.pi) + 0.5
    v = np.arctan2(z, np.hypot(x, y)) / math.pi + 0.5
    px = np.clip((u * W).astype(int), 0, W - 1)
    py = np.clip((v * H).astype(int), 0, H - 1)
    c = sky[py, px]
    t = np.clip(-z / 0.06, 0, 1)[:, None]                                 # blend to ground just below the horizon
    return c * (1 - t) + ground[None, :] * t


def save_float(name, arr, path):
    h, w = arr.shape[:2]
    rgba = np.ones((h, w, 4), np.float32)
    rgba[:, :, :3] = arr
    im = bpy.data.images.new(name, w, h, alpha=False, float_buffer=True)
    im.pixels.foreach_set(rgba.ravel())
    im.filepath_raw = path
    im.file_format = 'OPEN_EXR'
    im.save()


# bake sky: Blender equirect 2048 x 1024, row 0 = bottom
BW, BH = 2048, 1024
uu, vv2 = np.meshgrid((np.arange(BW) + 0.5) / BW, (np.arange(BH) + 0.5) / BH)
ph, th = (uu - 0.5) * 2 * math.pi, (vv2 - 0.5) * math.pi
d = np.stack([-np.cos(ph) * np.cos(th), np.sin(ph) * np.cos(th), np.sin(th)], -1).reshape(-1, 3)
bake = sample_blender(d).reshape(BH, BW, 3) * scale
save_float('sky_bake', bake, os.path.join(ROOT, 'textures', 'sky_bake.exr'))

# web sky: three.js equirect (u = atan2(dz, dx), v = asin(dy), Y up, site axes), row 0 = top in the JPG
WW, WH = 2048, 1024
uu, vv3 = np.meshgrid((np.arange(WW) + 0.5) / WW, 1 - (np.arange(WH) + 0.5) / WH)
ph, th = (uu - 0.5) * 2 * math.pi, (vv3 - 0.5) * math.pi
dt = np.stack([np.cos(ph) * np.cos(th), np.sin(th), np.sin(ph) * np.cos(th)], -1).reshape(-1, 3)   # three (= site) dir
db = np.stack([dt[:, 0], -dt[:, 2], dt[:, 1]], -1)                                                 # -> Blender
web = sample_blender(db).reshape(WH, WW, 3) * scale
# put a bright sun disk back for the visible sky
sun_site = np.array([SITE_SUN_HORIZ[0] * math.cos(theta), math.sin(theta), SITE_SUN_HORIZ[1] * math.cos(theta)])
sun_site /= np.linalg.norm(sun_site)
cosang = (dt @ sun_site).reshape(WH, WW)
web += (np.clip((cosang - math.cos(math.radians(0.6))) / (1 - math.cos(math.radians(0.6))), 0, 1) ** 0.3)[..., None] * 40 * scale
web += (np.clip((cosang - math.cos(math.radians(8))) / (1 - math.cos(math.radians(8))), 0, 1) ** 3)[..., None] * 3 * scale
up = web[: WH // 2]
K = float(np.percentile(up @ np.array([0.2126, 0.7152, 0.0722]), 99.0))
enc = np.clip(web / K, 0, 1)
enc = np.where(enc <= 0.0031308, enc * 12.92, 1.055 * np.power(enc, 1 / 2.4) - 0.055)
rgba = np.ones((WH, WW, 4), np.float32)
rgba[:, :, :3] = enc[::-1]                     # Blender images store bottom row first
im = bpy.data.images.new('sky_web', WW, WH, alpha=False)
im.pixels.foreach_set(rgba.ravel())
im.filepath_raw = os.path.join(ROOT, 'web', 'tex', 'sky.jpg')
im.file_format = 'JPEG'
bpy.context.scene.render.image_settings.quality = 88
im.save()

fog = (horizon * scale / K).clip(0, 1).tolist()
info = dict(source='Poly Haven kloofendal_48d_partly_cloudy_puresky (CC0)', sun_dir_site=sun_site.round(4).tolist(),
            sun_dir_blender=[float(sun_site[0]), float(-sun_site[2]), float(sun_site[1])], sun_strength=SUN_E,
            sun_color=[round(c, 4) for c in sun_col], sun_elevation_deg=round(math.degrees(theta), 2), web_sky_K=round(K, 4),
            horizon_rgb_web=[round(c, 4) for c in fog], hdri_scale=scale)
json.dump(info, open(os.path.join(ROOT, 'export', 'sky.json'), 'w'), indent=1)
print('SKY_DONE', info)
