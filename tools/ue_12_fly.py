# Runs inside Unreal Editor: camera flythrough SEQ_Fly — across the zebra crossing on 慕拉士大馬路, through the arcade passage,
# along the side of the ball cage, up over the trees, round the library, ending exactly on the solved 1990s photo camera — rendered with Movie Render Queue.
# Args: RES ("1920x1080"), SPATIAL ("4"), OUT (folder under export/renders, "fly"), RENDER ("1"; "0" = build the sequence only),
#       FRAMES ("a-b", optional sub-range).
# Path keys are site coordinates (x along the avenue, y up, z into the site); a time-aware Catmull-Rom curve is sampled
# every 4 frames so speed and heading change smoothly. Then: ffmpeg -framerate 24 -i fly_%04d.png ... (see tools/encode_fly.cmd).
import json
import math

import unreal

eal = unreal.EditorAssetLibrary
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
at = unreal.AssetToolsHelpers.get_asset_tools()
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
MAP = '/Game/Maps/MongHa2010'
SEQ_DIR, NAME = '/Game/MongHa/Sequences', 'SEQ_Fly'
FPS = 24
w, h = (int(v) for v in globals().get('RES', '1920x1080').split('x'))
spatial = int(globals().get('SPATIAL', '4'))
out_dir = r'G:\Claude\mongha-ue\export\renders' + '\\' + globals().get('OUT', 'fly')
if not unreal.EditorLevelLibrary.get_editor_world().get_path_name().startswith(MAP):
    les.load_level(MAP)
M = json.load(open(r'G:\Claude\mongha-ue\export\markers.json', encoding='utf-8'))
v90 = M['views']['court_1990']
PX = M['passage_x']

KEYS = [   # (seconds, camera position, look-at target)
    (0.0, (PX - 2.5, 1.65, -25.0), (PX, 6.0, 3.0)),        # opposite pavement, looking at the passage facade
    (6.0, (PX, 1.65, -12.5), (PX, 3.5, 5.0)),              # on the median, between the signal poles (PX +- 1.2)
    (11.0, (PX, 1.7, -1.5), (PX, 2.4, 16.0)),              # passage mouth
    (14.5, (PX, 1.85, 11.0), (PX + 1.0, 3.0, 30.0)),       # inside the passage
    (16.5, (PX + 1.4, 2.0, 14.6), (80.0, 2.5, 30.0)),      # out, right of the deck column on the axis (x PX+0.1, z 15.65)
    (19.0, (79.0, 1.8, 17.0), (68.0, 3.0, 32.0)),          # turn left along the cage end (fence z 19.5, columns z 15.65)
    (22.0, (70.2, 1.8, 19.5), (72.0, 3.5, 45.0)),          # into the lane between cage (x 74) and NW gallery (x 65)
    (24.0, (70.1, 4.5, 24.5), (75.0, 6.0, 55.0)),          # start rising before the planter + young tree at x 70.6, z 30.8
    (27.5, (71.2, 9.2, 32.5), (PX, 6.0, 62.0)),            # above the trees
    (33.0, (68.5, 9.5, 48.0), (PX, 6.5, 66.0)),            # NW side of the library
    (38.0, (66.5, 12.0, 80.0), (PX, 6.0, 64.0)),           # past the library (kept ~8 m off its corner), looking back
    (44.0, tuple(v90['p']), tuple(v90['t'])),              # the 1990s photo viewpoint
    (46.0, tuple(v90['p']), tuple(v90['t'])),              # hold
]
N = int(KEYS[-1][0] * FPS)


def hermite(keys, idx, t):
    """Catmull-Rom with tangents from neighbouring keys over their time span; zero tangent at the ends (ease in/out)."""
    ts = [k[0] for k in keys]
    i = max(0, min(len(ts) - 2, next((j for j in range(len(ts) - 1) if ts[j] <= t <= ts[j + 1]), len(ts) - 2)))
    t0, t1 = ts[i], ts[i + 1]
    p0, p1 = keys[i][idx], keys[i + 1][idx]

    def tangent(j):
        if j == 0 or j == len(ts) - 1 or keys[j][idx] == keys[j + 1 if j + 1 < len(ts) else j][idx]:
            return (0.0, 0.0, 0.0)
        a, b = keys[j - 1][idx], keys[j + 1][idx]
        return tuple((b[c] - a[c]) / (ts[j + 1] - ts[j - 1]) for c in range(3))
    m0, m1 = tangent(i), tangent(i + 1)
    d = t1 - t0
    s = (t - t0) / d if d else 0.0
    h00, h10, h01, h11 = 2 * s ** 3 - 3 * s ** 2 + 1, s ** 3 - 2 * s ** 2 + s, -2 * s ** 3 + 3 * s ** 2, s ** 3 - s ** 2
    return tuple(h00 * p0[c] + h10 * d * m0[c] + h01 * p1[c] + h11 * d * m1[c] for c in range(3))


def U(p):
    return (p[0] * 100.0, p[2] * 100.0, p[1] * 100.0)


# ---- camera actor
for a in eas.get_all_level_actors():
    if a.get_actor_label() == 'CAM_fly':
        eas.destroy_actor(a)
cam = eas.spawn_actor_from_class(unreal.CineCameraActor, unreal.Vector(*U(KEYS[0][1])))
cam.set_actor_label('CAM_fly')
cc = cam.get_cine_camera_component()
fb = cc.get_editor_property('filmback')
fb.set_editor_property('sensor_width', 36.0)
fb.set_editor_property('sensor_height', 20.25)
cc.set_editor_property('filmback', fb)
cc.set_editor_property('current_focal_length', 18.0)
fs = cc.get_editor_property('focus_settings')
fs.set_editor_property('focus_method', unreal.CameraFocusMethod.DISABLE)
cc.set_editor_property('focus_settings', fs)
cps = cc.get_editor_property('post_process_settings')   # exposure adapts from the bright street into the passage and back
for k, v in (('auto_exposure_method', unreal.AutoExposureMethod.AEM_HISTOGRAM), ('auto_exposure_min_brightness', 11.0),
             ('auto_exposure_max_brightness', 13.4), ('auto_exposure_speed_up', 1.5), ('auto_exposure_speed_down', 1.0),
             ('motion_blur_amount', 0.3), ('motion_blur_max', 2.0)):
    cps.set_editor_property(k, v)
    cps.set_editor_property('override_' + k, True)
cc.set_editor_property('post_process_settings', cps)

# ---- sequence
# never delete an old take: a sequence still held in memory cannot be force-deleted, and the editor then stops on a modal
# "Overwrite Existing Object" prompt (2026-10-21). Each run writes the next free SEQ_Fly_NN instead.
k = 1
while eal.does_asset_exist(f'{SEQ_DIR}/{NAME}_{k:02d}') or eal.does_asset_exist(f'{SEQ_DIR}/{NAME}'):
    if not eal.does_asset_exist(f'{SEQ_DIR}/{NAME}_{k:02d}'):
        break
    k += 1
NAME = f'{NAME}_{k:02d}'
path = f'{SEQ_DIR}/{NAME}'
seq = at.create_asset(NAME, SEQ_DIR, unreal.LevelSequence, unreal.LevelSequenceFactoryNew())
seq.set_display_rate(unreal.FrameRate(FPS, 1))
seq.set_playback_start(0)
seq.set_playback_end(N)
binding = seq.add_possessable(cam)
track = binding.add_track(unreal.MovieScene3DTransformTrack)
sec = track.add_section()
sec.set_range(0, N)
chans = {str(c.channel_name): c for c in sec.get_all_channels()}   # channel_name is an unreal.Name
loc = [chans.get(n) for n in ('Location.X', 'Location.Y', 'Location.Z')]
rot = [chans.get(n) for n in ('Rotation.X', 'Rotation.Y', 'Rotation.Z')]
prev_yaw = None
for f in list(range(0, N, 4)) + [N]:
    t = f / FPS
    p, q = hermite(KEYS, 1, t), hermite(KEYS, 2, t)
    P, Q = U(p), U(q)
    dx, dy, dz = Q[0] - P[0], Q[1] - P[1], Q[2] - P[2]
    yaw = math.degrees(math.atan2(dy, dx))
    if prev_yaw is not None:   # unwrap so the curve never spins the long way round
        while yaw - prev_yaw > 180:
            yaw -= 360
        while yaw - prev_yaw < -180:
            yaw += 360
    prev_yaw = yaw
    pitch = math.degrees(math.atan2(dz, math.hypot(dx, dy)))
    fn = unreal.FrameNumber(f)
    for ch, val in zip(loc, P):
        ch.add_key(fn, val, interpolation=unreal.MovieSceneKeyInterpolation.AUTO)
    for ch, val in zip(rot, (0.0, pitch, yaw)):
        ch.add_key(fn, val, interpolation=unreal.MovieSceneKeyInterpolation.AUTO)
cut = seq.add_track(unreal.MovieSceneCameraCutTrack)
cs = cut.add_section()
cs.set_range(0, N)
try:
    cs.set_camera_binding_id(seq.get_binding_id(binding))
except Exception:
    cs.set_camera_binding_id(unreal.MovieSceneSequenceExtensions.get_portable_binding_id(seq, seq, binding))
eal.save_loaded_asset(seq)
les.save_current_level()
print('SEQUENCE', path, 'frames', N, 'channels', sorted(chans))

# ---- render
if globals().get('RENDER', '1') != '0':
    mqs = unreal.get_editor_subsystem(unreal.MoviePipelineQueueSubsystem)
    queue = mqs.get_queue()
    for j in list(queue.get_jobs()):
        queue.delete_job(j)
    job = queue.allocate_new_job(unreal.MoviePipelineExecutorJob)
    job.job_name = 'fly'
    job.sequence = unreal.SoftObjectPath(path + '.' + NAME)
    job.map = unreal.SoftObjectPath(MAP + '.MongHa2010')
    cfg = job.get_configuration()
    o = cfg.find_or_add_setting_by_class(unreal.MoviePipelineOutputSetting)
    o.output_directory = unreal.DirectoryPath(out_dir)
    o.output_resolution = unreal.IntPoint(w, h)
    o.file_name_format = 'fly_{frame_number}'
    o.zero_pad_frame_numbers = 4
    o.override_existing_output = True
    if globals().get('FRAMES'):   # 'a-b': re-check part of the path without rendering the whole take
        fa, fb_ = (int(v) for v in globals()['FRAMES'].split('-'))
        o.use_custom_playback_range = True
        o.custom_start_frame = fa
        o.custom_end_frame = fb_
    cfg.find_or_add_setting_by_class(unreal.MoviePipelineDeferredPassBase)
    cfg.find_or_add_setting_by_class(unreal.MoviePipelineImageSequenceOutput_PNG)
    aa = cfg.find_or_add_setting_by_class(unreal.MoviePipelineAntiAliasingSetting)
    aa.spatial_sample_count = spatial
    aa.temporal_sample_count = 1
    aa.override_anti_aliasing = True
    aa.anti_aliasing_method = unreal.AntiAliasingMethod.AAM_TSR if spatial == 1 else unreal.AntiAliasingMethod.AAM_NONE
    aa.engine_warm_up_count = 48
    aa.render_warm_up_count = 48
    aa.render_warm_up_frames = True
    go = cfg.find_or_add_setting_by_class(unreal.MoviePipelineGameOverrideSetting)
    go.cinematic_quality_settings = True
    go.texture_streaming = unreal.MoviePipelineTextureStreamingMethod.DISABLED
    cv = cfg.find_or_add_setting_by_class(unreal.MoviePipelineConsoleVariableSetting)
    for k, val in (('r.Lumen.HardwareRayTracing.LightingMode', 2), ('r.Lumen.Reflections.MaxRoughnessToTrace', 0.6),
                   ('r.Lumen.ScreenProbeGather.ShortRangeAO.HardwareRayTracing', 0)):
        try:
            cv.add_or_update_console_variable(k, val)
        except Exception:
            pass
    mqs.render_queue_with_executor(unreal.MoviePipelinePIEExecutor)
    print('FLY_RENDER_STARTED', w, h, 'spatial', spatial, '->', out_dir)
for _k in ('RES', 'SPATIAL', 'OUT', 'RENDER', 'FRAMES'):
    globals().pop(_k, None)
