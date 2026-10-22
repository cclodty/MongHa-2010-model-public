"""Checks that every primitive in mh_geom produces outward-facing normals."""
import os
import sys
import bpy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mh_geom import MB, Fr, M, box, cylv, cylx, prism_x, prism_y, prism_z, B  # noqa: E402

bpy.ops.wm.read_factory_settings(use_empty=True)
coll = bpy.context.scene.collection
mat = M('T')
cases = []


def check(name, build, center, fr):
    mb = MB(name, coll)
    build(mb, fr)
    bm = mb.bm
    c = B(fr.p(*center))
    bad = 0
    for f in bm.faces:
        f.normal_update()
        if (f.calc_center_median() - c).dot(f.normal) <= 0:
            bad += 1
    cases.append((name, len(bm.faces), bad))
    mb.finish()


for rot in (0.0, 1.0, 3.14159):
    fr = Fr((3, 1, -2)).sub(1, 0, 2, rot)
    check(f'box{rot}', lambda mb, f: box(mb, f, -1, 2, 0, 3, -0.5, 0.5, mat), (0.5, 1.5, 0), fr)
    check(f'cylv{rot}', lambda mb, f: cylv(mb, f, 0, 0, 0, 2, 1, 12, mat), (0, 1, 0), fr)
    check(f'cylx{rot}', lambda mb, f: cylx(mb, f, -2, 2, 1, 0, 0.5, 10, mat), (0, 1, 0), fr)
    sq = [(-1, 0), (1, 0), (1, 2), (-1, 2)]   # CCW in (z,y) / (x,y) / (x,z)
    check(f'prism_x{rot}', lambda mb, f: prism_x(mb, f, sq, -0.5, 0.5, mat), (0, 1, 0), fr)
    check(f'prism_z{rot}', lambda mb, f: prism_z(mb, f, sq, -0.5, 0.5, mat), (0, 1, 0), fr)
    sq2 = [(-1, -1), (1, -1), (1, 1), (-1, 1)]
    check(f'prism_y{rot}', lambda mb, f: prism_y(mb, f, sq2, 0, 2, mat), (0, 1, 0), fr)

for name, n, bad in cases:
    print(f'{name:14s} faces={n:3d} inward={bad}')
print('ALL_OK' if all(b == 0 for _, _, b in cases) else 'SOME_BAD')
