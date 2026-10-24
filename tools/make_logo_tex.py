"""The 體育發展局 (Instituto do Desporto) logo on the sports hall's entrance gable (photo of 2026-10-24): refs/desporto_logo.png
(the user's copy of the logo) -> textures/T_Desporto_BC.png and T_Desporto_Mask.png, web/tex/desporto.jpg and desporto_a.jpg.
1024 px square, the logo centred across its width on white, the mask cutting it out.

Run:  python tools/make_logo_tex.py
"""
import os

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
N = 1024
logo = Image.open(os.path.join(ROOT, 'refs', 'desporto_logo.png')).convert('RGBA')
logo = logo.resize((N, round(logo.height * N / logo.width)), Image.LANCZOS)
sheet = Image.new('RGBA', (N, N), (255, 255, 255, 0))
sheet.alpha_composite(logo, (0, (N - logo.height) // 2))
rgb = Image.new('RGB', (N, N), (255, 255, 255))
rgb.paste(sheet, mask=sheet.split()[3])
mask = sheet.split()[3].convert('RGB')
rgb.save(os.path.join(ROOT, 'textures', 'T_Desporto_BC.png'))
mask.save(os.path.join(ROOT, 'textures', 'T_Desporto_Mask.png'))
rgb.save(os.path.join(ROOT, 'web', 'tex', 'desporto.jpg'), quality=92)
mask.save(os.path.join(ROOT, 'web', 'tex', 'desporto_a.jpg'), quality=92)
print('logo', logo.size, '->', N, N)
