# Runs inside Unreal Editor: photographic look — local exposure, haze, per-camera exposure + lens (DOF, fringe, grain).
import math
import unreal

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
MAP = '/Game/Maps/MongHa2010'
if not unreal.EditorLevelLibrary.get_editor_world().get_path_name().startswith(MAP):
    les.load_level(MAP)
acts = {a.get_actor_label(): a for a in eas.get_all_level_actors()}


def pp_set(s, values):
    for k, v in values.items():
        try:
            s.set_editor_property(k, v)
        except Exception as e:
            print('skip', k, e)
            continue
        try:
            s.set_editor_property('override_' + k, True)
        except Exception:
            pass
    return s


# ---- global: a camera-like tone response rather than a raw render
ppv = acts['PostProcess']
s = ppv.get_editor_property('settings')
pp_set(s, dict(
    local_exposure_highlight_contrast_scale=0.75, local_exposure_shadow_contrast_scale=0.62, local_exposure_detail_strength=1.1,
    bloom_intensity=0.35, bloom_threshold=1.0,
    scene_fringe_intensity=0.35, vignette_intensity=0.32, film_grain_intensity=0.12, film_grain_intensity_shadows=0.3,
    white_temp=6100.0, color_saturation=unreal.Vector4(0.9, 0.9, 0.9, 1.0), color_contrast=unreal.Vector4(1.04, 1.04, 1.04, 1.0),
    lumen_final_gather_quality=3.0, lumen_reflection_quality=3.0, lumen_scene_detail=3.0, lumen_scene_lighting_quality=3.0,
    lumen_final_gather_lighting_update_speed=4.0, lumen_scene_lighting_update_speed=4.0,
    ambient_occlusion_intensity=0.35, motion_blur_amount=0.0,
))
ppv.set_editor_property('settings', s)

# humid subtropical air: thicker aerial perspective + light haze
sa = acts['SkyAtmosphere'].get_component_by_class(unreal.SkyAtmosphereComponent)
for k, v in (('aerial_pespective_view_distance_scale', 2.5), ('aerial_perspective_view_distance_scale', 2.5), ('mie_scattering_scale', 0.011)):
    try:
        sa.set_editor_property(k, v)
    except Exception:
        pass
fc = acts['HeightFog'].get_component_by_class(unreal.ExponentialHeightFogComponent)
fc.set_editor_property('fog_density', 0.016)
fc.set_editor_property('fog_height_falloff', 0.12)
fc.set_editor_property('start_distance', 3000.0)
fc.set_editor_property('fog_inscattering_luminance', unreal.LinearColor(0.42, 0.47, 0.52, 1))
slc = acts['SkyLight'].get_component_by_class(unreal.SkyLightComponent)
slc.set_editor_property('intensity', 1.6)

# ---- per camera: exposure window (EV100), aperture and focus
VIEW_EV = dict(court_1990=13.1, avenue_2008=13.4, courtyard_aerial=13.2, library=12.1, gallery_deck=11.3, hall_corner=13.5)
VIEW_FSTOP = dict(court_1990=8.0, avenue_2008=8.0, courtyard_aerial=11.0, library=5.6, gallery_deck=5.6, hall_corner=8.0)
for label, a in acts.items():
    if not label.startswith('CAM_'):
        continue
    v = label[4:]
    cc = a.get_cine_camera_component()
    # focus on the look-at point: distance along the view axis to the first hit is overkill; use a sensible plane
    fwd = a.get_actor_forward_vector()
    hit = unreal.SystemLibrary.line_trace_single(a, a.get_actor_location(), a.get_actor_location() + fwd * 50000.0,
                                                 unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [], unreal.DrawDebugTrace.NONE, True)
    dist = 3000.0
    try:
        if hit and hit.to_tuple()[0]:
            dist = max(500.0, float(hit.to_tuple()[3]) * 1.0 if isinstance(hit.to_tuple()[3], float) else dist)
    except Exception:
        pass
    fs = cc.get_editor_property('focus_settings')
    fs.set_editor_property('focus_method', unreal.CameraFocusMethod.MANUAL)
    fs.set_editor_property('manual_focus_distance', dist)
    cc.set_editor_property('focus_settings', fs)
    cc.set_editor_property('current_aperture', VIEW_FSTOP.get(v, 8.0))
    cps = cc.get_editor_property('post_process_settings')
    ev = VIEW_EV.get(v, 13.0)
    pp_set(cps, dict(auto_exposure_method=unreal.AutoExposureMethod.AEM_HISTOGRAM,
                     auto_exposure_min_brightness=ev - 0.25, auto_exposure_max_brightness=ev + 0.25))
    cc.set_editor_property('post_process_settings', cps)
    cc.set_editor_property('post_process_blend_weight', 1.0)
    print('camera', v, 'EV', ev, 'f/', VIEW_FSTOP.get(v), 'focus cm', round(dist))
les.save_current_level()
print('LOOK_DONE')
