// Dex Hollow v2: original neon-punk rockstar, rigged. three.js, y up, faces +z.
// Rig: chest/neck/head, shoulders/elbows/wrists/fingers, hips/knees/ankles; expression + pose API.
import * as THREE from 'three';
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
export const M = {
  skin: phys(0xdba070, { roughness: 0.5, sheen: 0.5, sheenColor: new THREE.Color(0xff9a80), sheenRoughness: 0.4, bumpMap: skinBump, bumpScale: 0.8 }),
  skinD: std(0xb77a50),
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
function pivot(parent, x = 0, y = 0, z = 0) { const g = new THREE.Group(); g.position.set(x, y, z); parent.add(g); return g; }

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

// ---------- eyes with real eyelids, lashes, cornea shine and a lid crease
function makeEye(s) {
  const x = s * 0.21, y = 2.4, z = faceZ(x, y) - 0.012;
  const g = new THREE.Group(); g.position.set(x, y, z); g.userData.base = 0.93;
  g.add(ell(M.white, 0.118, 0.145, 0.062, 0, 0, 0, 40));
  const look = pivot(g);
  look.add(ell(M.limbal, 0.088, 0.108, 0.03, 0, -0.008, 0.03, 32), ell(M.iris, 0.076, 0.094, 0.03, 0, -0.008, 0.042, 32),
    ell(M.black, 0.038, 0.048, 0.02, 0, -0.008, 0.064, 24), ell(M.white, 0.02, 0.02, 0.012, 0.03, 0.04, 0.08, 12), ell(M.white, 0.01, 0.01, 0.008, -0.028, -0.04, 0.076, 8));
  g.add(ell(M.cornea, 0.108, 0.13, 0.07, 0, -0.004, 0.012, 32));
  const up = pivot(g);
  const lid = new THREE.Mesh(new THREE.SphereGeometry(1, 40, 20, 0, Math.PI * 2, 0, Math.PI / 2), M.skin); lid.scale.set(0.132, 0.16, 0.084); up.add(lid);
  const rim = []; for (let a = 0; a <= 18; a++) { const t = Math.PI * a / 18; rim.push([0.132 * Math.cos(t), 0.003, 0.084 * Math.sin(t) + 0.004]); }
  const outerIdx = s > 0 ? 0 : 18, liner = rim.slice(), e = rim[outerIdx];
  if (s > 0) liner.unshift([e[0] + 0.075, 0.04, 0.03]); else liner.push([e[0] - 0.075, 0.04, 0.03]);
  up.add(tube(M.black, liner, 0.015, 48));
  const lashes = []; const rr = rng(s > 0 ? 5 : 6);
  for (let k = 0; k < 9; k++) { const ti = outerIdx === 0 ? 1 + k : 17 - k, p = rim[ti]; const o = s * 0.5, d = new THREE.Vector3(p[0] * 2 * 0.5 + o * (0.3 + k * 0.05), 0.9, 0.4).normalize(); const L = 0.045 + 0.02 * rr();
    const P0 = new THREE.Vector3(...p); lashes.push(taperGeo([P0.toArray(), P0.clone().addScaledVector(d, L * 0.4).toArray(), P0.clone().addScaledVector(d, L * 0.8).add(new THREE.Vector3(0, 0.01, 0.012)).toArray(), P0.clone().addScaledVector(d, L).add(new THREE.Vector3(0, 0.02, 0.028)).toArray()], 0.0065, 0x0d0a12, 0x0d0a12, 4, 6)); }
  up.add(new THREE.Mesh(mergeGeometries(lashes), M.hair));
  const lo = pivot(g);
  const lid2 = new THREE.Mesh(new THREE.SphereGeometry(1, 40, 20, 0, Math.PI * 2, Math.PI / 2, Math.PI / 2), M.skin); lid2.scale.set(0.131, 0.158, 0.083); lo.add(lid2);
  // lid crease (fixed on the head)
  const cp = [-0.13, -0.05, 0.05, 0.13].map((dx, i) => { const wx = x + dx, wy = y + 0.2 + (i === 0 || i === 3 ? -0.03 : 0.012); return [dx, wy - y, faceZ(wx, wy) - z + 0.008]; });
  g.add(tube(new THREE.MeshStandardMaterial({ color: 0xc78a5e, roughness: 0.7, transparent: true, opacity: 0.55 }), cp, 0.005, 20));
  return { g, look, up, lo };
}

// ---------- the rig
export function buildDex() {
  const root = new THREE.Group();
  const rig = { root, j: {} };
  const all = o => o.traverse(m => { if (m.isMesh) { m.castShadow = true; m.receiveShadow = true; } });

  // legs
  const L1 = 0.4, L2 = 0.5, HIPY = 1.12;
  const hips = pivot(root, 0, 0, 0);
  hips.add(ell(M.jeans, 0.43, 0.22, 0.29, 0, 1.12, 0), rbox(M.black, 0.8, 0.1, 0.58, 0, 1.1, 0, 0.03), rbox(M.metal, 0.13, 0.1, 0.04, 0, 1.1, 0.3, 0.012));
  hips.add(tube(M.metal, [[0.3, 1.1, 0.26], [0.42, 0.98, 0.26], [0.4, 0.86, 0.2], [0.31, 0.8, 0.16]], 0.011));
  for (const s of [-1, 1]) {
    const hip = pivot(root, s * 0.2, HIPY, 0);
    hip.add(ell(M.jeans, 0.165, 0.165, 0.165, 0, 0, 0));
    const th = new THREE.Mesh(new THREE.CylinderGeometry(0.16, 0.145, L1, 28), M.jeans); th.position.y = -L1 / 2; hip.add(th);
    const knee = pivot(hip, 0, -L1, 0); knee.add(ell(M.jeans, 0.145, 0.145, 0.145, 0, 0, 0));
    const shin = new THREE.Mesh(new THREE.CylinderGeometry(0.145, 0.13, L2, 28), M.jeans); shin.position.y = -L2 / 2; knee.add(shin);
    // rips (move with the limb)
    const rip = (par, x, y, rx, ry, rot) => { const r = ell(M.skinD, rx, ry, 0.03, x, y, 0.138, 24); r.rotation.z = rot; par.add(r);
      for (let i = -1; i <= 1; i++) { const t = rbox(M.white, 0.013, ry * 1.6, 0.013, x + i * rx * 0.45, y, 0.162, 0.005); t.rotation.z = rot; par.add(t); } };
    if (s < 0) { rip(knee, 0, 0.0, 0.085, 0.065, 0); rip(hip, -0.02, -0.14, 0.05, 0.035, -0.35); } else { rip(hip, 0.02, -0.2, 0.07, 0.05, 0.1); }
    // boots
    const sh = new THREE.Mesh(new THREE.CylinderGeometry(0.175, 0.185, 0.34, 32), M.boot); sh.position.y = -L2 + 0.17; knee.add(sh);
    for (const yy of [-L2 + 0.1, -L2 + 0.26]) knee.add(rbox(M.metal, 0.3, 0.035, 0.3, 0, yy, 0, 0.015));
    const ank = pivot(knee, 0, -L2, 0);
    ank.add(rbox(M.boot, 0.36, 0.22, 0.58, 0, -0.1, 0.1, 0.09), rbox(M.sole, 0.4, 0.07, 0.62, 0, -0.185, 0.1, 0.03), rbox(M.metal, 0.12, 0.03, 0.05, 0, -0.04, 0.31, 0.012));
    rig.j[s < 0 ? 'legL' : 'legR'] = { hip, knee, ank, s };
  }

  // ---------- chest (spine pivot at the waist)
  const chest = pivot(root, 0, 1.15, 0); const ci = pivot(chest, 0, -1.15, 0); rig.j.chest = chest;
  // tee body
  const teeProf = [[0.43, 0], [0.43, 0.2], [0.4, 0.42], [0.36, 0.62], [0.27, 0.74], [0.17, 0.8]].map(([r, y]) => new THREE.Vector2(r * 0.93, y));
  const tee = new THREE.Mesh(new THREE.LatheGeometry(teeProf, 40), M.tee); tee.geometry.scale(1, 1, 0.72); tee.position.y = 1.04; ci.add(tee);
  const chev = new THREE.Shape(); chev.moveTo(-0.075, -0.02); chev.lineTo(0, 0.075); chev.lineTo(0.075, -0.02); chev.lineTo(0.048, -0.02); chev.lineTo(0, 0.038); chev.lineTo(-0.048, -0.02); chev.closePath();
  const ch = new THREE.Mesh(new THREE.ExtrudeGeometry(chev, { depth: 0.012, bevelEnabled: false }), M.white); ch.position.set(0, 1.46, 0.262); ci.add(ch);
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
    for (let i = 0; i < 5; i++) ci.add(ell(M.metal, 0.02, 0.02, 0.02, s * (0.2 + i * 0.002 - 0.0) + s * 0.0, 1.88 - i * 0.075, 0.3 + 0.0, 12));
    // front placket band (jacket edge)
    const pk = rbox(M.leatherS, 0.06, 0.78, 0.045, s * 0.255, 1.44, 0.305, 0.02); pk.rotation.z = -s * 0.05; pk.rotation.y = -s * 0.5; ci.add(pk);
    // diagonal zip pockets
    const pkt = rbox(M.leatherS, 0.17, 0.05, 0.03, s * 0.31, 1.23, 0.285, 0.015); pkt.rotation.z = -s * 0.35; pkt.rotation.y = -s * 0.8; ci.add(pkt);
    const zp = rbox(M.metal, 0.15, 0.012, 0.012, s * 0.31, 1.235, 0.3, 0.004); zp.rotation.z = -s * 0.35; zp.rotation.y = -s * 0.8; ci.add(zp);
  }
  // collar (popped), back patch
  const collar = new THREE.Mesh(new THREE.CylinderGeometry(0.255, 0.2, 0.14, 40, 1, true, GAP, Math.PI * 2 - 2 * GAP), M.leather); collar.scale.z = 0.8; collar.position.set(0, 1.9, -0.01); ci.add(collar);
  const bp = new THREE.Mesh(new THREE.CylinderGeometry(0.19, 0.19, 0.03, 40), M.pink); bp.rotation.x = Math.PI / 2; bp.position.set(0, 1.5, -0.318); ci.add(bp);
  const st = new THREE.Shape(); for (let i = 0; i < 10; i++) { const r = i % 2 ? 0.065 : 0.15, a = Math.PI / 2 + i * Math.PI / 5; i ? st.lineTo(Math.cos(a) * r, Math.sin(a) * r) : st.moveTo(Math.cos(a) * r, Math.sin(a) * r); } st.closePath();
  const star = new THREE.Mesh(new THREE.ExtrudeGeometry(st, { depth: 0.02, bevelEnabled: false }), M.teal); star.rotation.y = Math.PI; star.position.set(0, 1.5, -0.328); ci.add(star);
  const stitch = new THREE.Mesh(new THREE.TorusGeometry(0.17, 0.008, 8, 40), M.white); stitch.position.set(0, 1.5, -0.336); ci.add(stitch);
  for (const s of [-1, 1]) for (let i = 0; i < 3; i++) ci.add(ell(M.metal, 0.02, 0.02, 0.02, s * (0.37 + i * 0.012), 1.76 - i * 0.02, 0.06 - i * 0.07, 12));

  // ---------- arms
  const arms = {};
  for (const s of [-1, 1]) {
    const sh = pivot(ci, s * 0.4, 1.68, 0.0);
    sh.add(ell(M.leatherS, 0.12, 0.12, 0.12, 0, 0, 0, 28));
    const up = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.108, 0.32, 28, 4), M.leatherS); up.position.y = -0.16; sh.add(up);
    const el = pivot(sh, 0, -0.32, 0); el.add(ell(M.leatherS, 0.108, 0.108, 0.108, 0, 0, 0, 28));
    const fo = new THREE.Mesh(new THREE.CylinderGeometry(0.108, 0.097, 0.32, 28, 4), M.leatherS); fo.position.y = -0.16; el.add(fo);
    const wr = pivot(el, 0, -0.32, 0);
    wr.add(new THREE.Mesh(new THREE.CylinderGeometry(0.118, 0.123, 0.09, 24), M.leatherD)); wr.children[0].position.y = 0.04;
    if (s > 0) { const bd = new THREE.Mesh(new THREE.TorusGeometry(0.1, 0.028, 10, 24), M.wrist); bd.rotation.x = Math.PI / 2; bd.position.y = -0.03; wr.add(bd); }
    // hand: palm + 4 two-segment fingers + thumb
    const palm = rbox(M.skin, 0.075, 0.12, 0.13, 0, -0.08, 0, 0.035); wr.add(palm);
    const fingers = [];
    const zs = [0.045, 0.015, -0.015, -0.045], lens = [0.062, 0.07, 0.066, 0.052]; // index, middle, ring, pinky (front to back)
    zs.forEach((z, i) => {
      const f1 = pivot(wr, -s * 0.02, -0.135, z);
      f1.add(new THREE.Mesh(new THREE.CapsuleGeometry(0.022, lens[i] - 0.044, 6, 12), M.skin)); f1.children[0].position.y = -lens[i] / 2;
      const f2 = pivot(f1, 0, -lens[i], 0);
      f2.add(new THREE.Mesh(new THREE.CapsuleGeometry(0.02, lens[i] * 0.6 - 0.04, 6, 12), M.skin)); f2.children[0].position.y = -lens[i] * 0.3;
      fingers.push([f1, f2]);
    });
    const th1 = pivot(wr, -s * 0.05, -0.06, 0.05);
    th1.add(new THREE.Mesh(new THREE.CapsuleGeometry(0.026, 0.03, 6, 12), M.skin)); th1.children[0].position.y = -0.035;
    const th2 = pivot(th1, 0, -0.065, 0); th2.add(new THREE.Mesh(new THREE.CapsuleGeometry(0.022, 0.024, 6, 12), M.skin)); th2.children[0].position.y = -0.028;
    arms[s < 0 ? 'L' : 'R'] = { sh, el, wr, fingers, th: [th1, th2], s };
  }
  rig.j.arms = arms;

  // ---------- neck + head (pivot at the neck base)
  const neckP = pivot(ci, 0, 1.88, 0.02); const hi = pivot(neckP, 0, -1.88, -0.02); rig.j.neck = neckP;
  ci.add(new THREE.Mesh(new THREE.CylinderGeometry(0.13, 0.15, 0.22, 24), M.skinD)); ci.children[ci.children.length - 1].position.set(0, 1.9, 0.02);
  hi.add(headMesh());
  for (const s of [-1, 1]) {
    hi.add(ell(M.skinD, 0.07, 0.1, 0.05, s * 0.6, 2.36, 0, 24), ell(M.metal, 0.028, 0.028, 0.028, s * 0.615, 2.22, 0.01, 14));
  }
  hi.add(tube(M.metal, Array.from({ length: 13 }, (_, i) => { const a = i / 12 * Math.PI * 2; return [-0.61, 2.46 + 0.035 * Math.cos(a), 0.035 * Math.sin(a)]; }), 0.007, 24, true));
  // face
  const eyes = [makeEye(-1), makeEye(1)]; eyes.forEach(e => hi.add(e.g)); rig.eyes = eyes;
  rig.brows = [null, null]; rig.browHolder = pivot(hi);
  hi.add(rbox(M.metal, 0.065, 0.013, 0.013, -0.25, 2.665, faceZ(-0.25, 2.665) + 0.045, 0.005));
  hi.add(ell(M.skin, 0.046, 0.04, 0.045, 0, 2.272, faceZ(0, 2.272) + 0.012, 28));
  hi.add(ell(M.white, 0.012, 0.03, 0.01, -0.012, 2.31, faceZ(0, 2.31) + 0.05, 10)).children.at(-1).material = new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.25 });
  for (const s of [-1, 1]) { const x = s * 0.35, y = 2.2; const c = new THREE.Mesh(new THREE.PlaneGeometry(0.28, 0.2), M.blush); c.position.set(x, y, faceZ(x, y) + 0.004); c.rotation.y = s * 0.62; c.rotation.x = 0.1; hi.add(c); }
  rig.mouth = pivot(hi); rig.headInner = hi;

  // ---------- hair: scalp cap + ridge of strand clumps (messy teal/magenta mohawk) + volume + fringe + undercut stubble
  const R = rng(7), V3 = (...a) => new THREE.Vector3(...a);
  const CAPC = V3(0, 2.47, -0.05), CAPS = V3(0.66, 0.64, 0.62), CAPROT = -0.4;
  const cg = new THREE.SphereGeometry(1, 72, 44, 0, Math.PI * 2, 0, 1.22), cc = [];
  for (let i = 0; i < cg.attributes.position.count; i++) { const n = 0.75 + 0.5 * R(); cc.push(0.1 * n, 0.04 * n, 0.14 * n); }
  cg.setAttribute('color', new THREE.Float32BufferAttribute(cc, 3));
  const cap = new THREE.Mesh(cg, new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.95 })); cap.scale.copy(CAPS); cap.position.copy(CAPC); cap.rotation.x = CAPROT; cap.updateMatrix(); hi.add(cap);
  const capPt = (theta, phi) => V3(Math.sin(theta) * Math.sin(phi), Math.cos(theta), Math.sin(theta) * Math.cos(phi)).applyMatrix4(cap.matrix);
  const PAL = { a: [0x92105f, 0xff86d8], b: [0x07847b, 0x7afbf0] };
  const parts = [];
  const basis = d => { const up = Math.abs(d.y) < 0.9 ? V3(0, 1, 0) : V3(1, 0, 0); const u = V3().crossVectors(d, up).normalize(); return [u, V3().crossVectors(d, u).normalize()]; };
  const curve = (P, d, sv, l) => [P.clone().addScaledVector(d, -0.07), P.clone().addScaledVector(d, 0.3 * l).addScaledVector(sv, 0.03 * l), P.clone().addScaledVector(d, 0.65 * l).addScaledVector(sv, 0.2 * l), P.clone().addScaledVector(d, l).addScaledVector(sv, 0.55 * l)];
  const clump = (base, dir, len, rad, kind, sweep, nStr = 16, wob = 0.3) => {
    const d = dir.clone().normalize(), sv = sweep.clone().normalize(), [pa, pb] = PAL[kind], [u, v] = basis(d);
    parts.push(taperGeo(curve(base, d, sv, len).map(p => p.toArray()), rad * 0.8, new THREE.Color(pa).multiplyScalar(0.65), pb, 10, 20));
    for (let k = 0; k < nStr; k++) {
      const ang = R() * 6.283, rr = rad * Math.sqrt(R()), off = u.clone().multiplyScalar(Math.cos(ang) * rr).addScaledVector(v, Math.sin(ang) * rr), l = len * (0.8 + 0.34 * R());
      const sp = curve(base, d, sv, l).map((p, i) => p.addScaledVector(off, [1, 0.95, 0.6, 0.12][i]).add(V3(R() - 0.5, R() - 0.5, R() - 0.5).multiplyScalar(wob * len * 0.2 * (i > 1 ? 1 : 0.2))));
      const [qa, qb] = PAL[R() < 0.22 ? (kind === 'a' ? 'b' : 'a') : kind], lum = 0.8 + 0.4 * R();
      parts.push(taperGeo(sp.map(p => p.toArray()), 0.013 + 0.01 * R(), new THREE.Color(qa).multiplyScalar(0.55 * lum), new THREE.Color(qb).multiplyScalar(lum), 5, 12));
    }
  };
  // central ridge, front hairline -> over the crown -> nape; three lanes for thickness
  let flip = 0;
  for (let k = 0; k <= 11; k++) {
    const sPar = -1 + 2 * k / 11, theta = sPar < 0 ? -sPar * 0.9 : sPar * 1.25, phi = sPar < 0 ? 0 : Math.PI, prof = Math.sin(Math.PI * (0.06 + 0.88 * k / 11));
    for (const lane of [-0.14, 0, 0.14]) {
      const B0 = capPt(theta, phi), B = V3(lane, B0.y - Math.abs(lane) * 0.1, B0.z), n = B.clone().sub(CAPC).normalize();
      const dir = n.clone().multiplyScalar(0.8).add(V3(lane * 1.8, 0.9, 0)).normalize();
      const sw = sPar < -0.15 ? V3(lane * 2 + (R() - 0.5), 0.25, 1) : sPar > 0.25 ? V3(lane * 2 + (R() - 0.5), -0.15, -1) : V3(lane * 3 + (R() - 0.5) * 2, 0, -0.45);
      const len = (0.28 + 0.62 * Math.pow(prof, 0.9)) * (lane === 0 ? 1 : 0.84) * (0.9 + 0.2 * R());
      clump(B, dir, len, 0.085 + 0.02 * R(), (flip++ % 2) ? 'a' : 'b', sw, 16);
    }
  }
  // side volume + messy flyaways
  for (const sg of [-1, 1]) for (let k = 0; k < 7; k++) {
    const B = capPt(0.95 + 0.4 * R(), sg * (0.9 + 1.2 * R()) + (sg < 0 ? 0 : 0)), n = B.clone().sub(CAPC).normalize();
    clump(B, n.clone().add(V3(sg * 0.5, 0.25, 0)), 0.3 + 0.28 * R(), 0.06, (flip++ % 2) ? 'a' : 'b', V3(sg * 0.7, -0.35, -0.4), 14);
  }
  // swept fringe over the brow line
  for (let k = 0; k < 7; k++) {
    const ph = (-0.8 + 1.6 * k / 6), B = capPt(0.98 + 0.05 * R(), ph), n = B.clone().sub(CAPC).normalize();
    clump(B, n.clone().add(V3(0, -0.15, 0.55)), 0.24 + 0.14 * R(), 0.045, (flip++ % 2) ? 'a' : 'b', V3(Math.sign(ph) * 0.6, -0.1, 0.25), 12, 0.2);
  }
  // dense short hairline so no bare scalp shows at the front
  for (let k = 0; k < 900; k++) {
    const phi = (R() - 0.5) * 2.8, theta = 0.7 + 0.52 * R(), B = capPt(theta, phi), n = B.clone().sub(CAPC).normalize(), [qa, qb] = PAL[R() < 0.5 ? 'a' : 'b'], l = 0.09 + 0.12 * R();
    parts.push(taperGeo([B.clone().addScaledVector(n, -0.04).toArray(), B.clone().addScaledVector(n, l * 0.5).add(V3(0, 0.02, 0.02)).toArray(), B.clone().addScaledVector(n, l).add(V3(Math.sign(phi) * 0.02, 0.0, 0.05)).toArray()], 0.013, new THREE.Color(qa).multiplyScalar(0.5), new THREE.Color(qb).multiplyScalar(0.9), 4, 4));
  }
  // undercut stubble in dyed colours
  for (let k = 0; k < 760; k++) {
    const sg = R() < 0.5 ? -1 : 1, theta = 0.85 + 0.55 * R(), phi = sg * (0.7 + 1.9 * R()), B = capPt(theta, phi);
    if (Math.abs(B.x) < 0.2 && B.z > 0) continue;
    const n = B.clone().sub(CAPC).normalize(), [qa, qb] = PAL[R() < 0.5 ? 'a' : 'b'], l = 0.07 + 0.07 * R();
    parts.push(taperGeo([B.clone().addScaledVector(n, -0.03).toArray(), B.clone().addScaledVector(n, l * 0.5).add(V3(0, -0.01, 0)).toArray(), B.clone().addScaledVector(n, l).add(V3(0, -0.025, -0.01)).toArray()], 0.012, new THREE.Color(qa).multiplyScalar(0.4), new THREE.Color(qb).multiplyScalar(0.8), 4, 4));
  }
  // undercut covering the sides and back of the skull (sampled on the head itself, avoiding the face and ears)
  for (let k = 0; k < 2600; k++) {
    const a = R() * Math.PI * 2, y = 2.3 + 0.68 * R(), uy = (y - HEAD.cy) / HEAD.ry; if (Math.abs(uy) >= 0.98) continue;
    const r = Math.sqrt(1 - uy * uy), kk = kOf(y), P = V3(HEAD.rx * kk * r * Math.sin(a), y, HEAD.rz * r * Math.cos(a));
    if (Math.cos(a) > 0.1 && y < 2.8) continue;                    // face + forehead
    if (Math.abs(Math.sin(a)) > 0.8 && y < 2.52 && y > 2.2) continue; // ears
    const n = V3(P.x / 0.36, (P.y - HEAD.cy) / 0.34, P.z / 0.31).normalize(), [qa, qb] = PAL[R() < 0.5 ? 'a' : 'b'], l = 0.09 + 0.1 * R();
    const q = P.clone().addScaledVector(n, 0.0);
    parts.push(taperGeo([q.clone().addScaledVector(n, -0.03).toArray(), q.clone().addScaledVector(n, l * 0.5).add(V3(0, -0.015, -0.01)).toArray(), q.clone().addScaledVector(n, l).add(V3(0, -0.04, -0.03)).toArray()], 0.016, new THREE.Color(qa).multiplyScalar(0.45), new THREE.Color(qb).multiplyScalar(0.85), 4, 4));
  }
  // dyed undercut shell over the sides + back of the skull (solid colour under the strands)
  { const sg = new THREE.SphereGeometry(1, 96, 60, Math.PI * 0.8, Math.PI * 1.4, 0, 1.8), p = sg.attributes.position, col = [];
    for (let i = 0; i < p.count; i++) { const ux = p.getX(i), uy = p.getY(i), uz = p.getZ(i), y = uy * HEAD.ry + HEAD.cy, kk = kOf(y);
      p.setXYZ(i, ux * (HEAD.rx * kk + 0.012), y, uz * (HEAD.rz + 0.012));
      const n = 0.7 + 0.6 * R(), teal = (Math.sin(ux * 9) + Math.sin(uz * 11 + uy * 5)) > 0;
      col.push(...(teal ? [0.02 * n, 0.32 * n, 0.3 * n] : [0.36 * n, 0.04 * n, 0.24 * n])); }
    sg.setAttribute('color', new THREE.Float32BufferAttribute(col, 3)); sg.computeVertexNormals();
    hi.add(new THREE.Mesh(sg, new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.9 }))); }
  const hairMesh = new THREE.Mesh(mergeGeometries(parts), M.hair); hi.add(hairMesh); rig.hair = hairMesh;

  all(root);
  rig.L1 = L1; rig.L2 = L2;
  return rig;
}

// ---------- expressions
// strip between two polylines A and B (arrays of [x,y]) draped over the face surface; `puff` gives pillowy volume
function ribbon(A, B, rows, off, puff, mat, colors) {
  const n = A.length, pos = [], idx = [], col = [];
  for (let r = 0; r <= rows; r++) { const v = r / rows, o = off + puff * Math.pow(Math.sin(Math.PI * v), 0.8);
    for (let i = 0; i < n; i++) { const x = lerp(A[i][0], B[i][0], v), y = lerp(A[i][1], B[i][1], v); pos.push(x, y, faceZ(x, y) + o); if (colors) col.push(...colors(i, v)); } }
  for (let r = 0; r < rows; r++) for (let i = 0; i < n - 1; i++) { const a = r * n + i, b = a + 1, c = a + n, d = c + 1; idx.push(a, c, b, b, c, d); }
  const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  if (colors) g.setAttribute('color', new THREE.Float32BufferAttribute(col, 3));
  g.setIndex(idx); g.computeVertexNormals(); return new THREE.Mesh(g, mat);
}
function buildMouth(rig, e) {
  const g = rig.mouth; while (g.children.length) { const c = g.children.pop(); c.geometry?.dispose(); }
  const smile = e.smile ?? 0.3, open = e.open ?? 0, skew = e.skew ?? 0, width = e.width ?? 1, cy = 2.1, hw = 0.165 * width, N = 32;
  const mid = x => { const q = x / hw; return cy + (0.042 * smile + 0.012) * Math.pow(Math.abs(q), 2.2) + skew * 0.035 * q; };
  const xs = Array.from({ length: N + 1 }, (_, i) => -hw + 2 * hw * i / N), sf = x => Math.max(0, 1 - (x / hw) ** 2);
  const gap = open > 0.04 ? open * 0.19 : 0.0025;
  const inU = xs.map(x => [x, mid(x)]), inL = xs.map(x => [x, mid(x) - gap * Math.pow(sf(x), 0.85)]);
  const outU = xs.map((x, i) => [x, inU[i][1] + 0.034 * Math.pow(sf(x), 0.55) * (1 - 0.22 * Math.exp(-((x / (0.16 * hw)) ** 2)))]);
  const outL = xs.map((x, i) => [x, inL[i][1] - 0.047 * Math.pow(sf(x), 0.55)]);
  if (open > 0.04) {
    g.add(ribbon(inU, inL, 2, 0.002, 0.0, M.mouthIn));
    if (open > 0.15) { // upper teeth, shaded darker toward the corners
      const i0 = 4, i1 = N - 4, td = Math.min(0.062, open * 0.12);
      const T = xs.slice(i0, i1 + 1).map((x, k) => [x, inU[i0 + k][1] - 0.002]), Bm = xs.slice(i0, i1 + 1).map((x, k) => [x, Math.max(inL[i0 + k][1] + 0.005, inU[i0 + k][1] - td)]);
      g.add(ribbon(T, Bm, 1, 0.006, 0.003, M.teethM, (i, v) => { const q = Math.abs(i / (T.length - 1) - 0.5) * 2, l = 1 - 0.32 * q * q - 0.12 * (1 - v); return [0.97 * l, 0.94 * l, 0.9 * l]; }));
    }
    if (open > 0.5) g.add(ell(M.tongue, 0.07 * width, 0.02 + open * 0.02, 0.012, 0, inL[N / 2][1] + 0.028, faceZ(0, inL[N / 2][1]) + 0.005, 16));
  }
  g.add(ribbon(inU, outU, 5, 0.004, 0.016, M.lipU)); g.add(ribbon(inL, outL, 5, 0.004, 0.019, M.lipL));
  if (smile > 0.3) for (const sg of [-1, 1]) { const yc = mid(sg * hw);
    const t = tube(M.skinD, [[sg * (hw + 0.012), yc + 0.034], [sg * (hw + 0.036), yc + 0.006], [sg * (hw + 0.022), yc - 0.028]].map(([x, y]) => [x, y, faceZ(x, y) + 0.004]), 0.0065, 12); g.add(t); }
  g.traverse(m => { if (m.isMesh) m.castShadow = false; });
}
function buildBrows(rig, e) {
  const b = e.brow ?? [0, 0, 0, 0], arch = e.browArch ?? 0.028;
  [-1, 1].forEach((s, i) => {
    if (rig.brows[i]) { rig.browHolder.remove(rig.brows[i]); rig.brows[i].geometry.dispose(); }
    const y = b[i * 2], a = b[i * 2 + 1], N = 22, xin = s * 0.085, xout = s * 0.36, yin = 2.64 + y + a * 0.042, yout = 2.64 + y - a * 0.042 - 0.012;
    const C = [], top = [], bot = [];
    for (let k = 0; k <= N; k++) { const t = k / N; C.push([lerp(xin, xout, t), lerp(yin, yout, t) + arch * Math.sin(Math.PI * Math.pow(t, 0.85))]); }
    C.forEach((p, k) => { const t = k / N, q = C[Math.min(N, k + 1)], r = C[Math.max(0, k - 1)]; let dx = q[0] - r[0], dy = q[1] - r[1]; const L = Math.hypot(dx, dy) || 1; dx /= L; dy /= L;
      let nx = -dy, ny = dx; if (ny < 0) { nx = -nx; ny = -ny; }
      const th = (0.012 + 0.034 * Math.pow(Math.sin(Math.PI * (0.12 + 0.75 * t)), 0.9)) * (1 - 0.5 * t);
      top.push([p[0] + nx * th / 2, p[1] + ny * th / 2]); bot.push([p[0] - nx * th / 2, p[1] - ny * th / 2]); });
    const m = ribbon(bot, top, 4, 0.006, 0.013, M.brow); rig.brows[i] = m; rig.browHolder.add(m);
  });
}

export const EXPR = {
  neutral: { smile: 0.3, brow: [0, 0, 0, 0] },
  smile: { smile: 0.85, open: 0.3, brow: [0.012, -0.05, 0.012, -0.05], lid: [0.12, 0.12], squint: [0.3, 0.3], head: [0, 0, 0] },
  grin: { smile: 1, open: 0.55, brow: [0.03, 0.08, 0.03, 0.08], lid: [0.05, 0.05], squint: [0.5, 0.5] },
  smirk: { smile: 0.55, skew: 0.5, brow: [-0.005, -0.2, 0.05, 0.12], lid: [0.2, 0.05], squint: [0.3, 0.1], look: [0.4, 0.05], head: [0, -8, 6] },
  shout: { smile: 0.3, open: 1, width: 1.12, brow: [0.04, 0.35, 0.04, 0.35], lid: [0.1, 0.1], squint: [0.55, 0.55] },
  surprise: { smile: -0.05, open: 0.8, width: 0.6, brow: [0.13, 0.15, 0.13, 0.15], browArch: 0.045, lid: [-0.5, -0.5], eyeScale: 1.1 },
  panic: { smile: -0.5, open: 0.9, width: 0.95, brow: [0.1, 0.65, 0.1, 0.65], lid: [-0.4, -0.4], eyeScale: 1.1, look: [0.5, 0.3] },
  guilty: { smile: -0.1, skew: -0.3, brow: [0.03, 0.7, 0.03, 0.7], lid: [0.25, 0.25], look: [-0.7, -0.4], head: [8, 12, -6] },
  cool: { smile: 0.5, skew: 0.35, brow: [-0.01, -0.1, 0.03, 0.0], lid: [0.5, 0.5], squint: [0.2, 0.2], head: [-4, 0, 4] },
  laugh: { smile: 1, open: 0.9, brow: [0.05, 0.1, 0.05, 0.1], lid: [0.85, 0.85], squint: [0.85, 0.85], head: [-6, 0, 0] },
  sad: { smile: -0.7, open: 0.08, brow: [0.02, 0.85, 0.02, 0.85], lid: [0.3, 0.3], look: [0, -0.5], head: [10, 0, 0] },
  determined: { smile: 0.2, open: 0, brow: [-0.03, -0.7, -0.03, -0.7], browArch: 0.012, lid: [0.2, 0.2], squint: [0.25, 0.25] },
};
function applyHead(rig) { const a = rig._poseHead ?? [0, 0, 0], b = rig._exprHead ?? [0, 0, 0]; rig.j.neck.rotation.set((a[0] + b[0]) * D, (a[1] + b[1]) * D, (a[2] + b[2]) * D); }
export function setExpression(rig, spec) {
  const e = typeof spec === 'string' ? EXPR[spec] : spec;
  buildBrows(rig, e);
  const lid = e.lid ?? [0, 0], sq = e.squint ?? [0, 0], look = e.look ?? [0, 0], es = e.eyeScale ?? 1;
  rig.eyes.forEach((ey, i) => {
    const c = lid[i];
    ey.up.rotation.x = c <= 0 ? lerp(-82 * D, -100 * D, -c) : lerp(-82 * D, 82 * D, c);
    ey.lo.rotation.x = lerp(80 * D, 5 * D, sq[i]);
    ey.look.position.set(look[0] * 0.03, look[1] * 0.03, 0); ey.g.scale.setScalar(es * 0.93);
  });
  buildMouth(rig, e);
  rig._exprHead = e.head ?? [0, 0, 0]; applyHead(rig);
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
    a.fingers.forEach(([f1, f2], i) => { const c = cu[i + 1]; f1.rotation.z = -s * c * 1.25; f2.rotation.z = -s * c * 1.35; });
    a.th[0].rotation.z = -s * cu[0] * 0.7; a.th[1].rotation.z = -s * cu[0] * 0.9;
  }
  let hmax = 0;
  for (const k of ['legL', 'legR']) {
    const l = rig.j[k], q = p[k], s = l.s, a = q.hip[0] * D, kn = q.knee * D;
    l.hip.rotation.set(-a, 0, s * q.hip[1] * D);
    l.knee.rotation.set(kn, 0, 0);
    l.ank.rotation.set(a - kn, 0, -s * q.hip[1] * D); // keep soles flat
    hmax = Math.max(hmax, rig.L1 * Math.cos(a) * Math.cos(q.hip[1] * D) + rig.L2 * Math.cos(a - kn) * Math.cos(q.hip[1] * D));
  }
  rig.root.position.y = hmax - 0.9;
}
