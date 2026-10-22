# Runs inside Unreal Editor: pilot the level viewport through CAM_<name> (passed via UE_VIEW env-free global).
import unreal

les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
name = VIEW  # noqa: F821  (set by the caller: "VIEW='courtyard_aerial'\n" + this file)
cam = next(a for a in eas.get_all_level_actors() if a.get_actor_label() == 'CAM_' + name)
les.editor_set_game_view(True)
les.pilot_level_actor(cam)
unreal.SystemLibrary.execute_console_command(None, 'r.ScreenPercentage 100')
print('PILOTING', name)
