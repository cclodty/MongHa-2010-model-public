"""Near-final preview stills of the exported scene, without baking: the web viewer's textures (same table and scales as
web/index.html config()), the same HDRI sky and sun as web_bake.py, Cycles on the GPU with denoising, rounded edges
from a bevel shader. For checking changes against photos between bakes.

Run:  blender -b export/MongHa_2010.blend -P blender/preview_render.py -- --tag=r20 [--trees] [--context] [--samples=64]
          [--res=1200x800] [--cam=export/cams/mh001.json] [name:px,py,pz:tx,ty,tz:lens ...]
Views are in site metres (x along the avenue, y up, z into the estate); --cam reads a solved photo camera (tools/camsolve_mh001.py).
Output: export/renders/preview/<tag>_<name>.png
"""
import json
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TEX = os.path.join(ROOT, 'web', 'tex')
OUT = os.path.join(ROOT, 'export', 'renders', 'preview')
ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
opt = {a.split('=', 1)[0]: (a.split('=', 1)[1] if '=' in a else True) for a in ARGS if a.startswith('--')}
VIEWS = [a for a in ARGS if not a.startswith('--')]
TAG = opt.get('--tag', 'preview')
SAMPLES = int(opt.get('--samples', 64))
RES = tuple(int(v) for v in opt.get('--res', '1200x800').split('x'))
os.makedirs(OUT, exist_ok=True)
SKY = json.load(open(os.path.join(ROOT, 'export', 'sky.json')))
scene = bpy.context.scene


def B(x, y, z):
    """site -> blender"""
    return Vector((x, -z, y))


# ---------------------------------------------------------------- render settings
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
scene.cycles.use_denoising = True
scene.cycles.max_bounces = 6
scene.cycles.diffuse_bounces = 3
scene.cycles.transparent_max_bounces = 12
scene.view_settings.view_transform = 'AgX'
scene.view_settings.look = 'AgX - Medium High Contrast' if 'AgX - Medium High Contrast' in [
    i.identifier for i in scene.view_settings.bl_rna.properties['look'].enum_items_static] else 'None'
scene.view_settings.exposure = float(opt.get('--exposure', -0.6))
scene.render.resolution_x, scene.render.resolution_y = RES
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'

# ---------------------------------------------------------------- light: the web bake's HDRI sky (sun removed) + sun lamp
for ob in list(bpy.data.objects):
    if ob.type in ('LIGHT', 'CAMERA'):
        bpy.data.objects.remove(ob)
ld = bpy.data.lights.new('Sun', 'SUN')
ld.energy = SKY['sun_strength']
ld.color = SKY['sun_color']
ld.angle = math.radians(0.53)
sun = bpy.data.objects.new('Sun', ld)
scene.collection.objects.link(sun)
sun.rotation_euler = Vector(SKY['sun_dir_blender']).normalized().to_track_quat('Z', 'Y').to_euler()
world = bpy.data.worlds.new('Sky')
scene.world = world
world.use_nodes = True
wn = world.node_tree
wn.nodes.clear()
env = wn.nodes.new('ShaderNodeTexEnvironment')
env.image = bpy.data.images.load(os.path.join(ROOT, 'textures', 'sky_bake.exr'))
bg = wn.nodes.new('ShaderNodeBackground')
wout = wn.nodes.new('ShaderNodeOutputWorld')
wn.links.new(env.outputs['Color'], bg.inputs['Color'])
wn.links.new(bg.outputs[0], wout.inputs[0])

# ---------------------------------------------------------------- scene content
for ob in bpy.data.objects:
    if ob.name.startswith('SM_Context') and not opt.get('--context'):
        ob.hide_render = True
    if ob.name.startswith('_') or ob.name.startswith('MK_'):
        ob.hide_render = True
if opt.get('--trees'):
    sys.path.insert(0, HERE)
    import web_trees  # noqa: E402
    tc = bpy.data.collections.new('Trees')
    scene.collection.children.link(tc)
    web_trees.build(json.load(open(os.path.join(ROOT, 'export', 'markers.json'), encoding='utf-8')), tc)

# ---------------------------------------------------------------- materials: port of web/index.html config()
PHOTO = lambda name, rep, **kw: {**dict(map=name, normal=name + '_n', rough=1.0, roughMap=name + '_r', rep=rep, gain=2.0), **kw}
GRIME = lambda scale: dict(detail='grime', detailScale=scale)


def config(name):
    import re
    if re.match(r'^M_(Plaster|SlabEdge)_(Yellow|Green|Brick|Red)$', name) or name in ('M_Tile_White', 'M_Lib_YellowTile'):
        return dict(map='mosaic2', normal='mosaic2_n', rep=2, gain=1.35, rough=0.42, **GRIME(1 / 6))
    if name.startswith('M_Mosaic_'):
        return dict(map='mosaic2', normal='mosaic2_n', rep=2, gain=1.3, rough=0.42, **GRIME(1 / 5))
    if name in ('M_Plaster_White', 'M_Lib_Cream', 'M_Hall_White', 'M_Plaster_Ground', 'M_Plaster_Arcade', 'M_Concrete_Soffit'):
        return PHOTO('plaster', 0.5, gain=2.0)
    if name == 'M_Tile_Deck':
        return dict(map='paving', normal='paving_n', rep=2.5, gain=2.4, rough=0.7, **GRIME(0.2))
    if name == 'M_Paving_Courtyard':
        return dict(map='courtpave', normal='courtpave_n', rep=0.25, rot=math.pi / 4, white=True, gainC=1.0, rough=0.8, **GRIME(1.2))
    if name == 'M_Paving_Sidewalk':
        return dict(map='paving', normal='cfloor_n', rep=1.25, gain=2.4, rough=0.85, detail='cfloor', detailScale=0.4)
    if name in ('M_Roof_Screed', 'M_Concrete_Curb', 'M_Ground_Dirt', 'M_Concrete_Bench', 'M_Court_Surface', 'M_Hall_Grey', 'M_Context_Roof'):
        return PHOTO('cfloor', 0.5)
    if name == 'M_Asphalt':
        return PHOTO('asphalt', 0.25, white=True, gainC=0.36)
    if name == 'M_RoofTile_Terracotta':
        return PHOTO('roof', 0.7, white=True, gainC=0.9)
    if name.startswith('M_Shop_Shutter'):
        return PHOTO('shutter', 0.6)
    if name == 'M_BreezeBlock':
        return dict(map='breeze', alpha='breeze_a', rep=1 / 0.6, gain=1.3, rough=0.9)
    if name == 'M_ChainLink':
        return dict(alpha='chain_a', rep=10, rough=0.5)
    if name == 'M_Cloth_Atlas':
        return dict(map='cloth', alpha='cloth_a', rep=1, white=True, rough=0.95)
    if name == 'M_Sign_Atlas':
        return dict(map='signs', rep=1, white=True, rough=0.5)
    if name == 'M_PostOffice_Sign':
        return dict(map='post', rep=1, white=True, rough=0.5)
    if name == 'M_Billboard':
        return dict(map='billboard', rep=1, white=True, rough=0.6)
    if name == 'M_Sign_Desporto':
        return dict(map='desporto', alpha='desporto_a', rep=1, white=True, rough=0.5)
    if name in ('M_Context_Concrete', 'M_Context_Facade_B', 'M_Context_Facade_C'):
        return dict(map='facade', rep=1 / 12, gain=1.15, rough=0.8)
    if name == 'M_Hall_Stone':
        return dict(map='granite', rep=1 / 2.4, gain=1.7, rough=0.6)
    return {}


GLASS = {'M_Glass_Residential': ('win', 0.75), 'M_Shop_Glass': ('shop', 1.1)}
IMG = {}


def img(name, color):
    key = (name, color)
    if key not in IMG:
        im = bpy.data.images.load(os.path.join(TEX, name + '.jpg'), check_existing=False)
        im.colorspace_settings.name = 'sRGB' if color else 'Non-Color'
        IMG[key] = im
    return IMG[key]


def tex_node(nt, name, color, rep, rot=0.0, uv=None):
    t = nt.nodes.new('ShaderNodeTexImage')
    t.image = img(name, color)
    t.interpolation = 'Linear'
    mp = nt.nodes.new('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = (rep, rep, 1.0)
    mp.inputs['Rotation'].default_value = (0.0, 0.0, rot)
    nt.links.new((uv or uvnode(nt)).outputs['UV'], mp.inputs['Vector'])
    nt.links.new(mp.outputs['Vector'], t.inputs['Vector'])
    return t


def uvnode(nt):
    n = nt.nodes.get('PV_UV')
    if n is None:
        n = nt.nodes.new('ShaderNodeUVMap')
        n.name = 'PV_UV'
        n.uv_map = 'UVMap'
    return n


def rgb_mul(nt, a, b):
    m = nt.nodes.new('ShaderNodeMix')
    m.data_type = 'RGBA'
    m.blend_type = 'MULTIPLY'
    m.inputs['Factor'].default_value = 1.0
    nt.links.new(a, m.inputs[6])
    if isinstance(b, (tuple, list)):
        m.inputs[7].default_value = (*b[:3], 1.0)
    else:
        nt.links.new(b, m.inputs[7])
    return m.outputs[2]


def setup(m):
    if not m.use_nodes or m.name in ('M_Leaves', 'M_Bark') or m.name.startswith('Sky'):
        return
    nt = m.node_tree
    p = nt.nodes.get('Principled BSDF')
    if p is None:
        return
    base = tuple(p.inputs['Base Color'].default_value)[:3]
    rough = p.inputs['Roughness'].default_value
    metal = p.inputs['Metallic'].default_value
    out = nt.nodes.get('Material Output')
    for n in list(nt.nodes):
        if n not in (p, out):
            nt.nodes.remove(n)
    bev = nt.nodes.new('ShaderNodeBevel')
    bev.inputs['Radius'].default_value = 0.018
    bev.samples = 4
    nt.links.new(bev.outputs['Normal'], p.inputs['Normal'])
    name = m.name
    if name in GLASS or name in ('M_Glass_Library', 'M_Context_Glass', 'M_Lamp_Globe', 'M_TrafficLight_Green'):
        p.inputs['Base Color'].default_value = (0.01, 0.012, 0.013, 1)
        p.inputs['Roughness'].default_value = 0.05
        p.inputs['Metallic'].default_value = 0.0
        if name in GLASS:
            t = nt.nodes.new('ShaderNodeTexImage')
            t.image = img(GLASS[name][0], True)
            nt.links.new(uvnode(nt).outputs['UV'], t.inputs['Vector'])
            nt.links.new(t.outputs['Color'], p.inputs['Emission Color'])
            p.inputs['Emission Strength'].default_value = GLASS[name][1]
        elif name == 'M_Glass_Library':
            p.inputs['Base Color'].default_value = (0.32, 0.38, 0.36, 1)
            p.inputs['Roughness'].default_value = 0.32
            p.inputs['Emission Color'].default_value = (0.75, 0.79, 0.76, 1)
            p.inputs['Emission Strength'].default_value = 0.32
        elif name == 'M_Lamp_Globe':
            p.inputs['Emission Color'].default_value = (1.1, 1.05, 0.95, 1)
            p.inputs['Emission Strength'].default_value = 1.0
        elif name == 'M_TrafficLight_Green':
            p.inputs['Emission Color'].default_value = (0.2, 2.6, 1.2, 1)
            p.inputs['Emission Strength'].default_value = 1.0
        return
    c = config(name)
    col = tuple([c.get('gainC', 1.0)] * 3) if c.get('white') else tuple(v * c.get('gain', 1.0) for v in base)
    p.inputs['Roughness'].default_value = c.get('rough', rough)
    p.inputs['Metallic'].default_value = min(metal, 0.6)
    rep, rot = c.get('rep', 1.0), c.get('rot', 0.0)
    colour = None
    if c.get('map'):
        t = tex_node(nt, c['map'], True, rep, rot)
        colour = rgb_mul(nt, t.outputs['Color'], col)
        if c.get('detail'):
            d = tex_node(nt, c['detail'], False, rep * c['detailScale'], rot)
            twice = nt.nodes.new('ShaderNodeVectorMath')
            twice.operation = 'SCALE'
            twice.inputs['Scale'].default_value = 2.0
            nt.links.new(d.outputs['Color'], twice.inputs[0])
            colour = rgb_mul(nt, colour, twice.outputs['Vector'])
        nt.links.new(colour, p.inputs['Base Color'])
    else:
        p.inputs['Base Color'].default_value = (*col, 1.0)
    if c.get('normal'):
        nm = nt.nodes.new('ShaderNodeNormalMap')
        nm.inputs['Strength'].default_value = 0.8
        nt.links.new(tex_node(nt, c['normal'], False, rep, rot).outputs['Color'], nm.inputs['Color'])
        nt.links.new(nm.outputs['Normal'], bev.inputs['Normal'])
    if c.get('roughMap'):
        nt.links.new(tex_node(nt, c['roughMap'], False, rep, rot).outputs['Color'], p.inputs['Roughness'])
    if c.get('alpha'):
        a = tex_node(nt, c['alpha'], False, rep)
        gt = nt.nodes.new('ShaderNodeMath')
        gt.operation = 'GREATER_THAN'
        gt.inputs[1].default_value = 0.5
        nt.links.new(a.outputs['Color'], gt.inputs[0])
        nt.links.new(gt.outputs[0], p.inputs['Alpha'])


for m in bpy.data.materials:
    setup(m)


# ---------------------------------------------------------------- cameras and render
def shoot(name, cam_obj):
    scene.camera = cam_obj
    scene.render.filepath = os.path.join(OUT, f'{TAG}_{name}.png')
    bpy.ops.render.render(write_still=True)
    print('PREVIEW', scene.render.filepath)


if opt.get('--cam'):
    cj = json.load(open(opt['--cam'], encoding='utf-8'))
    scene.render.resolution_x, scene.render.resolution_y = cj['w'], cj['h']
    cd = bpy.data.cameras.new('cam_' + cj['name'])
    cd.sensor_fit = 'HORIZONTAL'
    cd.sensor_width = 36.0
    cd.lens = cj['f_px'] * 36.0 / cj['w']
    cd.clip_end = 3000
    cd.shift_x = -(cj.get('cx', cj['w'] / 2) - cj['w'] / 2) / cj['w']
    cd.shift_y = (cj.get('cy', cj['h'] / 2) - cj['h'] / 2) / cj['w']
    co = bpy.data.objects.new('cam_' + cj['name'], cd)
    scene.collection.objects.link(co)
    fwd, right, up = (B(*v) for v in (cj['fwd'], cj['right'], cj['up']))
    rotm = Matrix((right, up, -fwd)).transposed()
    co.matrix_world = Matrix.Translation(B(*cj['pos'])) @ rotm.to_4x4()
    shoot(cj['name'], co)
for v in VIEWS:
    name, p, t, lens = v.split(':')
    p = [float(x) for x in p.split(',')]
    t = [float(x) for x in t.split(',')]
    cd = bpy.data.cameras.new('cam_' + name)
    cd.lens = float(lens)
    cd.clip_end = 3000
    co = bpy.data.objects.new('cam_' + name, cd)
    scene.collection.objects.link(co)
    co.location = B(*p)
    co.rotation_euler = (B(*t) - B(*p)).to_track_quat('-Z', 'Y').to_euler()
    shoot(name, co)
