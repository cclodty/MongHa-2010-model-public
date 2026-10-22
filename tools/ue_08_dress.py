# Runs inside Unreal Editor: set dressing from Fab content — Megaplant trees/shrubs, cars, potted plants, leak/oil/garbage decals.
# Idempotent: everything it spawns is labelled FAB_* and removed on the next run.
import json
import math
import random

import unreal

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
eal = unreal.EditorAssetLibrary
MAP = '/Game/Maps/MongHa2010'
if not unreal.EditorLevelLibrary.get_editor_world().get_path_name().startswith(MAP):
    les.load_level(MAP)
world = unreal.EditorLevelLibrary.get_editor_world()
M = json.load(open(r'G:\Claude\mongha-ue\export\markers.json', encoding='utf-8'))
rng = random.Random(2010)

for a in eas.get_all_level_actors():
    if a.get_actor_label().startswith('FAB_'):
        eas.destroy_actor(a)


def ue(x, y, z):
    """site metres (x along avenue, y up, z into site) -> UE cm"""
    return unreal.Vector(x * 100, z * 100, y * 100)


def trace(a, b):
    h = unreal.SystemLibrary.line_trace_single(world, a, b, unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, True, [],
                                               unreal.DrawDebugTrace.NONE, True)
    if h is None:
        return None
    t = h.to_tuple()
    if not t[0]:
        return None
    return t[4], t[7], (t[9].get_actor_label() if t[9] else '')


def ground(x, z, top=60.0):
    hit = trace(ue(x, top, z), ue(x, -5, z))
    return hit[0].z / 100 if hit else 0.0


def load(p):
    a = unreal.load_asset(p)
    if a is None:
        print('missing', p)
    return a


def spawn_skm(label, mesh, loc, yaw, scale, folder):
    act = eas.spawn_actor_from_class(unreal.SkeletalMeshActor, loc, unreal.Rotator(0, 0, yaw))
    comp = act.get_editor_property('skeletal_mesh_component')
    try:
        comp.set_skeletal_mesh_asset(mesh)
    except Exception:
        comp.set_skinned_asset_and_update(mesh)
    act.set_actor_scale3d(unreal.Vector(scale, scale, scale))
    act.set_actor_label(label)
    act.set_folder_path(folder)
    return act


def spawn_sm(label, mesh, loc, rot, scale, folder):
    act = eas.spawn_actor_from_object(mesh, loc, rot)
    act.set_actor_scale3d(unreal.Vector(scale, scale, scale))
    act.set_actor_label(label)
    act.set_folder_path(folder)
    return act


# ---------------------------------------------------------------- trees (Megaplants, Nanite foliage skeletal meshes)
ML = '/Game/Megaplant_Library/'
TREES = {
    'hazelA': load(ML + 'Tree_Common_Hazel/Tree_Common_Hazel_01/Tree_Common_Hazel_01_A'),
    'hazelB': load(ML + 'Tree_Common_Hazel/Tree_Common_Hazel_01/Tree_Common_Hazel_01_B'),   # 3.5 m
    'medlarA': load(ML + 'Tree_Japanese_Medlar/Tree_Japanese_Medlar_01/Tree_Japanese_Medlar_01_A'),
    'medlarB': load(ML + 'Tree_Japanese_Medlar/Tree_Japanese_Medlar_01/Tree_Japanese_Medlar_01_B'),
    'bamboo': load(ML + 'Tree_Giant_Bamboo/Tree_Giant_Bamboo_01/Tree_Giant_Bamboo_01_A'),
}
SHRUB = load(ML + 'Tree_Japanese_Medlar/Tree_Japanese_Medlar_01/Tree_Japanese_Medlar_01_D')
SHRUB_C = load(ML + 'Tree_Japanese_Medlar/Tree_Japanese_Medlar_01/Tree_Japanese_Medlar_01_C')
YOUNG = [TREES['medlarA'], TREES['medlarB'], TREES['hazelB']]


def native_height(mesh):
    try:
        b = mesh.get_bounds()
        return max(100.0, 2 * b.box_extent.z)
    except Exception:
        return 600.0


n_tree = 0
for i, (x, z, r) in enumerate(M['trees']):
    if r < 1.4:   # round 6: young trees in the planter seats (photo 14); scale kept near 1 so leaves stay life-size
        mesh = rng.choice(YOUNG)
        H = (3.2 + 1.6 * r) * rng.uniform(0.9, 1.1) * 100
        sc = max(0.9, min(1.35, H / native_height(mesh)))
        spawn_skm(f'FAB_Tree_{i:02d}', mesh, ue(x, ground(x, z), z), rng.uniform(0, 360), sc, 'Dressing/Trees')
        n_tree += 1
        continue
    kind = rng.choice(['hazelA', 'medlarA', 'medlarB', 'hazelA'])
    scale = 0.75 + 0.4 * r + rng.uniform(-0.15, 0.15)            # r = canopy radius hint from the Blender layout (1.9-3 m)
    if i >= 25 and rng.random() < 0.12:                          # a few bamboo clumps in the back gardens
        kind, scale = 'bamboo', rng.uniform(0.5, 0.65)
    spawn_skm(f'FAB_Tree_{i:02d}', TREES[kind], ue(x, ground(x, z), z), rng.uniform(0, 360), scale, 'Dressing/Trees')
    n_tree += 1

# planter shrubs (replace the old blob bushes)
for i, s in enumerate(M['shrubs']):
    x, y, z = s['p']
    mesh = SHRUB_C if rng.random() < 0.3 else SHRUB
    sc = s['s'] * (1.0 if mesh == SHRUB else 0.75) * rng.uniform(0.85, 1.15)     # ~1-1.3 m bushes
    spawn_skm(f'FAB_Shrub_{i:02d}', mesh, ue(x, y, z), rng.uniform(0, 360), sc, 'Dressing/Shrubs')

# ---------------------------------------------------------------- cars on 慕拉士大馬路 (asphalt z -21..-3; drive on the left)
CAR = load('/Game/Fab/Generic_Sedan_Car/generic_sedan_car/StaticMeshes/generic_sedan_car')
PAINT = []
for k, h in dict(White='#e6e6e1', Silver='#a7abae', Black='#121314', Maroon='#4e1414', Navy='#1a2846', Champagne='#b5a688', White2='#ecebe6').items():
    path = f'/Game/MongHa/Materials/MI_CarPaint_{k}'
    mi = unreal.load_asset(path) if eal.does_asset_exist(path) else unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        f'MI_CarPaint_{k}', '/Game/MongHa/Materials', unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    mel = unreal.MaterialEditingLibrary
    mel.set_material_instance_parent(mi, unreal.load_asset('/Game/MongHa/Materials/M_MH_Opaque'))
    hh = h.lstrip('#')
    c = [((int(hh[j:j + 2], 16) / 255 + 0.055) / 1.055) ** 2.4 for j in (0, 2, 4)]
    mel.set_material_instance_vector_parameter_value(mi, 'Tint', unreal.LinearColor(c[0], c[1], c[2], 1))
    for kk, vv in (('Roughness', 0.22), ('Metallic', 0.35), ('Specular', 0.6), ('GrimeAmount', 0.0)):
        mel.set_material_instance_scalar_parameter_value(mi, kk, vv)
    mel.update_material_instance(mi)
    eal.save_loaded_asset(mi)
    PAINT.append(mi)
if CAR:
    for i, (x, lane, d) in enumerate(((49, -18.6, 1), (64, -14.6, 1), (93, -9.4, -1), (121, -5.6, -1), (138, -9.4, -1), (12, -5.6, -1), (30, -14.6, 1))):
        car = spawn_sm(f'FAB_Car_{i}', CAR, ue(x, 0.02, lane), unreal.Rotator(0, 0, 90 if d > 0 else -90), 1.0, 'Dressing/Cars')
        car.static_mesh_component.set_material(1, PAINT[i % len(PAINT)])

# ---------------------------------------------------------------- potted pothos against the flats along both side gallery decks
POT = load('/Game/Fab/_FREE__Pothos_Potted_Plant_-_Money_Plant/free_pothos_potted_plant_money_plant/StaticMeshes/free_pothos_potted_plant_money_plant')
if POT:
    n_pot = 0
    for x0, z in [(69.7, z) for z in range(25, 123, 5)] + [(110.3, z) for z in range(25, 123, 5)]:   # courtyard faces
        x = x0 + rng.uniform(-0.15, 0.15)
        z = z + rng.uniform(-1, 1)
        hit = trace(ue(x, 5.2, z), ue(x, 2.5, z))
        if hit and 3.3 < hit[0].z / 100 < 4.6 and rng.random() < 0.6:
            spawn_sm(f'FAB_Pot_{n_pot}', POT, hit[0], unreal.Rotator(0, 0, rng.uniform(0, 360)), rng.uniform(0.55, 0.75), 'Dressing/Pots')
            n_pot += 1
    print('pots', n_pot)

# ---------------------------------------------------------------- decals
DEC = '/Game/Fab/Megascans/Decals/'
def soft_leak():
    """The scanned leak at full strength read as black tar on our plaster: a child instance at half opacity."""
    base = load(DEC + 'Leakage_skiubhzc/Medium/skiubhzc_tier_2/Materials/MI_skiubhzc')
    if not base:
        return None
    path = '/Game/MongHa/Materials/MI_Leak_Soft'
    mi = unreal.load_asset(path) if eal.does_asset_exist(path) else unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        'MI_Leak_Soft', '/Game/MongHa/Materials', unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    mel = unreal.MaterialEditingLibrary
    mel.set_material_instance_parent(mi, base)
    for k, v in (('Opacity Intensity', 0.5), ('Contrast', 0.8), ('Brightness', 1.15), ('Saturation', 0.7)):
        mel.set_material_instance_scalar_parameter_value(mi, k, v)
    mel.update_material_instance(mi)
    eal.save_loaded_asset(mi)
    return mi


LEAKS = [m for m in (soft_leak(),) if m]
OIL = load(DEC + 'Oil_Stain_semlsbi/Medium/semlsbi_tier_2/Materials/MI_semlsbi')
TRASH = load(DEC + 'Small_Garbage_Scatter_shmpulh/Medium/shmpulh_tier_2/Materials/MI_shmpulh')


def decal(label, mat, loc, rot, size, folder='Dressing/Decals'):
    act = eas.spawn_actor_from_class(unreal.DecalActor, loc, rot)
    act.set_decal_material(mat)
    dc = act.get_editor_property('decal')
    dc.set_editor_property('decal_size', size)     # X = projection depth, Y/Z = footprint (half-extents)
    act.set_actor_label(label)
    act.set_folder_path(folder)
    return act


# water leaks on facades the cameras can see: sample rays from each view, keep vertical building hits
BUILD = ('SM_Estate_',)   # leaks on the blocks only; the library's cream slabs looked smeared
LEAK_ROLL = float(globals().get('LEAK_ROLL', 90))
placed = []
for v, cam in M['views'].items():
    p = ue(*cam['p'])
    t = ue(*cam['t'])
    f = (t - p)
    f.normalize()
    yaw0 = math.degrees(math.atan2(f.y, f.x))
    pit0 = math.degrees(math.asin(max(-1, min(1, f.z))))
    for _ in range(260):
        yaw = math.radians(yaw0 + rng.uniform(-45, 45))
        pit = math.radians(pit0 + rng.uniform(-28, 28))
        d = unreal.Vector(math.cos(pit) * math.cos(yaw), math.cos(pit) * math.sin(yaw), math.sin(pit))
        hit = trace(p, p + d * 25000.0)
        if not hit or not hit[2].startswith(BUILD) or abs(hit[1].z) > 0.2 or hit[0].z < 150:
            continue
        loc = hit[0]
        if len(placed) >= 60 or any((loc - q).length() < 600 for q in placed):
            continue
        n = hit[1]
        tang = unreal.Vector(-n.y, n.x, 0.0)
        tang.normalize()
        h = rng.uniform(120, 320)
        w = rng.uniform(50, 130)
        flat = True   # the whole footprint must sit on the same flat wall, or the box smears onto fins and returns
        for du, dv in ((-w, 0), (w, 0), (0, -h * 1.4), (0, h * 0.6), (-w, -h * 1.4), (w, -h * 1.4), (-w, h * 0.6), (w, h * 0.6)):   # box is +-size about loc - 0.4 h
            q = loc + tang * du + unreal.Vector(0, 0, dv)
            hh = trace(q + n * 40.0, q - n * 40.0)
            if not hh or (hh[1] - n).length() > 0.05 or abs((hh[0] - q).dot(n)) > 4.0:
                flat = False
                break
        if not flat:
            continue
        placed.append(loc)
        rot = unreal.Rotator(LEAK_ROLL + rng.uniform(-2, 2), 0, math.degrees(math.atan2(-n.y, -n.x)))   # roll, pitch, yaw
        decal(f'FAB_Leak_{len(placed):03d}', rng.choice(LEAKS), loc + unreal.Vector(0, 0, -h * 0.4), rot, unreal.Vector(8, h, w))   # rolled 90: local Y is vertical
print('leak decals', len(placed))

# oil stains on the avenue lanes, rubbish at kerbs / arcade corners
if OIL:
    for i in range(18):
        x, z = rng.uniform(-20, 170), rng.choice([-5.6, -9.4, -14.6, -18.6]) + rng.uniform(-0.6, 0.6)
        decal(f'FAB_Oil_{i}', OIL, ue(x, 0.1, z), unreal.Rotator(0, -90, rng.uniform(0, 360)), unreal.Vector(30, rng.uniform(80, 160), rng.uniform(80, 160)))
if TRASH:
    for i, (x, z) in enumerate(((53, -2.2), (60, -2.4), (88, -2.3), (113, -2.2), (5, 30), (5, 60), (66, 16), (100, 16), (66, 86), (100, 88))):
        decal(f'FAB_Trash_{i}', TRASH, ue(x, 0.1, z), unreal.Rotator(0, -90, rng.uniform(0, 360)), unreal.Vector(30, rng.uniform(60, 110), rng.uniform(60, 110)))

les.save_current_level()
print('trees', n_tree, 'shrubs', len(M['shrubs']))
print('DRESS_DONE')
