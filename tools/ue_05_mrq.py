# Runs inside Unreal Editor: one 1-frame LevelSequence per CAM_ actor, rendered with Movie Render Queue to PNG.
# Args (set by caller): VIEWS="a,b", RES="1920x1080", SPATIAL="8"
import unreal

eal = unreal.EditorAssetLibrary
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
at = unreal.AssetToolsHelpers.get_asset_tools()
MAP = '/Game/Maps/MongHa2010'
SEQ_DIR = '/Game/MongHa/Sequences'
OUT_DIR = r'G:\Claude\mongha-ue\export\renders'
w, h = (int(v) for v in globals().get('RES', '1920x1080').split('x'))
spatial = int(globals().get('SPATIAL', '8'))
views = [v for v in globals().get('VIEWS', '').split(',') if v]
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if not unreal.EditorLevelLibrary.get_editor_world().get_path_name().startswith(MAP):
    les.load_level(MAP)
cams = {a.get_actor_label()[4:]: a for a in eas.get_all_level_actors() if a.get_actor_label().startswith('CAM_')}
if not views:
    views = sorted(cams)
if not eal.does_directory_exist(SEQ_DIR):
    eal.make_directory(SEQ_DIR)

mqs = unreal.get_editor_subsystem(unreal.MoviePipelineQueueSubsystem)
queue = mqs.get_queue()
for j in list(queue.get_jobs()):
    queue.delete_job(j)

for v in views:
    cam = cams[v]
    name = 'SEQ_' + v
    path = f'{SEQ_DIR}/{name}'
    if eal.does_asset_exist(path):
        eal.delete_asset(path)
    seq = at.create_asset(name, SEQ_DIR, unreal.LevelSequence, unreal.LevelSequenceFactoryNew())
    seq.set_display_rate(unreal.FrameRate(24, 1))
    seq.set_playback_start(0)
    seq.set_playback_end(1)
    binding = seq.add_possessable(cam)
    cut_track = seq.add_track(unreal.MovieSceneCameraCutTrack)
    sec = cut_track.add_section()
    sec.set_range(0, 1)
    sec.set_camera_binding_id(seq.get_binding_id(binding)) if hasattr(seq, 'get_binding_id') else sec.set_camera_binding_id(unreal.MovieSceneSequenceExtensions.get_portable_binding_id(seq, seq, binding))
    eal.save_loaded_asset(seq)

    job = queue.allocate_new_job(unreal.MoviePipelineExecutorJob)
    job.job_name = v
    job.sequence = unreal.SoftObjectPath(path + '.' + name)
    job.map = unreal.SoftObjectPath(MAP + '.MongHa2010')
    cfg = job.get_configuration()
    out = cfg.find_or_add_setting_by_class(unreal.MoviePipelineOutputSetting)
    out.output_directory = unreal.DirectoryPath(OUT_DIR)
    out.output_resolution = unreal.IntPoint(w, h)
    out.file_name_format = '{sequence_name}'
    out.override_existing_output = True
    cfg.find_or_add_setting_by_class(unreal.MoviePipelineDeferredPassBase)
    cfg.find_or_add_setting_by_class(unreal.MoviePipelineImageSequenceOutput_PNG)
    aa = cfg.find_or_add_setting_by_class(unreal.MoviePipelineAntiAliasingSetting)
    aa.spatial_sample_count = spatial
    aa.temporal_sample_count = 1
    aa.override_anti_aliasing = True
    aa.anti_aliasing_method = unreal.AntiAliasingMethod.AAM_NONE
    aa.engine_warm_up_count = 64
    aa.render_warm_up_count = 64
    aa.render_warm_up_frames = True
    go = cfg.find_or_add_setting_by_class(unreal.MoviePipelineGameOverrideSetting)
    go.cinematic_quality_settings = True
    go.texture_streaming = unreal.MoviePipelineTextureStreamingMethod.DISABLED
    cv = cfg.find_or_add_setting_by_class(unreal.MoviePipelineConsoleVariableSetting)
    for k, val in (('r.Lumen.Reflections.HierarchicalScreenTraces.MaxIterations', 64), ('r.Lumen.HardwareRayTracing.LightingMode', 2),
                   ('r.Lumen.Reflections.MaxRoughnessToTrace', 0.6), ('r.Lumen.ScreenProbeGather.ShortRangeAO.HardwareRayTracing', 0)):
        try:
            cv.add_or_update_console_variable(k, val)
        except Exception:
            pass
    print('queued', v)

mqs.render_queue_with_executor(unreal.MoviePipelinePIEExecutor)
print('MRQ_STARTED', len(views))

for _k in ('VIEWS', 'RES', 'SPATIAL'):
    globals().pop(_k, None)
