# Runs inside Unreal Editor: move the sun to another time of day (same NOAA sun model and site orientation as ue_03_level.py)
# and shift every camera's exposure window. Args: TIME (local hours, default 9.5 = the ue_03 setup), DEV (EV offset, default 0).
#   golden hours, 15 May 2010: 7.5 lights the avenue facade, 17.2 lights the courtyard faces of the front and SE rows.
import datetime
import math

import unreal

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
TIME = float(globals().get('TIME', 9.5))
DEV = float(globals().get('DEV', 0.0))
DATE = (2010, 5, 15)
LAT, LON, TZ = 22.2066, 113.5519, 8.0
NORTH_SITE, EAST_SITE = (-0.666, -0.747), (0.747, -0.666)
VIEW_EV = dict(court_1990=13.1, avenue_2008=13.4, courtyard_aerial=13.2, library=12.1, gallery_deck=11.3)   # = ue_06_look.py


def sun_pos(y, m, d, hour):
    n = datetime.date(y, m, d).timetuple().tm_yday
    g = 2 * math.pi / 365 * (n - 1 + (hour - 12) / 24)
    eqt = 229.18 * (0.000075 + 0.001868 * math.cos(g) - 0.032077 * math.sin(g) - 0.014615 * math.cos(2 * g) - 0.040849 * math.sin(2 * g))
    decl = 0.006918 - 0.399912 * math.cos(g) + 0.070257 * math.sin(g) - 0.006758 * math.cos(2 * g) + 0.000907 * math.sin(2 * g) - 0.002697 * math.cos(3 * g) + 0.00148 * math.sin(3 * g)
    ha = math.radians((hour * 60 + eqt + 4 * LON - 60 * TZ) / 4 - 180)
    lat = math.radians(LAT)
    el = math.degrees(math.asin(math.sin(lat) * math.sin(decl) + math.cos(lat) * math.cos(decl) * math.cos(ha)))
    az = (math.degrees(math.atan2(math.sin(ha), math.cos(ha) * math.sin(lat) - math.tan(decl) * math.cos(lat))) + 180) % 360
    return az, el


az, el = sun_pos(*DATE, TIME)
ca, sa = math.cos(math.radians(az)), math.sin(math.radians(az))
hx, hz = ca * NORTH_SITE[0] + sa * EAST_SITE[0], ca * NORTH_SITE[1] + sa * EAST_SITE[1]   # towards the sun, site frame
yaw = math.degrees(math.atan2(-hz, -hx))                                                   # UE = (x*100, z*100, y*100)
acts = {a.get_actor_label(): a for a in eas.get_all_level_actors()}
acts['Sun'].set_actor_rotation(unreal.Rotator(roll=0, pitch=-el, yaw=yaw), False)
for label, a in acts.items():
    if not label.startswith('CAM_') or label[4:] not in VIEW_EV:
        continue
    cc = a.get_cine_camera_component()
    cps = cc.get_editor_property('post_process_settings')
    ev = VIEW_EV[label[4:]] + DEV
    cps.set_editor_property('auto_exposure_min_brightness', ev - 0.25)
    cps.set_editor_property('auto_exposure_max_brightness', ev + 0.25)
    cc.set_editor_property('post_process_settings', cps)
les.save_current_level()
print(f'LIGHT_DONE time {TIME} sun az {az:.1f} el {el:.1f} yaw {yaw:.1f} dEV {DEV}')
