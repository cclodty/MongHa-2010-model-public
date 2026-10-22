# Runs inside Unreal Editor: ground-level wear and the bougainvillea colour.
#  - damp / dirt stains around the planter seats, along the gallery walls and across the courtyard, litter at the stair feet
#  - library planter bushes flagged 'bouga' in markers.json get a magenta foliage instance
# Idempotent: decals are labelled DECAL_* and replaced on a rerun. Needs ue_08_dress.py (FAB_Shrub_*) first.
import json
import math
import random

import unreal

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
at = unreal.AssetToolsHelpers.get_asset_tools()
MAP = '/Game/Maps/MongHa2010'
if not unreal.EditorLevelLibrary.get_editor_world().get_path_name().startswith(MAP):
    les.load_level(MAP)
M = json.load(open(r'G:\Claude\mongha-ue\export\markers.json', encoding='utf-8'))
rng = random.Random(1990)
acts = {a.get_actor_label(): a for a in eas.get_all_level_actors()}
for lab, a in list(acts.items()):
    if lab.startswith('DECAL_'):
        eas.destroy_actor(a)
DEC = '/Game/Fab/Megascans/Decals/'
LX, LZ = M['library']
CX0, CX1, CZ0, CZ1, GW = 62.0, 104.0, 13.0, 119.0, 3.0


def child(name, parent_path, scalars=None, vectors=None):
    parent = unreal.load_asset(parent_path)
    if parent is None:
        print('missing', parent_path)
        return None
    path = f'/Game/MongHa/Materials/{name}'
    mi = unreal.load_asset(path) if eal.does_asset_exist(path) else at.create_asset(
        name, '/Game/MongHa/Materials', unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    mel.set_material_instance_parent(mi, parent)
    for k, v in (scalars or {}).items():
        mel.set_material_instance_scalar_parameter_value(mi, k, v)
    for k, v in (vectors or {}).items():
        mel.set_material_instance_vector_parameter_value(mi, k, unreal.LinearColor(*v))
    mel.update_material_instance(mi)
    eal.save_loaded_asset(mi)
    return mi


def ue(x, y, z):
    return unreal.Vector(x * 100, z * 100, y * 100)


def ground_decal(label, mat, x, z, size, yaw, depth=30.0, folder='Dressing/GroundDecals'):
    act = eas.spawn_actor_from_class(unreal.DecalActor, ue(x, 0.08, z), unreal.Rotator(0, -90, yaw))   # pitch -90: project down
    act.set_decal_material(mat)
    act.get_editor_property('decal').set_editor_property('decal_size', unreal.Vector(depth, size[0], size[1]))
    act.set_actor_label(label)
    act.set_folder_path(folder)
    return act


STAIN = child('MI_Stain_Soft', DEC + 'Oil_Stain_semlsbi/Medium/semlsbi_tier_2/Materials/MI_semlsbi',
              {'Opacity Intensity': 0.45, 'Saturation': 0.3, 'Brightness': 1.25, 'Contrast': 0.85})
LITTER = unreal.load_asset(DEC + 'Small_Garbage_Scatter_shmpulh/Medium/shmpulh_tier_2/Materials/MI_shmpulh')
n = 0
if STAIN:
    for x, z, r in M['trees']:   # young trees stand in the planter seats: damp soil washes out round their bases
        if r >= 1.4 or not (CX0 < x < CX1 and CZ0 < z < CZ1):
            continue
        for _ in range(2):
            ground_decal(f'DECAL_Planter_{n:03d}', STAIN, x + rng.uniform(-2.2, 2.2), z + rng.uniform(-1.4, 1.4),
                         (rng.uniform(70, 150), rng.uniform(60, 120)), rng.uniform(0, 360))
            n += 1
    for xw in (CX0 + 0.35, CX1 - 0.35):   # gallery decks: grime where the deck meets the flats
        for z in range(int(CZ0 + GW) + 4, int(CZ1 - GW) - 2, 9):
            act = eas.spawn_actor_from_class(unreal.DecalActor, ue(xw, 3.95, z + rng.uniform(-2, 2)),   # deck top ~3.8 m (GF)
                                             unreal.Rotator(0, -90, rng.uniform(0, 360)))
            act.set_decal_material(STAIN)
            act.get_editor_property('decal').set_editor_property('decal_size', unreal.Vector(40.0, rng.uniform(50, 110), rng.uniform(40, 80)))
            act.set_actor_label(f'DECAL_Deck_{n:03d}')
            act.set_folder_path('Dressing/GroundDecals')
            n += 1
    for _ in range(18):   # general wear across the open paving
        ground_decal(f'DECAL_Court_{n:03d}', STAIN, rng.uniform(CX0 + GW + 2, CX1 - GW - 2), rng.uniform(CZ0 + GW + 2, CZ1 - GW - 2),
                     (rng.uniform(80, 220), rng.uniform(60, 160)), rng.uniform(0, 360))
        n += 1
if LITTER:
    for xs, side in ((CX0 + GW, 1), (CX1 - GW, -1)):   # foot of the four dog-leg stairs (STAIRS = LZ +- 29)
        for zc in (LZ + 29, LZ - 29):
            ground_decal(f'DECAL_Litter_{n:03d}', LITTER, xs + side * rng.uniform(0.6, 1.4), zc + rng.uniform(-2.0, 2.0),
                         (rng.uniform(60, 100), rng.uniform(50, 90)), rng.uniform(0, 360))
            n += 1
print('ground decals', n)

# ---------------------------------------------------------------- bougainvillea on the library planters
BOUGA = child('MI_Bougainvillea', '/Game/Megaplant_Library/Tree_Japanese_Medlar/Materials/MI_Japanese_Medlar_01_Foliage',
              vectors={'BaseColor Tint': (0.85, 0.08, 0.95, 1.0), 'BaseColor Tint Leaves': tuple(globals().get('BOUGA_TINT', (0.9, 0.1, 0.9, 1.0))),
                       'Translucency Tint Leaves': (0.9, 0.2, 0.55, 0.0)})
nb = 0
if BOUGA:
    for i, s in enumerate(M['shrubs']):
        a = acts.get(f'FAB_Shrub_{i:02d}')
        if a is None or not s.get('bouga'):
            continue
        comp = a.get_editor_property('skeletal_mesh_component')
        mats = comp.get_materials()
        slot = next((k for k, m in enumerate(mats) if m and 'Foliage' in m.get_name()), len(mats) - 1)
        comp.set_material(slot, BOUGA)
        nb += 1
print('bougainvillea bushes', nb)
les.save_current_level()
print('DETAIL_DONE')
