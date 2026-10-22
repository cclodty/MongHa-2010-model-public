# Runs inside Unreal Editor: line up candidate props on the empty asphalt west of the estate, all rotated yaw 180
# (if local +Y is "out of the wall", their fronts face CAM_proptest), so one render shows orientation and scale.
import unreal

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
for a in eas.get_all_level_actors():
    if a.get_actor_label().startswith(('TEST_', 'CAM_proptest')):
        eas.destroy_actor(a)
D = '/Game/Deko_MatrixDemo/City/Meshes/'
PROPS = [D + 'SM_BLDG_Prop_AC_Window_A01_N1', D + 'SM_BLDG_Prop_AC_Window_A02_N1', '/Game/StaticMeshes/SM_OldConditioner',
         '/Game/StaticMeshes/SM_OldConditioner_AtlasTexture', D + 'SM_BLDG_Prop_FirehoseConn_Outlet_A01_N1',
         D + 'SM_BLDG_Prop_Lamp_Wall_A01_N1', D + 'SM_BLDG_Prop_Lamp_Wall_C01_N1']
for i, p in enumerate(PROPS):
    m = unreal.load_asset(p)
    a = eas.spawn_actor_from_object(m, unreal.Vector(1000 + i * 150, -1200, 60), unreal.Rotator(0, 0, 180))
    a.set_actor_label(f'TEST_{i}_{p.split("/")[-1]}')
cam = eas.spawn_actor_from_class(unreal.CineCameraActor, unreal.Vector(1450, -1750, 200), unreal.Rotator(0, -12, 90))
cam.set_actor_label('CAM_proptest')
cc = cam.get_cine_camera_component()
cc.set_editor_property('current_focal_length', 24.0)
print('PROPTEST_READY')
