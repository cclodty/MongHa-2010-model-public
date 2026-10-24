"""Sign textures made from images rather than lettered in Blender (make_signs.py):

- the 體育發展局 (Instituto do Desporto) logo on the sports hall's entrance gable (user, 2026-10-24): refs/desporto_logo.png
  -> T_Desporto_BC / T_Desporto_Mask, web/tex/desporto.jpg / desporto_a.jpg (1024 px square, the logo across its width);
- the hall's name lettered straight on its white gable (user, 2026-10-24), spaced out across it with the Portuguese line
  nearly as wide as in the user's photo of the entrance -> T_HallName_BC / T_HallName_Mask, web/tex/hallname.jpg /
  hallname_a.jpg (fonts of this Linux machine: WenQuanYi Zen Hei, Liberation Sans);
- the post office's red fascia lettered as in MH022, 郵政 and Correios in white (user, 2026-10-24: its lettering only,
  not the photo; the Macau Post emblem between them left out) -> T_PostSign_BC, web/tex/post.jpg;
- the real boards of 利誠美食 (fascia and blade sign, MH013) and 望廈托兒所 (photo 2), cut out of the photos and squared up
  (user, 2026-10-24: paste the photos' signs on; 鞋宜樂's photo was too skewed, its lettered board is back)
  -> T_PhotoSigns_BC, web/tex/photosigns.jpg. Cells as PHOTO_SIGNS in blender/build_estate.py.

Run:  python tools/make_sign_tex.py   (Pillow, numpy)
"""
import glob
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEX, WEB = os.path.join(ROOT, 'textures'), os.path.join(ROOT, 'web', 'tex')


def save(img, name, web):
    img.save(os.path.join(TEX, name + '.png'))
    img.convert('RGB').save(os.path.join(WEB, web + '.jpg'), quality=92)


def masked(rgba, name, web):
    """RGB on white where it is clear (so the cut edges do not darken) and the alpha as its own mask."""
    rgb = Image.new('RGB', rgba.size, (255, 255, 255))
    rgb.paste(rgba, mask=rgba.split()[3])
    a = rgba.split()[3].convert('RGB')
    save(rgb, f'T_{name}_BC', web)
    save(a, f'T_{name}_Mask', web + '_a')


# ---- the logo
N = 1024
logo = Image.open(os.path.join(ROOT, 'refs', 'desporto_logo.png')).convert('RGBA')
logo = logo.resize((N, round(logo.height * N / logo.width)), Image.LANCZOS)
sheet = Image.new('RGBA', (N, N), (255, 255, 255, 0))
sheet.alpha_composite(logo, (0, (N - logo.height) // 2))
masked(sheet, 'Desporto', 'desporto')

# ---- the hall's name, 5.86 x 1.3 m on the gable: five characters ~0.68 m high spread across it, under them the
#      Portuguese line ~0.4 m high and about as wide (the user's photo of the entrance), dark grey
W2, H2, K = 2048, 456, 2
cov = Image.new('L', (W2, H2), 0)
d = ImageDraw.Draw(cov)
cjk = ImageFont.truetype('/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc', 118 * K)
for i, ch in enumerate('望廈體育館'):
    d.text(((i + 0.5) * W2 / 5, 64 * K), ch, fill=255, font=cjk, anchor='mm', stroke_width=3 * K, stroke_fill=255)   # bold, as cast
size = 60 * K
lat = ImageFont.truetype('/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf', size)
while d.textlength('Pavilhão de Mong-Há', font=lat) < 0.9 * W2:
    size += K
    lat = ImageFont.truetype('/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf', size)
d.text((W2 / 2, 176 * K), 'Pavilhão de Mong-Há', fill=255, font=lat, anchor='mm')
rgba = Image.new('RGBA', (W2, H2), (0x34, 0x33, 0x2f, 0))
rgba.putalpha(cov)
masked(rgba.resize((W2 // K, H2 // K), Image.LANCZOS), 'HallName', 'hallname')

# ---- the post office's fascia, 4.36 x 0.99 m: 郵 and 政 spaced out on its left half, Correios on its right (MH022)
W3, H3 = 2048, 464
img = Image.new('RGB', (W3 * K, H3 * K), (0xb5, 0x1e, 0x1c))
d = ImageDraw.Draw(img)
white = (0xf6, 0xf1, 0xe8)
cjk3 = ImageFont.truetype('/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc', 205 * K)
for ch, cx in (('郵', 0.17), ('政', 0.355)):
    d.text((cx * W3 * K, 0.5 * H3 * K), ch, fill=white, font=cjk3, anchor='mm', stroke_width=4 * K, stroke_fill=white)
lat3 = ImageFont.truetype('/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf', 190 * K)
d.text((0.735 * W3 * K, 0.52 * H3 * K), 'Correios', fill=white, font=lat3, anchor='mm')
img = img.resize((W3, H3), Image.LANCZOS)
a = np.asarray(img, np.float32) * np.linspace(1.0, 0.9, W3)[None, :, None]   # a little darker towards its far end
save(Image.fromarray(a.clip(0, 255).astype(np.uint8)), 'T_PostSign_BC', 'post')

# ---- the photographed boards
PHOTOS = os.path.join(ROOT, 'photos')
src = lambda pat: Image.open(glob.glob(os.path.join(PHOTOS, '**', pat), recursive=True)[0]).convert('RGB')


def square_up(img, quad, w, h, sharp=80, neutral=False):
    """The photo's quadrilateral (TL, TR, BR, BL, px) as a w x h image, its contrast lifted alike in all channels;
    neutral: its brightest half (a white board) made grey-neutral."""
    A, b = [], []
    for (u, v), (x, y) in zip(((0, 0), (w, 0), (w, h), (0, h)), quad):
        A.append([u, v, 1, 0, 0, 0, -u * x, -v * x])
        b.append(x)
        A.append([0, 0, 0, u, v, 1, -u * y, -v * y])
        b.append(y)
    c = np.linalg.solve(np.array(A, float), np.array(b, float))
    out = img.transform((w, h), Image.PERSPECTIVE, tuple(c), Image.BICUBIC)
    if neutral:
        a = np.asarray(out, np.float32)
        lum = a.mean(axis=2)
        ref = np.median(a[lum > np.median(lum)], axis=0)
        out = Image.fromarray(np.clip(a * (ref.mean() / ref), 0, 255).astype(np.uint8))
    out = ImageOps.autocontrast(out, cutoff=0.5, preserve_tone=True)
    return out.filter(ImageFilter.UnsharpMask(radius=2, percent=sharp, threshold=2)) if sharp else out


m13, p2 = src('MH013_*'), src('相2_*')
CELLS = {   # name: (photo, TL, TR, BR, BL, cell x0, y0, x1, y1 in the 2048 px atlas, share of the cell's width it fills,
    #         sharpening, white board?). 利誠美食's fascia: up to where the next shop's awning hides it, the rest of the
    #         board left white
    'lisheng': (m13, ((318, 263), (430, 225.8), (430, 283.2), (321, 305)), (0, 0, 2048, 253), 0.66, 80, True),
    'nursery': (p2, ((1340, 538), (1652, 536), (1653, 593), (1340, 595)), (0, 650, 2048, 866), 1.0, 0, False),
    'lisheng_blade': (m13, ((208, 210), (296.5, 216.5), (296.5, 273), (208, 271.5)), (0, 870, 640, 1311), 1.0, 80, False),
}
atlas = Image.new('RGB', (2048, 2048), (128, 128, 128))
for name, (img, quad, (x0, y0, x1, y1), share, sharp, neutral) in CELLS.items():
    w = round((x1 - x0) * share)
    board = square_up(img, quad, w, y1 - y0, sharp, neutral)
    if w < x1 - x0:   # the board runs on in the colour of its right edge
        atlas.paste(board.crop((w - 6, 0, w - 2, y1 - y0)).resize((1, 1), Image.BOX).getpixel((0, 0)), (x0 + w, y0, x1, y1))
    atlas.paste(board, (x0, y0))
save(atlas, 'T_PhotoSigns_BC', 'photosigns')
print('sign textures done')
