"""Geometry helpers for the Mong-Ha estate build (Blender 5.x).

Everything is authored in a 'site' frame: x along Av. de Venceslau de Morais (NW->SE),
y up, z away from the avenue. B() converts a site point to Blender (Z-up) coordinates.
"""
import math
import bmesh
import bpy
from mathutils import Vector


def B(p):
    return Vector((p[0], -p[2], p[1]))


def s2l(hexcol):
    h = hexcol.lstrip('#')
    v = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in v)


MATS = {}


def M(name, color='#cccccc', rough=0.85, metal=0.0, alpha=1.0, emit=None, transmission=0.0):
    """Placeholder PBR material; the name is what Unreal keys its real material on."""
    if name in MATS:
        return MATS[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes.get('Principled BSDF')
    lin = s2l(color)
    b.inputs['Base Color'].default_value = (*lin, 1.0)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    if transmission:
        for key in ('Transmission Weight', 'Transmission'):
            if key in b.inputs:
                b.inputs[key].default_value = transmission
    if alpha < 1.0:
        b.inputs['Alpha'].default_value = alpha
    if emit:
        b.inputs['Emission Color'].default_value = (*s2l(emit), 1.0)
        b.inputs['Emission Strength'].default_value = 1.0
    m.diffuse_color = (*lin, alpha)
    MATS[name] = m
    return m


class Fr:
    """Local frame: origin o, local x -> ex, y up, local z -> ez (all in site coords)."""

    def __init__(self, o=(0, 0, 0), ex=(1, 0, 0), ez=(0, 0, 1)):
        self.o = Vector(o)
        self.ex = Vector(ex)
        self.ey = Vector((0, 1, 0))
        self.ez = Vector(ez)

    def p(self, x, y, z):
        return self.o + self.ex * x + self.ey * y + self.ez * z

    def sub(self, x=0.0, y=0.0, z=0.0, rot=0.0):
        """Child frame at local (x,y,z), rotated about y like three.js rotation.y."""
        c, s = math.cos(rot), math.sin(rot)
        return Fr(self.p(x, y, z), self.ex * c - self.ez * s, self.ex * s + self.ez * c)


class MB:
    """Accumulates faces (with material slots and metre-scaled UVs) into one mesh object."""

    def __init__(self, name, coll):
        self.name = name
        self.coll = coll
        self.bm = bmesh.new()
        self.uv = self.bm.loops.layers.uv.new('UVMap')
        self.mats = []
        self.nfaces = 0

    def mi(self, m):
        if m not in self.mats:
            self.mats.append(m)
        return self.mats.index(m)

    def poly(self, pts, m, uvs=None):
        vs = [self.bm.verts.new(B(p)) for p in pts]
        try:
            f = self.bm.faces.new(vs)
        except ValueError:
            return None
        f.material_index = self.mi(m)
        f.normal_update()
        n = f.normal
        for i, loop in enumerate(f.loops):
            if uvs is not None:
                loop[self.uv].uv = uvs[i]
                continue
            co = loop.vert.co
            ax = max(range(3), key=lambda k: abs(n[k]))
            if ax == 2:
                u, v = co.x, co.y
            elif ax == 0:
                u, v = (-co.y if n.x > 0 else co.y), co.z
            else:
                u, v = (co.x if n.y < 0 else -co.x), co.z
            loop[self.uv].uv = (u, v)
        self.nfaces += 1
        return f

    def finish(self):
        me = bpy.data.meshes.new(self.name)
        self.bm.to_mesh(me)
        self.bm.free()
        for m in self.mats:
            me.materials.append(m)
        ob = bpy.data.objects.new(self.name, me)
        self.coll.objects.link(ob)
        return ob


BOX_FACES = {'nx': (0, 4, 6, 2), 'px': (1, 3, 7, 5), 'ny': (0, 1, 5, 4),
             'py': (2, 6, 7, 3), 'nz': (0, 2, 3, 1), 'pz': (4, 5, 7, 6)}


def box(mb, fr, x0, x1, y0, y1, z0, z1, m, skip=()):
    """Axis-aligned box in frame fr. m: material or {face: material}; skip: faces to omit."""
    x0, x1 = min(x0, x1), max(x0, x1)
    y0, y1 = min(y0, y1), max(y0, y1)
    z0, z1 = min(z0, z1), max(z0, z1)
    c = [fr.p(x, y, z) for z in (z0, z1) for y in (y0, y1) for x in (x0, x1)]
    for k, idx in BOX_FACES.items():
        if k in skip:
            continue
        mat = m.get(k, m.get('*')) if isinstance(m, dict) else m
        if mat is None:
            continue
        mb.poly([c[i] for i in idx], mat)


def cylv(mb, fr, cx, cz, y0, y1, r, seg, m, caps=True, phase=0.0, r1=None, cap_m=None):
    """Vertical cylinder / prism (seg sides) in frame fr."""
    r1 = r if r1 is None else r1
    ang = [phase + 2 * math.pi * i / seg for i in range(seg)]
    lo = [fr.p(cx + r * math.sin(a), y0, cz + r * math.cos(a)) for a in ang]
    hi = [fr.p(cx + r1 * math.sin(a), y1, cz + r1 * math.cos(a)) for a in ang]
    circ = 2 * math.pi * r / seg
    for i in range(seg):
        j = (i + 1) % seg
        mb.poly([lo[i], lo[j], hi[j], hi[i]], m,
                uvs=[(i * circ, y0), ((i + 1) * circ, y0), ((i + 1) * circ, y1), (i * circ, y1)])
    if caps:
        mb.poly(hi, cap_m or m)
        mb.poly(list(reversed(lo)), cap_m or m)


def cylx(mb, fr, x0, x1, cy, cz, r, seg, m):
    """Horizontal cylinder along local x (pipes, rails)."""
    ang = [2 * math.pi * i / seg for i in range(seg)]
    a0 = [fr.p(x0, cy + r * math.sin(a), cz + r * math.cos(a)) for a in ang]
    a1 = [fr.p(x1, cy + r * math.sin(a), cz + r * math.cos(a)) for a in ang]
    for i in range(seg):
        j = (i + 1) % seg
        mb.poly([a0[i], a1[i], a1[j], a0[j]], m)


def prism_x(mb, fr, prof, x0, x1, m, cap_m=None):
    """Extrude a CCW profile given in (z, y) along local x from x0 to x1."""
    p0 = [fr.p(x0, y, z) for z, y in prof]
    p1 = [fr.p(x1, y, z) for z, y in prof]
    n = len(prof)
    mb.poly(p0, cap_m or m)
    mb.poly(list(reversed(p1)), cap_m or m)
    for i in range(n):
        j = (i + 1) % n
        mb.poly([p0[i], p1[i], p1[j], p0[j]], m)


def prism_z(mb, fr, prof, z0, z1, m, cap_m=None, side_m=None):
    """Extrude a CCW profile given in (x, y) along local z from z0 to z1."""
    p0 = [fr.p(x, y, z0) for x, y in prof]
    p1 = [fr.p(x, y, z1) for x, y in prof]
    n = len(prof)
    mb.poly(p1, cap_m or m)
    mb.poly(list(reversed(p0)), cap_m or m)
    for i in range(n):
        j = (i + 1) % n
        mb.poly([p0[i], p0[j], p1[j], p1[i]], side_m or m)


def prism_y(mb, fr, prof, y0, y1, m, cap_m=None):
    """Extrude a CCW profile given in (x, z) (seen from above, z towards viewer) along y."""
    # seen from +y looking down with x right, +z points *down* the screen, so a profile that is
    # CCW in (x, z) maths orientation is CW from above; flip for the top cap.
    p0 = [fr.p(x, y0, z) for x, z in prof]
    p1 = [fr.p(x, y1, z) for x, z in prof]
    n = len(prof)
    mb.poly(list(reversed(p1)), cap_m or m)
    mb.poly(p0, cap_m or m)
    for i in range(n):
        j = (i + 1) % n
        mb.poly([p0[i], p1[i], p1[j], p0[j]], m)


def quad_bezier(p0, p1, p2, steps=6):
    out = []
    for i in range(1, steps + 1):
        t = i / steps
        out.append(((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
                    (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]))
    return out


def arc(cx, cy, r, a0, a1, steps):
    return [(cx + r * math.cos(a0 + (a1 - a0) * i / steps), cy + r * math.sin(a0 + (a1 - a0) * i / steps)) for i in range(steps + 1)]
