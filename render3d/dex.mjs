// Dex Hollow: original neon-punk rockstar, built from primitives (three.js). Units ~ metres-ish, y up, faces +z.
import * as THREE from 'three';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';

const SKIN = 0xdba070;
export const mats = {
  skin: new THREE.MeshStandardMaterial({ color: SKIN, roughness: 0.55 }),
  skinD: new THREE.MeshStandardMaterial({ color: 0xb77a50, roughness: 0.6 }),
  leather: new THREE.MeshPhysicalMaterial({ color: 0x1b1b22, roughness: 0.38, clearcoat: 0.6, clearcoatRoughness: 0.35 }),
  leatherD: new THREE.MeshPhysicalMaterial({ color: 0x121217, roughness: 0.4, clearcoat: 0.5 }),
  tee: new THREE.MeshStandardMaterial({ color: 0xe8284f, roughness: 0.8 }),
  jeans: new THREE.MeshStandardMaterial({ color: 0x23252f, roughness: 0.85 }),
  boot: new THREE.MeshPhysicalMaterial({ color: 0x17171c, roughness: 0.45, clearcoat: 0.5 }),
  sole: new THREE.MeshStandardMaterial({ color: 0xd8d2c4, roughness: 0.8 }),
  metal: new THREE.MeshStandardMaterial({ color: 0xdfe4ec, metalness: 1, roughness: 0.22 }),
  white: new THREE.MeshStandardMaterial({ color: 0xfffdf8, roughness: 0.3 }),
  black: new THREE.MeshStandardMaterial({ color: 0x15111c, roughness: 0.5 }),
  teal: new THREE.MeshPhysicalMaterial({ color: 0x1fe6d2, roughness: 0.32, clearcoat: 0.7 }),
  pink: new THREE.MeshPhysicalMaterial({ color: 0xff2fa0, roughness: 0.32, clearcoat: 0.7 }),
  iris: new THREE.MeshStandardMaterial({ color: 0x3f9bff, roughness: 0.25 }),
  lip: new THREE.MeshStandardMaterial({ color: 0x5a1f2a, roughness: 0.5 }),
  blush: new THREE.MeshBasicMaterial({ color: 0xff7a8a, transparent: true, opacity: 0.3, depthWrite: false }),
  wrist: new THREE.MeshStandardMaterial({ color: 0xff2fa0, roughness: 0.7 }),
};

const HEAD = { cx: 0, cy: 2.38, rx: 0.6, ry: 0.57, rz: 0.55 };
// z of the head surface at (x,y)
const faceZ = (x, y) => HEAD.rz * Math.sqrt(Math.max(0.01, 1 - (x / HEAD.rx) ** 2 - ((y - HEAD.cy) / HEAD.ry) ** 2));

function ell(mat, rx, ry, rz, x = 0, y = 0, z = 0, seg = 48) {
  const m = new THREE.Mesh(new THREE.SphereGeometry(1, seg, Math.floor(seg * 0.75)), mat);
  m.scale.set(rx, ry, rz); m.position.set(x, y, z); m.castShadow = true; m.receiveShadow = true; return m;
}
function tube(mat, pts, r, seg = 40) {
  const m = new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts.map(p => new THREE.Vector3(...p))), seg, r, 10, false), mat);
  m.castShadow = true; return m;
}
function box(mat, w, h, d, x, y, z, r = 0.03) {
  const m = new THREE.Mesh(new RoundedBoxGeometry(w, h, d, 5, r), mat);
  m.position.set(x, y, z); m.castShadow = true; m.receiveShadow = true; return m;
}
function cone(mat, rad, h, from, dir) {
  const d = new THREE.Vector3(...dir).normalize();
  const m = new THREE.Mesh(new THREE.ConeGeometry(rad, h, 20), mat);
  m.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), d);
  m.position.copy(new THREE.Vector3(...from).addScaledVector(d, h / 2)); m.castShadow = true; return m;
}

export function buildDex() {
  const g = new THREE.Group();
  const add = (...o) => o.forEach(x => g.add(x));

  // ---------- boots (left & right)
  for (const s of [-1, 1]) {
    const x = s * 0.21;
    add(box(mats.boot, 0.36, 0.22, 0.58, x, 0.15, 0.1, 0.09));          // foot
    add(box(mats.sole, 0.4, 0.08, 0.62, x, 0.04, 0.1, 0.04));           // sole
    const shaft = new THREE.Mesh(new THREE.CylinderGeometry(0.175, 0.185, 0.36, 32), mats.boot);
    shaft.position.set(x, 0.38, 0); shaft.castShadow = true; add(shaft);
    for (const yy of [0.29, 0.45]) add(box(mats.metal, 0.3, 0.035, 0.3, x, yy, 0.0, 0.015)); // buckle bars
    add(box(mats.metal, 0.12, 0.03, 0.05, x, 0.24, 0.31, 0.012));                           // toe cap stud strip
  }
  // ---------- legs (jeans) + rips
  for (const s of [-1, 1]) {
    const x = s * 0.21;
    const leg = new THREE.Mesh(new THREE.CylinderGeometry(0.15, 0.158, 0.62, 28), mats.jeans);
    leg.position.set(x, 0.85, 0); leg.castShadow = true; add(leg);
  }
  const rip = (x, y, rx, ry, rot) => {
    const r = ell(mats.skinD, rx, ry, 0.03, x, y, 0.148); r.rotation.z = rot; add(r);
    for (let i = -1; i <= 1; i++) { const t = box(mats.white, 0.014, ry * 1.7, 0.014, x + i * 0.038, y, 0.172, 0.005); t.rotation.z = rot; add(t); }
  };
  rip(-0.215, 0.82, 0.085, 0.06, 0); rip(-0.255, 0.98, 0.05, 0.035, -0.35); rip(0.2, 0.74, 0.07, 0.05, 0.1);
  // hips + belt
  add(ell(mats.jeans, 0.44, 0.22, 0.3, 0, 1.15, 0));
  add(box(mats.black, 0.84, 0.1, 0.62, 0, 1.12, 0, 0.03));
  add(box(mats.metal, 0.14, 0.11, 0.04, 0, 1.12, 0.31, 0.012));
  // hip chain
  add(tube(mats.metal, [[0.3, 1.12, 0.26], [0.42, 0.98, 0.26], [0.4, 0.84, 0.2], [0.3, 0.78, 0.16]], 0.012));

  // ---------- torso: tee strip + jacket
  add(ell(mats.tee, 0.36, 0.38, 0.27, 0, 1.45, 0));
  add(box(mats.tee, 0.26, 0.6, 0.06, 0, 1.45, 0.265, 0.03)); // tee visible in the open front
  // tee print: white chevron
  const chev = new THREE.Shape(); chev.moveTo(-0.07, -0.02); chev.lineTo(0, 0.07); chev.lineTo(0.07, -0.02); chev.lineTo(0.045, -0.02); chev.lineTo(0, 0.035); chev.lineTo(-0.045, -0.02); chev.closePath();
  const ch = new THREE.Mesh(new THREE.ExtrudeGeometry(chev, { depth: 0.01, bevelEnabled: false }), mats.white); ch.position.set(0, 1.4, 0.3); add(ch);
  const jk = ell(mats.leather, 0.44, 0.42, 0.31, 0, 1.47, -0.02, 56); add(jk);
  for (const s of [-1, 1]) { // front panels / lapels, leaving the tee visible down the centre
    const lap = box(mats.leatherD, 0.17, 0.62, 0.07, s * 0.2, 1.45, 0.285, 0.035); lap.rotation.z = -s * 0.12; add(lap);
    const lapTop = box(mats.leatherD, 0.2, 0.12, 0.08, s * 0.17, 1.74, 0.25, 0.04); lapTop.rotation.z = s * 0.7; add(lapTop);
    for (let i = 0; i < 4; i++) { const st = ell(mats.metal, 0.021, 0.021, 0.021, s * (0.27 + i * 0.012), 1.72 - i * 0.1, 0.33, 14); add(st); }
    for (let i = 0; i < 3; i++) { const st = ell(mats.metal, 0.021, 0.021, 0.021, s * (0.36 + i * 0.03), 1.78 - i * 0.02, 0.1 - i * 0.07, 14); add(st); }
    // zip teeth (left panel only, asymmetric biker zip)
  }
  const zip = box(mats.metal, 0.012, 0.52, 0.012, -0.115, 1.45, 0.325, 0.004); zip.rotation.z = 0.05; add(zip);
  // back patch: pink disc with white stitching + teal star (original design)
  const bp = new THREE.Mesh(new THREE.CylinderGeometry(0.19, 0.19, 0.03, 40), mats.pink); bp.rotation.x = Math.PI / 2; bp.position.set(0, 1.52, -0.318); add(bp);
  const st = new THREE.Shape(); for (let i = 0; i < 10; i++) { const r = i % 2 ? 0.065 : 0.15, a = Math.PI / 2 + i * Math.PI / 5; i ? st.lineTo(Math.cos(a) * r, Math.sin(a) * r) : st.moveTo(Math.cos(a) * r, Math.sin(a) * r); } st.closePath();
  const star = new THREE.Mesh(new THREE.ExtrudeGeometry(st, { depth: 0.02, bevelEnabled: false }), mats.teal); star.rotation.y = Math.PI; star.position.set(0, 1.52, -0.328); add(star);
  const stitch = new THREE.Mesh(new THREE.TorusGeometry(0.17, 0.008, 8, 40), mats.white); stitch.position.set(0, 1.52, -0.336); add(stitch);
  // collar stand
  add(box(mats.leatherD, 0.34, 0.1, 0.2, 0, 1.86, 0.02, 0.04));
  // neck
  const neck = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.14, 0.2, 24), mats.skinD); neck.position.set(0, 1.92, 0.02); add(neck);

  // ---------- arms: sleeves, cuffs, hands, wristbands
  for (const s of [-1, 1]) {
    const arm = new THREE.Group();
    const sleeve = new THREE.Mesh(new THREE.CapsuleGeometry(0.125, 0.46, 12, 24), mats.leather); sleeve.castShadow = true;
    sleeve.position.y = -0.3; arm.add(sleeve);
    const cuff = new THREE.Mesh(new THREE.CylinderGeometry(0.13, 0.135, 0.1, 24), mats.leatherD); cuff.position.y = -0.62; arm.add(cuff);
    const band = new THREE.Mesh(new THREE.TorusGeometry(0.095, 0.03, 12, 24), mats.wrist); band.rotation.x = Math.PI / 2; band.position.y = -0.72; if (s > 0) arm.add(band);
    const hand = ell(mats.skin, 0.105, 0.115, 0.095, 0, -0.78, 0.01); arm.add(hand);
    const thumb = ell(mats.skin, 0.04, 0.06, 0.04, -s * 0.09, -0.74, 0.06); arm.add(thumb);
    for (let i = 0; i < 2; i++) arm.add(box(mats.metal, 0.035, 0.014, 0.024, 0, -0.60 + i * 0.0, 0.135, 0.005)); // sleeve stud
    arm.position.set(s * 0.43, 1.66, -0.02); arm.rotation.z = -s * 0.3; add(arm);
  }
  for (const s of [-1, 1]) for (let i = 0; i < 3; i++) add(ell(mats.metal, 0.022, 0.022, 0.022, s * 0.47, 1.72 - i * 0.07, 0.06, 14)); // shoulder studs

  // ---------- head
  add(ell(mats.skin, HEAD.rx, HEAD.ry, HEAD.rz, HEAD.cx, HEAD.cy, 0, 64));
  for (const s of [-1, 1]) {
    add(ell(mats.skinD, 0.07, 0.1, 0.05, s * 0.6, 2.36, 0, 24));
    add(ell(mats.metal, 0.028, 0.028, 0.028, s * 0.612, 2.22, 0.01, 14));
  }
  add(ell(mats.metal, 0.02, 0.02, 0.02, -0.605, 2.46, 0.0, 12));
  // eyes
  for (const s of [-1, 1]) {
    const x = s * 0.21, y = 2.4, z = faceZ(x, y);
    add(ell(mats.white, 0.118, 0.145, 0.06, x, y, z - 0.01, 32));
    add(ell(mats.iris, 0.078, 0.095, 0.03, x + s * 0.004, y - 0.01, z + 0.025, 28));
    add(ell(mats.black, 0.04, 0.05, 0.02, x + s * 0.004, y - 0.01, z + 0.05, 20));
    add(ell(mats.white, 0.016, 0.016, 0.012, x + 0.026, y + 0.035, z + 0.068, 10));
    // winged eyeliner arcs
    const pts = [];
    for (let a = 0; a <= 8; a++) { const t = a / 8; const px = x + s * (-0.125 + 0.25 * t) * -1; pts.push([x - s * 0.125 + s * 0.25 * t, y + 0.12 * Math.sin(Math.PI * t) + 0.005, 0]); }
    const arc = pts.map(p => [p[0], p[1], faceZ(p[0], p[1]) + 0.05]);
    arc.push([x + s * 0.19, y + 0.12, faceZ(x + s * 0.19, y + 0.12) + 0.04]);
    add(tube(mats.black, arc, 0.016, 30));
  }
  // brows (right one raised)
  const brow = (s, raise) => { const x0 = s * 0.34, x1 = s * 0.1; const p = [x0, x0 * 0.7 + x1 * 0.3, x1].map((x, i) => x);
    const ys = [2.6 + raise * 0.5, 2.67 + raise, 2.63 + raise * 1.5];
    return tube(mats.black, [[x0, ys[0], 0], [(x0 + x1) / 2, ys[1], 0], [x1, ys[2], 0]].map(([x, y]) => [x, y, faceZ(x, y) + 0.012]), 0.024); };
  add(brow(-1, 0)); add(brow(1, 0.05));
  add(box(mats.metal, 0.07, 0.014, 0.014, -0.25, 2.665, faceZ(-0.25, 2.665) + 0.03, 0.005)); // brow bar
  // nose, mouth, cheeks
  add(ell(mats.skinD, 0.05, 0.045, 0.045, 0, 2.28, faceZ(0, 2.28) + 0.015, 20));
  const mouth = [[-0.16, 2.14], [-0.05, 2.07], [0.07, 2.06], [0.2, 2.19]].map(([x, y]) => [x, y, faceZ(x, y) + 0.012]);
  add(tube(mats.lip, mouth, 0.02));
  add(tube(mats.lip, [[0.2, 2.19], [0.225, 2.22]].map(([x, y]) => [x, y, faceZ(x, y) + 0.012]), 0.014, 8));
  for (const s of [-1, 1]) { const x = s * 0.34, y = 2.2; const c = ell(mats.blush, 0.1, 0.075, 0.01, x, y, faceZ(x, y) - 0.002, 20); c.rotation.y = s * 0.6; add(c); }

  // ---------- hair: cap + neon spikes + swept-up front locks
  const cap = new THREE.Mesh(new THREE.SphereGeometry(1, 64, 40, 0, Math.PI * 2, 0, 1.3), mats.pink);
  cap.scale.set(0.66, 0.64, 0.62); cap.position.set(0, 2.46, -0.05); cap.rotation.x = -0.34; cap.castShadow = true; add(cap);
  const spikes = [[-80, 0.55, mats.teal], [-54, 0.72, mats.pink], [-27, 0.66, mats.teal], [0, 0.85, mats.pink], [27, 0.68, mats.teal], [54, 0.74, mats.pink], [80, 0.56, mats.teal]];
  spikes.forEach(([deg, h, m], i) => {
    const a = THREE.MathUtils.degToRad(deg); const dir = [Math.sin(a), Math.cos(a), 0.1 + (i % 2) * 0.18];
    const d = new THREE.Vector3(...dir).normalize();
    add(cone(m, 0.17, h, new THREE.Vector3(0, 2.46, -0.02).addScaledVector(d, 0.56).toArray(), dir));
  });
  // second row, further back, so the hair has depth from the sides and back
  [[-60, 0.6, mats.pink], [-20, 0.7, mats.teal], [20, 0.7, mats.pink], [60, 0.6, mats.teal], [0, 0.62, mats.teal]].forEach(([deg, h, m]) => {
    const a = THREE.MathUtils.degToRad(deg); const d = new THREE.Vector3(Math.sin(a) * 0.8, 0.6, -0.65).normalize();
    add(cone(m, 0.16, h, new THREE.Vector3(0, 2.46, -0.05).addScaledVector(d, 0.58).toArray(), d.toArray()));
  });
  [[-110, mats.teal], [110, mats.pink], [-150, mats.pink], [150, mats.teal], [180, mats.pink]].forEach(([deg, m]) => {
    const a = THREE.MathUtils.degToRad(deg); const d = new THREE.Vector3(Math.sin(a) * 0.9, 0.2, -Math.abs(Math.cos(a)) * 0.9 - 0.15).normalize();
    add(cone(m, 0.14, 0.42, new THREE.Vector3(0, 2.4, -0.05).addScaledVector(d, 0.6).toArray(), d.toArray()));
  });
  // messy locks sweeping up and forward from the hairline
  [[-0.3, mats.teal, 0.34], [-0.1, mats.pink, 0.4], [0.12, mats.teal, 0.42], [0.31, mats.pink, 0.32]].forEach(([x, m, h]) => {
    const y = 2.8; const z = faceZ(x, y) - 0.02;
    add(cone(m, 0.1, h, [x, y, z], [x * 0.7, 0.55, 0.9]));
  });

  g.traverse(o => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
  return g;
}
