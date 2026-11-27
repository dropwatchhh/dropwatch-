// Gig the raccoon: original 3D character, rigged (head, arms with 4-finger paws, legs, ringed tail), swappable eye/mouth variants.
import * as THREE from 'three';
const D = Math.PI / 180;
const std = (c, o = {}) => new THREE.MeshStandardMaterial({ color: c, roughness: 0.9, ...o });
function ell(mat, rx, ry, rz, x = 0, y = 0, z = 0, seg = 28) { const m = new THREE.Mesh(new THREE.SphereGeometry(1, seg, Math.max(8, seg * 0.7 | 0)), mat); m.scale.set(rx, ry, rz); m.position.set(x, y, z); return m; }
function pivot(parent, x = 0, y = 0, z = 0) { const g = new THREE.Group(); g.position.set(x, y, z); parent.add(g); return g; }
function tube(mat, pts, r, seg = 24) { return new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts.map(p => new THREE.Vector3(...p))), seg, r, 8, false), mat); }
function rng(seed) { let a = seed; return () => { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }

export function buildGig(opts = {}) {
  const root = new THREE.Group(), rig = { root, j: {} };
  const furC = opts.fur ?? 0x8f8b99;
  const fur = std(furC), furD = std(0x5a5664), dark = std(0x24222a), light = std(0xf0ebe6), pinkM = std(0xe58a9c), capM = std(0xe03a6a, { roughness: 0.55 }), teal = std(0x1fe6d2, { roughness: 0.5 });
  const white = new THREE.MeshBasicMaterial({ color: 0xffffff }), black = new THREE.MeshBasicMaterial({ color: 0x0b0a10 });
  const R = rng(5);

  // ---- body
  const body = pivot(root, 0, 0, 0); rig.j.body = body;
  const torso = pivot(body, 0, 1.0, 0); torso.add(ell(fur, 0.56, 0.62, 0.46, 0, 0, 0, 36), ell(light, 0.36, 0.44, 0.1, 0, -0.04, 0.38, 24)); rig.j.torso = torso;
  // fur tufts (instanced) so the silhouette is fuzzy
  const tuftGeo = new THREE.ConeGeometry(0.011, 0.06, 5); tuftGeo.translate(0, 0.028, 0); tuftGeo.computeVertexNormals();
  const tufts = (parent, rx, ry, rz, n, cx, cy, cz, skip) => { const im = new THREE.InstancedMesh(tuftGeo, new THREE.MeshStandardMaterial({ color: furC, roughness: 1, flatShading: false }), n), m = new THREE.Matrix4(), q = new THREE.Quaternion(), up = new THREE.Vector3(0, 1, 0); let k = 0;
    while (k < n) { const v = new THREE.Vector3(R() * 2 - 1, R() * 2 - 1, R() * 2 - 1); if (v.length() > 1 || v.length() < 0.2) continue; v.normalize(); if (skip && skip(v)) continue;
      const p = new THREE.Vector3(v.x * rx, v.y * ry, v.z * rz).add(new THREE.Vector3(cx, cy, cz)); const nrm = new THREE.Vector3(v.x / rx, v.y / ry, v.z / rz).normalize(); q.setFromUnitVectors(up, nrm);
      m.compose(p, q, new THREE.Vector3(0.9 + R() * 0.6, 0.7 + R() * 0.9, 0.9 + R() * 0.6)); im.setMatrixAt(k++, m); } parent.add(im); };
  tufts(torso, 0.56, 0.62, 0.46, 5500, 0, 0, 0, v => v.z > 0.5 && Math.abs(v.x) < 0.75);

  // ---- head (neck pivot), ears, mask, muzzle, cap
  const neck = pivot(torso, 0, 0.58, 0.05); rig.j.neck = neck; const head = pivot(neck, 0, 0.55, 0.02); rig.j.head = head;
  head.add(ell(fur, 0.62, 0.52, 0.54, 0, 0, 0, 40));
  tufts(head, 0.62, 0.52, 0.54, 5500, 0, 0, 0, v => v.z > 0.4 && Math.abs(v.x) < 0.9 && v.y < 0.75);
  for (const s of [-1, 1]) {
    head.add(ell(fur, 0.17, 0.2, 0.1, s * 0.4, 0.5, -0.05, 20), ell(dark, 0.11, 0.14, 0.06, s * 0.4, 0.5, 0.0, 16), ell(light, 0.04, 0.2, 0.05, s * 0.51, 0.52, -0.03, 10));      // ears
    const m = ell(dark, 0.22, 0.15, 0.11, s * 0.25, 0.08, 0.43, 22); m.rotation.z = -s * 0.35; head.add(m);                                                                 // mask
    head.add(ell(furD, 0.1, 0.05, 0.05, s * 0.16, 0.23, 0.48, 12));                                                                                                       // brow fur
    head.add(ell(light, 0.12, 0.1, 0.08, s * 0.4, -0.12, 0.38, 14));                                                                                                       // cheeks
  }
  head.add(ell(light, 0.24, 0.17, 0.2, 0, -0.14, 0.4, 26), ell(dark, 0.075, 0.055, 0.06, 0, -0.06, 0.58, 14), ell(light, 0.08, 0.05, 0.05, 0, 0.18, 0.5, 12));
  for (const s of [-1, 1]) for (let k = 0; k < 3; k++) head.add(tube(dark, [[s * 0.1, -0.13 - k * 0.02, 0.55], [s * 0.3, -0.12 - k * 0.05, 0.58], [s * 0.5, -0.1 - k * 0.09, 0.5]], 0.004, 8));   // whiskers
  // eyes: open / blink / wide / happy (swapped as named groups)
  const eyeGroup = (name, build) => { const g = new THREE.Group(); g.name = name; for (const s of [-1, 1]) build(g, s); head.add(g); return g; };
  eyeGroup('eyes_open', (g, s) => { g.add(ell(white, 0.1, 0.12, 0.05, s * 0.22, 0.1, 0.5, 16), ell(black, 0.055, 0.075, 0.03, s * 0.22 + s * -0.01, 0.1, 0.545, 12), ell(white, 0.02, 0.025, 0.012, s * 0.22 + 0.02, 0.14, 0.57, 8)); });
  eyeGroup('eyes_wide', (g, s) => { g.add(ell(white, 0.125, 0.15, 0.05, s * 0.22, 0.1, 0.5, 16), ell(black, 0.045, 0.06, 0.03, s * 0.22, 0.1, 0.55, 12), ell(white, 0.02, 0.025, 0.012, s * 0.22 + 0.02, 0.14, 0.575, 8)); });
  eyeGroup('eyes_blink', (g, s) => { g.add(tube(black, [[s * 0.12, 0.1, 0.55], [s * 0.22, 0.085, 0.56], [s * 0.32, 0.1, 0.55]], 0.012, 10)); });
  eyeGroup('eyes_happy', (g, s) => { g.add(tube(black, [[s * 0.12, 0.09, 0.55], [s * 0.22, 0.15, 0.56], [s * 0.32, 0.09, 0.55]], 0.014, 10)); });
  eyeGroup('eyes_squint', (g, s) => { g.add(ell(white, 0.1, 0.06, 0.05, s * 0.22, 0.09, 0.5, 14), ell(black, 0.05, 0.045, 0.03, s * 0.22, 0.09, 0.54, 10)); });
  // mouths
  const mouthGroup = (name, build) => { const g = new THREE.Group(); g.name = name; build(g); head.add(g); return g; };
  mouthGroup('mouth_closed', g => g.add(tube(dark, [[-0.1, -0.2, 0.58], [-0.04, -0.235, 0.6], [0, -0.2, 0.61], [0.04, -0.235, 0.6], [0.1, -0.2, 0.58]], 0.008, 12)));
  mouthGroup('mouth_open', g => { g.add(ell(dark, 0.1, 0.075, 0.04, 0, -0.26, 0.58, 16), ell(pinkM, 0.06, 0.03, 0.02, 0, -0.29, 0.6, 10)); });
  mouthGroup('mouth_chitter', g => { g.add(ell(dark, 0.14, 0.1, 0.04, 0, -0.27, 0.57, 18), ell(pinkM, 0.08, 0.04, 0.02, 0, -0.31, 0.59, 10), ell(white, 0.03, 0.025, 0.012, -0.05, -0.2, 0.6, 8), ell(white, 0.03, 0.025, 0.012, 0.05, -0.2, 0.6, 8)); });
  mouthGroup('mouth_smile', g => g.add(tube(dark, [[-0.16, -0.19, 0.57], [-0.08, -0.26, 0.6], [0.08, -0.26, 0.6], [0.16, -0.19, 0.57]], 0.009, 12)));
  // cap (tilted baseball cap with a brim)
  const cap = pivot(head, 0, 0.1, 0.02); cap.rotation.z = -0.1;
  const dome = new THREE.Mesh(new THREE.SphereGeometry(0.6, 32, 20, 0, Math.PI * 2, 0, 1.2), capM); dome.scale.set(1.06, 0.78, 1.0); cap.add(dome);
  const brim = new THREE.Mesh(new THREE.CylinderGeometry(0.46, 0.5, 0.045, 28, 1, false, -Math.PI / 2 - 1.2, 2.4), capM); brim.scale.z = 1.0; brim.position.set(0, 0.03, 0.5); brim.rotation.x = 0.12; brim.scale.set(1, 1, 0.7); cap.add(brim);
  cap.add(ell(teal, 0.1, 0.07, 0.02, 0, 0.2, 0.52, 14), tube(teal, [[-0.58, 0.12, 0.1], [0, 0.0, 0.6], [0.58, 0.12, 0.1]], 0.012, 20));

  // ---- arms (shoulder, elbow, paw with 4 fingers + thumb)
  const arms = {};
  for (const s of [-1, 1]) {
    const sh = pivot(torso, s * 0.5, 0.28, 0.06); sh.add(ell(fur, 0.15, 0.15, 0.15, 0, 0, 0, 18));
    sh.add(new THREE.Mesh(new THREE.CapsuleGeometry(0.13, 0.2, 8, 16), fur)); sh.children[1].position.y = -0.2;
    const el = pivot(sh, 0, -0.38, 0); el.add(ell(fur, 0.125, 0.125, 0.125, 0, 0, 0, 16));
    const fo = new THREE.Mesh(new THREE.CapsuleGeometry(0.115, 0.2, 8, 16), furD); fo.position.y = -0.2; el.add(fo);
    const wr = pivot(el, 0, -0.4, 0); wr.add(ell(furD, 0.12, 0.13, 0.12, 0, -0.07, 0, 18));
    const fingers = []; const zs = [0.075, 0.025, -0.025, -0.075];
    zs.forEach((z, i) => { const f1 = pivot(wr, -s * 0.01, -0.15, z); const c1 = new THREE.Mesh(new THREE.CapsuleGeometry(0.034, 0.05, 6, 10), furD); c1.position.y = -0.045; f1.add(c1);
      const f2 = pivot(f1, 0, -0.09, 0); const c2 = new THREE.Mesh(new THREE.CapsuleGeometry(0.03, 0.035, 6, 10), dark); c2.position.y = -0.035; f2.add(c2); fingers.push([f1, f2]); });
    const th = pivot(wr, -s * 0.07, -0.08, 0.07); th.add(new THREE.Mesh(new THREE.CapsuleGeometry(0.036, 0.05, 6, 10), furD)); th.children[0].position.y = -0.045;
    arms[s < 0 ? 'L' : 'R'] = { sh, el, wr, fingers, th, s };
  }
  rig.j.arms = arms;
  // ---- legs
  const legs = {};
  for (const s of [-1, 1]) {
    const hip = pivot(root, s * 0.28, 0.66, 0); hip.add(ell(fur, 0.19, 0.19, 0.19, 0, 0, 0, 16)); const th = new THREE.Mesh(new THREE.CapsuleGeometry(0.15, 0.1, 6, 14), fur); th.position.y = -0.14; hip.add(th);
    const knee = pivot(hip, 0, -0.26, 0); knee.add(ell(fur, 0.14, 0.14, 0.14, 0, 0, 0, 14)); const sn = new THREE.Mesh(new THREE.CapsuleGeometry(0.125, 0.1, 6, 12), furD); sn.position.y = -0.12; knee.add(sn);
    const ank = pivot(knee, 0, -0.27, 0); ank.add(ell(dark, 0.17, 0.09, 0.28, 0, -0.03, 0.1, 18)); for (const x of [-0.09, 0, 0.09]) ank.add(ell(furD, 0.045, 0.045, 0.06, x, -0.03, 0.34, 8));
    legs[s < 0 ? 'L' : 'R'] = { hip, knee, ank, s };
  }
  rig.j.legs = legs;
  // ---- ringed tail (segments along a curve)
  const tail = pivot(root, 0, 0.78, -0.42); rig.j.tail = tail;
  const curve = new THREE.CatmullRomCurve3([[0, 0, 0], [0, 0.15, -0.3], [0, 0.55, -0.5], [0, 0.95, -0.45], [0, 1.2, -0.25]].map(p => new THREE.Vector3(...p)));
  for (let i = 0; i < 12; i++) { const t = i / 11, p = curve.getPoint(t); const r = 0.2 * (1 - 0.35 * t); const seg = ell(i % 2 ? dark : fur, r, r * 0.8, r * 1.1, p.x, p.y, p.z, 14); const tg = curve.getTangent(t); seg.quaternion.setFromUnitVectors(new THREE.Vector3(0, 0, 1), tg); tail.add(seg); }
  tufts(tail, 0.18, 0.18, 0.18, 0, 0, 0, 0);
  root.traverse(o => { if (o.isMesh || o.isInstancedMesh) { o.castShadow = true; o.receiveShadow = true; } });
  return rig;
}

export function setGigFace(rig, f) {
  const want = new Set([f.eyes ?? 'eyes_open', f.mouth ?? 'mouth_closed']);
  rig.j.head.traverse(o => { if (/^(eyes|mouth)_/.test(o.name)) o.visible = want.has(o.name); });
}
// pose angles in degrees; arms {sh:[fwd,out], el, curl 0..1}, legs {hip, knee}, head [x,y,z], lean, tail
export function setGigPose(rig, p = {}) {
  const sp = p.spine ?? [0, 0, 0]; rig.j.torso.rotation.set(sp[0] * D, sp[1] * D, sp[2] * D);
  const h = p.head ?? [0, 0, 0]; rig.j.head.rotation.set(h[0] * D, h[1] * D, h[2] * D);
  for (const k of ['L', 'R']) { const a = rig.j.arms[k], q = p[k] ?? { sh: [5, 12], el: 10, curl: 0.3 }, s = a.s;
    a.sh.rotation.set(-q.sh[0] * D, 0, s * q.sh[1] * D); a.el.rotation.set(-q.el * D, 0, 0);
    a.fingers.forEach(([f1, f2], i) => { f1.rotation.z = -s * q.curl * 1.2; f2.rotation.z = -s * q.curl * 1.3; f1.rotation.x = (i - 1.5) * 0.15 * (1 - q.curl); });
    a.th.rotation.z = -s * (0.2 + q.curl * 0.8); }
  for (const k of ['L', 'R']) { const l = rig.j.legs[k], q = p['leg' + k] ?? { hip: 0, knee: 0 }; l.hip.rotation.x = -q.hip * D; l.knee.rotation.x = q.knee * D; l.ank.rotation.x = (q.hip - q.knee) * D; }
  rig.j.tail.rotation.set((p.tail?.[0] ?? 0) * D, (p.tail?.[1] ?? 0) * D, 0);
}
