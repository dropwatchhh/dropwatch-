"""Dex Hollow portrait in Blender (Cycles, CPU). Run:
  blender -b --factory-startup -P dex_portrait.py -- OUT.png SAMPLES PERCENT [EXPR]
Modelling is done in 'three-space' (x right, y up, z toward viewer) and converted to Blender (x, -z, y).
"""
import bpy, bmesh, math, random, sys, time
from mathutils import Vector

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = argv[0] if len(argv) > 0 else '/tmp/dex.png'
SAMPLES = int(argv[1]) if len(argv) > 1 else 32
PCT = int(argv[2]) if len(argv) > 2 else 50
EXPR = argv[3] if len(argv) > 3 else 'smile'

D = math.pi / 180
R = random.Random(7)
def P(x, y, z): return (x, -z, y)
def s01(t): t = min(1, max(0, t)); return t * t * (3 - 2 * t)
def lerp(a, b, t): return a + (b - a) * t
def V3(x, y, z): return Vector((x, y, z))

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

# ------------------------------------------------------------------ materials
def new_mat(name):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
    for n in list(nt.nodes): nt.nodes.remove(n)
    out = nt.nodes.new('ShaderNodeOutputMaterial'); b = nt.nodes.new('ShaderNodeBsdfPrincipled')
    nt.links.new(b.outputs['BSDF'], out.inputs['Surface']); return m, nt, b
def setp(b, **kw):
    for k, v in kw.items():
        name = k.replace('_', ' ')
        try: b.inputs[name].default_value = v
        except KeyError: print('MISSING INPUT', name)
def node(nt, t, **kw):
    n = nt.nodes.new(t)
    for k, v in kw.items(): setattr(n, k, v)
    return n
def bump_noise(nt, b, scale, detail, strength, dist=0.01, rough=0.5, voronoi=False):
    tc = node(nt, 'ShaderNodeTexCoord')
    tex = node(nt, 'ShaderNodeTexVoronoi' if voronoi else 'ShaderNodeTexNoise')
    tex.inputs['Scale'].default_value = scale
    if not voronoi: tex.inputs['Detail'].default_value = detail; tex.inputs['Roughness'].default_value = rough
    nt.links.new(tc.outputs['Object'], tex.inputs['Vector'])
    bm = node(nt, 'ShaderNodeBump'); bm.inputs['Strength'].default_value = strength; bm.inputs['Distance'].default_value = dist
    nt.links.new(tex.outputs['Distance' if voronoi else 'Fac'], bm.inputs['Height']); nt.links.new(bm.outputs['Normal'], b.inputs['Normal'])
    return tex

SKIN_C = (0.46, 0.21, 0.11, 1)
m_skin, nt, b = new_mat('skin'); setp(b, Base_Color=SKIN_C, Roughness=0.42, Subsurface_Weight=0.55, Subsurface_Radius=(1.0, 0.35, 0.22), Subsurface_Scale=0.06, Specular_IOR_Level=0.5, Sheen_Weight=0.25, Sheen_Roughness=0.4)
bump_noise(nt, b, 260, 6, 0.12, 0.004)
m_skinD, nt, b = new_mat('skinD'); setp(b, Base_Color=(0.45, 0.2, 0.11, 1), Roughness=0.5, Subsurface_Weight=0.4, Subsurface_Scale=0.04)
m_lipU, nt, b = new_mat('lipU'); setp(b, Base_Color=(0.42, 0.1, 0.14, 1), Roughness=0.3, Subsurface_Weight=0.5, Subsurface_Scale=0.03, Coat_Weight=0.4, Coat_Roughness=0.15)
m_lipL, nt, b = new_mat('lipL'); setp(b, Base_Color=(0.52, 0.14, 0.18, 1), Roughness=0.28, Subsurface_Weight=0.5, Subsurface_Scale=0.03, Coat_Weight=0.5, Coat_Roughness=0.12)
m_mouth, nt, b = new_mat('mouthIn'); setp(b, Base_Color=(0.07, 0.01, 0.02, 1), Roughness=0.7)
m_teeth, nt, b = new_mat('teeth'); setp(b, Base_Color=(0.9, 0.86, 0.8, 1), Roughness=0.25, Subsurface_Weight=0.3, Subsurface_Scale=0.01)
m_tongue, nt, b = new_mat('tongue'); setp(b, Base_Color=(0.5, 0.1, 0.14, 1), Roughness=0.5)
m_black, nt, b = new_mat('black'); setp(b, Base_Color=(0.01, 0.008, 0.012, 1), Roughness=0.45)
m_metal, nt, b = new_mat('metal'); setp(b, Base_Color=(0.8, 0.82, 0.86, 1), Metallic=1.0, Roughness=0.2)
m_tee, nt, b = new_mat('tee'); setp(b, Base_Color=(0.75, 0.03, 0.09, 1), Roughness=0.8, Sheen_Weight=0.4); bump_noise(nt, b, 500, 3, 0.2, 0.003)
m_white, nt, b = new_mat('white'); setp(b, Base_Color=(0.9, 0.9, 0.88, 1), Roughness=0.5)
m_leather, nt, b = new_mat('leather'); setp(b, Base_Color=(0.012, 0.012, 0.016, 1), Roughness=0.34, Coat_Weight=0.45, Coat_Roughness=0.2, Specular_IOR_Level=0.6)
bump_noise(nt, b, 380, 0, 0.35, 0.004, voronoi=True)
m_leatherD, nt, b = new_mat('leatherD'); setp(b, Base_Color=(0.006, 0.006, 0.009, 1), Roughness=0.4, Coat_Weight=0.3)
m_scalp, nt, b = new_mat('scalp'); setp(b, Base_Color=(0.05, 0.01, 0.08, 1), Roughness=0.9)
m_under, nt, b = new_mat('undercut'); setp(b, Base_Color=(0.02, 0.3, 0.28, 1), Roughness=0.8)
tex = node(nt, 'ShaderNodeTexNoise'); tex.inputs['Scale'].default_value = 14
tc = node(nt, 'ShaderNodeTexCoord'); nt.links.new(tc.outputs['Object'], tex.inputs['Vector'])
ramp = node(nt, 'ShaderNodeValToRGB'); ramp.color_ramp.elements[0].color = (0.005, 0.09, 0.085, 1); ramp.color_ramp.elements[1].color = (0.16, 0.012, 0.09, 1)
nt.links.new(tex.outputs['Fac'], ramp.inputs['Fac']); nt.links.new(ramp.outputs['Color'], b.inputs['Base Color'])

def hair_mat(name, c_base, c_tip):
    m, nt, b = new_mat(name); setp(b, Roughness=0.32, Coat_Weight=0.5, Coat_Roughness=0.2, Sheen_Weight=0.3, Specular_IOR_Level=0.6, Subsurface_Weight=0.15, Subsurface_Scale=0.02)
    geo = node(nt, 'ShaderNodeNewGeometry'); vm = node(nt, 'ShaderNodeVectorMath', operation='DISTANCE'); vm.inputs[1].default_value = (0, 0.05, 2.47)
    nt.links.new(geo.outputs['Position'], vm.inputs[0])
    mr = node(nt, 'ShaderNodeMapRange'); mr.inputs['From Min'].default_value = 0.55; mr.inputs['From Max'].default_value = 1.25
    nt.links.new(vm.outputs['Value'], mr.inputs['Value'])
    ramp = node(nt, 'ShaderNodeValToRGB'); ramp.color_ramp.elements[0].color = c_base; ramp.color_ramp.elements[1].color = c_tip
    nt.links.new(mr.outputs['Result'], ramp.inputs['Fac'])
    nz = node(nt, 'ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 60; nz.inputs['Detail'].default_value = 2
    nt.links.new(geo.outputs['Position'], nz.inputs['Vector'])
    mix = node(nt, 'ShaderNodeMix', data_type='RGBA', blend_type='MULTIPLY'); mix.inputs['Factor'].default_value = 0.5
    nt.links.new(ramp.outputs['Color'], mix.inputs['A']); nt.links.new(nz.outputs['Color'], mix.inputs['B'])
    mixc = node(nt, 'ShaderNodeMix', data_type='RGBA', blend_type='MIX'); mixc.inputs['Factor'].default_value = 0.35
    nt.links.new(ramp.outputs['Color'], mixc.inputs['A']); nt.links.new(mix.outputs['Result'], mixc.inputs['B'])
    nt.links.new(mixc.outputs['Result'], b.inputs['Base Color']); return m
m_teal = hair_mat('hairTeal', (0.0, 0.25, 0.23, 1), (0.25, 0.95, 0.85, 1))
m_pink = hair_mat('hairPink', (0.35, 0.0, 0.16, 1), (1.0, 0.25, 0.65, 1))
m_brow, nt, b = new_mat('brow'); setp(b, Base_Color=(0.012, 0.007, 0.009, 1), Roughness=0.5)
m_lash, nt, b = new_mat('lash'); setp(b, Base_Color=(0.005, 0.004, 0.006, 1), Roughness=0.4)
m_blush, nt, b = new_mat('blush')
setp(b, Base_Color=(0.8, 0.2, 0.25, 1), Roughness=0.6, Subsurface_Weight=0.3)
tc = node(nt, 'ShaderNodeTexCoord'); gr = node(nt, 'ShaderNodeTexGradient', gradient_type='SPHERICAL')
mp = node(nt, 'ShaderNodeMapping'); mp.inputs['Location'].default_value = (-0.5, -0.5, -0.5)
nt.links.new(tc.outputs['UV'], mp.inputs['Vector']); nt.links.new(mp.outputs['Vector'], gr.inputs['Vector'])
mrr = node(nt, 'ShaderNodeMapRange'); mrr.inputs['From Min'].default_value = 0.5; mrr.inputs['From Max'].default_value = 1.0; mrr.inputs['To Min'].default_value = 0.0; mrr.inputs['To Max'].default_value = 0.45
nt.links.new(gr.outputs['Fac'], mrr.inputs['Value']); nt.links.new(mrr.outputs['Result'], b.inputs['Alpha'])
m_blush.blend_method = 'BLEND' if hasattr(m_blush, 'blend_method') else None

def eye_mat():
    m, nt, b = new_mat('eye'); setp(b, Roughness=0.04, Coat_Weight=1.0, Coat_Roughness=0.0, Specular_IOR_Level=0.8)
    tc = node(nt, 'ShaderNodeTexCoord'); sp = node(nt, 'ShaderNodeSeparateXYZ'); nt.links.new(tc.outputs['Object'], sp.inputs['Vector'])
    sx = node(nt, 'ShaderNodeMath', operation='POWER'); sx.inputs[1].default_value = 2; nt.links.new(sp.outputs['X'], sx.inputs[0])
    sz = node(nt, 'ShaderNodeMath', operation='POWER'); sz.inputs[1].default_value = 2; nt.links.new(sp.outputs['Z'], sz.inputs[0])
    ad = node(nt, 'ShaderNodeMath', operation='ADD'); nt.links.new(sx.outputs['Value'], ad.inputs[0]); nt.links.new(sz.outputs['Value'], ad.inputs[1])
    rr0 = node(nt, 'ShaderNodeMath', operation='SQRT'); nt.links.new(ad.outputs['Value'], rr0.inputs[0])
    rr = node(nt, 'ShaderNodeMath', operation='MULTIPLY'); rr.inputs[1].default_value = 1 / 0.118; nt.links.new(rr0.outputs['Value'], rr.inputs[0])
    # front hemisphere only (front is -Y): fade to white sclera at the back
    ramp = node(nt, 'ShaderNodeValToRGB'); e = ramp.color_ramp.elements
    e[0].position = 0.0; e[0].color = (0.0, 0.0, 0.0, 1)
    e[1].position = 0.2; e[1].color = (0.0, 0.0, 0.0, 1)
    for pos, col in [(0.24, (0.05, 0.28, 0.85, 1)), (0.38, (0.03, 0.18, 0.7, 1)), (0.5, (0.01, 0.05, 0.3, 1)), (0.56, (0.85, 0.82, 0.8, 1)), (1.0, (0.88, 0.86, 0.85, 1))]:
        el = ramp.color_ramp.elements.new(pos); el.color = col
    nt.links.new(rr.outputs['Value'], ramp.inputs['Fac'])
    # slight streaks in the iris
    nz = node(nt, 'ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 14; nz.inputs['Detail'].default_value = 3
    nt.links.new(tc.outputs['Object'], nz.inputs['Vector'])
    mx = node(nt, 'ShaderNodeMix', data_type='RGBA', blend_type='OVERLAY'); mx.inputs['Factor'].default_value = 0.35
    nt.links.new(ramp.outputs['Color'], mx.inputs['A']); nt.links.new(nz.outputs['Color'], mx.inputs['B'])
    nt.links.new(mx.outputs['Result'], b.inputs['Base Color']); return m
m_eye = eye_mat()

# ------------------------------------------------------------------ mesh helpers
def mk_obj(name, verts, faces, mat, smooth=True, subsurf=0, solid=0.0, parent=None):
    me = bpy.data.meshes.new(name); me.from_pydata([P(*v) for v in verts], [], faces); me.update()
    ob = bpy.data.objects.new(name, me); scene.collection.objects.link(ob)
    if mat: ob.data.materials.append(mat)
    if smooth:
        for pl in me.polygons: pl.use_smooth = True
    if solid:
        md = ob.modifiers.new('solid', 'SOLIDIFY'); md.thickness = solid; md.offset = 0
    if subsurf:
        md = ob.modifiers.new('sub', 'SUBSURF'); md.levels = subsurf; md.render_levels = subsurf
    if parent: ob.parent = parent
    return ob
def sphere(name, r, loc, scale=(1, 1, 1), mat=None, seg=48, parent=None, world3=True):
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg // 2, radius=r)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); scene.collection.objects.link(ob)
    ob.location = P(*loc) if world3 else loc; ob.scale = scale
    for pl in me.polygons: pl.use_smooth = True
    if mat: ob.data.materials.append(mat)
    if parent: ob.parent = parent
    return ob
def cylinder_between(name, a, b, r0, r1, mat, seg=32):
    a, b = Vector(P(*a)), Vector(P(*b)); d = b - a; L = d.length
    bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r0, radius2=r1, depth=L)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); scene.collection.objects.link(ob)
    ob.location = (a + b) / 2; ob.rotation_mode = 'QUATERNION'; ob.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(d.normalized())
    for pl in me.polygons: pl.use_smooth = True
    ob.data.materials.append(mat); return ob
def curve_obj(name, splines, bevel, mat, kind='POLY', res=2, parent=None):
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = bevel; cu.bevel_resolution = 1; cu.resolution_u = res
    cu.use_fill_caps = False
    for pts, rads in splines:
        sp = cu.splines.new(kind); n = len(pts)
        if kind == 'POLY':
            sp.points.add(n - 1)
            for i, (p, r) in enumerate(zip(pts, rads)): sp.points[i].co = (*P(*p), 1.0); sp.points[i].radius = r
        else:
            sp.bezier_points.add(n - 1)
            for i, (p, r) in enumerate(zip(pts, rads)):
                bp = sp.bezier_points[i]; bp.co = P(*p); bp.radius = r; bp.handle_left_type = 'AUTO'; bp.handle_right_type = 'AUTO'
    ob = bpy.data.objects.new(name, cu); scene.collection.objects.link(ob); ob.data.materials.append(mat)
    if parent: ob.parent = parent
    return ob

# ------------------------------------------------------------------ the head (sculpted height field on a tapered ellipsoid)
HEAD = dict(cy=2.38, rx=0.6, ry=0.58, rz=0.56, taper=0.15)
def kOf(y): u = (y - HEAD['cy']) / HEAD['ry']; return 1 - HEAD['taper'] * s01(-u) if u < 0 else 1
def zf(u): return 1 + 0.06 * s01(-u) if u < 0 else 1
def faceZ0(x, y):
    u = (y - HEAD['cy']) / HEAD['ry']; k = kOf(y); v = 1 - (x / (HEAD['rx'] * k)) ** 2 - u * u
    return HEAD['rz'] * zf(u) * math.sqrt(max(0.01, v))
FEAT = [  # cx, cy, sx, sy, amplitude  (z displacement on the front of the face)
    (0, 2.34, .028, .08, .03), (0, 2.275, .05, .05, .06), (0, 2.235, .04, .03, .03), (-.06, 2.235, .03, .03, .016), (.06, 2.235, .03, .03, .016),
    (-.215, 2.4, .105, .11, -.034), (.215, 2.4, .105, .11, -.034), (-.22, 2.585, .14, .035, .022), (.22, 2.585, .14, .035, .022),
    (-.335, 2.2, .11, .11, .032), (.335, 2.2, .11, .11, .032), (0, 2.12, .17, .07, .03), (0, 2.168, .016, .03, -.009),
    (0, 1.92, .11, .07, .042), (0, 2.035, .1, .02, -.013), (-.4, 2.3, .09, .2, -.02), (.4, 2.3, .09, .2, -.02)]
def H(x, y):
    h = 0.0
    for cx, cy, sx, sy, a in FEAT: h += a * math.exp(-(((x - cx) / sx) ** 2 + ((y - cy) / sy) ** 2) / 2)
    return h
def surfZ(x, y): return faceZ0(x, y) + H(x, y)

bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=176, v_segments=120, radius=1.0)
for v in bm.verts:
    a, bb, c = v.co; ux, uy, uz = a, c, -bb
    y3 = uy * HEAD['ry'] + HEAD['cy']; k = kOf(y3); x3 = ux * HEAD['rx'] * k; z3 = uz * HEAD['rz'] * zf(uy)
    if z3 > 0: z3 += H(x3, y3) * s01(z3 / 0.18)
    v.co = Vector(P(x3, y3, z3))
bm.normal_update()
head_me = bpy.data.meshes.new('head'); bm.to_mesh(head_me)
head = bpy.data.objects.new('head', head_me); scene.collection.objects.link(head); head.data.materials.append(m_skin)
for pl in head_me.polygons: pl.use_smooth = True
md = head.modifiers.new('sub', 'SUBSURF'); md.levels = 1; md.render_levels = 1
# undercut shell + scalp: copy of the upper/back head faces pushed out a little
bm2 = bmesh.new(); bm2.from_mesh(head_me); keep = []
for f in bm2.faces:
    c = f.calc_center_median(); x3, y3, z3 = c.x, c.z, -c.y
    if y3 > 2.3 and not (z3 > 0.2 and y3 < 2.8): keep.append(f)
bmesh.ops.delete(bm2, geom=[f for f in bm2.faces if f not in keep], context='FACES')
for v in bm2.verts:
    x3, y3, z3 = v.co.x, v.co.z, -v.co.y; n = Vector((x3 / 0.36, (y3 - 2.38) / 0.34, z3 / 0.31)).normalized(); v.co += Vector(P(*(n * 0.007)))
sh_me = bpy.data.meshes.new('scalp'); bm2.to_mesh(sh_me); bm2.free()
scalp = bpy.data.objects.new('scalp', sh_me); scene.collection.objects.link(scalp); scalp.data.materials.append(m_under)
for pl in sh_me.polygons: pl.use_smooth = True

# ------------------------------------------------------------------ eyes, lids, lashes
EXPRS = {
    'smile': dict(smile=0.85, open=0.3, skew=0.0, width=1.0, brow=[0.012, -0.05, 0.012, -0.05], lid=(-0.3, -0.3), squint=0.3),
    'grin': dict(smile=1.0, open=0.55, skew=0.0, width=1.0, brow=[0.03, 0.08, 0.03, 0.08], lid=(-0.2, -0.2), squint=0.4),
    'smirk': dict(smile=0.55, open=0.0, skew=0.45, width=1.0, brow=[-0.005, -0.2, 0.05, 0.12], lid=(-0.05, -0.2), squint=0.2),
    'surprise': dict(smile=-0.05, open=0.8, skew=0.0, width=0.6, brow=[0.13, 0.15, 0.13, 0.15], lid=(-0.9, -0.9), squint=0.0),
}
E = EXPRS[EXPR]
def eye(s):
    x, y = s * 0.21, 2.4; z = surfZ(x, y) - 0.075
    ball = sphere('eye%d' % s, 0.118, (x, y, z), (1, 1, 1.1), m_eye, 64)
    lidr = 0.128
    def shell(name, upper):
        bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=40, v_segments=24, radius=lidr)
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if (v.co.z < -1e-4 if upper else v.co.z > 1e-4)], context='VERTS')
        me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
        ob = bpy.data.objects.new(name, me); scene.collection.objects.link(ob); ob.data.materials.append(m_skin)
        for pl in me.polygons: pl.use_smooth = True
        md = ob.modifiers.new('solid', 'SOLIDIFY'); md.thickness = 0.01; md.offset = 1
        ob.location = P(x, y, z); ob.scale = (1, 1, 1.1); return ob
    up, lo = shell('lidU%d' % s, True), shell('lidL%d' % s, False)
    c = E['lid'][0 if s < 0 else 1]
    up.rotation_euler = ((lerp(-82, 82, 0.5 + c * 0.5) if c > -1 else -90) * D, 0, 0)
    lo.rotation_euler = (lerp(80, 5, E['squint']) * D, 0, 0)
    # eyeliner on the upper-lid rim (child of the lid so it moves with it) + a wing
    rim = [(lidr * 1.005 * math.cos(math.pi * i / 18), -lidr * 1.005 * math.sin(math.pi * i / 18), 0.002) for i in range(19)]
    outer = 0 if s > 0 else 18; ox = rim[outer][0]
    wing = (ox + s * 0.05, -0.04, 0.03)
    pts = ([wing] + rim) if s > 0 else (rim + [wing])
    liner = curve_obj('liner%d' % s, [(pts, [1.0] * len(pts))], 0.0125, m_black, 'BEZIER', 4)
    liner.data.splines[0].use_smooth = True
    # port: curve points are in lid-local Blender coords already -> undo P() by passing raw through a custom path
    for sp in liner.data.splines:
        for i, bp in enumerate(sp.bezier_points): bp.co = pts[i]
    liner.parent = up; liner.matrix_parent_inverse = up.matrix_world.inverted()
    # lashes (outer half), fanning up/outward
    lashes = []
    for k in range(9):
        ti = (1 + k) if s > 0 else (17 - k); p = rim[ti]
        d = Vector((p[0] * 1.0 + s * (0.25 + 0.06 * k), -0.35, 0.95)).normalized(); L = 0.05 + 0.025 * R.random()
        p0 = Vector(p); lashes.append(([tuple(p0), tuple(p0 + d * L * 0.4), tuple(p0 + d * L * 0.8 + Vector((0, -0.01, 0.01))), tuple(p0 + d * L + Vector((0, -0.02, 0.025)))], [1, 0.8, 0.5, 0.15]))
    lash = curve_obj('lash%d' % s, [([P2 for P2 in pts_], r) for pts_, r in lashes], 0.0058, m_lash, 'POLY', 2)
    for sp, (pts_, r) in zip(lash.data.splines, lashes):
        for i, pt in enumerate(sp.points): pt.co = (*pts_[i], 1.0)
    lash.parent = up; lash.matrix_parent_inverse = up.matrix_world.inverted()
    return ball
eye(-1); eye(1)

# ------------------------------------------------------------------ lips, teeth, mouth
def ribbon(A, B, rows, off, puff):
    n = len(A); verts, faces = [], []
    for r in range(rows + 1):
        v = r / rows; o = off + puff * math.sin(math.pi * v) ** 0.8
        for i in range(n):
            x = lerp(A[i][0], B[i][0], v); y = lerp(A[i][1], B[i][1], v); verts.append((x, y, surfZ(x, y) + o))
    for r in range(rows):
        for i in range(n - 1): a = r * n + i; faces.append((a, a + n, a + n + 1, a + 1))
    return verts, faces
def mouth(e):
    smile, open_, skew, width = e['smile'], e['open'], e['skew'], e['width']; cy, hw, N = 2.1, 0.165 * e['width'], 40
    mid = lambda x: cy + (0.042 * smile + 0.012) * abs(x / hw) ** 2.2 + skew * 0.035 * (x / hw)
    xs = [-hw + 2 * hw * i / N for i in range(N + 1)]; sf = lambda x: max(0.0, 1 - (x / hw) ** 2)
    gap = open_ * 0.19 if open_ > 0.04 else 0.0025
    inU = [(x, mid(x)) for x in xs]; inL = [(x, mid(x) - gap * sf(x) ** 0.85) for x in xs]
    outU = [(x, inU[i][1] + 0.034 * sf(x) ** 0.55 * (1 - 0.22 * math.exp(-((x / (0.16 * hw)) ** 2)))) for i, x in enumerate(xs)]
    outL = [(x, inL[i][1] - 0.047 * sf(x) ** 0.55) for i, x in enumerate(xs)]
    v, f = ribbon(inU, outU, 5, 0.004, 0.016); mk_obj('lipU', v, f, m_lipU, True, 2)
    v, f = ribbon(inL, outL, 5, 0.004, 0.019); mk_obj('lipL', v, f, m_lipL, True, 2)
    if open_ > 0.04:
        v, f = ribbon(inU, inL, 2, 0.0015, 0.0); mk_obj('mouthIn', v, f, m_mouth, True)
        if open_ > 0.15:
            i0, i1 = 4, N - 4; td = min(0.062, open_ * 0.12)
            T = [(xs[i], inU[i][1] - 0.002) for i in range(i0, i1 + 1)]; Bm = [(xs[i], max(inL[i][1] + 0.005, inU[i][1] - td)) for i in range(i0, i1 + 1)]
            v, f = ribbon(T, Bm, 2, 0.004, 0.006); mk_obj('teethU', v, f, m_teeth, True, 1)
            T2 = [(xs[i], max(inU[i][1] - 0.005, inL[i][1] + min(0.04, open_ * 0.08))) for i in range(i0 + 3, i1 - 2)]; B2 = [(xs[i], inL[i][1] + 0.002) for i in range(i0 + 3, i1 - 2)]
            v, f = ribbon(B2, T2, 2, 0.003, 0.004); mk_obj('teethL', v, f, m_teeth, True, 1)
        if open_ > 0.5:
            sphere('tongue', 0.07, (0, inL[N // 2][1] + 0.02, surfZ(0, inL[N // 2][1]) + 0.0), (1, 0.4, 0.35), m_tongue, 24)
    if smile > 0.3:
        for sg in (-1, 1):
            yc = mid(sg * hw); pts = [(sg * (hw + 0.012), yc + 0.034), (sg * (hw + 0.036), yc + 0.006), (sg * (hw + 0.022), yc - 0.028)]
            pts = [(x, y, surfZ(x, y) + 0.003) for x, y in pts]
            curve_obj('crease', [(pts, [1, 1, 0.5])], 0.0042, m_skinD, 'BEZIER', 6)
mouth(E)

# ------------------------------------------------------------------ eyebrows: real hair strands, matching on both sides
def brows(e):
    b = e['brow']
    for i, s in enumerate((-1, 1)):
        y_, a_ = b[i * 2], b[i * 2 + 1]; N = 22; xin, xout = s * 0.085, s * 0.36; yin, yout = 2.64 + y_ + a_ * 0.042, 2.64 + y_ - a_ * 0.042 - 0.012; arch = 0.028
        C = [(lerp(xin, xout, k / N), lerp(yin, yout, k / N) + arch * math.sin(math.pi * (k / N) ** 0.85)) for k in range(N + 1)]
        def at(t):
            k = min(N - 1, int(t * N)); f = t * N - k; return (lerp(C[k][0], C[k + 1][0], f), lerp(C[k][1], C[k + 1][1], f), (C[k + 1][0] - C[k][0], C[k + 1][1] - C[k][1]))
        spl = []
        for _ in range(520):
            t = R.random() ** 0.9; x, y, (tx, ty) = at(t); L = math.hypot(tx, ty) or 1; tx, ty = tx / L, ty / L
            th = (0.012 + 0.034 * math.sin(math.pi * (0.12 + 0.75 * t)) ** 0.9) * (1 - 0.5 * t) * 1.15
            v = (R.random() - 0.5) * th; nx, ny = -ty, tx
            if ny < 0: nx, ny = -nx, -ny
            x0, y0 = x + nx * v, y + ny * v; ln = 0.032 + 0.03 * R.random() * (1 - 0.4 * t); ang = (v / th) * 0.7 + (R.random() - 0.5) * 0.25
            dx, dy = tx * math.cos(ang) - ny * 0 + nx * math.sin(ang), ty * math.cos(ang) + ny * math.sin(ang)
            p0 = (x0, y0, surfZ(x0, y0) + 0.0015); p1 = (x0 + dx * ln * 0.5, y0 + dy * ln * 0.5, surfZ(x0 + dx * ln * 0.5, y0 + dy * ln * 0.5) + 0.004)
            p2 = (x0 + dx * ln, y0 + dy * ln, surfZ(x0 + dx * ln, y0 + dy * ln) + 0.003)
            spl.append(([p0, p1, p2], [1.0, 0.75, 0.2]))
        curve_obj('brow%d' % i, spl, 0.0024, m_brow, 'BEZIER', 2)
brows(E)

# ------------------------------------------------------------------ hair: strand clumps (teal / magenta mohawk)
CAPC, CAPS, CAPROT = V3(0, 2.47, -0.05), V3(0.66, 0.64, 0.62), -0.4
def capPt(theta, phi):
    p = V3(math.sin(theta) * math.sin(phi) * CAPS.x, math.cos(theta) * CAPS.y, math.sin(theta) * math.cos(phi) * CAPS.z)
    c, s_ = math.cos(CAPROT), math.sin(CAPROT)
    return V3(p.x, p.y * c - p.z * s_, p.y * s_ + p.z * c) + CAPC
strands = {'a': [], 'b': []}
def basis(d):
    up = V3(0, 1, 0) if abs(d.y) < 0.9 else V3(1, 0, 0); u = d.cross(up).normalized(); return u, d.cross(u).normalized()
def curve_pts(P0, d, sv, l):
    return [P0 - d * 0.07, P0 + d * (0.3 * l) + sv * (0.03 * l), P0 + d * (0.65 * l) + sv * (0.2 * l), P0 + d * l + sv * (0.55 * l)]
def clump(base, dir_, ln, rad, kind, sweep, n=16, wob=0.3):
    d, sv = dir_.normalized(), sweep.normalized(); u, v = basis(d)
    strands[kind].append(([tuple(p) for p in curve_pts(base, d, sv, ln)], [1.0, 0.9, 0.55, 0.12], rad * 0.8))
    for _ in range(n):
        ang, rr = R.random() * 6.283, rad * math.sqrt(R.random()); off = u * (math.cos(ang) * rr) + v * (math.sin(ang) * rr); l = ln * (0.8 + 0.34 * R.random())
        pts = curve_pts(base, d, sv, l); pts = [p + off * f + (V3(R.random() - .5, R.random() - .5, R.random() - .5) * (wob * ln * 0.2 * (1 if i > 1 else 0.2))) for i, (p, f) in enumerate(zip(pts, [1, .95, .6, .12]))]
        k = kind if R.random() > 0.22 else ('b' if kind == 'a' else 'a')
        strands[k].append(([tuple(p) for p in pts], [1.0, 0.85, 0.5, 0.1], 0.0125 + 0.009 * R.random()))
flip = 0
for k in range(12):
    sPar = -1 + 2 * k / 11; theta = -sPar * 0.9 if sPar < 0 else sPar * 1.25; phi = 0 if sPar < 0 else math.pi; prof = math.sin(math.pi * (0.06 + 0.88 * k / 11))
    for lane in (-0.14, 0, 0.14):
        B0 = capPt(theta, phi); B = V3(lane, B0.y - abs(lane) * 0.1, B0.z); n = (B - CAPC).normalized()
        dir_ = (n * 0.8 + V3(lane * 1.8, 0.9, 0)).normalized()
        sw = V3(lane * 2 + (R.random() - .5), 0.25, 1) if sPar < -0.15 else (V3(lane * 2 + (R.random() - .5), -0.15, -1) if sPar > 0.25 else V3(lane * 3 + (R.random() - .5) * 2, 0, -0.45))
        ln = (0.28 + 0.62 * prof ** 0.9) * (1 if lane == 0 else 0.84) * (0.9 + 0.2 * R.random())
        clump(B, dir_, ln, 0.085 + 0.02 * R.random(), 'a' if flip % 2 else 'b', sw, 16); flip += 1
for sg in (-1, 1):
    for k in range(7):
        B = capPt(0.95 + 0.4 * R.random(), sg * (0.9 + 1.2 * R.random())); n = (B - CAPC).normalized()
        clump(B, n + V3(sg * 0.5, 0.25, 0), 0.3 + 0.28 * R.random(), 0.06, 'a' if flip % 2 else 'b', V3(sg * 0.7, -0.35, -0.4), 14); flip += 1
for k in range(7):
    ph = -0.8 + 1.6 * k / 6; B = capPt(0.98 + 0.05 * R.random(), ph); n = (B - CAPC).normalized()
    clump(B, n + V3(0, -0.15, 0.55), 0.24 + 0.14 * R.random(), 0.045, 'a' if flip % 2 else 'b', V3(math.copysign(0.6, ph), -0.1, 0.25), 12, 0.2); flip += 1
short = {'a': [], 'b': []}
for _ in range(900):
    phi = (R.random() - 0.5) * 2.8; theta = 0.7 + 0.52 * R.random(); B = capPt(theta, phi); n = (B - CAPC).normalized(); l = 0.09 + 0.12 * R.random()
    short['a' if R.random() < 0.5 else 'b'].append(([tuple(B - n * 0.04), tuple(B + n * l * 0.5 + V3(0, 0.02, 0.02)), tuple(B + n * l + V3(math.copysign(0.02, phi), 0.03, -0.03))], [1.0, 0.7, 0.2]))
for _ in range(2200):
    a = R.random() * 6.283; y = 2.3 + 0.68 * R.random(); uy = (y - 2.38) / 0.58
    if abs(uy) >= 0.98: continue
    r = math.sqrt(1 - uy * uy); kk = kOf(y); Pp = V3(0.6 * kk * r * math.sin(a), y, 0.56 * r * math.cos(a))
    if math.cos(a) > 0.1 and y < 2.8: continue
    if abs(math.sin(a)) > 0.8 and 2.2 < y < 2.52: continue
    n = V3(Pp.x / 0.36, (Pp.y - 2.38) / 0.34, Pp.z / 0.31).normalized(); l = 0.09 + 0.1 * R.random()
    short['a' if R.random() < 0.5 else 'b'].append(([tuple(Pp - n * 0.03), tuple(Pp + n * l * 0.5 + V3(0, -0.015, -0.01)), tuple(Pp + n * l + V3(0, -0.04, -0.03))], [1.0, 0.7, 0.2]))
for kind, mat in (('a', m_pink), ('b', m_teal)):
    long_ = strands[kind]
    # one curve object per strand radius class keeps bevel simple: use point radius as the taper, bevel_depth = typical base radius
    cu_thin = [(p, r) for p, r, rad in long_ if rad < 0.03]; cu_core = [(p, [x * 1.0 for x in r]) for p, r, rad in long_ if rad >= 0.03]
    curve_obj('hairThin' + kind, cu_thin, 0.011, mat, 'BEZIER', 3)
    curve_obj('hairCore' + kind, cu_core, 0.042, mat, 'BEZIER', 3)
    curve_obj('hairShort' + kind, short[kind], 0.0105, mat, 'POLY', 1)

# ------------------------------------------------------------------ body: neck, tee, jacket, collar, lapels, shoulders
def lathe(profile, segs, phi0, phiL, zs, y0, ys=1.0, closed_front=False):
    verts, faces = [], []; rows = len(profile); cols = segs + 1
    for r, (rad, yy) in enumerate(profile):
        for c in range(cols):
            ph = phi0 + phiL * c / segs; verts.append((rad * math.sin(ph), y0 + yy * ys, rad * math.cos(ph) * zs))
    for r in range(rows - 1):
        for c in range(segs): a = r * cols + c; faces.append((a, a + 1, a + cols + 1, a + cols))
    return verts, faces
v, f = lathe([(0.13, 0), (0.14, 0.12), (0.15, 0.3)], 40, 0, 2 * math.pi, 1.0, 1.75); mk_obj('neck', v, f, m_skinD, True, 1)
teeProf = [(r * 0.93, y) for r, y in [(0.43, 0), (0.43, 0.2), (0.4, 0.42), (0.36, 0.62), (0.27, 0.74), (0.17, 0.8)]]
v, f = lathe(teeProf, 56, 0, 2 * math.pi, 0.72, 1.04); mk_obj('tee', v, f, m_tee, True, 1, 0.01)
GAP = 0.5; jProf = [(0.47, 0), (0.465, 0.05), (0.43, 0.24), (0.42, 0.4), (0.43, 0.55), (0.4, 0.66), (0.3, 0.75), (0.215, 0.8), (0.2, 0.84)]
v, f = lathe(jProf, 72, GAP, 2 * math.pi - 2 * GAP, 0.74, 1.04); mk_obj('jacket', v, f, m_leather, True, 2, 0.028)
v, f = lathe([(0.26, 1.83), (0.235, 1.9), (0.205, 1.97)], 48, GAP, 2 * math.pi - 2 * GAP, 0.8, 0); mk_obj('collar', [(x, y, z - 0.01) for x, y, z in v], f, m_leather, True, 2, 0.022)
for s in (-1, 1):
    poly = [(0.10 * s, 1.90, 0.31), (0.30 * s, 1.86, 0.25), (0.35 * s, 1.74, 0.30), (0.20 * s, 1.45, 0.345), (0.10 * s, 1.45, 0.345)]
    cv = [(0.10 * s, 1.90, 0.31), (0.30 * s, 1.86, 0.25), (0.35 * s, 1.74, 0.30), (0.20 * s, 1.45, 0.345), (0.10 * s, 1.45, 0.345)]
    cen = (sum(p[0] for p in poly) / 5, sum(p[1] for p in poly) / 5, sum(p[2] for p in poly) / 5)
    verts = poly + [cen]; faces = [(i, (i + 1) % 5, 5) for i in range(5)] if s > 0 else [((i + 1) % 5, i, 5) for i in range(5)]
    mk_obj('lapel%d' % s, verts, faces, m_leatherD, True, 2, 0.035)
    for k in range(5):
        t = k / 4; pp = (lerp(0.30, 0.20, t) * s, lerp(1.82, 1.5, t), lerp(0.285, 0.36, t)); sphere('stud', 0.021, pp, (1, 1, 1), m_metal, 14)
    # shoulder + upper arm
    cylinder_between('sleeve%d' % s, (0.4 * s, 1.68, 0.0), (0.52 * s, 1.22, 0.0), 0.125, 0.11, m_leather, 40)
    sphere('shoulder', 0.125, (0.4 * s, 1.68, 0.0), (1, 1, 1), m_leather, 40)
    for k in range(3): sphere('studS', 0.02, (0.39 * s + 0.03 * k * s, 1.8 - 0.02 * k, 0.06 - 0.07 * k), (1, 1, 1), m_metal, 12)
# chevron print on the tee
chev = [(-0.075, 1.44, 0.268), (0, 1.54, 0.268), (0.075, 1.44, 0.268), (0.048, 1.44, 0.268), (0, 1.505, 0.268), (-0.048, 1.44, 0.268)]
mk_obj('chev', chev + [(0, 1.485, 0.268)], [(0, 1, 6), (1, 2, 6), (2, 3, 6), (3, 4, 6), (4, 5, 6), (5, 0, 6)], m_white, False, 0, 0.012)
# ears + earrings
for s in (-1, 1):
    sphere('ear', 0.1, (0.6 * s, 2.36, 0), (0.7, 1.0, 0.5), m_skinD, 24); sphere('ring', 0.028, (0.615 * s, 2.22, 0.01), (1, 1, 1), m_metal, 14)
# soft blush
for s in (-1, 1):
    bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.14)
    me = bpy.data.meshes.new('blush'); bm.to_mesh(me); bm.free(); ob = bpy.data.objects.new('blush', me); scene.collection.objects.link(ob)
    ob.data.materials.append(m_blush)
    uv = me.uv_layers.new(name='UV');
    for i, loop in enumerate(me.loops): uv.data[i].uv = [(0, 0), (1, 0), (1, 1), (0, 1)][i % 4]
    ob.location = P(s * 0.35, 2.2, surfZ(s * 0.35, 2.2) + 0.006); ob.rotation_euler = (math.pi / 2 - 0.1, 0, 0)
    ob.rotation_euler = (90 * D, 0, -s * 0.0); ob.rotation_euler.z = s * 0.6 * D * -1

# ------------------------------------------------------------------ backdrop, lights, camera
bd, nt, b = new_mat('backdrop'); setp(b, Base_Color=(0.02, 0.008, 0.05, 1), Roughness=0.9, Emission_Strength=1.0)
tc = node(nt, 'ShaderNodeTexCoord'); sepz = node(nt, 'ShaderNodeSeparateXYZ'); nt.links.new(tc.outputs['Object'], sepz.inputs['Vector'])
rp = node(nt, 'ShaderNodeValToRGB'); rp.color_ramp.elements[0].color = (0.04, 0.005, 0.1, 1); rp.color_ramp.elements[1].color = (0.45, 0.12, 0.7, 1)
mr = node(nt, 'ShaderNodeMapRange'); mr.inputs['From Min'].default_value = -2.0; mr.inputs['From Max'].default_value = 8.0
nt.links.new(sepz.outputs['Z'], mr.inputs['Value']); nt.links.new(mr.outputs['Result'], rp.inputs['Fac'])
nt.links.new(rp.outputs['Color'], b.inputs['Emission Color']); setp(b, Emission_Strength=0.55)
bdv = [(-6, 4, -2), (6, 4, -2), (6, 4, 8), (-6, 4, 8)]
mk_obj('backdrop', [(-9, -2, 0), (9, -2, 0), (9, 9, 0), (-9, 9, 0)], [(0, 1, 2, 3)], bd, False)
bpy.data.objects['backdrop'].location = (0, 4.2, 0); bpy.data.objects['backdrop'].rotation_euler = (0, 0, 0)
bpy.data.objects['backdrop'].location = (0, 4.2, 0)
bk, nt, b = new_mat('bokeh'); setp(b, Base_Color=(0, 0, 0, 1)); b.inputs['Emission Strength'].default_value = 40
BR = random.Random(3)
for i in range(16):
    c = (0.1, 1.0, 0.9, 1) if i % 2 else (1.0, 0.15, 0.55, 1)
    m_, nt_, b_ = new_mat('bk%d' % i); setp(b_, Base_Color=(0, 0, 0, 1), Emission_Color=c, Emission_Strength=7)
    sp_ = sphere('bokeh', 0.05 + 0.08 * BR.random(), (BR.uniform(-3.2, 3.2), 0, BR.uniform(0.6, 4.4)), (1, 1, 1), m_, 16, world3=False)
    sp_.location = (BR.uniform(-3.2, 3.2), BR.uniform(3.3, 3.9), BR.uniform(0.6, 4.6))
tgt = bpy.data.objects.new('target', None); scene.collection.objects.link(tgt); tgt.location = P(0.0, 2.38, 0.5)
def light(name, loc, energy, color, size, kind='AREA'):
    l = bpy.data.lights.new(name, kind); l.energy = energy; l.color = color
    if kind == 'AREA': l.size = size
    ob = bpy.data.objects.new(name, l); scene.collection.objects.link(ob); ob.location = loc
    c = ob.constraints.new('TRACK_TO'); c.target = tgt; c.track_axis = 'TRACK_NEGATIVE_Z'; c.up_axis = 'UP_Y'; return ob
light('key', (-3.2, -3.6, 4.6), 330, (1.0, 0.93, 0.86), 2.6)
light('fill', (3.6, -3.0, 2.4), 110, (1.0, 0.45, 0.8), 3.0)
light('rimT', (-3.0, 2.6, 4.2), 700, (0.2, 1.0, 0.9), 1.5)
light('rimP', (3.0, 2.2, 3.6), 600, (1.0, 0.2, 0.6), 1.5)
light('top', (0.0, -1.0, 6.5), 120, (0.8, 0.8, 1.0), 2.5)
cam = bpy.data.cameras.new('cam'); cam.lens = 85; cam.sensor_width = 36; cam.sensor_height = 36; cam.sensor_fit = 'VERTICAL'
cam.dof.use_dof = True; cam.dof.focus_object = tgt; cam.dof.aperture_fstop = 4.0
co = bpy.data.objects.new('cam', cam); scene.collection.objects.link(co); scene.camera = co
co.location = P(0.9, 2.45, 6.2); cc = co.constraints.new('TRACK_TO'); cc.target = tgt; cc.track_axis = 'TRACK_NEGATIVE_Z'; cc.up_axis = 'UP_Y'
cam.sensor_width = 36

# world
w = bpy.data.worlds.new('w'); w.use_nodes = True; w.node_tree.nodes['Background'].inputs['Color'].default_value = (0.01, 0.006, 0.02, 1); w.node_tree.nodes['Background'].inputs['Strength'].default_value = 1.0
scene.world = w

# render settings
sc = scene; sc.render.engine = 'CYCLES'; cy = sc.cycles; cy.device = 'CPU'; cy.samples = SAMPLES; cy.use_adaptive_sampling = True; cy.adaptive_threshold = 0.02
cy.use_denoising = True; cy.denoiser = 'OPENIMAGEDENOISE'; cy.max_bounces = 6; cy.diffuse_bounces = 3; cy.glossy_bounces = 4; cy.transmission_bounces = 4
cy.sample_clamp_indirect = 8.0; cy.caustics_reflective = False; cy.caustics_refractive = False
sc.render.resolution_x = 1080; sc.render.resolution_y = 1920; sc.render.resolution_percentage = PCT; sc.render.threads_mode = 'AUTO'
sc.view_settings.view_transform = 'AgX'
try: sc.view_settings.look = 'AgX - Medium High Contrast'
except Exception as ex: print('look not set', ex)
import os
if os.environ.get('ENGINE_OVERRIDE') == 'EEVEE':
    sc.render.engine = 'BLENDER_EEVEE'
    try: sc.eevee.taa_render_samples = 32
    except Exception as ex: print('eevee samples', ex)
sc.render.image_settings.file_format = 'PNG'; sc.render.filepath = OUT
t0 = time.time(); bpy.ops.render.render(write_still=True); print('RENDER_SECONDS', round(time.time() - t0, 1), 'samples', SAMPLES, 'percent', PCT)
