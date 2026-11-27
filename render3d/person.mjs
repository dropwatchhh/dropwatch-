// Dex Hollow v2: original neon-punk rockstar, rigged. three.js, y up, faces +z.
// Rig: chest/neck/head, shoulders/elbows/wrists/fingers, hips/knees/ankles; expression + pose API.
import * as THREE from 'three';
import { buildJacket } from './jacket.mjs';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';

const D = Math.PI / 180;
const S01 = t => { t = Math.min(1, Math.max(0, t)); return t * t * (3 - 2 * t); };
const lerp = (a, b, t) => a + (b - a) * t;


function rng(seed) { let a = seed; return () => { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
function canvasTex(size, draw, repeat = [1, 1]) {
  const c = document.createElement('canvas'); c.width = c.height = size; const g = c.getContext('2d'); draw(g, size);
  const t = new THREE.CanvasTexture(c); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(...repeat); t.anisotropy = 4; return t;
}
const R0 = rng(99);
const skinBump = canvasTex(512, (g, s) => { g.fillStyle = '#808080'; g.fillRect(0, 0, s, s);
  for (let i = 0; i < 12000; i++) { const v = R0() < 0.5 ? 30 : 225; g.fillStyle = `rgba(${v},${v},${v},${0.08 + 0.18 * R0()})`; g.beginPath(); g.arc(R0() * s, R0() * s, 0.5 + R0() * 1.3, 0, 6.3); g.fill(); } }, [5, 4]);
const leatherBump = canvasTex(512, (g, s) => { g.fillStyle = '#808080'; g.fillRect(0, 0, s, s);
  for (let i = 0; i < 16000; i++) { const v = R0() < 0.5 ? 50 : 210; g.fillStyle = `rgba(${v},${v},${v},${0.1 + 0.2 * R0()})`; g.fillRect(R0() * s, R0() * s, 1 + R0() * 2, 1 + R0() * 2); }
  for (let i = 0; i < 7; i++) { const y = R0() * s, x0 = R0() * s * 0.6, w = 60 + R0() * 150, wob = (R0() - 0.5) * 10;
    for (const [dy, col] of [[0, 'rgba(20,20,20,0.7)'], [3, 'rgba(235,235,235,0.5)']]) { g.strokeStyle = col; g.lineWidth = 2 + R0() * 3; g.beginPath(); g.moveTo(x0, y + dy); g.quadraticCurveTo(x0 + w / 2, y + dy + wob, x0 + w, y + dy); g.stroke(); } } }, [4, 3]);

const phys = (c, o = {}) => new THREE.MeshPhysicalMaterial({ color: c, roughness: 0.4, ...o });
const std = (c, o = {}) => new THREE.MeshStandardMaterial({ color: c, roughness: 0.6, ...o });
export const MBASE = {
  skin: phys(0xb78262, { roughness: 0.5, sheen: 0.5, sheenColor: new THREE.Color(0xff9a80), sheenRoughness: 0.4, bumpMap: skinBump, bumpScale: 0.8 }),
  skinD: std(0x9a6a4f),
  leather: phys(0x1d1d25, { roughness: 0.36, clearcoat: 0.6, clearcoatRoughness: 0.35, side: THREE.DoubleSide, bumpMap: leatherBump, bumpScale: 2.2 }),
  leatherD: phys(0x121218, { roughness: 0.38, clearcoat: 0.6 }),
  leatherS: phys(0x1d1d25, { roughness: 0.36, clearcoat: 0.6, clearcoatRoughness: 0.35, side: THREE.DoubleSide, bumpMap: leatherBump, bumpScale: 1.1 }),
  lipU: phys(0x9a3a4c, { roughness: 0.35, clearcoat: 0.4, side: THREE.DoubleSide }), lipL: phys(0xb9505f, { roughness: 0.3, clearcoat: 0.5, side: THREE.DoubleSide }),
  brow: new THREE.MeshStandardMaterial({ color: 0x1a1016, roughness: 0.8, side: THREE.DoubleSide }),
  cornea: new THREE.MeshPhysicalMaterial({ color: 0xffffff, transparent: true, opacity: 0.16, roughness: 0, clearcoat: 1, depthWrite: false }),
  teethM: new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.3, side: THREE.DoubleSide }),
  tee: std(0xe8284f, { roughness: 0.85, side: THREE.DoubleSide }),
  jeans: std(0x262833, { roughness: 0.88 }),
  boot: phys(0x17171c, { roughness: 0.42, clearcoat: 0.55 }),
  sole: std(0xd8d2c4, { roughness: 0.8 }),
  metal: std(0xdfe4ec, { metalness: 1, roughness: 0.22 }),
  white: std(0xfffdf8, { roughness: 0.3 }),
  black: std(0x15111c, { roughness: 0.5, side: THREE.DoubleSide }),
  iris: phys(0x3f9bff, { roughness: 0.2, clearcoat: 1 }),
  limbal: std(0x1a4fa8, { roughness: 0.3 }),
  lip: std(0x6a2230, { roughness: 0.45 }),
  mouthIn: new THREE.MeshStandardMaterial({ color: 0x3a0f18, roughness: 0.7, side: THREE.DoubleSide }),
  tongue: std(0xd8607a, { roughness: 0.5 }),
  blush: new THREE.MeshBasicMaterial({ color: 0xff6f84, transparent: true, opacity: 0.55, depthWrite: false, alphaMap: canvasTex(128, (g, s) => { const r = g.createRadialGradient(s / 2, s / 2, 0, s / 2, s / 2, s / 2); r.addColorStop(0, '#fff'); r.addColorStop(0.5, '#555'); r.addColorStop(1, '#000'); g.fillStyle = r; g.fillRect(0, 0, s, s); }) }),
  wrist: std(0xff2fa0, { roughness: 0.7 }),
  hair: new THREE.MeshPhysicalMaterial({ vertexColors: true, roughness: 0.28, clearcoat: 0.9, clearcoatRoughness: 0.2 }),
  pink: phys(0xff2fa0, { roughness: 0.3, clearcoat: 0.8 }),
  teal: phys(0x1fe6d2, { roughness: 0.3, clearcoat: 0.8 }),
};

export const M = MBASE;
// ---------- geometry helpers
function ell(mat, rx, ry, rz, x = 0, y = 0, z = 0, seg = 40) {
  const m = new THREE.Mesh(new THREE.SphereGeometry(1, seg, Math.max(8, Math.floor(seg * 0.7))), mat);
  m.scale.set(rx, ry, rz); m.position.set(x, y, z); return m;
}
function rbox(mat, w, h, d, x, y, z, r = 0.03) {
  const m = new THREE.Mesh(new RoundedBoxGeometry(w, h, d, 5, r), mat); m.position.set(x, y, z); return m;
}
function tube(mat, pts, r, seg = 40, closed = false) {
  return new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts.map(p => new THREE.Vector3(...p)), closed), seg, r, 8, closed), mat);
}
function pivot(parent, x = 0, y = 0, z = 0) { const g = new THREE.Bone(); g.position.set(x, y, z); parent.add(g); return g; }

// tapered tube with vertex colours base -> tip
function taperGeo(points, r0, cBase, cTip, radial = 6, segs = 14) {
  const curve = new THREE.CatmullRomCurve3(points.map(p => new THREE.Vector3(...p)));
  const fr = curve.computeFrenetFrames(segs, false);
  const pos = [], col = [], idx = [];
  const cb = new THREE.Color(cBase), ct = new THREE.Color(cTip), c = new THREE.Color();
  for (let i = 0; i <= segs; i++) {
    const t = i / segs, P = curve.getPointAt(t), r = r0 * Math.pow(1 - t, 0.85) + 0.0012;
    c.copy(cb).lerp(ct, Math.pow(t, 0.8));
    for (let j = 0; j <= radial; j++) {
      const v = j / radial * Math.PI * 2, n = fr.normals[i].clone().multiplyScalar(Math.cos(v)).addScaledVector(fr.binormals[i], Math.sin(v));
      pos.push(P.x + n.x * r, P.y + n.y * r, P.z + n.z * r); col.push(c.r, c.g, c.b);
    }
  }
  for (let i = 0; i < segs; i++) for (let j = 0; j < radial; j++) { const a = i * (radial + 1) + j, b = a + radial + 1; idx.push(a, b, a + 1, b, b + 1, a + 1); }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); g.setAttribute('color', new THREE.Float32BufferAttribute(col, 3)); g.setIndex(idx); g.computeVertexNormals();
  return g;
}

// ---------- head shape: ellipsoid that tapers to a defined chin
const HEAD = { cy: 2.38, rx: 0.6, ry: 0.58, rz: 0.56, taper: 0.15 };
const zf = u => u < 0 ? 1 + 0.06 * S01(-u) : 1;
const kOf = y => { const u = (y - HEAD.cy) / HEAD.ry; return u < 0 ? 1 - HEAD.taper * S01(-u) : 1; };
export const faceZ = (x, y) => { const u = (y - HEAD.cy) / HEAD.ry, k = kOf(y); return HEAD.rz * zf(u) * Math.sqrt(Math.max(0.01, 1 - (x / (HEAD.rx * k)) ** 2 - u * u)); };

function headMesh() {
  const g = new THREE.SphereGeometry(1, 96, 64), p = g.attributes.position;
  for (let i = 0; i < p.count; i++) {
    const ux = p.getX(i), uy = p.getY(i), uz = p.getZ(i);
    const y = uy * HEAD.ry + HEAD.cy, k = kOf(y);
    p.setXYZ(i, ux * HEAD.rx * k, y, uz * HEAD.rz * zf(uy));
  }
  g.computeVertexNormals();
  return new THREE.Mesh(g, M.skin);
}

// ---------- the rig
export function buildPerson(opts = {}) {
  const M = {}; for (const k of Object.keys(MBASE)) M[k] = MBASE[k].clone(); for (const [k, v] of Object.entries(opts.mats || {})) M[k].color.set(v);
  const PUNK = opts.punk !== false;
  if (opts.fabric) for (const k of ['leather', 'leatherS', 'leatherD']) { M[k].clearcoat = 0; M[k].roughness = 0.85; M[k].bumpScale = 0; }
  const root = new THREE.Group();
  const rig = { root, j: {} };
  const all = o => o.traverse(m => { if (m.isMesh) { m.castShadow = true; m.receiveShadow = true; } });

  // legs
  // adult proportions: small head (HS), long legs, tall torso (YS), long arms (UA/FA)
  const HS = opts.headScale ?? 0.5, YS = opts.torsoStretch ?? 1.85, XS = 1.12, UA = 0.68, FA = 0.58;
  const L1 = 0.9, L2 = 0.85, HIPY = 2.0, WAIST = HIPY + 0.05;
  const hips = pivot(root, 0, HIPY - 1.12, 0);
  hips.add(ell(M.jeans, 0.43, 0.22, 0.29, 0, 1.12, 0), rbox(M.black, 0.8, 0.1, 0.58, 0, 1.1, 0, 0.03), rbox(M.metal, 0.13, 0.1, 0.04, 0, 1.1, 0.3, 0.012));
  if (PUNK) hips.add(tube(M.metal, [[0.3, 1.1, 0.26], [0.42, 0.98, 0.26], [0.4, 0.86, 0.2], [0.31, 0.8, 0.16]], 0.011));
  for (const s of [-1, 1]) {
    const hip = pivot(root, s * 0.2, HIPY, 0);
    hip.add(ell(M.jeans, 0.21, 0.21, 0.21, 0, 0, 0));
    const th = new THREE.Mesh(new THREE.CylinderGeometry(0.16, 0.145, L1, 28), M.jeans); th.position.y = -L1 / 2; th.scale.set(1.3, 1, 1.3); hip.add(th);
    const knee = pivot(hip, 0, -L1, 0); knee.add(ell(M.jeans, 0.175, 0.175, 0.175, 0, 0, 0));
    const shin = new THREE.Mesh(new THREE.CylinderGeometry(0.145, 0.13, L2, 28), M.jeans); shin.position.y = -L2 / 2; shin.scale.set(1.2, 1, 1.2); knee.add(shin);
    // rips (move with the limb)
    const rip = (par, x, y, rx, ry, rot) => { const r = ell(M.skinD, rx, ry, 0.03, x, y, 0.138, 24); r.rotation.z = rot; par.add(r);
      for (let i = -1; i <= 1; i++) { const t = rbox(M.white, 0.013, ry * 1.6, 0.013, x + i * rx * 0.45, y, 0.162, 0.005); t.rotation.z = rot; par.add(t); } };
    if (PUNK) if (s < 0) { rip(knee, 0, 0.0, 0.085, 0.065, 0); rip(hip, -0.02, -0.14, 0.05, 0.035, -0.35); } else { rip(hip, 0.02, -0.2, 0.07, 0.05, 0.1); }
    // boots
    const sh = new THREE.Mesh(new THREE.CylinderGeometry(0.175, 0.185, 0.34, 32), M.boot); sh.position.y = -L2 + 0.17; if (!opts.sneakers) knee.add(sh);
    if (PUNK) for (const yy of [-L2 + 0.1, -L2 + 0.26]) knee.add(rbox(M.metal, 0.3, 0.035, 0.3, 0, yy, 0, 0.015));
    for (const yy of [0.045, -0.03]) { const t = new THREE.Mesh(new THREE.TorusGeometry(0.15, 0.011, 8, 28), M.jeansD ?? M.black); t.rotation.x = Math.PI / 2; t.position.y = yy; knee.add(t); }   // knee wrinkles
    if (PUNK) for (let k = 0; k < 5; k++) { const y0 = -L2 + 0.05 + k * 0.058; for (const sg of [-1, 1]) knee.add(tube(std(0xe9e1cf, { roughness: 0.8 }), [[-sg * 0.075, y0, 0.178], [0, y0 + 0.03, 0.188], [sg * 0.075, y0 + 0.058, 0.178]], 0.008, 10)); }   // boot laces
    const ank = pivot(knee, 0, -L2, 0);
    ank.add(rbox(M.boot, 0.36, 0.22, 0.58, 0, -0.1, 0.1, 0.09), rbox(M.sole, 0.4, 0.07, 0.62, 0, -0.185, 0.1, 0.03), rbox(M.metal, 0.12, 0.03, 0.05, 0, -0.04, 0.31, 0.012));
    rig.j[s < 0 ? 'legL' : 'legR'] = { hip, knee, ank, s };
  }

  // ---------- chest (spine pivot at the waist)
  const chest = pivot(root, 0, WAIST, 0); const ci = pivot(chest, 0, -1.15 * YS, 0); ci.scale.set(XS, YS, XS); rig.j.chest = chest;
  // tee body
  const teeProf = [[0.43, 0], [0.43, 0.2], [0.4, 0.42], [0.36, 0.62], [0.27, 0.74], [0.17, 0.8]].map(([r, y]) => new THREE.Vector2(r * 0.93, y));
  const tee = new THREE.Mesh(new THREE.LatheGeometry(teeProf, 40), M.tee); { const tp = tee.geometry.attributes.position; for (let i = 0; i < tp.count; i++) { const y = tp.getY(i), k = Math.min(1, Math.max(0, (y - 0.5) / 0.28)), sm = k * k * (3 - 2 * k); tp.setX(i, tp.getX(i) * (0.88 + 0.1 * sm)); tp.setZ(i, tp.getZ(i) * (0.5 + 0.26 * sm)); } tee.geometry.computeVertexNormals(); } tee.position.y = 1.04; ci.add(tee);
  const chev = new THREE.Shape(); chev.moveTo(-0.075, -0.02); chev.lineTo(0, 0.075); chev.lineTo(0.075, -0.02); chev.lineTo(0.048, -0.02); chev.lineTo(0, 0.038); chev.lineTo(-0.048, -0.02); chev.closePath();
  const ch = new THREE.Mesh(new THREE.ExtrudeGeometry(chev, { depth: 0.012, bevelEnabled: false }), M.white); ch.position.set(0, 1.46, 0.262); if (PUNK) ci.add(ch);
  // jacket: tailored lathe, flared hem, open front gap
  const jProf = [[0.47, 0], [0.465, 0.05], [0.43, 0.24], [0.42, 0.4], [0.43, 0.55], [0.4, 0.66], [0.3, 0.75], [0.215, 0.8], [0.2, 0.84]].map(([r, y]) => new THREE.Vector2(r, y));
  const GAP = 0.5;
  const jg = new THREE.LatheGeometry(jProf, 64, GAP, Math.PI * 2 - 2 * GAP); jg.scale(1, 1, 0.74);
  const jacket = new THREE.Mesh(jg, M.leather); jacket.position.y = 1.04; ci.add(jacket);
  // front edges + lapels
  const lapShape = new THREE.Shape(); lapShape.moveTo(0, 0); lapShape.lineTo(0.2, 0.06); lapShape.lineTo(0.24, -0.1); lapShape.lineTo(0.08, -0.42); lapShape.lineTo(0, -0.42); lapShape.closePath();
  for (const s of [-1, 1]) {
    const lap = new THREE.Mesh(new THREE.ExtrudeGeometry(lapShape, { depth: 0.03, bevelEnabled: true, bevelThickness: 0.012, bevelSize: 0.012, bevelSegments: 2 }), M.leatherS);
    lap.scale.x = s; lap.position.set(s * 0.065, 1.84, 0.255); lap.rotation.y = -s * 0.5; lap.rotation.z = s * 0.14; ci.add(lap);
    if (PUNK) for (let i = 0; i < 5; i++) ci.add(ell(M.metal, 0.02, 0.02, 0.02, s * (0.2 + i * 0.002 - 0.0) + s * 0.0, 1.88 - i * 0.075, 0.3 + 0.0, 12));
    // front placket band (jacket edge)
    const pk = rbox(M.leatherS, 0.06, 0.78, 0.045, s * 0.255, 1.44, 0.305, 0.02); pk.rotation.z = -s * 0.05; pk.rotation.y = -s * 0.5; ci.add(pk);
    // diagonal zip pockets
    const pkt = rbox(M.leatherS, 0.17, 0.05, 0.03, s * 0.31, 1.23, 0.285, 0.015); pkt.rotation.z = -s * 0.35; pkt.rotation.y = -s * 0.8; ci.add(pkt);
    const zp = rbox(M.metal, 0.15, 0.012, 0.012, s * 0.31, 1.235, 0.3, 0.004); zp.rotation.z = -s * 0.35; zp.rotation.y = -s * 0.8; ci.add(zp);
  }
  // collar (popped), back patch
  const collar = new THREE.Mesh(new THREE.CylinderGeometry(0.255, 0.2, 0.14, 40, 1, true, GAP, Math.PI * 2 - 2 * GAP), M.leather); collar.scale.z = 0.8; collar.position.set(0, 1.9, -0.01); ci.add(collar);
  const bp = new THREE.Mesh(new THREE.CylinderGeometry(0.19, 0.19, 0.03, 40), M.pink); bp.rotation.x = Math.PI / 2; bp.position.set(0, 1.5, -0.318); if (PUNK) ci.add(bp);
  const st = new THREE.Shape(); for (let i = 0; i < 10; i++) { const r = i % 2 ? 0.065 : 0.15, a = Math.PI / 2 + i * Math.PI / 5; i ? st.lineTo(Math.cos(a) * r, Math.sin(a) * r) : st.moveTo(Math.cos(a) * r, Math.sin(a) * r); } st.closePath();
  const star = new THREE.Mesh(new THREE.ExtrudeGeometry(st, { depth: 0.02, bevelEnabled: false }), M.teal); star.rotation.y = Math.PI; star.position.set(0, 1.5, -0.328); if (PUNK) ci.add(star);
  const stitch = new THREE.Mesh(new THREE.TorusGeometry(0.17, 0.008, 8, 40), M.white); stitch.position.set(0, 1.5, -0.336); if (PUNK) ci.add(stitch);
  if (PUNK) for (const s of [-1, 1]) for (let i = 0; i < 3; i++) ci.add(ell(M.metal, 0.02, 0.02, 0.02, s * (0.37 + i * 0.012), 1.76 - i * 0.02, 0.06 - i * 0.07, 12));

  // ---------- arms
  const arms = {};
  for (const s of [-1, 1]) {
    const sh = pivot(chest, s * 0.5, (1.68 - 1.15) * YS, 0.0);
    sh.add(ell(M.leatherS, 0.15, 0.15, 0.15, 0, 0, 0, 28));
    const up = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.108, UA, 28, 4), M.leatherS); up.position.y = -UA / 2; up.scale.set(1.25, 1, 1.25); sh.add(up);
    const el = pivot(sh, 0, -UA, 0); el.add(ell(M.leatherS, 0.134, 0.134, 0.134, 0, 0, 0, 28));
    const fo = new THREE.Mesh(new THREE.CylinderGeometry(0.108, 0.097, FA, 28, 4), M.leatherS); fo.position.y = -FA / 2; fo.scale.set(1.25, 1, 1.25); el.add(fo);
    for (const [yy, rr] of [[0.07, 0.112], [0.035, 0.115], [-0.04, 0.104], [-0.075, 0.1]]) { const t = new THREE.Mesh(new THREE.TorusGeometry(rr, 0.012, 8, 28), M.leatherD); t.rotation.x = Math.PI / 2; t.position.y = yy; t.scale.set(1, 1, 0.8); el.add(t); }   // elbow folds
    for (const yy of [-0.05, -0.1]) { const t = new THREE.Mesh(new THREE.TorusGeometry(0.115, 0.01, 8, 28), M.leatherD); t.rotation.x = Math.PI / 2; t.position.y = yy; sh.add(t); }   // shoulder folds
    if (PUNK) { const epa = rbox(M.leatherD, 0.2, 0.05, 0.16, 0, 0.1, 0, 0.02); epa.rotation.z = s * 0.35; sh.add(epa); for (let k = 0; k < 2; k++) sh.add(ell(M.metal, 0.018, 0.018, 0.018, s * (0.02 + k * 0.05), 0.14 - k * 0.012, 0.0, 12)); }
    const wr = pivot(el, 0, -FA, 0);
    wr.add(new THREE.Mesh(new THREE.CylinderGeometry(0.118, 0.123, 0.09, 24), M.leatherD)); wr.children[0].position.y = 0.04;
    if (s > 0) { const bd = new THREE.Mesh(new THREE.TorusGeometry(0.1, 0.028, 10, 24), M.wrist); bd.rotation.x = Math.PI / 2; bd.position.y = -0.03; wr.add(bd); }
    // hand: big rounded palm, 4 two-joint fingers with knuckle spheres, 2-joint thumb; optional hand-held mic prop
    const hg = pivot(wr, 0, 0, 0); hg.scale.setScalar(1.42);
    hg.add(ell(M.skin, 0.064, 0.092, 0.092, 0, -0.105, 0, 28));
    hg.add(ell(M.skin, 0.05, 0.05, 0.07, -s * 0.03, -0.045, 0, 20));                 // wrist / heel of the hand
    const fingers = [];
    const zs = [0.064, 0.022, -0.022, -0.062], lens = [0.098, 0.108, 0.1, 0.08], rad = [0.029, 0.03, 0.028, 0.025];  // index, middle, ring, pinky (front to back)
    zs.forEach((z, i) => {
      const f1 = pivot(hg, -s * 0.012, -0.178, z); f1.add(ell(M.skin, rad[i] * 1.05, rad[i] * 1.05, rad[i] * 1.05, 0, 0, 0, 14));
      const c1 = new THREE.Mesh(new THREE.CapsuleGeometry(rad[i], lens[i] - rad[i] * 2, 8, 14), M.skin); c1.position.y = -lens[i] / 2; f1.add(c1);
      const f2 = pivot(f1, 0, -lens[i], 0); f2.add(ell(M.skin, rad[i] * 0.95, rad[i] * 0.95, rad[i] * 0.95, 0, 0, 0, 14));
      const l2 = lens[i] * 0.78, c2 = new THREE.Mesh(new THREE.CapsuleGeometry(rad[i] * 0.92, l2 - rad[i] * 1.84, 8, 14), M.skin); c2.position.y = -l2 / 2; f2.add(c2);
      fingers.push([f1, f2]);
    });
    const th1 = pivot(hg, -s * 0.058, -0.085, 0.075); th1.rotation.x = -0.2; th1.add(ell(M.skin, 0.036, 0.036, 0.036, 0, 0, 0, 14));
    const t1 = new THREE.Mesh(new THREE.CapsuleGeometry(0.033, 0.05, 8, 14), M.skin); t1.position.y = -0.045; th1.add(t1);
    const th2 = pivot(th1, 0, -0.09, 0); th2.add(ell(M.skin, 0.031, 0.031, 0.031, 0, 0, 0, 14));
    const t2 = new THREE.Mesh(new THREE.CapsuleGeometry(0.03, 0.04, 8, 14), M.skin); t2.position.y = -0.04; th2.add(t2);
    // hand-held microphone (visible only when the pose asks for it): handle runs front-to-back through the curled fingers
    const prop = new THREE.Group(); prop.visible = false;
    const handle = new THREE.Mesh(new THREE.CylinderGeometry(0.036, 0.04, 0.4, 20), std(0x23222b, { metalness: 0.6, roughness: 0.35 })); handle.rotation.x = Math.PI / 2; prop.add(handle);
    const mhead = new THREE.Mesh(new THREE.SphereGeometry(0.1, 24, 18), std(0x9ea3ad, { metalness: 0.9, roughness: 0.25 })); mhead.position.z = 0.27; prop.add(mhead);
    const mring = new THREE.Mesh(new THREE.TorusGeometry(0.1, 0.012, 8, 24), std(0xd8dbe2, { metalness: 1, roughness: 0.2 })); mring.position.z = 0.19; prop.add(mring);
    prop.position.set(-s * 0.07, -0.205, 0.0); hg.add(prop);
    arms[s < 0 ? 'L' : 'R'] = { sh, el, wr, fingers, th: [th1, th2], s, prop };
  }
  rig.j.arms = arms;
  // ---------- jacket detail: seams, diagonal zip, chest pocket, belly folds, shoulder and hem stitching
  if (PUNK) { const seam = (pts, r = 0.008, m = M.leatherD) => ci.add(tube(m, pts, r, 20));
    for (const s of [-1, 1]) {
      seam([[s * 0.2, 1.87, -0.03], [s * 0.3, 1.82, -0.03], [s * 0.4, 1.74, -0.03]]);                                   // shoulder seams
      seam([[s * 0.46, 1.08, 0.0], [s * 0.42, 1.3, 0.0], [s * 0.43, 1.5, 0.0], [s * 0.4, 1.7, 0.0]]);                   // side seams
      seam([[s * 0.36, 1.2, 0.21], [s * 0.3, 1.25, 0.28], [s * 0.22, 1.22, 0.31]], 0.01);                               // belly folds
      seam([[s * 0.38, 1.33, 0.19], [s * 0.31, 1.37, 0.27], [s * 0.24, 1.35, 0.3]], 0.008);
      seam([[s * 0.4, 1.46, 0.15], [s * 0.34, 1.5, 0.24]], 0.007);
    }
    seam([[-0.07, 1.74, 0.322], [-0.18, 1.56, 0.335], [-0.3, 1.38, 0.33]], 0.011, M.metal);                           // asymmetric biker zip
    for (let k = 0; k < 9; k++) { const t = k / 8; ci.add(ell(M.metal, 0.014, 0.014, 0.014, lerp(-0.07, -0.3, t), lerp(1.74, 1.38, t), 0.338 - 0.02 * Math.sin(t * Math.PI) * 0 + 0.0, 8)); }
    const pocket = rbox(M.leatherD, 0.18, 0.1, 0.03, 0.24, 1.56, 0.335, 0.02); pocket.rotation.z = -0.12; ci.add(pocket); ci.add(ell(M.metal, 0.02, 0.02, 0.02, 0.24, 1.56, 0.355, 10));
    seam([[0.15, 1.6, 0.34], [0.33, 1.56, 0.34]], 0.006, M.black);
    seam([[-0.42, 1.12, 0.14], [-0.2, 1.08, 0.3], [0.0, 1.07, 0.31], [0.2, 1.08, 0.3], [0.42, 1.12, 0.14]], 0.007, M.black);  // hem stitching
  }

  // ---------- neck + head (pivot at the neck base)
  const neckP = pivot(chest, 0, (1.88 - 1.15) * YS, 0.02); const hi = pivot(neckP, 0, -1.88 * HS, -0.02 * HS); hi.scale.setScalar(HS); rig.j.neck = neckP;
  ci.add(new THREE.Mesh(new THREE.CylinderGeometry(0.13, 0.15, 0.22, 24), M.skinD)); ci.children[ci.children.length - 1].position.set(0, 1.9, 0.02);
  rig.headInner = hi;
  rig.attachHead = (scene3d) => { hi.add(scene3d); rig.headRoot = scene3d; };
  all(root);

  // ---------- style extras: bowling-jacket stripes + pearls (Nana Dot)
  if (opts.bowling) {
    const cream = std(0xf4ead4, { roughness: 0.7 });
    for (const k of ['L', 'R']) { const a = arms[k]; for (const yy of [-0.12, -0.17]) { const t = new THREE.Mesh(new THREE.TorusGeometry(0.1, 0.014, 8, 28), cream); t.rotation.x = Math.PI / 2; t.position.y = yy; a.el.add(t); } }
    const band = new THREE.Mesh(new THREE.TorusGeometry(0.46, 0.022, 10, 56), cream); band.rotation.x = Math.PI / 2; band.scale.y = 0.74; band.position.y = 1.06; ci.add(band);
    const col2 = new THREE.Mesh(new THREE.TorusGeometry(0.22, 0.02, 8, 40), cream); col2.rotation.x = Math.PI / 2; col2.scale.y = 0.8; col2.position.set(0, 1.93, 0.0); ci.add(col2);
    const patch = ell(cream, 0.07, 0.05, 0.015, -0.24, 1.55, 0.33, 16); ci.add(patch);
  }
  if (opts.pearls) { for (let i = 0; i < 26; i++) { const a = i / 26 * Math.PI * 2; ci.add(ell(std(0xf3efe6, { roughness: 0.25 }), 0.022, 0.022, 0.022, Math.sin(a) * 0.17, 1.88, Math.cos(a) * 0.17 * 0.9 + 0.02, 10)); } }
  if (opts.jacketV2 !== false) {   // replace the old tube/lathe jacket by the skinned fitted jacket
    const hide = new Set([M.leather, M.leatherS, M.leatherD, M.metal, M.pink, M.teal, M.black]);
    for (const top of [ci, arms.L.sh, arms.R.sh]) top.traverse(o => { if (!o.isMesh) return; const m = o.material; if (hide.has(m) || (m === M.white && o !== ch) || (m.color && m.color.getHex() === 0xf4ead4)) o.visible = false; });
    hips.children[0].scale.x *= 0.9; hips.children[0].scale.z *= 0.8;
    hips.children.slice(1).forEach(o => { o.visible = false; });   // belt, buckle and chain sit under the jacket
    for (const k of ['L', 'R']) { const w = arms[k].wr; const fa = new THREE.Mesh(new THREE.CylinderGeometry(0.082, 0.092, 0.16, 20), M.skin); fa.position.y = -0.03; w.add(fa); const wm = new THREE.Mesh(new THREE.SphereGeometry(0.085, 18, 12), M.skin); wm.scale.set(1, 0.7, 1); wm.position.y = -0.1; w.add(wm); }
    root.updateMatrixWorld(true);
    const J = buildJacket(rig, { bones: [chest, arms.L.sh, arms.L.el, arms.R.sh, arms.R.el] }, M, { punk: PUNK, lapels: opts.lapels, rib: !!opts.bowling });
    for (const m of J.meshes) { root.add(m); } root.updateMatrixWorld(true); for (const m of J.meshes) m.bind(J.skeleton); rig.jacket = J;
  }
  rig.L1 = L1; rig.L2 = L2; rig.root.scale.setScalar(opts.scale ?? 1); rig.M = M;
  return rig;
}


// ---------- face: the Blender head carries every eye/brow/mouth variant as a named group; show exactly one of each
function applyHead(rig) { const a = rig._poseHead ?? [0, 0, 0], b = rig._exprHead ?? [0, 0, 0]; rig.j.neck.rotation.set((a[0] + b[0]) * D, (a[1] + b[1]) * D, (a[2] + b[2]) * D); }
export function setFace(rig, f) {
  const want = new Set([f.eyes ?? 'eyes_open', f.brows ?? 'brows_flat', f.mouth ?? 'mouth_smile']);
  rig.headRoot.traverse(o => { if (/^(eyes|brows|mouth)_/.test(o.name)) o.visible = want.has(o.name); });
  rig._exprHead = f.head ?? [0, 0, 0]; applyHead(rig);
}

// ---------- poses (degrees). sh:[forward, out], el: flex, curl:[thumb,index,middle,ring,pinky]; legs: hip:[forward,out], knee flex
const CURL_RELAX = [0.35, 0.45, 0.5, 0.55, 0.6], OPEN = [0.1, 0.1, 0.1, 0.1, 0.1], FIST = [0.8, 1, 1, 1, 1], HORNS = [0.9, 0, 1, 1, 0];
export const POSES = {
  neutral: { yaw: 8, spine: [2, 0, 0], head: [0, 0, 0], L: { sh: [6, 10], el: 14, curl: CURL_RELAX }, R: { sh: [4, 10], el: 18, curl: CURL_RELAX }, legL: { hip: [4, 3], knee: 8 }, legR: { hip: [-3, 3], knee: 4 } },
  rock: { yaw: -10, spine: [-6, -12, 0], head: [-6, 8, -8], L: { sh: [8, 38], el: 105, curl: OPEN }, R: { sh: [165, 18], el: 25, curl: HORNS }, legL: { hip: [8, 24], knee: 28 }, legR: { hip: [-6, 22], knee: 20 } },
  shrug: { yaw: 6, spine: [0, 0, 3], head: [4, 0, 10], L: { sh: [20, 28], el: 95, curl: OPEN }, R: { sh: [20, 28], el: 95, curl: OPEN }, legL: { hip: [0, 6], knee: 6 }, legR: { hip: [6, 8], knee: 28 } },
  panic: { yaw: -6, spine: [-8, 0, 4], head: [-8, 0, -6], L: { sh: [110, 44], el: 30, curl: OPEN }, R: { sh: [125, 36], el: 25, curl: OPEN }, legL: { hip: [48, 6], knee: 78 }, legR: { hip: [4, 8], knee: 20 } },
  strum: { yaw: 18, spine: [-14, 8, 0], head: [-6, -6, 4], L: { sh: [105, 8], el: 24, curl: FIST }, R: { sh: [38, 22], el: 82, curl: CURL_RELAX }, legL: { hip: [44, 16], knee: 84 }, legR: { hip: [28, 20], knee: 62 } },
};
export function setPose(rig, spec) {
  const p = typeof spec === 'string' ? POSES[spec] : spec;
  rig.root.rotation.y = (p.yaw ?? 0) * D;
  const sp = p.spine ?? [0, 0, 0]; rig.j.chest.rotation.set(sp[0] * D, sp[1] * D, sp[2] * D);
  rig._poseHead = p.head ?? [0, 0, 0]; applyHead(rig);
  for (const k of ['L', 'R']) {
    const a = rig.j.arms[k], q = p[k], s = a.s;
    a.sh.rotation.set(-q.sh[0] * D, 0, s * q.sh[1] * D);
    a.el.rotation.set(-q.el * D, 0, 0);
    const cu = q.curl;
    a.fingers.forEach(([f1, f2], i) => { const c = cu[i + 1]; f1.rotation.z = -s * c * 1.25; f2.rotation.z = -s * c * 1.35; f1.rotation.x = (i - 1.5) * 0.17 * (1 - c); });
    a.prop.visible = !!q.prop; a.wr.rotation.y = s * (q.roll ?? 0) * D;
    a.th[0].rotation.z = -s * (0.15 + cu[0] * 0.7); a.th[1].rotation.z = -s * cu[0] * 0.9;
  }
  let hmax = 0;
  for (const k of ['legL', 'legR']) {
    const l = rig.j[k], q = p[k], s = l.s, a = q.hip[0] * D, kn = q.knee * D;
    l.hip.rotation.set(-a, 0, s * q.hip[1] * D);
    l.knee.rotation.set(kn, 0, 0);
    l.ank.rotation.set(a - kn, 0, -s * q.hip[1] * D); // keep soles flat
    hmax = Math.max(hmax, rig.L1 * Math.cos(a) * Math.cos(q.hip[1] * D) + rig.L2 * Math.cos(a - kn) * Math.cos(q.hip[1] * D));
  }
  rig.root.position.y = hmax - (rig.L1 + rig.L2);
}

export const buildDex = () => buildPerson({});
