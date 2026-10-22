# Runs inside Unreal Editor: list what the user added from Fab (meshes, material instances, decals) with sizes.
import unreal

eal = unreal.EditorAssetLibrary
ar = unreal.AssetRegistryHelpers.get_asset_registry()
ROOTS = [r for r in ('/Game/Fab', '/Game/Megascans', '/Game/MSPresets', '/Game/Quixel') if eal.does_directory_exist(r)]
print('roots', ROOTS)
for root in ROOTS:
    for d in ar.get_assets_by_path(root, recursive=True):
        cls = str(d.asset_class_path.asset_name)
        if cls not in ('StaticMesh', 'MaterialInstanceConstant', 'Material', 'SkeletalMesh', 'Blueprint', 'FoliageType_InstancedStaticMesh'):
            continue
        line = f'{cls:28s} {d.package_name}'
        if cls == 'StaticMesh':
            sm = unreal.load_asset(str(d.package_name))
            bb = sm.get_bounding_box()
            line += f'  size_m=({(bb.max.x - bb.min.x) / 100:.1f},{(bb.max.y - bb.min.y) / 100:.1f},{(bb.max.z - bb.min.z) / 100:.1f})'
        print(line)
print('SCAN_DONE')
