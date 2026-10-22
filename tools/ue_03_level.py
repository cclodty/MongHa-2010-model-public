# Runs inside Unreal Editor: level with the estate, physically based sun/sky (Macau sun position), Lumen post, cine cameras.
import datetime
import json
import math
import unreal

ROOT = r"G:\Claude\mongha-ue"
MAP = '/Game/Maps/MongHa2010'
SUN_DATE = (2010, 5, 15, 9.5)            # local time UTC+8; morning light on the avenue facades
LAT, LON, TZ = 22.2066, 113.5519, 8.0
NORTH_SITE = (-0.666, -0.747)            # true north in the site frame (x along avenue, z into the site)
EAST_SITE = (0.747, -0.666)

eal = unreal.EditorAssetLibrary
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
markers = json.load(open(ROOT + r"\export\markers.json", encoding='utf-8'))

if not eal.does_directory_exist('/Game/Maps'):
    eal.make_directory('/Game/Maps')
if eal.does_asset_exist(MAP):
    les.load_level(MAP)
    for a in eas.get_all_level_actors():
        eas.destroy_actor(a)
else:
    les.new_level(MAP)

# ---- estate meshes at the origin (vertices are already in world space)
KEEP = {'SM_Courtyard', 'SM_Estate_BACK', 'SM_Estate_FRONT', 'SM_Estate_NW', 'SM_Estate_SE', 'SM_Galleries_Bridges',
        'SM_Ground_Streets', 'SM_Library'}   # round 6 meshes (blender/ue_export.py); older ring / hall / context assets stay unused
meshes = {}
for p in eal.list_assets('/Game/MongHa/Meshes', recursive=True):
    sm = unreal.load_asset(p)
    if isinstance(sm, unreal.StaticMesh) and sm.get_name() in KEEP:
        a = eas.spawn_actor_from_object(sm, unreal.Vector(0, 0, 0))
        a.set_actor_label(sm.get_name())
        meshes[sm.get_name()] = a

# ---- work out how site metres map to Unreal centimetres from the library's position
lib = next((a for n, a in meshes.items() if 'Library' in n), None)
origin, extent = lib.get_actor_bounds(False)
LX, LZ = markers['library']
sx = 1 if origin.x * LX > 0 else -1
sz = 1 if origin.y * LZ > 0 else -1
swap = abs(abs(origin.x) - LX * 100) > abs(abs(origin.x) - LZ * 100)
print('library bounds centre', origin, 'swap', swap, 'signs', sx, sz)


def U(x, y, z):
    """site metres -> Unreal cm."""
    if swap:
        return unreal.Vector(sz * z * 100, sx * x * 100, y * 100)
    return unreal.Vector(sx * x * 100, sz * z * 100, y * 100)


def Uh(x, z):
    v = U(x, 0, z)
    return v.x, v.y


# ---- sun position (NOAA approximation)
def sun_pos(y, m, d, hour):
    n = datetime.date(y, m, d).timetuple().tm_yday
    g = 2 * math.pi / 365 * (n - 1 + (hour - 12) / 24)
    eqt = 229.18 * (0.000075 + 0.001868 * math.cos(g) - 0.032077 * math.sin(g) - 0.014615 * math.cos(2 * g) - 0.040849 * math.sin(2 * g))
    decl = 0.006918 - 0.399912 * math.cos(g) + 0.070257 * math.sin(g) - 0.006758 * math.cos(2 * g) + 0.000907 * math.sin(2 * g) - 0.002697 * math.cos(3 * g) + 0.00148 * math.sin(3 * g)
    tst = hour * 60 + eqt + 4 * LON - 60 * TZ
    ha = math.radians(tst / 4 - 180)
    lat = math.radians(LAT)
    el = math.degrees(math.asin(math.sin(lat) * math.sin(decl) + math.cos(lat) * math.cos(decl) * math.cos(ha)))
    az = (math.degrees(math.atan2(math.sin(ha), math.cos(ha) * math.sin(lat) - math.tan(decl) * math.cos(lat))) + 180) % 360
    return az, el


az, el = sun_pos(*SUN_DATE)
ca, sa = math.cos(math.radians(az)), math.sin(math.radians(az))
hx, hz = ca * NORTH_SITE[0] + sa * EAST_SITE[0], ca * NORTH_SITE[1] + sa * EAST_SITE[1]   # towards the sun, site frame
ux, uy = Uh(hx, hz)
yaw = math.degrees(math.atan2(-uy, -ux))
print(f'sun azimuth {az:.1f} elevation {el:.1f} -> light yaw {yaw:.1f}')


def spawn(cls, loc=(0, 0, 0), rot=None, label=None):
    a = eas.spawn_actor_from_class(cls, unreal.Vector(*loc), rot or unreal.Rotator(0, 0, 0))
    if label:
        a.set_actor_label(label)
    return a


sun = spawn(unreal.DirectionalLight, (0, 0, 5000), unreal.Rotator(roll=0, pitch=-el, yaw=yaw), 'Sun')
lc = sun.get_component_by_class(unreal.DirectionalLightComponent)
lc.set_mobility(unreal.ComponentMobility.MOVABLE)
lc.set_editor_property('intensity', 100000.0)
lc.set_editor_property('light_source_angle', 0.53)
lc.set_editor_property('atmosphere_sun_light', True)
lc.set_editor_property('light_color', unreal.Color(r=255, g=244, b=228, a=255))
spawn(unreal.SkyAtmosphere, label='SkyAtmosphere')
sky = spawn(unreal.SkyLight, (0, 0, 2000), label='SkyLight')
slc = sky.get_component_by_class(unreal.SkyLightComponent)
slc.set_mobility(unreal.ComponentMobility.MOVABLE)
slc.set_editor_property('real_time_capture', True)
slc.set_editor_property('intensity', 1.0)
spawn(unreal.VolumetricCloud, label='Clouds')
fog = spawn(unreal.ExponentialHeightFog, (0, 0, 0), label='HeightFog')
fc = fog.get_component_by_class(unreal.ExponentialHeightFogComponent)
fc.set_editor_property('fog_density', 0.006)
fc.set_editor_property('fog_height_falloff', 0.2)

ppv = spawn(unreal.PostProcessVolume, label='PostProcess')
ppv.set_editor_property('unbound', True)
s = ppv.get_editor_property('settings')
for k, v in dict(auto_exposure_method=unreal.AutoExposureMethod.AEM_HISTOGRAM, auto_exposure_min_brightness=14.0, auto_exposure_max_brightness=14.0,
                 auto_exposure_bias=0.3, bloom_intensity=0.25, vignette_intensity=0.25, film_grain_intensity=0.08,
                 lumen_final_gather_quality=2.0, lumen_reflection_quality=2.0, lumen_scene_detail=2.0, lumen_scene_lighting_quality=2.0,
                 ambient_occlusion_intensity=0.4).items():
    try:
        s.set_editor_property(k, v)
        s.set_editor_property('override_' + k, True)
    except Exception as e:
        print('pp skip', k, e)
ppv.set_editor_property('settings', s)

# ---- cine cameras for the reference views (vertical FOV from the web model)
SENSOR_W, SENSOR_H = 36.0, 20.25
for name, v in markers['views'].items():
    if name == 'hall_corner':   # the sports hall is not part of the model any more
        continue
    p, t = U(*v['p']), U(*v['t'])
    d = t - p
    yaw_c = math.degrees(math.atan2(d.y, d.x))
    pitch_c = math.degrees(math.atan2(d.z, math.hypot(d.x, d.y)))
    cam = spawn(unreal.CineCameraActor, (p.x, p.y, p.z), unreal.Rotator(roll=0, pitch=pitch_c, yaw=yaw_c), 'CAM_' + name)
    cc = cam.get_cine_camera_component()
    fb = cc.get_editor_property('filmback')
    fb.set_editor_property('sensor_width', SENSOR_W)
    fb.set_editor_property('sensor_height', SENSOR_H)
    cc.set_editor_property('filmback', fb)
    cc.set_editor_property('current_focal_length', (SENSOR_H / 2) / math.tan(math.radians(v['fov']) / 2))
    fs = cc.get_editor_property('focus_settings')
    fs.set_editor_property('focus_method', unreal.CameraFocusMethod.DISABLE)
    cc.set_editor_property('focus_settings', fs)

les.save_current_level()
print('LEVEL_DONE', MAP, 'actors', len(eas.get_all_level_actors()))
