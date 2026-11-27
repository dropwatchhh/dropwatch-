// Fitted jacket as skinned geometry: torso shell, lapels, collar, sleeves that bend with the arm bones, zip, studs, seams, wrinkles.
// Everything is generated on one analytic body-shaped surface, so details sit flush on it (no floating pieces).
import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';

const sm = (a, b, x) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };
const lerp = (a, b, t) => a + (b - a) * t;
// Catmull-Rom through table rows [key, v1, v2...]
function cr(tab, y) {
  const n = tab.length; if (y <= tab[0][0]) return tab[0].slice(1); if (y >= tab[n - 1][0]) return tab[n - 1].slice(1);
  let i = 0; while (y > tab[i + 1][0]) i++;
  const p0 = tab[Math.max(0, i - 1)], p1 = tab[i], p2 = tab[i + 1], p3 = tab[Math.min(n - 1, i + 2)], t = (y - p1[0]) / (p2[0] - p1[0]), t2 = t * t, t3 = t2 * t;
  return p1.slice(1).map((_, k) => 0.5 * ((2 * p1[k + 1]) + (-p0[k + 1] + p2[k + 1]) * t + (2 * p0[k + 1] - 5 * p1[k + 1] + 4 * p2[k + 1] - p3[k + 1]) * t2 + (-p0[k + 1] + 3 * p1[k + 1] - 3 * p2[k + 1] + p3[k + 1]) * t3));
}
// torso key rows: [y, half-width, half-depth, z-centre]   (rig units: waist = 2.05, shoulder joints y = 3.03, collar base 3.32)
const TORSO = [[1.74, 0.468, 0.305, 0.0], [1.88, 0.452, 0.292, 0.0], [2.08, 0.425, 0.272, 0.0], [2.28, 0.428, 0.274, 0.006], [2.52, 0.468, 0.294, 0.016], [2.78, 0.512, 0.308, 0.02], [3.0, 0.534, 0.296, 0.0], [3.13, 0.47, 0.262, -0.012], [3.24, 0.34, 0.228, -0.016], [3.32, 0.236, 0.214, -0.012]];
const SLEEVE = [[1.76, 0.12], [1.9, 0.116], [2.1, 0.126], [2.35, 0.14], [2.6, 0.155], [2.85, 0.17], [3.0, 0.175], [3.08, 0.152], [3.13, 0.1], [3.17, 0.0]];
let ZIP_TOP = 2.5; const Y0 = 1.74, Y1 = 3.32, E = 0.83;   // E: superellipse exponent (2/2.4)
const gap = y => 0.62 * sm(ZIP_TOP - 0.04, 3.3, y);        // half-angle of the open front V
const sg = v => (v < 0 ? -1 : 1);
function surf(th, y, off = 0) {
  const [rx, rz, zc] = cr(TORSO, y), s = Math.sin(th), c = Math.cos(th);
  const f = (t, yy) => { const [a, b, z] = cr(TORSO, yy); const ss = Math.sin(t), cc = Math.cos(t); return new THREE.Vector3(a * sg(ss) * Math.abs(ss) ** E, yy, z + b * sg(cc) * Math.abs(cc) ** E); };
  const p = f(th, y); if (!off) return p;
  const du = f(th + 0.01, y).sub(f(th - 0.01, y)), dv = f(th, y + 0.01).sub(f(th, y - 0.01)); const n = du.cross(dv).normalize(); if (n.dot(new THREE.Vector3(Math.sin(th), 0, Math.cos(th))) < 0) n.negate();
  return p.addScaledVector(n, off);
}
function grid(uSeg, vSeg, fn) {   // fn(u,v) -> Vector3
  const pos = [], idx = [];
  for (let j = 0; j <= vSeg; j++) for (let i = 0; i <= uSeg; i++) { const p = fn(i / uSeg, j / vSeg); pos.push(p.x, p.y, p.z); }
  for (let j = 0; j < vSeg; j++) for (let i = 0; i < uSeg; i++) { const a = j * (uSeg + 1) + i, b = a + 1, c = a + uSeg + 1, d = c + 1; idx.push(a, c, b, b, c, d); }
  const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); g.setIndex(idx); g.computeVertexNormals(); return g;
}
// ribbon on the torso surface following a (theta,y) path, with width in theta and an outward offset
function ribbon(path, w, off, seg = 40) {
  const pts = []; for (let i = 0; i <= seg; i++) pts.push(path(i / seg));
  return grid(1, seg, (u, v) => { const [th, y] = pts[Math.round(v * seg)]; return surf(th + (u - 0.5) * w, y, off); });
}
function stud(p, n, r = 0.016) { const g = new THREE.SphereGeometry(r, 12, 8, 0, Math.PI * 2, 0, Math.PI / 2); g.rotateX(Math.PI / 2); const q = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 0, 1), n); g.applyQuaternion(q); g.translate(p.x, p.y, p.z); return g; }
function box(p, n, up, w, h, d) { const g = new THREE.BoxGeometry(w, h, d); const z = n.clone().normalize(), x = new THREE.Vector3().crossVectors(up, z).normalize(), y = new THREE.Vector3().crossVectors(z, x); const m = new THREE.Matrix4().makeBasis(x, y, z).setPosition(p); g.applyMatrix4(m); return g; }
const nrm = (th, y) => surf(th, y, 0.01).sub(surf(th, y, 0)).normalize();

export function buildJacket(rig, B, mats, opts = {}) {
  // B: { chest, sh:{L,R}, el:{L,R}, bones:[...] } ; bones order: chest, shL, elL, shR, elR
  const PUNK = opts.punk !== false, RIB = !!opts.rib, LAPEL = opts.lapels ?? (PUNK && !RIB); ZIP_TOP = RIB ? 3.2 : 2.5;
  const ribM = new THREE.MeshStandardMaterial({ color: opts.ribColor ?? 0xf1e7d0, roughness: 0.9, side: THREE.DoubleSide });
  const leather = mats.leather.clone(); leather.side = THREE.DoubleSide; leather.roughness = 0.46; if ('clearcoat' in leather) leather.clearcoat = 0.25;
  const frags = { leather: [], leatherD: [], metal: [], stitch: [], pink: [], teal: [], rib: [] };
  const W = []; // per-fragment weight functions
  const add = (kind, g, wf) => { g.userData.wf = wf; frags[kind].push(g); };
  const chestW = (p) => { // torso: chest bone, blended into the shoulder bone near the shoulder tip
    const f = sm(0.4, 0.54, Math.abs(p.x)) * sm(2.8, 3.05, p.y) * 0.5; const side = p.x < 0 ? 1 : 3; return [[0, 1 - f], [side, f]];
  };
  const sleeveW = (s) => (p) => { const shI = s < 0 ? 1 : 3, elI = s < 0 ? 2 : 4; const we = 1 - sm(2.21, 2.49, p.y), wc = 0.55 * sm(3.0, 3.2, p.y); return [[elI, we], [shI, (1 - we) * (1 - wc)], [0, (1 - we) * wc]]; };

  // ---- torso shell
  const torso = grid(120, 70, (u, v) => { const y = lerp(Y0, Y1, v), g = gap(y); const th = g + u * (Math.PI * 2 - 2 * g); const p = surf(th, y);
    const fold = 0.0085 * Math.sin(y * 34 + Math.sin(th * 2.0) * 1.4) * sm(1.95, 2.25, y) * (1 - sm(2.4, 2.65, y)) * Math.max(0, Math.cos(th) * 0.8 + 0.2); // belly creases
    const back = 0.006 * Math.sin(th * 5 + y * 9) * Math.max(0, -Math.cos(th));
    const n = nrm(th, y); return p.addScaledVector(n, fold + back); });
  add('leather', torso, chestW);
  // hem band (thicker leather welt) and waist seam
  add(RIB ? 'rib' : 'leatherD', ribbonRing(1.74, 1.86, 0.014), chestW);
  if (RIB) { add('leatherD', ribbonRing(1.8, 1.82, 0.0165), chestW); }
  function ribbonRing(ya, yb, off) { return grid(120, 6, (u, v) => { const y = lerp(ya, yb, v), g = gap(y); return surf(g + u * (Math.PI * 2 - 2 * g), y, off * (1 - 0.3 * Math.abs(v - 0.5))); }); }

  // ---- lapels (notch lapel, rolled edge) + top-stitch
  if (LAPEL) for (const s of [-1, 1]) {
    const Wk = [[0, 0.30], [0.18, 0.2], [0.26, 0.2], [0.5, 0.4], [0.78, 0.24], [1, 0.0]];
    const Wf = v => cr(Wk, v)[0], yf = v => lerp(3.3, 2.6, v);
    const lap = grid(14, 40, (u, v) => { const y = yf(v), g = gap(y), th = s * (g + 0.012 + u * Wf(v)); const off = 0.014 + 0.026 * (1 - u) * (0.4 + 0.6 * sm(0, 0.3, v)) * (1 - 0.7 * sm(0.55, 1, v)) + 0.008 * Math.sin(u * Math.PI); return surf(th < 0 ? th + Math.PI * 2 : th, y, off); });
    add('leather', lap, chestW);
    const edge = ribbon(v => [(s * (gap(yf(v)) + 0.012 + Wf(v) - 0.012) + (s < 0 ? Math.PI * 2 : 0)), yf(v)], 0.014, 0.027, 50);
    add('stitch', edge, chestW);
    if (PUNK) for (let i = 0; i < 4; i++) { const v = 0.3 + i * 0.1, y = yf(v), th = s * (gap(y) + 0.012 + Wf(v) * 0.55) + (s < 0 ? Math.PI * 2 : 0); const p = surf(th, y, 0.036); add('metal', stud(p, nrm(th, y)), chestW); }
  }
  // ---- collar stand (double wall + rim), open at the front
  { const gc = 0.5, mk = (dr, y0, y1, flare) => grid(60, 8, (u, v) => { const th = gc + u * (Math.PI * 2 - 2 * gc), y = lerp(y0, y1, v), r = 0.222 + dr + flare * v; return new THREE.Vector3(r * 1.03 * Math.sin(th), y, -0.012 + r * Math.cos(th) * 0.97); });
    add(RIB ? 'rib' : 'leather', mk(0.0, 3.25, 3.42, 0.04), chestW); add(RIB ? 'rib' : 'leather', mk(-0.02, 3.25, 3.42, 0.035), chestW);
    if (RIB) add('leatherD', mk(0.0045, 3.335, 3.35, 0.0), chestW);
    const rim = grid(60, 1, (u, v) => { const th = gc + u * (Math.PI * 2 - 2 * gc), r = 0.245 - 0.02 * v; return new THREE.Vector3(r * 1.03 * Math.sin(th), 3.42, -0.012 + r * Math.cos(th) * 0.97); }); add(RIB ? 'rib' : 'leatherD', rim, chestW);
    if (PUNK) for (const s of [-1, 1]) { const th = s * 0.62, p = new THREE.Vector3(0.24 * 1.03 * Math.sin(th), 3.37, -0.012 + 0.24 * Math.cos(th) * 0.97); add('metal', stud(p, new THREE.Vector3(Math.sin(th), 0, Math.cos(th))), chestW); } }
  // ---- zipper: tape, teeth, pull
  { const tape = (s) => ribbon(v => [0 + s * 0.02 + (s < 0 ? Math.PI * 2 : 0) * 0, lerp(Y0 + 0.03, ZIP_TOP, v)], 0.018, 0.009, 36);
    for (const s of [-1, 1]) add('leatherD', ribbon(v => [(s < 0 ? Math.PI * 2 - 0.022 : 0.022), lerp(Y0 + 0.04, ZIP_TOP, v)], 0.022, 0.009, 36), chestW);
    const teeth = []; for (let k = 0; k < 24; k++) { const y = Y0 + 0.06 + k * 0.032, p = surf(0, y, 0.018), n = nrm(0, y); teeth.push(box(p.clone().add(new THREE.Vector3(k % 2 ? 0.006 : -0.006, 0, 0)), n, new THREE.Vector3(0, 1, 0), 0.016, 0.015, 0.012)); }
    add('metal', mergeGeometries(teeth), chestW);
    add('metal', box(surf(0, ZIP_TOP + 0.015, 0.03), nrm(0, ZIP_TOP), new THREE.Vector3(0, 1, 0), 0.04, 0.07, 0.014), chestW); }
  // ---- slanted zip pockets, side seams, princess seams, yoke
  for (const s of [-1, 1]) {
    const pk = ribbon(v => [(s * (0.55 + 0.1 * v) + (s < 0 ? Math.PI * 2 : 0)), lerp(2.0, 2.2, v)], 0.04, 0.012, 24); add('leatherD', pk, chestW);
    const tt = []; for (let k = 0; k < 8; k++) { const v = k / 7, th = s * (0.55 + 0.1 * v) + (s < 0 ? Math.PI * 2 : 0), y = lerp(2.0, 2.2, v); tt.push(box(surf(th, y, 0.02), nrm(th, y), new THREE.Vector3(0, 1, 0), 0.016, 0.012, 0.01)); }
    if (PUNK) add('metal', mergeGeometries(tt), chestW);
    add('stitch', ribbon(v => [(s * 1.5 + (s < 0 ? Math.PI * 2 : 0)), lerp(1.86, 3.0, v)], 0.008, 0.008, 40), chestW);                                  // side seam
    add('stitch', ribbon(v => [(s * (0.95 - 0.35 * v) + (s < 0 ? Math.PI * 2 : 0)), lerp(1.9, 3.18, v)], 0.008, 0.008, 40), chestW);                      // princess seam
    // epaulette strap + studs
    const ep = ribbon(v => [(s > 0 ? Math.PI / 2 : Math.PI * 1.5) + s * 0.0, lerp(3.2, 3.02, v)], 0.2, 0.014, 20); add('leatherD', ep, chestW);
    if (PUNK) for (let k = 0; k < 2; k++) { const y = 3.17 - k * 0.07, th = s > 0 ? Math.PI / 2 : Math.PI * 1.5; add('metal', stud(surf(th, y, 0.022), nrm(th, y), 0.018), chestW); }
  }
  // ---- back: yoke seam, patch + star (flat, flush)
  add('stitch', ribbon(v => [lerp(Math.PI * 0.55, Math.PI * 1.45, v), 3.02], 0.008, 0.008, 40), chestW);
  if (PUNK) {
    const BX = 0.43, Yc = 2.62;   // back-centre patch: circle and 5-point star mapped onto the surface (arc length = BX * dtheta)
    const pt = (x, y, off) => surf(Math.PI - x / BX, Yc + y, off);
    const fan = (pts, off) => { const pos = [], idx = []; pos.push(...Object.values(pt(0, 0, off))); pts.forEach(([x, y]) => pos.push(...Object.values(pt(x, y, off)))); for (let i = 0; i < pts.length; i++) idx.push(0, 1 + i, 1 + ((i + 1) % pts.length)); const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); g.setIndex(idx); g.computeVertexNormals(); return g; };
    const circ = [], star = []; for (let i = 0; i < 48; i++) { const a = i / 48 * Math.PI * 2; circ.push([0.2 * Math.cos(a), 0.2 * Math.sin(a)]); }
    for (let i = 0; i < 10; i++) { const a = Math.PI / 2 + i * Math.PI / 5, r = i % 2 ? 0.07 : 0.165; star.push([r * Math.cos(a), r * Math.sin(a)]); }
    add('pink', fan(circ, 0.022), chestW); add('teal', fan(star, 0.028), chestW);
  }
  // ---- sleeves (skinned along the arm), forward elbow curve, creases at the elbow and wrist, cuff band
  const sleeveGeo = (s) => grid(48, 90, (u, v) => { const y = lerp(3.17, 1.76, v), a = u * Math.PI * 2, r = cr(SLEEVE, y)[0];
    const cz = 0.035 * Math.exp(-(((y - 2.35) / 0.45) ** 2)) + 0.012 * sm(2.9, 3.1, y);
    const front = Math.max(0, Math.cos(a)); const back = Math.max(0, -Math.cos(a));
    const crease = 0.008 * Math.sin((y - 2.35) * 46) * Math.exp(-(((y - 2.35) / 0.2) ** 2)) * front - 0.005 * Math.sin((y - 2.35) * 40) * Math.exp(-(((y - 2.35) / 0.2) ** 2)) * back
      + 0.004 * Math.sin(y * 66) * Math.exp(-(((y - 1.98) / 0.12) ** 2));
    const rr = r + crease; return new THREE.Vector3(s * 0.5 + rr * 0.97 * Math.sin(a), y, cz + rr * Math.cos(a) * 1.04); });
  for (const s of [-1, 1]) {
    add('leather', sleeveGeo(s), sleeveW(s));
    // cuff strap + zip slit + studs, sleeve seam line (front) and elbow patch seam
    const cuff = grid(48, 6, (u, v) => { const y = lerp(1.78, 1.9, v), a = u * Math.PI * 2, r = cr(SLEEVE, y)[0] + 0.012; return new THREE.Vector3(s * 0.5 + r * 0.97 * Math.sin(a), y, 0.0 + r * Math.cos(a) * 1.04); }); add(RIB ? 'rib' : 'leatherD', cuff, sleeveW(s));
    if (RIB) { const st = grid(48, 2, (u, v) => { const y = lerp(1.835, 1.85, v), a = u * Math.PI * 2, r = cr(SLEEVE, y)[0] + 0.0145; return new THREE.Vector3(s * 0.5 + r * 0.97 * Math.sin(a), y, r * Math.cos(a) * 1.04); }); add('leatherD', st, sleeveW(s)); }
    const seam = (a0, y0, y1, k) => { const g = grid(1, 60, (u, v) => { const y = lerp(y0, y1, v), r = cr(SLEEVE, y)[0] + 0.007, cz = 0.035 * Math.exp(-(((y - 2.35) / 0.45) ** 2)) + 0.012 * sm(2.9, 3.1, y), a = a0 + (u - 0.5) * 0.045; return new THREE.Vector3(s * 0.5 + r * 0.97 * Math.sin(a), y, cz + r * Math.cos(a) * 1.04); }); add('stitch', g, sleeveW(s)); };
    seam(Math.PI * 0.5, 3.1, 1.9); seam(Math.PI * 1.5, 3.1, 1.9);
    if (PUNK) { const a = Math.PI * 0.78; for (let k = 0; k < 3; k++) { const y = 1.94 + k * 0.11, r = cr(SLEEVE, y)[0] + 0.012, p = new THREE.Vector3(s * 0.5 + r * 0.97 * Math.sin(a), y, r * Math.cos(a) * 1.04); add('metal', stud(p, new THREE.Vector3(Math.sin(a), 0, Math.cos(a)), 0.014), sleeveW(s)); } }
  }
  if (RIB) { /* varsity rib at hem/collar handled by caller via stripes */ }
  // ---- skin each material group
  const bones = B.bones, skel = new THREE.Skeleton(bones);
  const out = [];
  const matOf = { leather, leatherD: mats.leatherD.clone(), metal: mats.metal, stitch: new THREE.MeshStandardMaterial({ color: 0xcfc6b0, roughness: 0.8 }), pink: mats.pink, teal: mats.teal, rib: ribM };
  matOf.leatherD.side = THREE.DoubleSide; for (const k of ['pink', 'teal']) { matOf[k] = matOf[k].clone(); matOf[k].side = THREE.DoubleSide; }
  for (const [kind, list] of Object.entries(frags)) {
    if (!list.length) continue;
    const parts = list.map(g => { const q = g.index ? g : g; const pos = q.attributes.position; const n = pos.count; const si = new Uint16Array(n * 4), sw = new Float32Array(n * 4);
      for (let i = 0; i < n; i++) { const ws = g.userData.wf({ x: pos.getX(i), y: pos.getY(i), z: pos.getZ(i) }).filter(a => a[1] > 1e-4).sort((a, b) => b[1] - a[1]).slice(0, 4); const tot = ws.reduce((a, b) => a + b[1], 0) || 1; ws.forEach((a, k) => { si[i * 4 + k] = a[0]; sw[i * 4 + k] = a[1] / tot; }); }
      g.setAttribute('skinIndex', new THREE.Uint16BufferAttribute(si, 4)); g.setAttribute('skinWeight', new THREE.Float32BufferAttribute(sw, 4)); return g; });
    const cl = g => { for (const a of Object.keys(g.attributes)) if (!['position', 'normal', 'uv', 'skinIndex', 'skinWeight'].includes(a)) g.deleteAttribute(a); if (!g.attributes.uv) g.setAttribute('uv', new THREE.Float32BufferAttribute(new Float32Array(g.attributes.position.count * 2), 2)); return g; };
    const merged = mergeGeometries(parts.map(cl), false);
    if (kind === 'leather' || kind === 'leatherD') merged.computeVertexNormals();
    const mesh = new THREE.SkinnedMesh(merged, matOf[kind]); mesh.castShadow = true; mesh.receiveShadow = true; mesh.frustumCulled = false; out.push(mesh);
  }
  return { meshes: out, skeleton: skel };
}
