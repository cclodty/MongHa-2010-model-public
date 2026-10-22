"""Package the web viewer as a standalone static website for other hosts (Netlify, GitHub Pages, itch.io, ...).

Writes export/mongha_site/ and export/mongha_2010_site.zip:
  index.html  (full HTML document; loads three.js etc. from the jsDelivr CDN, so viewers need internet)
  assets/     plain .glb models, lightmaps, sun masks, manifest.json
  tex/        textures and sky; draco/  the Draco mesh decoder
  README.txt  how to upload; CREDITS.txt  sources and licences
  og.jpg      1200 x 630 share thumbnail (the 一樓走廊 view, captured from the viewer canvas)
Run after web_bake.py:  py -3 tools/export_site.py [--url=https://your-site/]
The URL goes into the Open Graph / Twitter tags: Facebook, WhatsApp etc. only show the thumbnail for an absolute URL.
"""
import json
import os
import shutil
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(ROOT, 'web')
OUT = os.path.join(ROOT, 'export', 'mongha_site')
ZIP = os.path.join(ROOT, 'export', 'mongha_2010_site.zip')
SITE_URL = next((a.split('=', 1)[1] for a in sys.argv if a.startswith('--url=')), 'https://mongha2010site.vercel.app/')   # user's Vercel deploy
SITE_URL = SITE_URL.rstrip('/') + '/'
TITLE = '望廈平民新邨 2010'
DESC = '澳門望廈平民新邨（1988–2011）拆卸前的可漫遊三維重建'

os.makedirs(OUT, exist_ok=True)
for n in os.listdir(OUT):   # empty it rather than delete it: a local preview server may hold the folder open
    full = os.path.join(OUT, n)
    shutil.rmtree(full) if os.path.isdir(full) else os.remove(full)
for d in ('assets', 'tex', 'draco'):
    os.makedirs(os.path.join(OUT, d))

man = json.load(open(os.path.join(WEB, 'assets', 'manifest.json'), encoding='utf-8'))
for f in man['files']:   # plain GLB instead of the base64 wrapper claude.ai needs
    shutil.copy2(os.path.join(WEB, 'assets', f['glb']), os.path.join(OUT, 'assets', f['glb']))
    f.pop('packed', None)
    f.pop('packed_bytes', None)
for e in man['objects'].values():
    for k in ('lightmap', 'mask'):
        if e.get(k):
            shutil.copy2(os.path.join(WEB, 'assets', e[k]), os.path.join(OUT, 'assets', e[k]))
with open(os.path.join(OUT, 'assets', 'manifest.json'), 'w', encoding='utf-8') as fh:
    json.dump(man, fh, ensure_ascii=False)

page = open(os.path.join(WEB, 'index.html'), encoding='utf-8').read()
def tex_used(n):   # photo sets load their normal/roughness maps as name + '_n' / '_r'
    base = n[:-4]
    for suf in ('_n', '_r'):
        if base.endswith(suf) and ("'" + base[:-2] + "'") in page:
            return True
    return ("'" + base + "'") in page or n in ('sky.jpg', 'streaks.jpg', 'leaves.jpg', 'leaves_a.jpg')


used_tex = sorted(n for n in os.listdir(os.path.join(WEB, 'tex')) if n.endswith('.jpg') and tex_used(n))
for n in used_tex:
    shutil.copy2(os.path.join(WEB, 'tex', n), os.path.join(OUT, 'tex', n))
for n in os.listdir(os.path.join(WEB, 'draco')):
    shutil.copy2(os.path.join(WEB, 'draco', n), os.path.join(OUT, 'draco', n))

shutil.copy2(os.path.join(WEB, 'og.jpg'), os.path.join(OUT, 'og.jpg'))
img = SITE_URL + 'og.jpg'
share = ''.join(f'<meta {k}="{n}" content="{v}">\n' for k, n, v in (
    ('name', 'description', DESC), ('property', 'og:type', 'website'), ('property', 'og:site_name', TITLE),
    ('property', 'og:title', TITLE), ('property', 'og:description', DESC), ('property', 'og:url', SITE_URL),
    ('property', 'og:locale', 'zh_HK'), ('property', 'og:image', img), ('property', 'og:image:secure_url', img),
    ('property', 'og:image:type', 'image/jpeg'), ('property', 'og:image:width', '1200'), ('property', 'og:image:height', '630'),
    ('property', 'og:image:alt', '望廈平民新邨一樓走廊（三維重建）'), ('name', 'twitter:card', 'summary_large_image'),
    ('name', 'twitter:title', TITLE), ('name', 'twitter:description', DESC), ('name', 'twitter:image', img)))
share += f'<link rel="canonical" href="{SITE_URL}">\n'
doc = ('<!doctype html>\n<html lang="zh-Hant">\n<head>\n<meta charset="utf-8">\n'
       + share
       + page.replace('<div id="stage">', '</head>\n<body>\n<div id="stage">', 1)
       + '\n</body>\n</html>\n')
doc = doc.replace('<meta name="claude:viewport-fit-sides" content="cover">\n', '')
open(os.path.join(OUT, 'index.html'), 'w', encoding='utf-8').write(doc)

open(os.path.join(OUT, 'README.txt'), 'w', encoding='utf-8').write('''望廈平民新邨 2010 — 網頁版（獨立網站檔案）

這個資料夾是一個完整的靜態網站，上載到任何網站寄存服務後，別人用瀏覽器開連結就能看，手機也可以。
注意：直接在電腦上雙擊 index.html 是開不到的（瀏覽器不准網頁讀取電腦上的其他檔案），一定要放上網站。
觀看的人需要連上互聯網（網頁會從 jsDelivr 載入 three.js 等程式庫）。

上載方法（任選一個，都是免費的）：

1. Netlify Drop（最簡單）
   開 https://app.netlify.com/drop ，把整個 mongha_site 資料夾拖進去，幾秒後就有公開網址。
   想網址長期保留，需要用電郵註冊一個 Netlify 帳戶。

2. itch.io
   登入後選「Upload new project」，Kind of project 選「HTML」，上載 mongha_2010_site.zip，
   勾選「This file will be played in the browser」，建議把視窗大小設為 1280 × 760 並開啟全螢幕按鈕。

3. GitHub Pages
   開一個新的公開 repository，把資料夾內所有檔案上載，再在 Settings → Pages 選 main 分支。

4. Cloudflare Pages
   Workers & Pages → Create → Pages → Upload assets，上載整個資料夾。

5. Vercel（目前使用中：''' + SITE_URL + '''）
   用新的檔案取代舊的再部署即可（Framework 選 Other，不需要 build 指令）。

分享縮圖：og.jpg（一樓走廊視點）已寫進網頁的 Open Graph 標籤，網址指向 ''' + SITE_URL + '''og.jpg。
重新部署後，Facebook 可能仍顯示舊的預覽，可在 https://developers.facebook.com/tools/debug/ 貼上網址按「重新抓取」。
如果網站網址改了，縮圖網址也要跟着改（重新匯出時加 --url=新網址）。

檔案總大小約 30 MB，第一次開需要一點時間載入。
''')
open(os.path.join(OUT, 'CREDITS.txt'), 'w', encoding='utf-8').write('''出處與授權

模型：按居民在 Facebook 群組「老餅話當年」分享的舊相、2008 年 Google 街景、建築師 CBMoreno 的資料，
以及 OpenStreetMap 的地段資料重建。舊相本身沒有包含在這個網站內。
未有相片根據的細節（例如部分座的顏色次序、前半中庭的佈置）是推斷。

天空：Poly Haven「Kloofendal 48d Partly Cloudy (Pure Sky)」，CC0。
材質：Poly Haven painted_plaster_wall、concrete_floor_worn_001、asphalt_02、clay_roof_tiles_02、
      painted_metal_shutter，CC0。其餘貼圖（紙皮石、窗內、衣物、招牌、樹葉等）由程式生成。
程式庫：three.js（MIT）、three-mesh-bvh（MIT）、n8ao（ISC）、postprocessing（Zlib），經 jsDelivr 載入；
        draco/ 內的 Draco 解碼器（Apache License 2.0，Google）。
字型：Google Fonts（霞鶩文楷 TC、Noto Sans TC、IBM Plex Mono，OFL）。
''')

if os.path.exists(ZIP):
    os.remove(ZIP)
with zipfile.ZipFile(ZIP, 'w', zipfile.ZIP_DEFLATED) as z:
    for base, _, names in os.walk(OUT):
        for n in names:
            full = os.path.join(base, n)
            z.write(full, os.path.relpath(full, OUT))
size = sum(os.path.getsize(os.path.join(b, n)) for b, _, ns in os.walk(OUT) for n in ns)
print('URL', SITE_URL)
print('SITE', OUT, round(size / 1e6, 1), 'MB;', 'ZIP', ZIP, round(os.path.getsize(ZIP) / 1e6, 1), 'MB; textures', len(used_tex))
