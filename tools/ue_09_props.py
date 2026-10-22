# Runs inside Unreal Editor: AAA props from Fab on the estate.
#  - air conditioners at every markers.json 'ac' spot (the Blender boxes are cut out in blender/ue_export.py):
#    window units = Dekogon AC_Window A01/A02, split units on brackets = "Old Air Conditioner" (DTry)
#  - globe wall lamps under the gallery decks, fire-hose outlets by the passage, pallets / plywood by shuttered shops
# All these assets have their front on local +Y. Idempotent: everything spawned is labelled PROP_* and replaced on a rerun.
import json
import math
import random

import unreal

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
eal = unreal.EditorAssetLibrary
sme = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
MAP = '/Game/Maps/MongHa2010'
if not unreal.EditorLevelLibrary.get_editor_world().get_path_name().startswith(MAP):
    les.load_level(MAP)
world = unreal.EditorLevelLibrary.get_editor_world()
M = json.load(open(r'G:\Claude\mongha-ue\export\markers.json', encoding='utf-8'))
rng = random.Random(1988)
for a in eas.get_all_level_actors():
    if a.get_actor_label().startswith(('PROP_', 'TEST_', 'CAM_proptest', 'CAM_detail_')):
        eas.destroy_actor(a)

D = '/Game/Deko_MatrixDemo/City/Meshes/'


def load(p, nanite=True):
    m = unreal.load_asset(p)
    if m is None:
        print('missing', p)
        return None
    ns = m.get_editor_property('nanite_settings')
    if nanite and not ns.get_editor_property('enabled'):   # the AC pack ships without Nanite (34k tris x hundreds)
        ns.set_editor_property('enabled', True)
        sme.set_nanite_settings(m, ns, apply_changes=True)
        eal.save_loaded_asset(m)
        print('nanite enabled', m.get_name())
    return m


def ue(x, y, z):
    return unreal.Vector(x * 100, z * 100, y * 100)


def yaw_for(ox, oz):
    """yaw that turns local +Y onto the site direction (ox, oz)  (UE yaw takes +Y to (-sin, cos))."""
    return math.degrees(math.atan2(-ox, oz))


def put(label, mesh, loc, yaw, scale, folder, roll=0.0):
    act = eas.spawn_actor_from_object(mesh, loc, unreal.Rotator(roll, 0, yaw))   # roll tips local +Y/Z about the sheet's width
    act.set_actor_scale3d(unreal.Vector(scale, scale, scale) if not isinstance(scale, unreal.Vector) else scale)
    act.set_actor_label(label)
    act.set_folder_path(folder)
    return act


def trace(a, b):
    h = unreal.SystemLibrary.line_trace_single(world, a, b, unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, True, [],
                                               unreal.DrawDebugTrace.NONE, True)
    if h is None:
        return None
    t = h.to_tuple()
    if not t[0]:
        return None
    return t[4], t[7], (t[9].get_actor_label() if t[9] else '')


# ---------------------------------------------------------------- air conditioners
WIN = [(load(D + 'SM_BLDG_Prop_AC_Window_A01_N1'), 1.25, 0.62), (load(D + 'SM_BLDG_Prop_AC_Window_A02_N1'), 0.78, 0.38)]
SPLIT = [load('/Game/StaticMeshes/SM_OldConditioner'), load('/Game/StaticMeshes/SM_OldConditioner_AtlasTexture')]
n_ac = 0
for i, a in enumerate(M['ac']):
    x, y, z = a['p']
    if not (50 <= x <= 130 and 1.5 <= z <= 145):   # hillside blocks are not in the Unreal model (17 m blocks, 2026-10-23)
        continue
    ox, oz = a['out'][0], a['out'][2]
    yaw = yaw_for(ox, oz) + rng.uniform(-1.2, 1.2)
    if a['kind'] == 'window':
        r = rng.random()
        mesh, sc = (WIN[0][0], WIN[0][1]) if r < WIN[0][2] else (WIN[1][0], WIN[1][1])
        put(f'PROP_AC_{i:03d}', mesh, ue(x, y, z), yaw, sc * rng.uniform(0.96, 1.04), 'Dressing/AC')
    else:
        mesh = rng.choice(SPLIT)
        put(f'PROP_AC_{i:03d}', mesh, ue(x, y - 0.07, z), yaw, 0.8 * rng.uniform(0.96, 1.04), 'Dressing/AC')
    n_ac += 1
print('air conditioners', n_ac)

# ---------------------------------------------------------------- globe wall lamps on the ground-floor walls under the gallery decks
LAMP = load(D + 'SM_BLDG_Prop_Lamp_Wall_A01_N1')
CX0, CX1, CZ0, CZ1 = 62, 104, 13, 119      # courtyard faces (build_estate.py)
n_lamp = 0
if LAMP:
    runs = [((x, CZ0 + 8), (0, -1)) for x in range(CX0 + 5, CX1 - 3, 7)] + [((x, CZ1 - 8), (0, 1)) for x in range(CX0 + 5, CX1 - 3, 7)] + \
           [((CX0 + 8, z), (-1, 0)) for z in range(CZ0 + 6, CZ1 - 3, 8)] + [((CX1 - 8, z), (1, 0)) for z in range(CZ0 + 6, CZ1 - 3, 8)]
    for (sx, sz), (dx, dz) in runs:
        hit = trace(ue(sx, 2.7, sz), ue(sx + dx * 12, 2.7, sz + dz * 12))
        if not hit or not hit[2].startswith('SM_Estate_') or abs(hit[1].z) > 0.1:
            continue
        n = hit[1]
        put(f'PROP_Lamp_{n_lamp:02d}', LAMP, hit[0] + n * 1.0, yaw_for(n.x, n.y), 0.9, 'Dressing/Lamps')
        n_lamp += 1
print('wall lamps', n_lamp)

# ---------------------------------------------------------------- fire-hose outlets either side of the avenue passage, 0.6 m up
HOSE = load(D + 'SM_BLDG_Prop_FirehoseConn_Outlet_A01_N1')
n_hose = 0
if HOSE:
    for sx in (M['passage_x'] - 3.4, M['passage_x'] + 3.4, M['passage_x'] - 22.0):
        hit = trace(ue(sx, 0.6, -2.0), ue(sx, 0.6, 10.0))
        if hit and hit[2].startswith('SM_Estate_') and abs(hit[1].z) < 0.1:
            n = hit[1]
            put(f'PROP_Hose_{n_hose}', HOSE, hit[0] + n * 0.5, yaw_for(n.x, n.y), 1.0, 'Dressing/Street')
            n_hose += 1
print('hose outlets', n_hose)

# ---------------------------------------------------------------- pallets and plywood outside a few shuttered shops on the avenue
PALLETS = [m for m in (load(D + 'SM_WoodenPallet_A01_N1'), load(D + 'SM_WoodenPallet_B01_N1'), load(D + 'SM_WoodenPallet_C01_N1')) if m]
PLY = [m for m in (load(D + 'SM_PlywoodBoards_A01_N1'), load(D + 'SM_PlywoodBoards_C01_N1')) if m]
LEAN = float(globals().get('LEAN', 6.0))   # sign checked in a render
n_clutter = 0
for k, sx in enumerate((57.5, 69.0, 101.5, 108.0)):
    hit = trace(ue(sx, 0.4, -2.0), ue(sx, 0.4, 10.0))
    if not hit or not hit[2].startswith('SM_Estate_'):
        continue
    n = hit[1]
    base = hit[0] + n * 30.0
    base.z = 0.5
    yaw = yaw_for(n.x, n.y)
    if k % 2 == 0 and PLY:   # sheet leaning on the shutter
        put(f'PROP_Ply_{k}', rng.choice(PLY), hit[0] + n * 22.0 + unreal.Vector(0, 0, -hit[0].z + 1), yaw, 0.85, 'Dressing/Street', roll=LEAN)
    else:                    # a short stack of pallets
        for j in range(rng.randint(2, 4)):
            put(f'PROP_Pallet_{k}_{j}', rng.choice(PALLETS), base + unreal.Vector(rng.uniform(-4, 4), rng.uniform(-4, 4), 12.0 * j + 1),
                yaw + rng.uniform(-6, 6), 1.0, 'Dressing/Street')
    n_clutter += 1
print('shop clutter', n_clutter)

# ---------------------------------------------------------------- close-up cameras for judging prop detail
for name, p, t, fov in (('detail_street', (70.0, 1.6, -2.5), (79.0, 9.5, 3.0), 62.0),
                        ('detail_court', (96.0, 1.6, 30.0), (103.5, 3.0, 20.0), 64.0)):
    P, T = ue(*p), ue(*t)
    d = T - P
    cam = eas.spawn_actor_from_class(unreal.CineCameraActor, P, unreal.Rotator(0, math.degrees(math.atan2(d.z, math.hypot(d.x, d.y))),
                                                                              math.degrees(math.atan2(d.y, d.x))))
    cam.set_actor_label('CAM_' + name)
    cc = cam.get_cine_camera_component()
    fb = cc.get_editor_property('filmback')
    fb.set_editor_property('sensor_width', 36.0)
    fb.set_editor_property('sensor_height', 20.25)
    cc.set_editor_property('filmback', fb)
    cc.set_editor_property('current_focal_length', 10.125 / math.tan(math.radians(fov) / 2))
    fs = cc.get_editor_property('focus_settings')
    fs.set_editor_property('focus_method', unreal.CameraFocusMethod.DISABLE)
    cc.set_editor_property('focus_settings', fs)
    cps = cc.get_editor_property('post_process_settings')
    cps.set_editor_property('auto_exposure_method', unreal.AutoExposureMethod.AEM_HISTOGRAM)
    for k, v in (('auto_exposure_min_brightness', 12.6), ('auto_exposure_max_brightness', 13.1)):
        cps.set_editor_property(k, v)
        cps.set_editor_property('override_' + k, True)
    cps.set_editor_property('override_auto_exposure_method', True)
    cc.set_editor_property('post_process_settings', cps)

les.save_current_level()
print('PROPS_DONE')
