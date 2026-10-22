# Runs inside Unreal Editor: bring the web version's photo / pattern textures into the Unreal materials.
#  - Poly Haven CC0 sets (cc0/, 2K): painted_metal_shutter, clay_roof_tiles_02 -> /Game/MongHa/Textures/PH/T_PH_<name>_{BC,R,N}
#  - normal maps generated for three.js are OpenGL style (green up): T_Mosaic2_N, T_CourtPave_N and the Poly Haven nor_gl
#    maps get flip_green_channel so Unreal (DirectX) reads them the right way round.
import os

import unreal

eal = unreal.EditorAssetLibrary
at = unreal.AssetToolsHelpers.get_asset_tools()
CC0 = r'G:\Claude\mongha-ue\cc0'
DEST = '/Game/MongHa/Textures/PH'
SETS = {'painted_metal_shutter': 'Shutter', 'clay_roof_tiles_02': 'Roof'}
MAPS = {'Diffuse.jpg': 'BC', 'Rough.jpg': 'R', 'nor_gl.jpg': 'N'}
if not eal.does_directory_exist(DEST):
    eal.make_directory(DEST)

tasks = []
for folder, short in SETS.items():
    for fn, suffix in MAPS.items():
        src = os.path.join(CC0, folder, fn)
        if not os.path.exists(src):
            print('missing', src)
            continue
        t = unreal.AssetImportTask()
        t.set_editor_property('filename', src)
        t.set_editor_property('destination_path', DEST)
        t.set_editor_property('destination_name', f'T_PH_{short}_{suffix}')
        t.set_editor_property('automated', True)
        t.set_editor_property('replace_existing', True)
        t.set_editor_property('save', False)
        tasks.append(t)
at.import_asset_tasks(tasks)


def fix(path, normal=False, linear=False, flip_green=False):
    tex = unreal.load_asset(path)
    if tex is None:
        print('missing', path)
        return
    if normal:
        tex.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_NORMALMAP)
        tex.set_editor_property('srgb', False)
    elif linear:
        tex.set_editor_property('srgb', False)
    tex.set_editor_property('flip_green_channel', flip_green)
    eal.save_loaded_asset(tex)
    print('texture', path.split('/')[-1], 'normal' if normal else 'linear' if linear else 'srgb', 'flipG' if flip_green else '')


for short in SETS.values():
    fix(f'{DEST}/T_PH_{short}_BC')
    fix(f'{DEST}/T_PH_{short}_R', linear=True)
    fix(f'{DEST}/T_PH_{short}_N', normal=True, flip_green=True)
for name in ('T_Mosaic2_N', 'T_CourtPave_N'):   # make_web_textures.py writes OpenGL normals for three.js
    fix(f'/Game/MongHa/Textures/{name}', normal=True, flip_green=True)
print('TEXTURES_DONE')
