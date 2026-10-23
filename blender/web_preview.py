"""Export the scene for the web viewer without baking, for watching changes as they are made (seconds instead of a bake).

Run on the exported scene:
  blender -b export/MongHa_2010.blend -P blender/web_preview.py -- [--out=export/web_preview] [--bevel]
or the whole loop (build, export, pack):  python tools/preview.py

Writes <out>/assets/: one Draco GLB per family, each also wrapped as .glb.json for claude.ai (see tools/pack_web.py), and
manifest.json with "baked": false. web/index.html then shades everything live: the sun with shadow maps, the HDRI for sky
light. Same trees, materials and views as web_bake.py; the surrounding towers stay out, as there.
"""
import base64
import json
import math
import os
import sys
import time

import bpy

ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
opt = {a.split('=', 1)[0]: (a.split('=', 1)[1] if '=' in a else True) for a in ARGS if a.startswith('--')}
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(os.path.abspath(opt.get('--out', os.path.join(ROOT, 'export', 'web_preview'))), 'assets')
os.makedirs(OUT, exist_ok=True)
for n in os.listdir(OUT):   # stale families would otherwise linger in the folder
    if n.endswith(('.glb', '.glb.json')) or n == 'manifest.json':
        os.remove(os.path.join(OUT, n))
SKY = json.load(open(os.path.join(ROOT, 'export', 'sky.json'), encoding='utf-8'))
MARK = json.load(open(os.path.join(ROOT, 'export', 'markers.json'), encoding='utf-8'))
BEVEL = {'SM_Estate_FRONT', 'SM_Estate_BACK', 'SM_Estate_NW', 'SM_Estate_SE', 'SM_Estate_SlopeBlocks', 'SM_Galleries_Bridges', 'SM_Library', 'SM_Courtyard', 'SM_SportsHall_Simple'}
t0 = time.time()

sys.path.insert(0, HERE)
import web_trees  # noqa: E402
tc = bpy.data.collections.new('WebTrees')
bpy.context.scene.collection.children.link(tc)
web_trees.build(MARK, tc)
for gone in ('SM_Context_Massing',):
    if gone in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects[gone])
src = sorted((o for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith('SM_')), key=lambda o: o.name)


def select_only(ob):
    bpy.context.view_layer.update()
    for o in list(bpy.context.view_layer.objects):
        o.select_set(False)
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob


if '--bevel' in opt:   # web_bake.py's chamfer, so corners catch the sun; slower, and the GLBs grow
    for ob in src:
        if ob.name in BEVEL:
            md = ob.modifiers.new('Bevel', 'BEVEL')
            md.width, md.segments, md.limit_method = 0.025, 2, 'ANGLE'
            md.angle_limit = math.radians(40)
            md.use_clamp_overlap = True
            select_only(ob)
            bpy.ops.object.modifier_apply(modifier=md.name)

mat_info = {}
for m in bpy.data.materials:
    b = m.node_tree.nodes.get('Principled BSDF') if m.use_nodes else None
    if b:
        c = b.inputs['Base Color'].default_value
        mat_info[m.name] = dict(color=[round(c[0], 4), round(c[1], 4), round(c[2], 4)],
                                rough=round(b.inputs['Roughness'].default_value, 3), metal=round(b.inputs['Metallic'].default_value, 3))
manifest = dict(baked=False, objects={}, sun=SKY['sun_dir_site'], sun_strength=SKY['sun_strength'], sun_color=SKY['sun_color'],
                sky_K=SKY['web_sky_K'], horizon=SKY['horizon_rgb_web'], views=MARK['views'], materials=mat_info, files=[],
                built=time.strftime('%Y-%m-%d %H:%M'))
for ob in src:
    manifest['objects'][ob.name] = dict(family=ob.name, kind='RT')
    for o in bpy.context.view_layer.objects:
        o.select_set(o is ob)
    path = os.path.join(OUT, ob.name + '.glb')
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True, export_apply=False,
                              export_texcoords=True, export_normals=True, export_materials='EXPORT', export_image_format='NONE',
                              export_vertex_color='NONE',
                              export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=7,
                              export_draco_position_quantization=16, export_draco_normal_quantization=10,
                              export_draco_texcoord_quantization=14,
                              export_cameras=False, export_lights=False, export_extras=False, export_yup=True)
    data = open(path, 'rb').read()
    packed = ob.name + '.glb.json'
    with open(os.path.join(OUT, packed), 'w', encoding='ascii') as fh:
        json.dump({'format': 'glb-base64', 'name': ob.name + '.glb', 'data': base64.b64encode(data).decode('ascii')}, fh)
    manifest['files'].append(dict(family=ob.name, glb=ob.name + '.glb', bytes=len(data), packed=packed,
                                  packed_bytes=os.path.getsize(os.path.join(OUT, packed))))
    print('EXPORTED', ob.name, len(data) // 1024, 'KB')
with open(os.path.join(OUT, 'manifest.json'), 'w', encoding='utf-8') as fh:
    json.dump(manifest, fh, ensure_ascii=False, indent=1)
print('WEB_PREVIEW_DONE', OUT, sum(f['packed_bytes'] for f in manifest['files']) // 1024, 'KB', f'{time.time() - t0:.0f}s')
