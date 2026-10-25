"""Bake the estate's lighting for the web viewer and export compressed glTF.

Run on the exported scene:
  blender -b export/MongHa_2010.blend -P blender/web_bake.py -- [--quick] [--only=SM_Library,SM_Courtyard] [--samples=256]
      [--sun-samples=24] [--vc-samples=160] [--denoise] [--out=export/web_bake]
--out: write the GLBs, lightmaps and manifest there instead of web/assets (copy them over once the bake has finished,
so a long bake never leaves web/assets half new).
--rebake=SM_Estate_NW,SM_Estate_SE: bake and export only these families into a full bake already in --out, merging
their entries into its manifest.json; every other object stays in the scene whole, so it still shades and lights them.
Without a GPU (a cloud machine's CPU is ~100 times slower), bake with fewer samples and --denoise: each lightmap's sky
and bounce light goes through OpenImageDenoise (the compositor's Denoise node, on the CPU), e.g.
  -- --samples=96 --sun-samples=24 --vc-samples=160 --denoise   (about two hours on four CPU cores)

Every mesh is split three ways:
  *_LM  large faces  -> own lightmap UV ('LM') + baked lightmap image (direct + indirect diffuse light)
  *_VC  small faces  -> baked light stored per vertex (railings, frames, garments, foliage)
  *_NB  glass, glowing or see-through surfaces that the viewer shades itself
Light values are irradiance-like multipliers of albedo. Baked light excludes the direct sun: the viewer adds the sun
live (so normal maps and bevels respond) and multiplies it by a baked sun-visibility mask (_SM.jpg, or vertex alpha).
Stored as (v / LMAX) in sRGB (lightmaps) or sqrt(v / LMAX) (vertex colours); see manifest.json.
"""
import json
import math
import os
import sys
import tempfile
import time

import bmesh
import bpy
import numpy as np

ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
QUICK = '--quick' in ARGS
ONLY = next((a.split('=', 1)[1].split(',') for a in ARGS if a.startswith('--only=')), None)
REBAKE = next((a.split('=', 1)[1].split(',') for a in ARGS if a.startswith('--rebake=')), None)
SAMPLES = int(next((a.split('=', 1)[1] for a in ARGS if a.startswith('--samples=')), 48 if QUICK else 1536))
SUN_SAMPLES = int(next((a.split('=', 1)[1] for a in ARGS if a.startswith('--sun-samples=')), min(SAMPLES, 256)))   # sun only
VC_SAMPLES = int(next((a.split('=', 1)[1] for a in ARGS if a.startswith('--vc-samples=')), SAMPLES))   # per-vertex light
DENOISE = '--denoise' in ARGS
try:
    sys.stdout.reconfigure(line_buffering=True)   # progress lines as they come, also when logged to a file
except Exception:
    pass
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, next((a.split('=', 1)[1] for a in ARGS if a.startswith('--out=')), os.path.join('web', 'assets')))
os.makedirs(OUT, exist_ok=True)
LMAX = 1.6      # sky + bounce only (the sun is added live); values are albedo multipliers
SKY = json.load(open(os.path.join(ROOT, 'export', 'sky.json'), encoding='utf-8'))
BEVEL = {'SM_Estate_FRONT', 'SM_Estate_BACK', 'SM_Estate_NW', 'SM_Estate_SE', 'SM_Estate_SlopeBlocks', 'SM_Galleries_Bridges', 'SM_Library', 'SM_Courtyard', 'SM_SportsHall_Simple'}
MARK = json.load(open(os.path.join(ROOT, 'export', 'markers.json'), encoding='utf-8'))

# texel density (texels per metre) and size caps per family; the far ground and towers get much less
DENSITY = {'SM_Context_Massing': 1.5, 'SM_Ground_Far': 0.6, 'SM_Library': 26.0, 'SM_Galleries_Bridges': 22.0, 'SM_Courtyard': 20.0,
           'SM_SportsHall_Simple': 12.0}
SPLIT_LM = {'SM_Estate_NW': 1, 'SM_Estate_SE': 1}   # the 106 m side rows get two lightmaps each   # lightmap split in two along Blender axis (0 = x, 1 = y)
DEFAULT_DENSITY = 4.0 if QUICK else 11.0
MAX_RES = 2048 if QUICK else 4096
AREA_TH = 0.3   # m^2: below this a face is lit per vertex (keeps the lightmap island count manageable)
NO_BAKE = ('M_Glass_Residential', 'M_Shop_Glass', 'M_Glass_Library', 'M_Context_Glass', 'M_Lamp_Globe', 'M_TrafficLight_Green')
SEE_THROUGH = {'M_ChainLink': 0.3, 'M_BreezeBlock': 0.55, 'M_Cloth_Atlas': 0.9}
CARDS = ('M_Sign_Desporto', 'M_Sign_HallName')   # a logo and lettering on cards 5 mm off the hall's gable, cut out in the viewer
VC_FORCE = ('M_Leaves', 'M_Bark')   # foliage is lit per vertex whatever the card size

scene = bpy.context.scene
scene.render.engine = 'CYCLES'
prefs = bpy.context.preferences.addons['cycles'].preferences
for dev_type in ('OPTIX', 'CUDA'):
    try:
        prefs.compute_device_type = dev_type
        prefs.get_devices()
        if any(d.type == dev_type for d in prefs.devices):
            break
    except Exception:
        continue
for d in prefs.devices:
    d.use = d.type != 'CPU'
scene.cycles.device = 'GPU'
scene.cycles.samples = SAMPLES
scene.cycles.max_bounces = 6
scene.cycles.diffuse_bounces = 4
scene.render.bake.margin = 6
print('BAKE device', prefs.compute_device_type, [d.name for d in prefs.devices if d.use], 'samples', SAMPLES, 'sun', SUN_SAMPLES,
      'vc', VC_SAMPLES, 'denoise', DENOISE)

# ---------------------------------------------------------------- light: Poly Haven HDRI sky (sun removed) + matching sun lamp
for ob in list(bpy.data.objects):
    if ob.type == 'LIGHT':
        bpy.data.objects.remove(ob)
from mathutils import Vector  # noqa: E402
SUN_B = Vector(SKY['sun_dir_blender']).normalized()
SUN_E = SKY['sun_strength']
ld = bpy.data.lights.new('Sun', 'SUN')
ld.energy = SUN_E
ld.color = SKY['sun_color']
ld.angle = math.radians(0.53)
sun = bpy.data.objects.new('Sun', ld)
scene.collection.objects.link(sun)
sun.rotation_euler = SUN_B.to_track_quat('Z', 'Y').to_euler()
world = bpy.data.worlds.new('Sky')
scene.world = world
world.use_nodes = True
nt = world.node_tree
nt.nodes.clear()
env = nt.nodes.new('ShaderNodeTexEnvironment')
env.image = bpy.data.images.load(os.path.join(ROOT, 'textures', 'sky_bake.exr'))
bg = nt.nodes.new('ShaderNodeBackground')
outn = nt.nodes.new('ShaderNodeOutputWorld')
nt.links.new(env.outputs['Color'], bg.inputs['Color'])
bg.inputs['Strength'].default_value = 1.0
nt.links.new(bg.outputs[0], outn.inputs[0])
world.cycles.sampling_method = 'MANUAL'
world.cycles.sample_map_resolution = 1024


def sky_on(on):
    bg.inputs['Strength'].default_value = 1.0 if on else 0.0


def see_through_shadows_only(m, b):
    """Alpha only for shadow rays: the surface itself bakes as opaque (cards' transparent corners would bake black),
    while light still passes through leaves, mesh fences and breeze blocks."""
    nt = m.node_tree
    bc = b.inputs['Base Color']
    for l in list(bc.links):   # Cycles divides the diffuse light pass by albedo: black atlas texels would bake to 0
        nt.links.remove(l)
        bc.default_value = (0.32, 0.42, 0.22, 1.0)
    a_in = b.inputs['Alpha']
    src = a_in.links[0].from_socket if a_in.links else None
    lp = nt.nodes.new('ShaderNodeLightPath')
    one_minus = nt.nodes.new('ShaderNodeMath')
    one_minus.operation = 'SUBTRACT'
    one_minus.inputs[0].default_value = 1.0
    if src:
        nt.links.new(src, one_minus.inputs[1])
    else:
        one_minus.inputs[1].default_value = a_in.default_value
    mul = nt.nodes.new('ShaderNodeMath')
    mul.operation = 'MULTIPLY'
    nt.links.new(lp.outputs['Is Shadow Ray'], mul.inputs[0])
    nt.links.new(one_minus.outputs[0], mul.inputs[1])
    res = nt.nodes.new('ShaderNodeMath')
    res.operation = 'SUBTRACT'
    res.inputs[0].default_value = 1.0
    nt.links.new(mul.outputs[0], res.inputs[1])
    nt.links.new(res.outputs[0], a_in)


def card_only(m, b):
    """A card that only carries a cut-out logo or lettering bakes as opaque itself (bake rays start as camera rays) but
    is invisible to every other ray: the wall that shows round the letters must not bake in the card's shade."""
    lp = m.node_tree.nodes.new('ShaderNodeLightPath')
    m.node_tree.links.new(lp.outputs['Is Camera Ray'], b.inputs['Alpha'])


# ---------------------------------------------------------------- materials: a bake image node in each, see-through where needed
BAKE_NODE = 'LM_BAKE'
for m in bpy.data.materials:
    if not m.use_nodes:
        continue
    n = m.node_tree.nodes.get(BAKE_NODE) or m.node_tree.nodes.new('ShaderNodeTexImage')
    n.name = BAKE_NODE
    b = m.node_tree.nodes.get('Principled BSDF')
    if b and m.name in SEE_THROUGH:
        b.inputs['Alpha'].default_value = SEE_THROUGH[m.name]
    if b and (m.name in SEE_THROUGH or m.name == 'M_Leaves'):
        see_through_shadows_only(m, b)
    if b and m.name in CARDS:
        card_only(m, b)
    if b and m.name in NO_BAKE and 'Glass' in m.name:   # glass lets light into the rooms but casts a faint shadow
        b.inputs['Alpha'].default_value = 0.15


# ---------------------------------------------------------------- split objects into LM / VC / NB
def face_class(me):
    area = np.zeros(len(me.polygons))
    me.polygons.foreach_get('area', area)
    mi = np.zeros(len(me.polygons), dtype=np.int32)
    me.polygons.foreach_get('material_index', mi)
    names = [s.name if s else '' for s in me.materials]
    nb = np.array([names[i] in NO_BAKE for i in mi], dtype=bool) if len(mi) else np.zeros(0, bool)
    vf = np.array([names[i] in VC_FORCE for i in mi], dtype=bool) if len(mi) else np.zeros(0, bool)
    cls = np.where(nb, 2, np.where((area >= AREA_TH) & ~vf, 0, 1))
    return cls


VC_STEP = 0.4   # m: longest edge left in a per-vertex part
VC_SUBDIV = {'SM_Galleries_Bridges', 'SM_Courtyard', 'SM_Library', 'SM_SportsHall_Simple'}   # stairs, posts, benches; doing the blocks too doubled their GLBs


def vc_subdivide(bm):
    """Per-vertex light is sampled only at vertices. A post or rail has vertices only where it meets the ground, a landing
    or another rail, all half-buried, so it came out almost black (stair posts, 2026-10-22). Cut long edges so there are
    samples in the open; edges of equal length (cylinder sides, rail tubes) share a cut count, so quads stay quads."""
    groups = {}
    for e in bm.edges:
        n = int(e.calc_length() / VC_STEP)
        if n >= 1:
            groups.setdefault(min(n, 24), []).append(e)
    for n, edges in sorted(groups.items()):
        edges = [e for e in edges if e.is_valid]
        if edges:
            bmesh.ops.subdivide_edges(bm, edges=edges, cuts=n, use_grid_fill=True)


def split(ob):
    cls = face_class(ob.data)
    parts = {}
    for c, suffix in ((0, '_LM'), (1, '_VC'), (2, '_NB')):
        if not (cls == c).any():
            continue
        me = ob.data.copy()
        bm = bmesh.new()
        bm.from_mesh(me)
        bm.faces.ensure_lookup_table()
        kill = [f for f, k in zip(bm.faces, cls) if k != c]
        bmesh.ops.delete(bm, geom=kill, context='FACES')
        if c == 0:
            bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0005)
        if c == 1 and ob.name in VC_SUBDIV:
            vc_subdivide(bm)
        bm.to_mesh(me)
        bm.free()
        nob = bpy.data.objects.new(ob.name + suffix, me)
        for col in ob.users_collection:
            col.objects.link(nob)
        parts[suffix] = nob
    bpy.data.objects.remove(ob)
    return parts


def ground_far(ob):
    """Pull the huge background ground quad out of the streets so it gets its own coarse lightmap."""
    me = ob.data
    area = np.zeros(len(me.polygons))
    me.polygons.foreach_get('area', area)
    big = area > 20000
    if not big.any():
        return None
    far = ob.copy()
    far.data = me.copy()
    far.name = 'SM_Ground_Far'
    for col in ob.users_collection:
        col.objects.link(far)
    for target, keep in ((ob, ~big), (far, big)):
        bm = bmesh.new()
        bm.from_mesh(target.data)
        bm.faces.ensure_lookup_table()
        bmesh.ops.delete(bm, geom=[f for f, k in zip(bm.faces, keep) if not k], context='FACES')
        bm.to_mesh(target.data)
        bm.free()
    return far


def split_halves(ob, axis):
    """Two objects (each with its own lightmap) from one, cut at the median face centre along axis."""
    me = ob.data
    c = np.zeros(len(me.polygons) * 3)
    me.polygons.foreach_get('center', c)
    c = c.reshape(-1, 3)[:, axis]
    cut = float(np.median(c))
    out = []
    for k, keep in enumerate((c < cut, c >= cut)):
        part = ob.copy()
        part.data = me.copy()
        part.name = f'{ob.name}{k}'
        for col in ob.users_collection:
            col.objects.link(part)
        bm = bmesh.new()
        bm.from_mesh(part.data)
        bm.faces.ensure_lookup_table()
        bmesh.ops.delete(bm, geom=[f for f, kk in zip(bm.faces, keep) if not kk], context='FACES')
        bm.to_mesh(part.data)
        bm.free()
        out.append(part)
    bpy.data.objects.remove(ob)
    return out


def select_only(ob):
    bpy.context.view_layer.update()
    for o in list(bpy.context.view_layer.objects):
        if o is not None:
            o.select_set(False)
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob


def lightmap_uv(ob, density):
    me = ob.data
    if 'LM' not in me.uv_layers:
        me.uv_layers.new(name='LM')
    me.uv_layers.active = me.uv_layers['LM']
    select_only(ob)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(35), island_margin=0.0, area_weight=0.0, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(rotate=True, scale=True, margin_method='FRACTION', margin=0.0009)
    bpy.ops.object.mode_set(mode='OBJECT')
    area = np.zeros(len(me.polygons))
    me.polygons.foreach_get('area', area)
    side = math.sqrt(area.sum() / 0.62) * density          # ~62 % packing efficiency
    res = int(min(MAX_RES, max(256, 2 ** math.ceil(math.log2(max(side, 1))))))
    me.uv_layers.active = me.uv_layers[0]
    return res


def set_bake_image(ob, img):
    for slot in ob.material_slots:
        m = slot.material
        if m and m.use_nodes:
            n = m.node_tree.nodes[BAKE_NODE]
            n.image = img
            m.node_tree.nodes.active = n


def encode_srgb(x):
    x = np.clip(x, 0, 1)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def bevel(ob):
    """Chamfer the big surfaces' edges (2.5 cm, two segments) so corners catch the live sun."""
    n0 = len(ob.data.polygons)
    md = ob.modifiers.new('Bevel', 'BEVEL')
    md.width = 0.025
    md.segments = 2
    md.limit_method = 'ANGLE'
    md.angle_limit = math.radians(40)
    md.use_clamp_overlap = True
    select_only(ob)
    bpy.ops.object.modifier_apply(modifier=md.name)
    print(f'BEVEL {ob.name} {n0} -> {len(ob.data.polygons)} faces')


def bake_image(ob, res, kind, **kw):
    img = bpy.data.images.new(f'{ob.name}_{kind}', res, res, alpha=False, float_buffer=True)
    img.colorspace_settings.name = 'Non-Color'
    set_bake_image(ob, img)
    select_only(ob)
    bpy.ops.object.bake(target='IMAGE_TEXTURES', uv_layer='LM', margin=6, use_clear=True, **kw)
    px = np.empty(res * res * 4, np.float32)
    img.pixels.foreach_get(px)
    bpy.data.images.remove(img)
    return px.reshape(res, res, 4)[:, :, :3]


def save_jpg(name, arr, q=90):
    h, w = arr.shape[:2]
    rgba = np.ones((h, w, 4), np.float32)
    rgba[:, :, :3] = arr if arr.ndim == 3 else arr[..., None]
    out = bpy.data.images.new(name, w, h, alpha=False)
    out.pixels.foreach_set(rgba.ravel())
    out.filepath_raw = os.path.join(OUT, name + '.jpg')
    out.file_format = 'JPEG'
    scene.render.image_settings.quality = q
    out.save()
    bpy.data.images.remove(out)


_DN = {}


def denoise(px):
    """OpenImageDenoise over a baked lightmap (linear, HDR), through the compositor's Denoise node on the CPU, in a
    scene of its own with nothing to render."""
    res = px.shape[0]
    if not _DN:
        dn = bpy.data.scenes.new('Denoise')
        dn.render.engine = 'CYCLES'
        dn.cycles.samples = 1
        dn.cycles.device = 'CPU'
        dn.render.compositor_device = 'CPU'
        dn.render.compositor_denoise_device = 'CPU'
        dn.render.compositor_denoise_final_quality = 'HIGH'
        dn.render.use_compositing = True
        dn.render.resolution_percentage = 100
        dn.render.image_settings.file_format = 'OPEN_EXR'
        dn.render.image_settings.color_depth = '32'
        ng = bpy.data.node_groups.new('Denoise', 'CompositorNodeTree')
        dn.compositing_node_group = ng
        ng.interface.new_socket('Image', in_out='OUTPUT', socket_type='NodeSocketColor')
        src, node, out = ng.nodes.new('CompositorNodeImage'), ng.nodes.new('CompositorNodeDenoise'), ng.nodes.new('NodeGroupOutput')
        node.inputs['HDR'].default_value = True
        ng.links.new(src.outputs['Image'], node.inputs['Image'])
        ng.links.new(node.outputs['Image'], out.inputs[0])
        _DN.update(scene=dn, src=src, dir=tempfile.mkdtemp(prefix='mh_denoise_'))
    dn = _DN['scene']
    img = bpy.data.images.new('denoise_in', res, res, alpha=False, float_buffer=True)
    img.colorspace_settings.name = 'Non-Color'
    rgba = np.ones((res, res, 4), np.float32)
    rgba[:, :, :3] = px
    img.pixels.foreach_set(rgba.ravel())
    _DN['src'].image = img
    dn.render.resolution_x = dn.render.resolution_y = res
    path = os.path.join(_DN['dir'], 'denoised.exr')
    dn.render.filepath = path
    bpy.ops.render.render(write_still=True, scene=dn.name)
    got = bpy.data.images.load(path)
    got.colorspace_settings.name = 'Non-Color'
    arr = np.empty(res * res * 4, np.float32)
    got.pixels.foreach_get(arr)
    for im in (got, img):
        bpy.data.images.remove(im)
    os.remove(path)
    return np.clip(arr.reshape(res, res, 4)[:, :, :3], 0, None)


def sun_mask(direct, normals):
    """Sun visibility 0..1 from the sun-only direct bake and the surface normal (Cycles: value = E cos / pi)."""
    cosg = normals @ np.array(SUN_B, np.float32)
    m = direct * math.pi / (SUN_E * np.maximum(cosg, 0.06))
    return np.where(cosg > 0.02, np.clip(m, 0, 1), 0.0)


def bake_lightmap(ob, res):
    t = time.time()
    scene.cycles.samples = SAMPLES
    sky_on(True)
    full = bake_image(ob, res, 'full', type='DIFFUSE', pass_filter={'DIRECT', 'INDIRECT'})
    scene.cycles.samples = SUN_SAMPLES
    sky_on(False)
    direct = bake_image(ob, res, 'sun', type='DIFFUSE', pass_filter={'DIRECT'})
    scene.cycles.samples = 4
    nrm = bake_image(ob, res, 'nrm', type='NORMAL', normal_space='OBJECT') * 2 - 1
    sky_on(True)
    scene.cycles.samples = SAMPLES
    sun_g = direct[:, :, 1] / max(SKY['sun_color'][1], 1e-3)
    mask = sun_mask(sun_g, nrm)
    px = np.clip(full - direct, 0, None)                       # sky + bounce
    if DENOISE:
        px = denoise(px)
    save_jpg(ob.name + '_SM', mask, 92)
    enc = encode_srgb(px / LMAX)
    out = bpy.data.images.new(ob.name + '_lm', res, res, alpha=False)
    rgba = np.ones((res, res, 4), np.float32)
    rgba[:, :, :3] = enc
    out.pixels.foreach_set(rgba.ravel())
    out.filepath_raw = os.path.join(OUT, ob.name + '.jpg')
    out.file_format = 'JPEG'
    scene.render.image_settings.quality = 90
    out.save()
    stats = dict(mean=float(px.mean()), p99=float(np.percentile(px, 99)), max=float(px.max()), lit=float((mask > 0.5).mean()))
    bpy.data.images.remove(out)
    print(f'BAKED LM {ob.name} {res}px in {time.time() - t:.0f}s', stats)
    return stats


def bake_vertex(ob):
    me = ob.data
    for a in list(me.color_attributes):
        me.color_attributes.remove(a)
    ca = me.color_attributes.new('BakeF', 'FLOAT_COLOR', 'CORNER')
    me.color_attributes.active_color = ca
    select_only(ob)
    t = time.time()
    n = len(me.loops)

    def bake_corners(**kw):
        bpy.ops.object.bake(target='VERTEX_COLORS', use_clear=True, **kw)
        arr = np.empty(n * 4, np.float32)
        me.color_attributes['BakeF'].data.foreach_get('color', arr)
        return arr.reshape(n, 4)[:, :3]
    scene.cycles.samples = VC_SAMPLES
    sky_on(True)
    full = bake_corners(type='DIFFUSE', pass_filter={'DIRECT', 'INDIRECT'})
    scene.cycles.samples = SUN_SAMPLES
    sky_on(False)
    direct = bake_corners(type='DIFFUSE', pass_filter={'DIRECT'})
    sky_on(True)
    scene.cycles.samples = SAMPLES
    cn = np.empty(n * 3, np.float32)
    me.corner_normals.foreach_get('vector', cn)
    mask = sun_mask(direct[:, 1] / max(SKY['sun_color'][1], 1e-3), cn.reshape(n, 3))
    v = np.clip(full - direct, 0, None)
    out = np.ones((n, 4), np.float32)
    out[:, :3] = np.sqrt(np.clip(v / LMAX, 0, 1))             # stored as-is in COLOR_0; the viewer squares it back
    out[:, 3] = mask                                           # sun visibility
    cb = me.color_attributes.new('Bake', 'FLOAT_COLOR', 'CORNER')
    if n:
        cb.data.foreach_set('color', out.ravel())
    me.color_attributes.remove(me.color_attributes['BakeF'])
    me.color_attributes.active_color = me.color_attributes['Bake']
    me.color_attributes.render_color_index = me.color_attributes.active_color_index
    print(f'BAKED VC {ob.name} {n} corners in {time.time() - t:.0f}s mean={float(v.mean()):.3f} lit={float((mask > 0.5).mean()):.2f}')


# ---------------------------------------------------------------- run
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import web_trees  # noqa: E402
tc = bpy.data.collections.new('WebTrees')
scene.collection.children.link(tc)
web_trees.build(MARK, tc)
for m in bpy.data.materials:   # web_trees adds materials after the bake nodes were set up
    if m.use_nodes and BAKE_NODE not in m.node_tree.nodes:
        m.node_tree.nodes.new('ShaderNodeTexImage').name = BAKE_NODE
        if m.name == 'M_Leaves':
            see_through_shadows_only(m, m.node_tree.nodes['Principled BSDF'])
# the web model leaves out the surrounding towers; the sports hall and the hillside blocks are back in (user, 2026-10-22)
for gone in ('SM_Context_Massing',):
    if gone in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects[gone])
src = [o for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith('SM_')]
if ONLY:
    keep = set(ONLY) | {'SM_Ground_Streets'}
    for o in src:
        if o.name not in keep:
            o.hide_render = True        # still casts nothing; quick pilots bake fewer objects
gf = ground_far(bpy.data.objects['SM_Ground_Streets']) if 'SM_Ground_Streets' in bpy.data.objects else None
src = [o for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith('SM_') and not o.hide_render]
manifest = dict(lmax=LMAX, vc_encoding='sqrt', lm_encoding='srgb', objects={}, samples=SAMPLES, sun_samples=SUN_SAMPLES,
                vc_samples=VC_SAMPLES, denoised=DENOISE,
                sun=SKY['sun_dir_site'], sun_strength=SUN_E, sun_color=SKY['sun_color'], sky_K=SKY['web_sky_K'],
                horizon=SKY['horizon_rgb_web'], views=MARK['views'])
for o in src:
    family = o.name
    if REBAKE and family not in REBAKE:
        continue   # kept whole: it still casts its shadows and bounce light on the families re-baked
    parts = split(o)
    for suffix, ob0 in parts.items():
        pieces = split_halves(ob0, SPLIT_LM[family]) if (suffix == '_LM' and family in SPLIT_LM) else [ob0]
        for ob in pieces:
            entry = dict(family=family, kind=suffix[1:])
            if suffix == '_LM':
                if family in BEVEL:
                    bevel(ob)
                res = lightmap_uv(ob, DENSITY.get(family, DEFAULT_DENSITY))
                entry.update(lightmap=ob.name + '.jpg', mask=ob.name + '_SM.jpg', res=res, stats=bake_lightmap(ob, res))
            elif suffix == '_VC':
                bake_vertex(ob)
            manifest['objects'][ob.name] = entry

# ---------------------------------------------------------------- export: one GLB per family (artifact files must stay < 15 MB)
mat_info = {}
for m in bpy.data.materials:
    b = m.node_tree.nodes.get('Principled BSDF') if m.use_nodes else None
    if b:
        c = b.inputs['Base Color'].default_value
        mat_info[m.name] = dict(color=[round(c[0], 4), round(c[1], 4), round(c[2], 4)],
                                rough=round(b.inputs['Roughness'].default_value, 3), metal=round(b.inputs['Metallic'].default_value, 3))
manifest['materials'] = mat_info
families = sorted({e['family'] for e in manifest['objects'].values()})
manifest['files'] = []
for fam in families:
    obs = [bpy.data.objects[n] for n, e in manifest['objects'].items() if e['family'] == fam]
    for o in bpy.context.view_layer.objects:
        o.select_set(o in obs)
    path = os.path.join(OUT, fam + '.glb')
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True, export_apply=False,
                              export_texcoords=True, export_normals=True, export_materials='EXPORT', export_image_format='NONE',
                              export_vertex_color='ACTIVE', export_all_vertex_colors=False,
                              export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=7,
                              export_draco_position_quantization=16, export_draco_normal_quantization=10,
                              export_draco_texcoord_quantization=14, export_draco_color_quantization=10,
                              export_cameras=False, export_lights=False, export_extras=False, export_yup=True)
    manifest['files'].append(dict(family=fam, glb=fam + '.glb', bytes=os.path.getsize(path)))
    print('EXPORTED', fam, os.path.getsize(path) // 1024, 'KB')
if REBAKE:   # into the full bake already in OUT: its other families' entries stay as they were
    full = json.load(open(os.path.join(OUT, 'manifest.json'), encoding='utf-8'))
    full['objects'] = {n: e for n, e in full['objects'].items() if e['family'] not in REBAKE} | manifest['objects']
    full['files'] = sorted([f for f in full['files'] if f['family'] not in REBAKE] + manifest['files'], key=lambda f: f['family'])
    full['materials'] = manifest['materials']
    full['rebaked'] = sorted(set(full.get('rebaked', [])) | set(REBAKE))
    manifest = full
with open(os.path.join(OUT, 'manifest.json'), 'w', encoding='utf-8') as fh:
    json.dump(manifest, fh, ensure_ascii=False, indent=1)
print('WEB_BAKE_DONE')
