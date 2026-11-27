"""Dex Hollow portrait in Blender (Cycles, CPU). Run:
  blender -b --factory-startup -P dex_portrait.py -- OUT.png SAMPLES PERCENT [EXPR]
Modelling is done in 'three-space' (x right, y up, z toward viewer) and converted to Blender (x, -z, y).
"""
import bpy, bmesh, math, random, sys, time
from mathutils import Vector

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = '/tmp/dex.png'; SAMPLES = 64; PCT = 100; EXPR = 'smile'; YAW = 0.0; CAMX = 0.0; CAMD = 6.9
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

def simple(name, color, rough=0.5, metal=0.0):
    m, nt, b = new_mat(name); setp(b, Base_Color=color, Roughness=rough, Metallic=metal); return m
m_skin = simple('skin', (0.46, 0.21, 0.11, 1), 0.5); m_skinD = simple('skinD', (0.36, 0.15, 0.08, 1), 0.55)
m_lipU = simple('lipU', (0.42, 0.10, 0.14, 1), 0.32); m_lipL = simple('lipL', (0.52, 0.14, 0.18, 1), 0.28)
m_mouth = simple('mouthIn', (0.07, 0.01, 0.02, 1), 0.7); m_teeth = simple('teeth', (0.9, 0.86, 0.8, 1), 0.25); m_tongue = simple('tongue', (0.5, 0.1, 0.14, 1), 0.5)
m_black = simple('black', (0.01, 0.008, 0.012, 1), 0.45); m_metal = simple('metal', (0.8, 0.82, 0.86, 1), 0.2, 1.0); m_white = simple('white', (0.9, 0.9, 0.88, 1), 0.5)
m_under = simple('undercut', (0.05, 0.03, 0.09, 1), 0.9); m_teal = simple('hairT', (0.1, 0.5, 0.5, 1), 0.35); m_pink = simple('hairP', (0.6, 0.1, 0.3, 1), 0.35)
m_brow = simple('brow', (0.003, 0.003, 0.005, 1), 0.3); m_lash = simple('lash', (0.005, 0.004, 0.006, 1), 0.4)
# eye texture: front-facing planar iris/pupil/sclera, so it exports as a normal image texture
def iris_image():
    N = 256; img = bpy.data.images.new('irisTex', N, N, alpha=True); px = []
    def lerp3(a, b, t): return [a[i] + (b[i] - a[i]) * t for i in range(3)]
    for j in range(N):
        for i in range(N):
            u, v = (i + 0.5) / N, (j + 0.5) / N; r = math.hypot(u - 0.5, v - 0.5) * 2
            if r < 0.2: c = (0.0, 0.0, 0.0)
            elif r < 0.24: c = lerp3((0, 0, 0), (0.05, 0.28, 0.85), (r - 0.2) / 0.04)
            elif r < 0.38: c = lerp3((0.05, 0.28, 0.85), (0.03, 0.18, 0.7), (r - 0.24) / 0.14)
            elif r < 0.5: c = lerp3((0.03, 0.18, 0.7), (0.01, 0.05, 0.3), (r - 0.38) / 0.12)
            elif r < 0.56: c = lerp3((0.01, 0.05, 0.3), (0.85, 0.82, 0.8), (r - 0.5) / 0.06)
            else: c = (0.88, 0.86, 0.85)
            px += [c[0], c[1], c[2], 1.0]
    img.pixels = px; img.pack(); return img
m_eye, nt, b = new_mat('eye'); setp(b, Roughness=0.05, Coat_Weight=1.0)
tx = nt.nodes.new('ShaderNodeTexImage'); tx.image = iris_image(); tx.interpolation = 'Linear'; tx.extension = 'CLIP'
nt.links.new(tx.outputs['Color'], b.inputs['Base Color'])
def uv_planar(ob, r=0.118):
    me = ob.data; uv = me.uv_layers.new(name='UV') if not me.uv_layers else me.uv_layers[0]
    for lp in me.loops:
        co = me.vertices[lp.vertex_index].co; uv.data[lp.index].uv = (0.5 + co.x / (2 * r), 0.5 + co.z / (2 * r))

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

# natural hairline: height of the hairline for each azimuth a (0 = front, +-pi/2 = ears, pi = nape)
HLPTS = [(0, 2.80), (30, 2.78), (50, 2.72), (64, 2.62), (78, 2.52), (92, 2.42), (112, 2.24), (140, 2.08), (180, 2.0)]
def hairline_y(a):
    d = abs(math.degrees(a)); y = HLPTS[-1][1]
    for (d0, y0), (d1, y1) in zip(HLPTS, HLPTS[1:]):
        if d <= d1: y = lerp(y0, y1, s01((d - d0) / (d1 - d0))); break
    return y + 0.012 * math.sin(a * 9) + 0.008 * math.sin(a * 17 + 1)
def head_pt(a, y):
    uy = (y - 2.38) / 0.58; r = math.sqrt(max(0.0, 1 - uy * uy)); kk = kOf(y)
    p = V3(0.6 * kk * r * math.sin(a), y, 0.56 * zf(uy) * r * math.cos(a)); n = V3(p.x / 0.36, (p.y - 2.38) / 0.34, p.z / 0.31).normalized(); return p, n

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
    if y3 > hairline_y(math.atan2(x3, z3)) + 0.03: keep.append(f)
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
E = EXPRS[EXPR]  # replaced per layer by the runner
def eye(s):
    x, y = s * 0.21, 2.4; z = surfZ(x, y) - 0.098
    ball = sphere('eye%d' % s, 0.118, (x, y, z), (1, 1, 1.1), m_eye, 64); uv_planar(ball)
    lidr = 0.122
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
# eyes are built per layer (see runner)


def eye_closed(s):
    x0, y0 = s * 0.21, 2.4; zs = surfZ(x0, y0)
    sphere('lidclosed%d' % s, 1.0, (x0, y0 + 0.01, zs - 0.012), (0.13, 0.03, 0.078), m_skin, 40)
    def dome(x, y): dx, dy = (x - x0) / 0.13, (y - (y0 + 0.01)) / 0.078; return zs - 0.012 + 0.03 * math.sqrt(max(0.0, 1 - dx * dx - dy * dy)) + 0.004
    pts = []
    for i in range(17):
        t = -1 + 2 * i / 16; x = x0 + t * 0.122; y = y0 - 0.028 * (1 - t * t) + 0.004; pts.append((x, y, dome(x, y)))
    outer = pts[-1] if s > 0 else pts[0]
    wing = (outer[0] + s * 0.055, outer[1] + 0.03, outer[2] - 0.004)
    line = (pts + [wing]) if s > 0 else ([wing] + pts)
    curve_obj('linerC%d' % s, [(line, [1.0] * len(line))], 0.0125, m_black, 'BEZIER', 4)
    lashes = []
    for k in range(9):
        p = pts[(7 + k) if s > 0 else (9 - k)]
        d = Vector((s * (0.25 + 0.04 * k), -0.9, 0.32)).normalized(); L = 0.05 + 0.025 * R.random(); p0 = Vector(p)
        lashes.append(([tuple(p0), tuple(p0 + d * L * 0.4), tuple(p0 + d * L * 0.8 + Vector((0, 0.01, 0.006))), tuple(p0 + d * L + Vector((0, 0.022, 0.012)))], [1, 0.8, 0.5, 0.15]))
    curve_obj('lashC%d' % s, lashes, 0.0058, m_lash, 'POLY', 2)

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
# mouth is built per layer

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
        curve_obj('brow%d' % i, spl, 0.0033, m_brow, 'BEZIER', 2)
# brows are built per layer

# ------------------------------------------------------------------ hair: messy spiky locks all over the head
# Each spike is a lock of 25-35 fine strands that twist around each other and converge to a feathered tip;
# plus a dense short under-layer, feathered baby hairs along a natural hairline, and a few flyaways.
HR = random.Random(11)
strands = {'a': [], 'b': []}      # long strand splines (spike locks)
under = {'a': [], 'b': []}
baby = {'a': [], 'b': []}
fly = {'a': [], 'b': []}
def basis(d):
    up = V3(0, 1, 0) if abs(d.y) < 0.9 else V3(1, 0, 0); u = d.cross(up).normalized(); return u, d.cross(u).normalized()
def kind_at(p): return 'a' if (math.sin(5.0 * p.x + 3.0 * p.y) + math.sin(4.0 * p.z - 2.0 * p.y + 1.0)) > 0 else 'b'
# scalp sample points, uniform over the area above the hairline (uniform in azimuth and height)
def scalp_sample(extra=0.0):
    while True:
        a_ = HR.uniform(-math.pi, math.pi); y = HR.uniform(1.97, 2.955)
        if y > hairline_y(a_) + extra: return a_, y
# ---- glossy black rockstar gel spikes: 20-30 separate rigid wedge-shaped clumps, wide base, one sharp tip, pointing up and outward
STYLE = argv[1] if len(argv) > 1 else 'A'
CFG = {
    'A': dict(n=26, dist=0.30, Lmin=0.42, Lmax=0.62, up=1.0, out=0.95, back=0.0, flat=0.55, Rb=(0.23, 0.28), bend=0.05, tall_top=0.16, alt=False),
    'B': dict(n=24, dist=0.31, Lmin=0.40, Lmax=0.80, up=1.0, out=0.40, back=0.8, flat=0.42, Rb=(0.23, 0.29), bend=0.16, tall_top=0.30, alt=False),
    'C': dict(n=28, dist=0.28, Lmin=0.34, Lmax=0.78, up=0.75, out=1.3, back=0.0, flat=0.62, Rb=(0.24, 0.30), bend=0.08, tall_top=0.24, alt=True),
}[STYLE]
spikes = []
tries = 0
def front_ok(a_, y): return abs(a_) > 1.2 or y > hairline_y(a_) + 0.34
while len(spikes) < CFG['n'] and tries < 80000:
    tries += 1; a_, y = scalp_sample(0.06); p, n = head_pt(a_, y)
    if not front_ok(a_, y): continue
    if all((p - q[0]).length > CFG['dist'] for q in spikes): spikes.append((p, n, a_, y))
spike_objs = []
HAIRCOL_S = {'a': ((0.006, 0.006, 0.011), (0.035, 0.038, 0.055)), 'b': ((0.006, 0.006, 0.011), (0.03, 0.034, 0.05))}
def sgn(x): return -1.0 if x < 0 else 1.0
def build_wedge(si, p, n):
    topness = max(0.0, n.y); nf = V3(n.x, n.y, min(n.z, 0.1) if n.y < 0.8 else n.z * 0.5)
    d = (nf * CFG['out'] + V3(0, CFG['up'], 0) + V3(0, 0, -CFG['back']) + V3(HR.uniform(-1, 1), HR.uniform(-0.25, 0.25), HR.uniform(-1, 1)) * 0.12)
    d.z = min(d.z, 0.12); d = d.normalized()
    L = lerp(CFG['Lmin'], CFG['Lmax'], HR.random())
    if CFG['alt'] and si % 2: L *= 0.7
    L += CFG['tall_top'] * topness
    Rb = HR.uniform(*CFG['Rb']); wax = V3(0, 1, 0).cross(nf)
    if wax.length < 0.2: wax = V3(1, 0, 0)
    wax = wax.normalized(); dep = d.cross(wax).normalized(); wax = dep.cross(d).normalized()
    bend = nf.normalized() * CFG['bend'] * L; K = 44; NT = 16
    bm2 = bmesh.new(); rings = []; thetas = {}
    for ti in range(NT + 1):
        t = ti / NT; c = p - d * 0.08 + d * (L * t + 0.08) + bend * (t * t)
        rw = Rb * (1 - t) ** 0.66 * (1 + 0.4 * math.exp(-t * 7.0)); rd = rw * CFG['flat'] * (1 - 0.15 * t); ring = []
        for k in range(K):
            th = 6.2832 * k / K; cs, sn = math.cos(th), math.sin(th)
            m = 1 + (0.022 * math.sin(26 * th + 2 * t) + 0.015 * math.sin(43 * th - 3 * t)) * (1 - t ** 2)
            pos = c + wax * (sgn(cs) * abs(cs) ** 0.85) * rw * m + dep * (sgn(sn) * abs(sn) ** 0.85) * rd * m
            thetas[(ti, k)] = th; ring.append(bm2.verts.new(P(*pos)))
        rings.append(ring)
    tipv = bm2.verts.new(P(*(p - d * 0.08 + d * (L + 0.08) + bend)))
    for ti in range(NT):
        for k in range(K): bm2.faces.new((rings[ti][k], rings[ti][(k + 1) % K], rings[ti + 1][(k + 1) % K], rings[ti + 1][k]))
    for k in range(K): bm2.faces.new((rings[NT][k], rings[NT][(k + 1) % K], tipv))
    me = bpy.data.meshes.new('wedge%d' % si); bm2.to_mesh(me); bm2.free()
    ca = me.color_attributes.new('Col', 'FLOAT_COLOR', 'POINT'); bs, tp = HAIRCOL_S['a']
    for i, vv in enumerate(me.vertices):
        if i < (NT + 1) * K: ti, k = divmod(i, K); th = thetas[(ti, k)]
        else: ti, k, th = NT, 0, 0.0
        t = ti / NT; streak = 0.6 + 0.8 * (math.sin(52 * th + si) * 0.5 + 0.5) ** 2
        ca.data[i].color = (lerp(bs[0], tp[0], t) * streak, lerp(bs[1], tp[1], t) * streak, lerp(bs[2], tp[2], t) * streak, 1.0)
    for pl in me.polygons: pl.use_smooth = True
    ob = bpy.data.objects.new('wedge%d' % si, me); scene.collection.objects.link(ob); return ob
for si, (p, n, a_, y) in enumerate(spikes): spike_objs.append(build_wedge(si, p, n))
for _ in range(4200):
    a_, y = scalp_sample(0.0); p, n = head_pt(a_, y); l = HR.uniform(0.06, 0.14)
    dd = (n + V3(0, 0.45, 0) + V3(HR.uniform(-1, 1), HR.uniform(-1, 1), HR.uniform(-1, 1)) * 0.3).normalized()
    pts = [tuple(p - n * 0.03), tuple(p + dd * l * 0.5), tuple(p + dd * l + V3(0, -0.01, 0))]
    under[kind_at(p)].append((pts, [1.0, 0.75, 0.15]))
for _ in range(1500):  # feathered baby hairs along the hairline, densest right at the edge, lying nearly flat
    a_ = HR.uniform(-math.pi * 0.97, math.pi * 0.97); dist = HR.expovariate(1 / 0.03)
    if dist > 0.12: continue
    y = hairline_y(a_) + dist; p, n = head_pt(a_, y); l = HR.uniform(0.03, 0.065)
    dd = (n * 0.3 + V3(0, 0.6, 0) + V3(HR.uniform(-1, 1), 0, HR.uniform(-1, 1)) * 0.25).normalized()
    pts = [tuple(p - n * 0.01), tuple(p + dd * l * 0.5 + n * 0.006), tuple(p + dd * l + n * 0.004)]
    baby[kind_at(p)].append((pts, [1.0, 0.7, 0.2]))
for _ in range(0):  # flyaways (removed: no wispy strands)
    a_, y = scalp_sample(0.12); p, n = head_pt(a_, y); l = HR.uniform(0.35, 0.7)
    dd = (n + V3(0, 0.5, 0) + V3(HR.uniform(-1, 1), HR.uniform(-1, 1), HR.uniform(-1, 1)) * 0.5).normalized(); u, v = basis(dd); curl = (u * HR.uniform(-1, 1) + v * HR.uniform(-1, 1)).normalized() * 0.25 * l
    pts = [tuple(p + dd * (l * t) + curl * (t * t) + V3(0, -0.05 * l * t ** 3, 0)) for t in (0, 0.25, 0.5, 0.75, 1.0)]
    fly[kind_at(p)].append((pts, [1.0, 0.85, 0.6, 0.35, 0.1]))
for kind, mat in (('a', m_pink), ('b', m_teal)):
    curve_obj('under' + kind, under[kind], 0.02, mat, 'POLY', 1)
    curve_obj('baby' + kind, baby[kind], 0.011, mat, 'POLY', 1)
    curve_obj('fly' + kind, fly[kind], 0.007, mat, 'BEZIER', 2)
for ob in scene.objects:
    if ob.type == 'CURVE' and (ob.name.startswith(('locks', 'under', 'baby', 'fly'))): ob.data.bevel_resolution = 1 if ob.name.startswith('locks') else 0


# ================================================================== export section
OUTP = argv[0] if argv else '/tmp/dex_head.glb'
for s_ in (-1, 1):
    sphere('ear', 0.1, (0.6 * s_, 2.36, 0), (0.7, 1.0, 0.5), m_skinD, 24); sphere('ring', 0.028, (0.615 * s_, 2.22, 0.01), (1, 1, 1), m_metal, 14)

def build_variant(name, fn):
    before = set(scene.objects); fn(); new = set(scene.objects) - before
    root = bpy.data.objects.new(name, None); scene.collection.objects.link(root)
    for ob in new:
        if ob.parent is None: ob.parent = root
    return root
def eyes_variant(lid, sq, closed):
    def f():
        globals()['E'] = {'lid': (lid, lid), 'squint': sq}; R.seed(5)
        if closed: eye_closed(-1); eye_closed(1)
        else: eye(-1); eye(1)
    return f
def brows_variant(b):
    def f(): globals()['E'] = {'brow': b}; R.seed(21); brows(globals()['E'])
    return f
def mouth_variant(p):
    def f(): mouth(dict(smile=p['smile'], open=p['open'], skew=p.get('skew', 0.0), width=p.get('width', 1.0)))
    return f
for n, lid, sq, cl in [("eyes_open", -0.45, 0.0, False), ("eyes_half", -0.12, 0.2, False), ("eyes_closed", 0.95, 0.3, True), ("eyes_wide", -0.9, 0.0, False), ("eyes_squint", -0.15, 0.55, False)]:
    build_variant(n, eyes_variant(lid, sq, cl))
for n, b in [("brows_flat", [0, 0, 0, 0]), ("brows_up", [0.05, 0.08, 0.05, 0.08]), ("brows_high", [0.13, 0.15, 0.13, 0.15]), ("brows_worried", [0.03, 0.7, 0.03, 0.7]),
             ("brows_smirk", [-0.005, -0.2, 0.05, 0.12]), ("brows_angry", [-0.03, -0.7, -0.03, -0.7])]:
    build_variant(n, brows_variant(b))
for n, p in [("mouth_smile", dict(smile=0.85, open=0.0)), ("mouth_closed_grin", dict(smile=1.0, open=0.0)), ("mouth_closed_worried", dict(smile=-0.35, open=0.0, skew=-0.2)),
             ("mouth_closed_smirk", dict(smile=0.55, open=0.0, skew=0.45)), ("mouth_A", dict(smile=0.5, open=0.8)), ("mouth_E", dict(smile=0.9, open=0.3, width=1.1)),
             ("mouth_O", dict(smile=0.1, open=0.55, width=0.55)), ("mouth_Obig", dict(smile=-0.05, open=0.8, width=0.6)), ("mouth_shout", dict(smile=0.3, open=1.0, width=1.12)),
             ("mouth_grin_open", dict(smile=1.0, open=0.55))]:
    build_variant(n, mouth_variant(p))

# hair: convert curves to meshes, bake the base->tip colour ramp into vertex colours, join into one mesh
m_hair, nt_, b_ = new_mat('hair'); setp(b_, Roughness=0.2)
vc = nt_.nodes.new('ShaderNodeVertexColor'); vc.layer_name = 'Col'; nt_.links.new(vc.outputs['Color'], b_.inputs['Base Color'])
HAIRCOL = {'a': ((0.004, 0.004, 0.008), (0.03, 0.032, 0.046)), 'b': ((0.004, 0.004, 0.008), (0.028, 0.03, 0.044))}
hair_objs = []
for ob in [o for o in scene.objects if o.type == 'CURVE' and o.name.startswith(('under', 'baby', 'fly'))]:
    kind = ob.name[-1]; bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True); bpy.context.view_layer.objects.active = ob
    bpy.ops.object.convert(target='MESH'); me = ob.data
    ca = me.color_attributes.new('Col', 'FLOAT_COLOR', 'POINT'); base, tip = HAIRCOL[kind]
    for i, v in enumerate(me.vertices):
        d = (v.co - Vector((0, 0.05, 2.47))).length; t = min(1.0, max(0.0, (d - 0.55) / 0.7)); lum = 0.8 + 0.4 * (math.sin(v.co.x * 61) * math.sin(v.co.z * 53) * 0.5 + 0.5)
        ca.data[i].color = (lerp(base[0], tip[0], t) * lum, lerp(base[1], tip[1], t) * lum, lerp(base[2], tip[2], t) * lum, 1.0)
    me.materials.clear(); me.materials.append(m_hair); hair_objs.append(ob)
for ob in spike_objs: ob.data.materials.clear(); ob.data.materials.append(m_hair); hair_objs.append(ob)
bpy.ops.object.select_all(action='DESELECT')
for ob in hair_objs: ob.select_set(True)
bpy.context.view_layer.objects.active = hair_objs[0]; bpy.ops.object.join(); bpy.context.active_object.name = 'hair'
print('HAIR VERTS', len(bpy.data.objects['hair'].data.vertices))
tot = sum(len(o.data.vertices) for o in scene.objects if o.type == 'MESH'); print('TOTAL MESH VERTS', tot)

bpy.ops.object.select_all(action='DESELECT')
props = bpy.ops.export_scene.gltf.get_rna_type().properties.keys()
kw = dict(filepath=OUTP, export_format='GLB', export_apply=True, export_yup=True, export_cameras=False, export_lights=False)
for k, v in (('export_vertex_color', 'ACTIVE'), ('export_active_vertex_color_when_no_material', True), ('export_all_vertex_colors', True)):
    if k in props: kw[k] = v
bpy.ops.export_scene.gltf(**kw); print('EXPORTED', OUTP)
