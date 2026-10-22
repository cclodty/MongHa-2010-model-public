# Runs inside Unreal Editor: import textures + the Blender-built FBX, enable Nanite.
import os
import unreal

ROOT = r"G:\Claude\mongha-ue"
TEX_DIR = os.path.join(ROOT, "textures")
FBX = os.path.join(ROOT, "export", "MongHa_2010_UE.fbx")   # blender/ue_export.py: estate only, edges chamfered
at = unreal.AssetToolsHelpers.get_asset_tools()
eal = unreal.EditorAssetLibrary


def fbx_options():
    ui = unreal.FbxImportUI()
    ui.set_editor_property('import_materials', False)
    ui.set_editor_property('import_textures', False)
    sm = ui.get_editor_property('static_mesh_import_data')
    for k, v in (('combine_meshes', False), ('generate_lightmap_u_vs', False), ('auto_generate_collision', False),
                 ('build_nanite', True), ('remove_degenerates', True)):
        try:
            sm.set_editor_property(k, v)
        except Exception as e:
            print('fbx option skipped', k, e)
    return ui


def import_files(files, dest, options=None):
    tasks = []
    for f in files:
        t = unreal.AssetImportTask()
        if options:
            t.set_editor_property('options', options)
        t.set_editor_property('filename', f)
        t.set_editor_property('destination_path', dest)
        t.set_editor_property('automated', True)
        t.set_editor_property('replace_existing', True)
        t.set_editor_property('save', True)
        tasks.append(t)
    at.import_asset_tasks(tasks)
    out = []
    for t in tasks:
        out += list(t.get_editor_property('imported_object_paths'))
    return out


# --- textures
if globals().get('SKIP_TEX'):
    TEX_DIR = None
pngs = [] if TEX_DIR is None else [os.path.join(TEX_DIR, f) for f in sorted(os.listdir(TEX_DIR)) if f.endswith('.png')]
imported = import_files(pngs, '/Game/MongHa/Textures')
print('textures imported:', len(imported))
for p in eal.list_assets('/Game/MongHa/Textures', recursive=False):
    tex = unreal.load_asset(p)
    if not isinstance(tex, unreal.Texture2D):
        continue
    name = tex.get_name()
    if name.endswith('_N'):
        tex.set_editor_property('srgb', False)
        tex.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_NORMALMAP)
    eal.save_loaded_asset(tex)

# --- meshes
if not eal.does_directory_exist('/Game/MongHa/Meshes'):
    eal.make_directory('/Game/MongHa/Meshes')
mesh_paths = import_files([FBX], '/Game/MongHa/Meshes', fbx_options())
print('fbx imported objects:', len(mesh_paths))
sme = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
for p in eal.list_assets('/Game/MongHa/Meshes', recursive=True):
    a = unreal.load_asset(p)
    if isinstance(a, unreal.StaticMesh):
        ns = a.get_editor_property('nanite_settings')
        ns.set_editor_property('enabled', True)
        try:
            sme.set_nanite_settings(a, ns, apply_changes=True)
        except Exception:
            a.set_editor_property('nanite_settings', ns)
        bs = a.get_editor_property('body_setup')   # walkable: collide against the render mesh itself
        if bs:
            bs.set_editor_property('collision_trace_flag', unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        eal.save_loaded_asset(a)
        slots = [str(s.get_editor_property('material_slot_name')) for s in a.get_editor_property('static_materials')]
        bb = a.get_bounding_box()
        print('MESH', a.get_name(), 'slots', len(slots), 'min', bb.min, 'max', bb.max)
print('IMPORT_DONE')
