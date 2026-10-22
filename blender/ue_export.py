"""Unreal export of the estate: the web-bake model minus the surroundings, every edge chamfered for Nanite.

Run after build_estate.py --export:
  G:/Blender/blender.exe -b G:/Claude/mongha-ue/export/MongHa_2010.blend --factory-startup -P ue_export.py
Writes export/MongHa_2010_UE.fbx (imported by tools/ue_01_import.py).
"""
import math
import os

import bmesh
import bpy

EXPORT = r'G:\Claude\mongha-ue\export'
GONE = ('SM_Context_Massing', 'SM_SportsHall_Simple', 'SM_Estate_SlopeBlocks')   # user: estate only (round 3)
WIDTH = {'SM_Ground_Streets': 0.015}   # kerbs and steps; the rest 2 cm

for name in GONE:
    if name in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects[name])

for ob in [o for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith('SM_')]:
    n0 = len(ob.data.polygons)
    bm = bmesh.new()   # boxes come out with split vertices; weld them so the bevel sees shared edges
    bm.from_mesh(ob.data)
    slots = [s.material.name if s.material else '' for s in ob.material_slots]
    ac = [f for f in bm.faces if slots[f.material_index] == 'M_AC_Unit']   # markers.json 'ac' -> scanned units in UE
    if ac:
        bmesh.ops.delete(bm, geom=ac, context='FACES')
        print(f'AC boxes removed from {ob.name}: {len(ac)} faces')
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0005)
    bm.to_mesh(ob.data)
    bm.free()
    md = ob.modifiers.new('Bevel', 'BEVEL')
    md.width = WIDTH.get(ob.name, 0.02)
    md.segments = 2
    md.limit_method = 'ANGLE'
    md.angle_limit = math.radians(40)
    md.use_clamp_overlap = True
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.modifier_apply(modifier=md.name)
    print(f'BEVEL {ob.name} {n0} -> {len(ob.data.polygons)} faces')

bpy.ops.export_scene.fbx(filepath=os.path.join(EXPORT, 'MongHa_2010_UE.fbx'), use_selection=False, object_types={'MESH'},
                         apply_unit_scale=True, apply_scale_options='FBX_SCALE_UNITS', mesh_smooth_type='FACE',
                         use_mesh_modifiers=True, path_mode='AUTO', batch_mode='OFF')
print('UE_EXPORTED')
