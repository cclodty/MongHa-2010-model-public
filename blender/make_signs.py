"""Shop signboard atlas: bilingual (Chinese / Portuguese) fascia boards and vertical blade signs, rendered from
Blender text objects with Windows CJK fonts, then weathered in numpy.

Run:  blender -b --factory-startup -P make_signs.py
Layout of textures/T_Signs_BC.png (2048 px): 2 x 7 fascia cells of 1024 x 228 px on top,
8 blade cells of 256 x 448 px along the bottom. Shop names are invented, except 望廈體育館 (cell 4, MH064), 利誠美食 (cells 3 and 10), 鞋宜樂 and 望廈托兒所 (residents' 2010 photos) and the hillside shops
望廈飲食, 金富美食 and Maria Beauty Center (MH006, MH068); the Portuguese lines of those three are not legible in the photos.
"""
import os
import sys

import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_textures import blur, save, tile_noise  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'textures')
bpy.ops.wm.read_factory_settings(use_empty=True)
FONTS = {k: bpy.data.fonts.load(p) for k, p in (('kai', 'C:/Windows/Fonts/NotoSerifTC-VF.ttf'), ('hei', 'C:/Windows/Fonts/msjhbd.ttc'),
                                                  ('ming', 'C:/Windows/Fonts/NotoSansTC-VF.ttf'), ('latin', 'C:/Windows/Fonts/arialbd.ttf'))}
P, FW, FH, BW, BH = 2048, 1024, 228, 256, 448
U = 0.01                                    # world units per pixel

FASCIA = [('望廈飲食', 'ESTABELECIMENTO DE COMIDAS', 'black'), ('金富美食', 'ESTABELECIMENTO DE COMIDAS', 'black'),
          ('Maria Beauty Center', 'SALÃO DE BELEZA', 'purple'),
          ('利誠美食', 'ESTABELECIMENTO DE COMIDAS LI SENG', 'whitegold'), ('望廈體育館', 'Pavilhão de Mong-Há', 'wall'), ('新華理髮', 'CABELEIREIRO', 'white'),
          ('好運麵包西餅', 'PADARIA', 'yellow'), ('大中電器', 'ELECTRODOMÉSTICOS', 'red'), ('望廈托兒所', 'CRECHE DE MONG-HÁ', 'yellow'),
          ('華豐雜貨', 'MERCEARIA', 'green'), ('利誠美食', 'ESTABELECIMENTO DE COMIDAS', 'yellow'), ('鞋宜樂', 'SAPATARIA E MALAS', 'yellowgreen'),
          ('明記海味', 'PRODUTOS SECOS', 'yellow'), ('老友記冰室', 'CASA DE CHÁ', 'green')]
BLADE = [('RAMPA DOS CAVALLEIROS 1847', 'stone'), ('茶餐廳', 'red'), ('地產', 'blue'), ('五金', 'yellow'), ('士多', 'red'), ('理髮', 'white'),
         ('麵包', 'yellow'), ('電器', 'red')]
SCHEME = {   # background, main text, border / sub text
    'red': ('#b5221f', '#fbf3df', '#f1cf3a'), 'white': ('#f1ece0', '#b5221f', '#1f4e8c'),
    'yellow': ('#efc93a', '#b5221f', '#2a2a2a'), 'blue': ('#1f4e8c', '#fbf3df', '#fbf3df'),
    'green': ('#1d6845', '#fbf3df', '#f1cf3a'),
    'yellowgreen': ('#efd447', '#1f7a3a', '#1f7a3a'),   # 鞋宜樂: yellow board, green characters (photo 22)
    'whitegold': ('#eeeadc', '#a5822c', '#8a6d22'),     # 利誠美食 fascia: white board, gold characters (photo 3)
    'stone': ('#a19d93', '#4e4a43', '#5a564e'),          # 馬交石 carving: crowned shield over RAMPA DOS CAVALLEIROS 1847 (MH079)
    'wall': ('#e6e0d0', '#34332f', '#34332f'),             # sports hall name lettered on its white gable (MH064)
    'black': ('#1d1c1a', '#c9302a', '#e9e2d2'),          # 望廈飲食 / 金富美食: black boards, red characters (MH068)
    'purple': ('#3b2f6e', '#f4f0f8', '#d9d2ec'),         # Maria Beauty Center (MH068)
}


def mat(hexcol):
    m = bpy.data.materials.get(hexcol) or bpy.data.materials.new(hexcol)
    h = hexcol.lstrip('#')
    m.diffuse_color = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)] + [1]
    return m


def rect(x, y, w, h, col, z=0.0):
    """pixel rect (top-left x,y) -> plane"""
    bpy.ops.mesh.primitive_plane_add(size=1, location=((x + w / 2) * U, -(y + h / 2) * U, z))
    o = bpy.context.object
    o.scale = (w * U, h * U, 1)
    o.data.materials.append(mat(col))
    return o


def text(body, font, cx, cy, maxw, maxh, col, z=0.02, vertical=False):
    cu = bpy.data.curves.new('t', 'FONT')
    cu.body = '\n'.join(body) if vertical else body
    cu.font = FONTS[font]
    cu.align_x, cu.align_y = 'CENTER', 'CENTER'
    cu.size = 1.0
    if vertical:
        cu.space_line = 0.95
    o = bpy.data.objects.new('t', cu)
    bpy.context.collection.objects.link(o)
    o.data.materials.append(mat(col))
    bpy.context.view_layer.update()
    w, h = o.dimensions.x, o.dimensions.y
    s = min(maxw * U / max(w, 1e-6), maxh * U / max(h, 1e-6))
    o.scale = (s, s, 1)
    o.location = (cx * U, -cy * U, z)
    bpy.context.view_layer.update()
    # centre on the actual glyph box (align_y CENTER is relative to the line, not the ink)
    bb = [o.matrix_world @ __import__('mathutils').Vector(c) for c in o.bound_box]
    mx = (min(v.x for v in bb) + max(v.x for v in bb)) / 2
    my = (min(v.y for v in bb) + max(v.y for v in bb)) / 2
    o.location.x += cx * U - mx
    o.location.y += -cy * U - my
    return o


rng = np.random.default_rng(1999)
rect(0, 0, P, P, '#2a2a2a', z=-0.01)
for k, (zh, pt, sc) in enumerate(FASCIA):
    bg, fg, ac = SCHEME[sc]
    x, y = (k % 2) * FW, (k // 2) * FH
    rect(x, y, FW, FH, bg)
    if sc != 'wall':   # thin border (not on the lettering painted straight onto a wall)
        rect(x + 10, y + 10, FW - 20, 6, ac, 0.005)
        rect(x + 10, y + FH - 16, FW - 20, 6, ac, 0.005)
    font = 'hei'          # Microsoft JhengHei Bold; the variable Noto TC fonts only load their thin master here
    rng.random(), rng.random()
    text(zh, font, x + FW / 2, y + FH * 0.42, FW * 0.86, FH * 0.56, fg)
    text(pt, 'latin', x + FW / 2, y + FH * 0.8, FW * 0.6, FH * 0.11, ac)
for k, (zh, sc) in enumerate(BLADE):
    bg, fg, ac = SCHEME[sc]
    x, y = k * BW, 7 * FH + 4
    rect(x, y, BW, P - y, bg)
    if sc == 'stone':   # blade cell 0: the 1847 carving on the 馬交石 boulder, crown and shield over four lines of capitals
        for bx, by, bw_, bh in ((60, 70, 136, 6), (60, 70, 6, 120), (190, 70, 6, 120), (72, 186, 56, 6), (128, 186, 56, 6),
                                (122, 190, 12, 22), (125, 80, 6, 100), (75, 120, 106, 6)):
            rect(x + bx, y + bh * 0 + by, bw_, bh, ac, 0.004)                          # shield outline and cross
        for cx_ in (78, 98, 118, 138, 158, 178):
            rect(x + cx_, y + 40, 8, 22, ac, 0.004)                                     # crown points
        rect(x + 74, y + 58, 108, 8, ac, 0.004)
        for line, cy_ in (('RAMPA', 262), ('DOS', 300), ('CAVALLEIROS', 338), ('1847', 380)):
            text(line, 'latin', x + BW / 2, y + cy_, BW * 0.8, 30, fg)
        continue
    rect(x + 8, y + 8, BW - 16, P - y - 16, ac, 0.004)
    rect(x + 16, y + 16, BW - 32, P - y - 32, bg, 0.006)
    text(zh, 'hei', x + BW / 2, y + (P - y) / 2, BW * 0.62, (P - y) * 0.84, fg, vertical=True)

cam = bpy.data.cameras.new('cam')
cam.type = 'ORTHO'
cam.ortho_scale = P * U
co = bpy.data.objects.new('cam', cam)
co.location = (P * U / 2, -P * U / 2, 10)
bpy.context.collection.objects.link(co)
sc = bpy.context.scene
sc.camera = co
sc.render.engine = 'BLENDER_WORKBENCH'
sc.display.shading.light = 'FLAT'
sc.display.shading.color_type = 'MATERIAL'
sc.view_settings.view_transform = 'Standard'
sc.render.resolution_x = sc.render.resolution_y = P
sc.render.filepath = os.path.join(OUT, '_signs_raw.png')
sc.render.image_settings.file_format = 'PNG'
bpy.ops.render.render(write_still=True)

# weathering: sun-faded colours, grime from the top edge, soot speckle
im = bpy.data.images.load(sc.render.filepath)
a = np.array(im.pixels[:], np.float32).reshape(P, P, 4)[::-1, :, :3]
lum = a.mean(-1, keepdims=True)
a = a * 0.82 + lum * 0.18
noise = tile_noise(P, 24, seed=11)
a *= (0.86 + 0.18 * noise)[..., None]
for k in range(len(FASCIA)):
    x, y = (k % 2) * FW, (k // 2) * FH
    g = np.linspace(0.78, 1.0, FH)[:, None, None] ** rng.uniform(0.5, 2.0)
    a[y:y + FH, x:x + FW] *= g
save('T_Signs_BC', blur(a, 1).clip(0, 1))
os.remove(sc.render.filepath)
print('SIGNS_DONE')

# ---- the post office fascia (red board with white lettering), its own 1024 x 256 texture
for o in list(bpy.data.objects):
    if o.type != 'CAMERA':
        bpy.data.objects.remove(o)
W2, H2 = 1024, 256
rect(0, 0, W2, H2, '#b3201f')
text('郵政局', 'hei', W2 * 0.3, H2 * 0.5, W2 * 0.42, H2 * 0.6, '#fbf6ea')
text('CORREIOS', 'latin', W2 * 0.73, H2 * 0.52, W2 * 0.4, H2 * 0.3, '#fbf6ea')
co.location = (W2 * U / 2, -H2 * U / 2, 10)
cam.ortho_scale = W2 * U
sc.render.resolution_x, sc.render.resolution_y = W2, H2
bpy.ops.render.render(write_still=True)
im = bpy.data.images.load(sc.render.filepath)
a = np.array(im.pixels[:], np.float32).reshape(H2, W2, 4)[::-1, :, :3]
a *= (0.88 + 0.14 * tile_noise(W2, 12, seed=5)[:H2])[..., None]
save('T_PostSign_BC', blur(a, 1).clip(0, 1))
os.remove(sc.render.filepath)
print('POST_DONE')

# ---- the 2010 sports-for-all billboard on the sports hall's avenue end (MH008): 2048 x 1024, only the wording legible
#      in the photo (全城動起來 / Participa a cidade inteira / 2010), colour dots in place of its crowd photo
for o in list(bpy.data.objects):
    if o.type != 'CAMERA':
        bpy.data.objects.remove(o)
W3, H3 = 2048, 1024
rect(0, 0, W3, H3, '#f3efe4')
rect(0, H3 - 150, W3, 150, '#f0b52e', 0.004)                                   # yellow foot band
rect(1180, 0, W3 - 1180, H3, '#f2c94c', 0.002)                                 # warm right panel
for k in range(70):                                                            # crowd of colour dots instead of the photo
    x, y = 120 + (k % 14) * 70 + (k // 14) % 2 * 35, 470 + (k // 14) * 62
    rect(x, y, 34, 34, ('#c8372d', '#2a63a8', '#3b8f4e', '#e07a2a', '#6b4ea0')[k % 5], 0.006)
text('全城動起來', 'hei', 560, 200, 980, 220, '#c8372d')
text('Participa a cidade inteira', 'latin', 560, 370, 900, 80, '#1d3f73')
text('2010', 'latin', 1620, 230, 700, 300, '#c8372d')
co.location = (W3 * U / 2, -H3 * U / 2, 10)
cam.ortho_scale = W3 * U
sc.render.resolution_x, sc.render.resolution_y = W3, H3
bpy.ops.render.render(write_still=True)
im = bpy.data.images.load(sc.render.filepath)
a = np.array(im.pixels[:], np.float32).reshape(H3, W3, 4)[::-1, :, :3]
a *= (0.9 + 0.12 * tile_noise(W3, 16, seed=7)[:H3])[..., None]
save('T_Billboard_BC', blur(a, 1).clip(0, 1))
os.remove(sc.render.filepath)
print('BILLBOARD_DONE')
