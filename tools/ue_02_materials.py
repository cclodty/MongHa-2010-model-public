# Runs inside Unreal Editor: master materials + one instance per Blender material slot, assigned by slot name.
import unreal

at = unreal.AssetToolsHelpers.get_asset_tools()
mel = unreal.MaterialEditingLibrary
eal = unreal.EditorAssetLibrary
MAT_DIR = '/Game/MongHa/Materials'
TEX = '/Game/MongHa/Textures/'


def lin(hexcol, a=1.0):
    h = hexcol.lstrip('#')
    v = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    v = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in v]
    return unreal.LinearColor(v[0], v[1], v[2], a)


def tex(name):
    path = name[1:] if name.startswith('@') else TEX + name   # '@' = full asset path (Fab content)
    return unreal.load_asset(path) if eal.does_asset_exist(path) else None


def fresh(name, cls, factory):
    """Reuse an existing asset (cleared) instead of deleting it: deleting referenced materials pops a
    modal dialog, which crashed the editor when the desktop could not create the window."""
    path = f'{MAT_DIR}/{name}'
    if eal.does_asset_exist(path):
        a = unreal.load_asset(path)
        if isinstance(a, unreal.Material):
            mel.delete_all_material_expressions(a)
        elif isinstance(a, unreal.MaterialInstanceConstant):
            mel.clear_all_material_instance_parameters(a)
        return a
    return at.create_asset(name, MAT_DIR, cls, factory)


def build_master(name, masked):
    m = fresh(name, unreal.Material, unreal.MaterialFactoryNew())
    E = lambda cls, x, y: mel.create_material_expression(m, cls, x, y)  # noqa: E731
    white = unreal.load_asset('/Engine/EngineResources/WhiteSquareTexture')
    flat = unreal.load_asset('/Engine/EngineMaterials/FlatNormal')
    tc = E(unreal.MaterialExpressionTextureCoordinate, -1600, 0)
    uvs = E(unreal.MaterialExpressionScalarParameter, -1600, 120)
    uvs.set_editor_property('parameter_name', 'UVScale')
    uvs.set_editor_property('default_value', 1.0)
    uv0 = E(unreal.MaterialExpressionMultiply, -1800, 40)
    mel.connect_material_expressions(tc, '', uv0, 'A')
    mel.connect_material_expressions(uvs, '', uv0, 'B')
    # optional rotation of the base layers (UVAngle in turns; the courtyard paving is laid at 45 deg, photo 14)
    ang = E(unreal.MaterialExpressionScalarParameter, -2000, 200)
    ang.set_editor_property('parameter_name', 'UVAngle')
    ang.set_editor_property('default_value', 0.0)
    cos_ = E(unreal.MaterialExpressionCosine, -1850, 180)
    cos_.set_editor_property('period', 1.0)
    sin_ = E(unreal.MaterialExpressionSine, -1850, 260)
    sin_.set_editor_property('period', 1.0)
    mel.connect_material_expressions(ang, '', cos_, '')
    mel.connect_material_expressions(ang, '', sin_, '')
    cu = E(unreal.MaterialExpressionComponentMask, -1700, 100)
    cv = E(unreal.MaterialExpressionComponentMask, -1700, 160)
    for m_, (r_, g_) in ((cu, (True, False)), (cv, (False, True))):
        m_.set_editor_property('r', r_)
        m_.set_editor_property('g', g_)
        m_.set_editor_property('b', False)
        m_.set_editor_property('a', False)
        mel.connect_material_expressions(uv0, '', m_, '')
    uc, vs_, us, vc = (E(unreal.MaterialExpressionMultiply, -1600, 60 + 50 * i) for i in range(4))
    for node, a_, b_ in ((uc, cu, cos_), (vs_, cv, sin_), (us, cu, sin_), (vc, cv, cos_)):
        mel.connect_material_expressions(a_, '', node, 'A')
        mel.connect_material_expressions(b_, '', node, 'B')
    ru = E(unreal.MaterialExpressionSubtract, -1500, 80)   # u' = u cos - v sin
    mel.connect_material_expressions(uc, '', ru, 'A')
    mel.connect_material_expressions(vs_, '', ru, 'B')
    rv = E(unreal.MaterialExpressionAdd, -1500, 160)       # v' = u sin + v cos
    mel.connect_material_expressions(us, '', rv, 'A')
    mel.connect_material_expressions(vc, '', rv, 'B')
    uv = E(unreal.MaterialExpressionAppendVector, -1400, 40)
    mel.connect_material_expressions(ru, '', uv, 'A')
    mel.connect_material_expressions(rv, '', uv, 'B')

    def tparam(pname, default, x, y, normal=False):
        t = E(unreal.MaterialExpressionTextureSampleParameter2D, x, y)
        t.set_editor_property('parameter_name', pname)
        t.set_editor_property('texture', default)
        if normal:
            t.set_editor_property('sampler_type', unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
        mel.connect_material_expressions(uv, '', t, 'UVs')
        return t

    def sparam(pname, val, x, y):
        s = E(unreal.MaterialExpressionScalarParameter, x, y)
        s.set_editor_property('parameter_name', pname)
        s.set_editor_property('default_value', val)
        return s

    def vparam(pname, col, x, y):
        v = E(unreal.MaterialExpressionVectorParameter, x, y)
        v.set_editor_property('parameter_name', pname)
        v.set_editor_property('default_value', col)
        return v

    base = tparam('BaseTex', white, -1100, -300)
    # scanned albedo -> neutral detail (desaturate, normalise to ~1) so the photographed plaster colour comes from Tint
    ds = E(unreal.MaterialExpressionDesaturation, -950, -420)
    mel.connect_material_expressions(base, 'RGB', ds, '')
    mel.connect_material_expressions(sparam('BaseDesat', 0.0, -1100, -480), '', ds, 'Fraction')
    gain = E(unreal.MaterialExpressionMultiply, -850, -350)
    mel.connect_material_expressions(ds, '', gain, 'A')
    mel.connect_material_expressions(sparam('BaseGain', 1.0, -1000, -560), '', gain, 'B')
    tint = vparam('Tint', unreal.LinearColor(1, 1, 1, 1), -1100, -80)
    bt = E(unreal.MaterialExpressionMultiply, -800, -250)
    mel.connect_material_expressions(gain, '', bt, 'A')
    mel.connect_material_expressions(tint, '', bt, 'B')
    # weathering streaks / mould, sampled at its own (larger) scale
    gs = sparam('GrimeScale', 0.25, -1600, 420)
    guv = E(unreal.MaterialExpressionMultiply, -1400, 380)
    mel.connect_material_expressions(tc, '', guv, 'A')
    mel.connect_material_expressions(gs, '', guv, 'B')
    gt = E(unreal.MaterialExpressionTextureSampleParameter2D, -1100, 340)
    gt.set_editor_property('parameter_name', 'GrimeTex')
    gt.set_editor_property('texture', tex('T_Grime_Mask') or white)
    mel.connect_material_expressions(guv, '', gt, 'UVs')
    ga = sparam('GrimeAmount', 0.0, -1100, 560)
    gmul = E(unreal.MaterialExpressionMultiply, -800, 400)
    mel.connect_material_expressions(gt, 'R', gmul, 'A')
    mel.connect_material_expressions(ga, '', gmul, 'B')
    gc = vparam('GrimeColor', unreal.LinearColor(0.42, 0.39, 0.34, 1), -1100, 180)
    dirty = E(unreal.MaterialExpressionMultiply, -800, 100)
    mel.connect_material_expressions(bt, '', dirty, 'A')
    mel.connect_material_expressions(gc, '', dirty, 'B')
    lerp = E(unreal.MaterialExpressionLinearInterpolate, -500, -100)
    mel.connect_material_expressions(bt, '', lerp, 'A')
    mel.connect_material_expressions(dirty, '', lerp, 'B')
    mel.connect_material_expressions(gmul, '', lerp, 'Alpha')
    # rain streaks under each floor band (4 m x 8 m tile; UVs are world metres, V down the wall) on vertical faces only
    sst = E(unreal.MaterialExpressionConstant2Vector, -1600, 1500)
    sst.set_editor_property('r', 0.25)
    sst.set_editor_property('g', 0.125)
    suv = E(unreal.MaterialExpressionMultiply, -1400, 1450)
    mel.connect_material_expressions(tc, '', suv, 'A')
    mel.connect_material_expressions(sst, '', suv, 'B')
    st = E(unreal.MaterialExpressionTextureSampleParameter2D, -1200, 1450)
    st.set_editor_property('parameter_name', 'StreakTex')
    st.set_editor_property('texture', tex('T_Streaks') or white)
    mel.connect_material_expressions(suv, '', st, 'UVs')
    vn = E(unreal.MaterialExpressionVertexNormalWS, -1400, 1650)
    vz = E(unreal.MaterialExpressionComponentMask, -1250, 1650)
    for c, on in (('r', False), ('g', False), ('b', True), ('a', False)):
        vz.set_editor_property(c, on)
    mel.connect_material_expressions(vn, '', vz, '')
    vabs = E(unreal.MaterialExpressionAbs, -1100, 1650)
    mel.connect_material_expressions(vz, '', vabs, '')
    vert = E(unreal.MaterialExpressionOneMinus, -1000, 1650)
    mel.connect_material_expressions(vabs, '', vert, '')
    samt = E(unreal.MaterialExpressionMultiply, -900, 1600)
    mel.connect_material_expressions(vert, '', samt, 'A')
    mel.connect_material_expressions(sparam('StreakAmount', 0.0, -1100, 1780), '', samt, 'B')
    one_c = E(unreal.MaterialExpressionConstant, -1000, 1400)
    one_c.set_editor_property('r', 1.0)
    sfac = E(unreal.MaterialExpressionLinearInterpolate, -750, 1450)
    mel.connect_material_expressions(one_c, '', sfac, 'A')
    mel.connect_material_expressions(st, 'R', sfac, 'B')
    mel.connect_material_expressions(samt, '', sfac, 'Alpha')
    # contact grime: distance field probed ContactRadius out along the normal; nearby geometry (corners, under ledges) darkens
    wp = E(unreal.MaterialExpressionWorldPosition, -1600, 1950)
    crad = sparam('ContactRadius', 40.0, -1600, 2100)
    noff = E(unreal.MaterialExpressionMultiply, -1400, 2050)
    mel.connect_material_expressions(vn, '', noff, 'A')
    mel.connect_material_expressions(crad, '', noff, 'B')
    probe = E(unreal.MaterialExpressionAdd, -1250, 1980)
    mel.connect_material_expressions(wp, '', probe, 'A')
    mel.connect_material_expressions(noff, '', probe, 'B')
    dts = E(unreal.MaterialExpressionDistanceToNearestSurface, -1100, 1980)
    mel.connect_material_expressions(probe, '', dts, 'Position')
    dn = E(unreal.MaterialExpressionDivide, -950, 2000)
    mel.connect_material_expressions(dts, '', dn, 'A')
    mel.connect_material_expressions(crad, '', dn, 'B')
    dsat = E(unreal.MaterialExpressionSaturate, -820, 2000)
    mel.connect_material_expressions(dn, '', dsat, '')
    cmask = E(unreal.MaterialExpressionOneMinus, -700, 2000)
    mel.connect_material_expressions(dsat, '', cmask, '')
    camt0 = E(unreal.MaterialExpressionMultiply, -580, 2000)
    mel.connect_material_expressions(cmask, '', camt0, 'A')
    mel.connect_material_expressions(sparam('ContactAmount', 0.0, -700, 2150), '', camt0, 'B')
    # the global distance field coarsens away from the camera (everything far reads as a corner): fade out 15 -> 40 m
    pd = E(unreal.MaterialExpressionPixelDepth, -820, 2250)
    fsub = E(unreal.MaterialExpressionSubtract, -700, 2250)
    fsub.set_editor_property('const_a', 4000.0)
    mel.connect_material_expressions(pd, '', fsub, 'B')
    fdiv = E(unreal.MaterialExpressionDivide, -580, 2250)
    fdiv.set_editor_property('const_b', 2500.0)
    mel.connect_material_expressions(fsub, '', fdiv, 'A')
    fsat = E(unreal.MaterialExpressionSaturate, -470, 2250)
    mel.connect_material_expressions(fdiv, '', fsat, '')
    camt = E(unreal.MaterialExpressionMultiply, -460, 2100)
    mel.connect_material_expressions(camt0, '', camt, 'A')
    mel.connect_material_expressions(fsat, '', camt, 'B')
    cfac = E(unreal.MaterialExpressionOneMinus, -360, 2000)
    mel.connect_material_expressions(camt, '', cfac, '')
    # macro variation: a very large grime sample (~30 m) lifts / lowers the albedo so tiling never lines up
    muv = E(unreal.MaterialExpressionMultiply, -1400, 2350)
    mel.connect_material_expressions(tc, '', muv, 'A')
    mel.connect_material_expressions(sparam('MacroScale', 0.033, -1600, 2400), '', muv, 'B')
    mt_ = E(unreal.MaterialExpressionTextureSample, -1200, 2350)
    mt_.set_editor_property('texture', tex('T_Grime_Mask') or white)
    mel.connect_material_expressions(muv, '', mt_, 'UVs')
    mc = E(unreal.MaterialExpressionSubtract, -1000, 2350)
    mc.set_editor_property('const_b', 0.5)
    mel.connect_material_expressions(mt_, 'R', mc, 'A')
    mm = E(unreal.MaterialExpressionMultiply, -880, 2350)
    mel.connect_material_expressions(mc, '', mm, 'A')
    mel.connect_material_expressions(sparam('MacroAmount', 0.0, -1000, 2500), '', mm, 'B')
    mfac = E(unreal.MaterialExpressionAdd, -760, 2350)
    mfac.set_editor_property('const_a', 1.0)
    mel.connect_material_expressions(mm, '', mfac, 'B')
    f1 = E(unreal.MaterialExpressionMultiply, -350, -100)
    mel.connect_material_expressions(lerp, '', f1, 'A')
    mel.connect_material_expressions(sfac, '', f1, 'B')
    f2 = E(unreal.MaterialExpressionMultiply, -250, -60)
    mel.connect_material_expressions(f1, '', f2, 'A')
    mel.connect_material_expressions(cfac, '', f2, 'B')
    f3 = E(unreal.MaterialExpressionMultiply, -150, -20)
    mel.connect_material_expressions(f2, '', f3, 'A')
    mel.connect_material_expressions(mfac, '', f3, 'B')
    mel.connect_material_property(f3, '', unreal.MaterialProperty.MP_BASE_COLOR)
    nrm = tparam('NormalTex', flat, -500, 200, normal=True)
    mel.connect_material_property(nrm, 'RGB', unreal.MaterialProperty.MP_NORMAL)
    rt = tparam('RoughTex', white, -800, 650)
    rs = sparam('Roughness', 0.8, -800, 860)
    rsel = E(unreal.MaterialExpressionLinearInterpolate, -650, 650)   # Megascans ORM keeps roughness in G
    mel.connect_material_expressions(rt, 'R', rsel, 'A')
    mel.connect_material_expressions(rt, 'G', rsel, 'B')
    mel.connect_material_expressions(sparam('RoughFromG', 0.0, -800, 760), '', rsel, 'Alpha')
    rm = E(unreal.MaterialExpressionMultiply, -500, 700)
    mel.connect_material_expressions(rsel, '', rm, 'A')
    mel.connect_material_expressions(rs, '', rm, 'B')
    # wetter / dirtier patches are a little rougher
    mel.connect_material_property(rm, '', unreal.MaterialProperty.MP_ROUGHNESS)
    mel.connect_material_property(sparam('Metallic', 0.0, -500, 900), '', unreal.MaterialProperty.MP_METALLIC)
    mel.connect_material_property(sparam('Specular', 0.5, -500, 1000), '', unreal.MaterialProperty.MP_SPECULAR)
    mel.connect_material_property(vparam('Emissive', unreal.LinearColor(0, 0, 0, 1), -500, 1100), '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    if masked:
        mt = tparam('MaskTex', white, -500, 1250)
        mel.connect_material_property(mt, 'R', unreal.MaterialProperty.MP_OPACITY_MASK)
        m.set_editor_property('blend_mode', unreal.BlendMode.BLEND_MASKED)
        m.set_editor_property('two_sided', True)
    mel.recompile_material(m)
    eal.save_loaded_asset(m)
    return m


def build_glass(name):
    """Window glass: dark specular pane + the room behind it as emissive (daylight-lit interior, in nits),
    fading out at grazing angles where the pane mostly reflects."""
    m = fresh(name, unreal.Material, unreal.MaterialFactoryNew())
    E = lambda cls, x, y: mel.create_material_expression(m, cls, x, y)  # noqa: E731
    # flat-plane parallax: the room image sits Depth (in UV units) behind the pane, clamped to its atlas cell
    tc = E(unreal.MaterialExpressionTextureCoordinate, -2000, 200)
    cells = E(unreal.MaterialExpressionScalarParameter, -2000, 350)
    cells.set_editor_property('parameter_name', 'Cells')
    cells.set_editor_property('default_value', 8.0)
    dp = E(unreal.MaterialExpressionScalarParameter, -2000, 450)
    dp.set_editor_property('parameter_name', 'Depth')
    dp.set_editor_property('default_value', 0.06)
    zero = E(unreal.MaterialExpressionConstant, -2000, 550)
    bo = E(unreal.MaterialExpressionBumpOffset, -1750, 200)
    mel.connect_material_expressions(tc, '', bo, 'Coordinate')
    mel.connect_material_expressions(zero, '', bo, 'Height')
    mel.connect_material_expressions(dp, '', bo, 'HeightRatioInput')
    scaled = E(unreal.MaterialExpressionMultiply, -1750, 350)
    mel.connect_material_expressions(tc, '', scaled, 'A')
    mel.connect_material_expressions(cells, '', scaled, 'B')
    fl = E(unreal.MaterialExpressionFloor, -1600, 350)
    mel.connect_material_expressions(scaled, '', fl, '')
    cmin = E(unreal.MaterialExpressionDivide, -1450, 350)
    mel.connect_material_expressions(fl, '', cmin, 'A')
    mel.connect_material_expressions(cells, '', cmin, 'B')
    one = E(unreal.MaterialExpressionConstant, -1600, 480)
    one.set_editor_property('r', 1.0)
    fl1 = E(unreal.MaterialExpressionAdd, -1450, 470)
    mel.connect_material_expressions(fl, '', fl1, 'A')
    mel.connect_material_expressions(one, '', fl1, 'B')
    cmax = E(unreal.MaterialExpressionDivide, -1300, 470)
    mel.connect_material_expressions(fl1, '', cmax, 'A')
    mel.connect_material_expressions(cells, '', cmax, 'B')
    lo = E(unreal.MaterialExpressionAdd, -1150, 350)
    lo.set_editor_property('const_b', 0.002)
    mel.connect_material_expressions(cmin, '', lo, 'A')
    hi = E(unreal.MaterialExpressionSubtract, -1150, 470)
    hi.set_editor_property('const_b', 0.002)
    mel.connect_material_expressions(cmax, '', hi, 'A')
    cl = E(unreal.MaterialExpressionClamp, -1050, 200)
    mel.connect_material_expressions(bo, '', cl, '')
    mel.connect_material_expressions(lo, '', cl, 'Min')
    mel.connect_material_expressions(hi, '', cl, 'Max')
    t = E(unreal.MaterialExpressionTextureSampleParameter2D, -900, 200)
    mel.connect_material_expressions(cl, '', t, 'UVs')
    t.set_editor_property('parameter_name', 'InteriorTex')
    t.set_editor_property('texture', tex('T_WindowAtlas_BC') or unreal.load_asset('/Engine/EngineResources/WhiteSquareTexture'))
    nits = E(unreal.MaterialExpressionScalarParameter, -900, 420)
    nits.set_editor_property('parameter_name', 'InteriorNits')
    nits.set_editor_property('default_value', 1800.0)
    fr = E(unreal.MaterialExpressionFresnel, -900, 540)
    fr.set_editor_property('exponent', 5.0)
    fr.set_editor_property('base_reflect_fraction', 0.04)
    inv = E(unreal.MaterialExpressionOneMinus, -700, 540)
    mel.connect_material_expressions(fr, '', inv, '')
    a = E(unreal.MaterialExpressionMultiply, -600, 250)
    mel.connect_material_expressions(t, 'RGB', a, 'A')
    mel.connect_material_expressions(nits, '', a, 'B')
    b = E(unreal.MaterialExpressionMultiply, -400, 300)
    mel.connect_material_expressions(a, '', b, 'A')
    mel.connect_material_expressions(inv, '', b, 'B')
    mel.connect_material_property(b, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    for pname, val, prop, y in (('Roughness', 0.03, unreal.MaterialProperty.MP_ROUGHNESS, -100),
                                ('Specular', 0.7, unreal.MaterialProperty.MP_SPECULAR, 0)):
        sp = E(unreal.MaterialExpressionScalarParameter, -400, y)
        sp.set_editor_property('parameter_name', pname)
        sp.set_editor_property('default_value', val)
        mel.connect_material_property(sp, '', prop)
    tint = E(unreal.MaterialExpressionVectorParameter, -400, -250)
    tint.set_editor_property('parameter_name', 'Tint')
    tint.set_editor_property('default_value', unreal.LinearColor(0.004, 0.005, 0.006, 1))
    mel.connect_material_property(tint, '', unreal.MaterialProperty.MP_BASE_COLOR)
    mel.recompile_material(m)
    eal.save_loaded_asset(m)
    return m


# The bridge runs a whole request inside one editor tick, and every saved asset renders a Lumen thumbnail whose GPU memory
# is only released when a frame ends. One long run grew the editor past the commit limit (92 GB, crash 2026-10-20), so the
# work is split: PART = 'masters' | 'inst:<from>:<to>' | 'assign' (tools/ue_materials.py drives the batches).
PART = globals().get('PART', 'all')
if PART in ('all', 'masters'):
    OPAQUE = build_master('M_MH_Opaque', False)
    MASKED = build_master('M_MH_Masked', True)
    GLASS = build_glass('M_MH_Glass')
else:
    OPAQUE, MASKED, GLASS = (unreal.load_asset(f'{MAT_DIR}/{n}') for n in ('M_MH_Opaque', 'M_MH_Masked', 'M_MH_Glass'))

# Fab Megascans scans (2 m tiles) used as neutral detail under our tints; falls back to the procedural maps if absent
FAB = '/Game/Fab/Megascans/Surfaces/'


def scan(folder, code, gain, desat=1.0, uv=0.5):
    d = f'{FAB}{folder}_{code}/Medium/{code}_tier_2/Textures/'
    if not eal.does_directory_exist(f'{FAB}{folder}_{code}'):
        return {}
    return dict(BaseTex=f'@{d}T_{code}_2K_B', NormalTex=f'@{d}T_{code}_2K_N', RoughTex=f'@{d}T_{code}_2K_ORM',
                RoughFromG=1.0, BaseGain=gain, BaseDesat=desat, UVScale=uv)


STUCCO = scan('Stucco_Facade', 'wfnhfaq', 1.75)
PAINTED = scan('Painted_Concrete_Wall', 'ugkkedvlw', 2.0)
WEATHERED = scan('Weathered_Concrete_Wall', 'vi4idbm', 2.6, desat=0.8)
FLOOR = scan('Dirty_Concrete_Floor', 'ue4idgdlw', 1.85)
ROAD = scan('Road_Asphalt', 'rh0ribp0', 1.7, desat=0.4, uv=0.25)

# plaster colours as photographed (weathered); same hexes as the web model
PL = dict(Yellow='#c8a868', Green='#859a82', Brick='#9b5e4a', Red='#b06c58')
PLASTER = {**dict(NormalTex='T_Stucco_N', UVScale=1.0, Roughness=0.92, GrimeAmount=0.75, GrimeScale=0.22), **STUCCO}
SLAB = {**PLASTER, **PAINTED}


def FACADE(tint):
    """Generic 1990s-2000s high-rise: 12 m x 12 m tile of windows, cages and AC boxes (make_cloth_facade.py)."""
    return dict(BaseTex='T_Facade_BC', RoughTex='T_Facade_R', UVScale=1.0 / 12, Tint=tint, Roughness=1.0, GrimeAmount=0.5, GrimeScale=0.02)



CONCRETE = {**PLASTER, **WEATHERED}
# the coloured walls, stair towers and posts are glazed 2.5 cm wall mosaic (photos; web viewer uses the same T_Mosaic2)
MOSAIC = dict(BaseTex='T_Mosaic2_BC', NormalTex='T_Mosaic2_N', UVScale=2.0, BaseGain=1.3, Roughness=0.42, Specular=0.55,
              GrimeAmount=0.5, GrimeScale=0.17)
PH_SHUTTER = dict(BaseTex='PH/T_PH_Shutter_BC', NormalTex='PH/T_PH_Shutter_N', RoughTex='PH/T_PH_Shutter_R', UVScale=0.6,
                  BaseDesat=1.0, BaseGain=1.95, Roughness=1.0, Metallic=0.6, GrimeAmount=0.7)
SPEC = {}
for k, h in PL.items():
    SPEC[f'M_Plaster_{k}'] = dict(MOSAIC, Tint=h)
    SPEC[f'M_SlabEdge_{k}'] = dict(MOSAIC, Tint=h, GrimeAmount=0.7)
SPEC.update({
    'M_Plaster_White': dict(PLASTER, Tint='#d9d3c6'),
    'M_Plaster_Ground': dict(PLASTER, Tint='#c4b8a1', GrimeAmount=0.9),
    'M_Plaster_Arcade': dict(PLASTER, Tint='#cfc4ad'),
    'M_Concrete_Soffit': dict(SLAB, Tint='#b3ab9b'),
    'M_Roof_Screed': {**PLASTER, **FLOOR, 'Tint': '#8f8b80', 'GrimeAmount': 1.0, 'GrimeScale': 0.15},
    'M_Concrete_Curb': dict(CONCRETE, Tint='#a29d91'),
    'M_Concrete_Bench': dict(CONCRETE, Tint='#c7c1b4'),
    'M_RoofTile_Terracotta': dict(BaseTex='PH/T_PH_Roof_BC', NormalTex='PH/T_PH_Roof_N', RoughTex='PH/T_PH_Roof_R', UVScale=0.7, Tint='#ffffff', BaseGain=1.0, Roughness=1.0, GrimeAmount=0.4),
    'M_BreezeBlock': dict(BaseTex='T_Breeze_BC', NormalTex='T_Breeze_N', MaskTex='T_Breeze_Mask', UVScale=1.0 / 0.6, Tint='#d4cfc4', Roughness=0.9, GrimeAmount=0.5, masked=True),
    'M_ChainLink': dict(MaskTex='T_ChainLink_Mask', UVScale=10.0, Tint='#2a2c2b', Roughness=0.45, Metallic=0.7, masked=True),
    'M_Dark_Void': dict(Tint='#151615', Roughness=1.0),
    'M_WindowFrame': dict(Tint='#d6d1c5', Roughness=0.45, GrimeAmount=0.4),
    'M_Glass_Residential': dict(glass=True, InteriorTex='T_WindowAtlas_BC', Cells=8, Depth=0.05, InteriorNits=1500.0, Tint='#0b1012'),
    'M_Shop_Glass': dict(glass=True, InteriorTex='T_ShopAtlas_BC', Cells=4, Depth=0.12, InteriorNits=3200.0, Tint='#0b1012'),
    'M_Glass_Library': dict(Tint='#aab6b1', Roughness=0.3, Specular=0.6, GrimeAmount=0.2),   # frosted: nothing visible inside (user, round 4)
    'M_Context_Glass': dict(Tint='#2c3438', Roughness=0.06, Specular=0.8),
    'M_Metal_WindowBars': dict(Tint='#34373a', Roughness=0.5, Metallic=0.8),
    'M_Metal_Railing': dict(Tint='#cfcbc0', Roughness=0.45, Metallic=0.3, GrimeAmount=0.5),
    'M_Metal_Pipe': dict(Tint='#2f3231', Roughness=0.4, Metallic=0.9),
    'M_Metal_Gate': dict(Tint='#5f625d', Roughness=0.45, Metallic=0.85),
    'M_Steel_Black': dict(Tint='#202322', Roughness=0.5, Metallic=0.8),
    'M_AC_Unit': dict(Tint='#d9d7cf', Roughness=0.5, GrimeAmount=0.6),
    'M_Laundry_Pole': dict(Tint='#8a8578', Roughness=0.45, Metallic=0.6),
    'M_Shop_Shutter': dict(PH_SHUTTER, Tint='#8c8e89'),
    'M_Shop_Interior': dict(Tint='#1e2120', Roughness=0.9),
    'M_Mosaic_Red': dict(MOSAIC, Tint='#c4483b', GrimeAmount=0.35),
    'M_Mosaic_Yellow': dict(MOSAIC, Tint='#efdc9f', GrimeAmount=0.45),
    'M_Tile_Deck': dict(BaseTex='T_Paving_BC', NormalTex='T_Paving_N', RoughTex='T_Paving_R', UVScale=3.0, Tint='#d8d1bd', Roughness=1.0, GrimeAmount=0.4),
    'M_Tile_Dado': dict(BaseTex='T_Mosaic_BC', NormalTex='T_Mosaic_N', UVScale=1.0, Tint='#c5b28d', Roughness=0.5),
    'M_Wood_Door': dict(Tint='#4f3d2c', Roughness=0.6),
    'M_Paving_Courtyard': dict(BaseTex='T_CourtPave_BC', NormalTex='T_CourtPave_N', UVScale=0.25, UVAngle=0.125, Tint='#e2ded4', BaseGain=0.9, Roughness=0.8, GrimeAmount=0.5, GrimeScale=0.05),   # 2 m pale slabs, blue-grey bands, 45 deg
    'M_Paving_Sidewalk': dict(BaseTex='T_Paving_BC', NormalTex='T_Paving_N', RoughTex='T_Paving_R', UVScale=1.25, Tint='#d9cdb8', Roughness=1.0, GrimeAmount=0.4, GrimeScale=0.05),
    'M_Asphalt': {**dict(NormalTex='T_Stucco_N', UVScale=0.7, Tint='#4d4f4f', Roughness=0.9, GrimeAmount=0.4, GrimeScale=0.05, GrimeColor='#6a6a66'), **(dict(ROAD, Tint='#ffffff', Roughness=1.0) if ROAD else {})},
    'M_Road_Paint': dict(Tint='#e2e0d6', Roughness=0.6),
    'M_Ground_Dirt': {**dict(NormalTex='T_Stucco_N'), **FLOOR, 'Tint': '#7d796f', 'Roughness': 1.0},
    'M_Grass': dict(Tint='#556b3f', Roughness=1.0),
    'M_Lib_Cream': dict(PLASTER, Tint='#d9caa9'),
    'M_Lib_GreenMetal': dict(Tint='#2f5640', Roughness=0.38, Metallic=0.6, GrimeAmount=0.3),
    'M_Lib_GreenPlinth': dict(Tint='#2e4b40', Roughness=0.7),
    'M_Lib_Mullion': dict(Tint='#ece7dc', Roughness=0.4),
    'M_Lib_Sign': dict(Tint='#2a5541', Roughness=0.4),
    'M_Soil': dict(Tint='#3d3126', Roughness=1.0),
    'M_Foliage_Shrub': dict(Tint='#3f6a30', Roughness=0.85),
    'M_Foliage_Bougainvillea': dict(Tint='#b52a6c', Roughness=0.8),
    'M_Court_Surface': {**dict(NormalTex='T_Stucco_N', Tint='#868a80', Roughness=0.9, GrimeAmount=0.5, GrimeScale=0.08), **FLOOR},
    'M_Court_Line': dict(Tint='#ddd9cb', Roughness=0.7),
    'M_Play_Blue': dict(Tint='#2f5a91', Roughness=0.4, Metallic=0.3),
    'M_Play_Red': dict(Tint='#a83b30', Roughness=0.5),
    'M_Sand': dict(NormalTex='T_Stucco_N', UVScale=3.0, Tint='#c9b585', Roughness=1.0),
    'M_Wood_Planter': dict(Tint='#8a6a42', Roughness=0.8),
    'M_Water_Pond': dict(Tint='#16231f', Roughness=0.03, Specular=0.8),
    'M_Rock': dict(NormalTex='T_Stucco_N', UVScale=2.0, Tint='#7c796f', Roughness=0.9),
    'M_Lamp_Globe': dict(Tint='#f2ede0', Roughness=0.3, Emissive='#2a271e'),
    'M_Hall_White': dict(PLASTER, Tint='#dcd8ce'),
    'M_Hall_Grey': dict(PLASTER, Tint='#555b5d'),
    'M_Hall_Stone': dict(PLASTER, Tint='#8f908a'),
    'M_Context_Concrete': FACADE('#ffffff'),
    'M_Context_Facade_B': FACADE('#f2e0d6'),
    'M_Context_Facade_C': FACADE('#dde6ea'),
    'M_Context_Roof': {**PLASTER, **FLOOR, 'Tint': '#8e8b84', 'GrimeAmount': 1.0, 'GrimeScale': 0.1},
    'M_PostOffice_Sign': dict(BaseTex='T_PostSign_BC', UVScale=1.0, Tint='#ffffff', Roughness=0.5),
    'M_Sign_Atlas': dict(BaseTex='T_Signs_BC', UVScale=1.0, Tint='#ffffff', Roughness=0.55),
    'M_Cloth_Atlas': dict(BaseTex='T_ClothAtlas_BC', MaskTex='T_ClothAtlas_Mask', UVScale=1.0, Tint='#ffffff', Roughness=0.95, masked=True),
    'M_Metal_KerbRail': dict(Tint='#c9cbc6', Roughness=0.45, Metallic=0.5, GrimeAmount=0.4),
    'M_Metal_StreetPole': dict(Tint='#8a8f8c', Roughness=0.5, Metallic=0.7, GrimeAmount=0.3),
    'M_TrafficLight_Box': dict(Tint='#1c1d1d', Roughness=0.5),
    'M_TrafficLight_Green': dict(Tint='#10261b', Roughness=0.25, Emissive=(400.0, 3500.0, 1800.0)),
    'M_TrafficLight_Red': dict(Tint='#4a1210', Roughness=0.25),
    'M_Roof_Tank': dict(Tint='#cfd2d0', Roughness=0.35, Metallic=0.8, GrimeAmount=0.5),
    'M_PostOffice_Red': dict(Tint='#b3201f', Roughness=0.5),
    # round 4-6 slots (same hexes as build_estate.py)
    'M_Planter_Tile': dict(BaseTex='T_Mosaic_BC', NormalTex='T_Mosaic_N', RoughTex='T_Mosaic_R', UVScale=1.0, Tint='#8a4a35', Roughness=0.9, GrimeAmount=0.5),
    'M_Tile_White': dict(MOSAIC, Tint='#e4e1d8', GrimeAmount=0.55),
    'M_Tile_Maroon': dict(MOSAIC, Tint='#6a2b26', GrimeAmount=0.35),
    'M_Lib_YellowTile': dict(MOSAIC, Tint='#d6b45f', GrimeAmount=0.4),
    'M_Hall_RedTile': dict(BaseTex='T_Mosaic_BC', NormalTex='T_Mosaic_N', UVScale=2.0, Tint='#a8362c', Roughness=0.5),
    'M_Shop_Shutter_Green': dict(PH_SHUTTER, Tint='#56705f'),
    'M_Shop_Shutter_Pale': dict(PH_SHUTTER, Tint='#b8bab3'),
    'M_Frame_Green': dict(Tint='#2f8a45', Roughness=0.4, Metallic=0.3),
    'M_Awning_Green': dict(Tint='#2f6b4a', Roughness=0.8, GrimeAmount=0.5),
    'M_GlassBlock': dict(Tint='#b9cfcc', Roughness=0.2, Specular=0.6),
    'M_Metal_BalconyRail': dict(Tint='#2b3632', Roughness=0.5, Metallic=0.6, GrimeAmount=0.3),
    'M_Metal_Awning': dict(Tint='#8a8f8a', Roughness=0.5, Metallic=0.6, GrimeAmount=0.6),
    'M_Metal_CreamRail': dict(Tint='#e4ddcc', Roughness=0.45, Metallic=0.3, GrimeAmount=0.4),
    'M_Play_Rubber': dict(Tint='#2f3231', Roughness=0.95),
    'M_Play_Timber': dict(Tint='#8a6440', Roughness=0.8, GrimeAmount=0.4),
    'M_BusShelter_Metal': dict(Tint='#a3a8a6', Roughness=0.45, Metallic=0.7, GrimeAmount=0.3),
})
for k, h in dict(Red='#b8282a', Yellow='#e8c635', Green='#1d6845', White='#efebe0', Blue='#1d4a86', Orange='#d9661e').items():
    SPEC[f'M_Sign_{k}'] = dict(Tint=h, Roughness=0.4)
for i, h in enumerate(['#e8e2d6', '#c9473e', '#3f6ea8', '#e3c34d', '#f2f2ee', '#6c9a6c', '#d98cab', '#4b4b4b']):
    SPEC[f'M_Cloth_{i}'] = dict(Tint=h, Roughness=0.95)

INST = {}
names = sorted(SPEC)
if PART.startswith('inst:'):
    a, b = (int(v) for v in PART.split(':')[1:])
    todo = names[a:b]
else:
    todo = names if PART == 'all' else []
for name in names:
    if name not in todo:
        path = f'{MAT_DIR}/MI_{name[2:]}'
        if eal.does_asset_exist(path):
            INST[name] = unreal.load_asset(path)
for name in todo:
    s = SPEC[name]
    mi = fresh('MI_' + name[2:], unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    mel.set_material_instance_parent(mi, GLASS if s.get('glass') else MASKED if s.get('masked') else OPAQUE)
    if not s.get('glass'):   # weathering layers of the master (streaks / contact grime / macro variation) scale with the grime
        g = float(s.get('GrimeAmount', 0.0))
        s = {**dict(StreakAmount=round(0.75 * g, 3), ContactAmount=0.45 if g >= 0.3 else 0.2, MacroAmount=0.22), **s}
    for key, val in s.items():
        if key in ('masked', 'glass'):
            continue
        if key.endswith('Tex'):
            t = tex(val)
            if t:
                mel.set_material_instance_texture_parameter_value(mi, key, t)
        elif key in ('Tint', 'GrimeColor', 'Emissive'):
            col = unreal.LinearColor(val[0], val[1], val[2], 1) if isinstance(val, tuple) else lin(val)   # tuple = absolute nits
            mel.set_material_instance_vector_parameter_value(mi, key, col)
        else:
            mel.set_material_instance_scalar_parameter_value(mi, key, float(val))
    mel.update_material_instance(mi)
    eal.save_loaded_asset(mi)
    INST[name] = mi

missing = set()
ASSIGN = globals().get('MESHES', '')
if PART in ('all', 'assign'):
    for p in eal.list_assets('/Game/MongHa/Meshes', recursive=True):
        sm = unreal.load_asset(p)
        if not isinstance(sm, unreal.StaticMesh) or (ASSIGN and sm.get_name() not in ASSIGN.split(',')):
            continue
        mats = list(sm.get_editor_property('static_materials'))   # one property change = one rebuild (set_material rebuilds per slot)
        for sl in mats:
            slot = str(sl.get_editor_property('material_slot_name'))
            key = slot if slot in INST else next((k for k in sorted(INST, key=len, reverse=True) if slot.startswith(k)), None)
            if key:
                sl.set_editor_property('material_interface', INST[key])
            else:
                missing.add(slot)
        sm.set_editor_property('static_materials', mats)
        eal.save_loaded_asset(sm)
        print('assigned', sm.get_name(), len(mats))
print('instances', len(INST), 'done now', len(todo), 'unmapped slots', sorted(missing))
print('MATERIALS_DONE', PART)
