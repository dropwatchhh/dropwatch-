// World pieces for Episode 1: parking lot, detailed van, van cab, Maple Street, flower stand, and props. All real 3D, all original.
import * as THREE from 'three';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';

export const cv = (w, h, f) => { const c = document.createElement('canvas'); c.width = w; c.height = h; f(c.getContext('2d'), w, h); return c; };
export const tex = (c, rep) => { const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; if (rep) { t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(...rep); } t.anisotropy = 4; return t; };
export const std = (c, o = {}) => new THREE.MeshStandardMaterial({ color: c, roughness: 0.6, ...o });
const OA = (o, p) => { for (const k of Object.keys(p)) { if (k === 'position' || k === 'scale') o[k].copy(p[k]); else if (k === 'rotation') o.rotation.copy(p.rotation); else o[k] = p[k]; } return o; };
const shadows = (o, cast = true, recv = true) => { o.traverse(m => { if (m.isMesh) { m.castShadow = cast; m.receiveShadow = recv; } }); return o; };
export function legBetween(a, b, r, m, seg = 10) { const A = new THREE.Vector3(...a), B = new THREE.Vector3(...b), d = B.clone().sub(A), L = d.length(); const o = new THREE.Mesh(new THREE.CylinderGeometry(r, r, L, seg), m); o.position.copy(A.clone().add(B).multiplyScalar(0.5)); o.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), d.normalize()); o.castShadow = true; return o; }
export function skyGradient(stops) { return tex(cv(8, 512, (g, w, h) => { const gr = g.createLinearGradient(0, 0, 0, h); stops.forEach(([t, c]) => gr.addColorStop(t, c)); g.fillStyle = gr; g.fillRect(0, 0, w, h); })); }
export function sunSprite(x, y, z, s) { const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex(cv(256, 256, (g, w) => { const r = g.createRadialGradient(w / 2, w / 2, 0, w / 2, w / 2, w / 2); r.addColorStop(0, 'rgba(255,240,200,1)'); r.addColorStop(0.25, 'rgba(255,190,110,0.7)'); r.addColorStop(1, 'rgba(255,150,80,0)'); g.fillStyle = r; g.fillRect(0, 0, w, w); })), blending: THREE.AdditiveBlending, depthWrite: false, fog: false })); sp.position.set(x, y, z); sp.scale.set(s, s, 1); return sp; }
const windowTex = (c1, c2, rep) => tex(cv(256, 256, (g, w, h) => { g.fillStyle = c1; g.fillRect(0, 0, w, h); for (let y = 12; y < h - 20; y += 36) for (let x = 12; x < w - 20; x += 40) { g.fillStyle = Math.random() < 0.45 ? '#ffe3a0' : c2; g.fillRect(x, y, 24, 22); } }), rep);
const asphaltTex = rep => tex(cv(512, 512, (g, w, h) => { g.fillStyle = '#4a4655'; g.fillRect(0, 0, w, h); for (let i = 0; i < 9000; i++) { const v = 60 + Math.random() * 40; g.fillStyle = `rgba(${v},${v - 4},${v + 8},0.35)`; g.fillRect(Math.random() * w, Math.random() * h, 2, 2); } }), rep);

// ================= van (front faces +x) =================
export function makeVan(opts = {}) {
  const g = new THREE.Group(), body = std(0xe8803a, { roughness: 0.42, metalness: 0.05 }), cream = std(0xf4ead8), dark = std(0x23202c, { roughness: 0.4 }), glass = std(0x24344f, { roughness: 0.12, metalness: 0.3 }), chrome = std(0xd6d9e0, { metalness: 0.9, roughness: 0.25 });
  const add = (geo, m, x, y, z) => { const o = new THREE.Mesh(geo, m); o.position.set(x, y, z); o.castShadow = o.receiveShadow = true; g.add(o); return o; };
  add(new RoundedBoxGeometry(6.6, 2.2, 3.1, 8, 0.4), body, 0, 1.65, 0);
  add(new RoundedBoxGeometry(5.8, 0.45, 2.9, 6, 0.18), cream, -0.2, 2.9, 0);
  add(new RoundedBoxGeometry(2.0, 1.0, 3.14, 6, 0.2), glass, 2.1, 2.05, 0); add(new RoundedBoxGeometry(1.6, 0.95, 3.14, 6, 0.2), glass, -0.6, 2.05, 0); add(new RoundedBoxGeometry(1.2, 0.95, 3.14, 6, 0.2), glass, -2.2, 2.05, 0);
  add(new THREE.BoxGeometry(6.4, 0.14, 3.16), cream, 0, 1.25, 0);
  add(new RoundedBoxGeometry(0.4, 0.55, 3.2, 4, 0.1), dark, 3.35, 0.7, 0); add(new RoundedBoxGeometry(0.4, 0.55, 3.2, 4, 0.1), dark, -3.35, 0.7, 0);
  for (const z of [-1.0, 1.0]) { add(new THREE.SphereGeometry(0.22, 14, 10), new THREE.MeshBasicMaterial({ color: 0xfff1b8 }), 3.38, 1.55, z); add(new THREE.CylinderGeometry(0.3, 0.3, 0.04, 20), chrome, 3.31, 1.55, z).rotation.z = Math.PI / 2; add(new THREE.SphereGeometry(0.16, 12, 10), new THREE.MeshBasicMaterial({ color: 0xff3b3b }), -3.34, 1.55, z); }
  add(new RoundedBoxGeometry(0.1, 0.5, 1.3, 3, 0.04), dark, 3.36, 1.2, 0);                                  // grille
  for (let k = 0; k < 4; k++) add(new THREE.BoxGeometry(0.06, 0.02, 1.2), chrome, 3.42, 1.05 + k * 0.1, 0);
  add(new RoundedBoxGeometry(0.06, 0.2, 0.7, 3, 0.02), cream, -3.38, 0.75, 0);                               // plate
  for (const z of [-1.62, 1.62]) { add(new THREE.BoxGeometry(0.12, 0.35, 0.08), dark, 2.5, 2.2, z * 1.02); add(new RoundedBoxGeometry(0.1, 0.3, 0.22, 3, 0.04), dark, 2.5, 2.2, z * 1.1); }  // mirrors
  for (const z of [-1.57, 1.57]) { add(new RoundedBoxGeometry(0.5, 0.06, 0.04, 2, 0.02), chrome, 0.9, 1.7, z); add(new RoundedBoxGeometry(0.5, 0.06, 0.04, 2, 0.02), chrome, 1.6, 1.7, z); add(new THREE.BoxGeometry(0.03, 1.8, 0.02), dark, 1.2, 1.7, z); }   // door seams + handles
  const rack = new THREE.Group(); for (const x of [-2.2, 0.2, 2.2]) rack.add(legBetween([x, 3.15, -1.2], [x, 3.15, 1.2], 0.035, dark)); for (const z of [-1.2, 1.2]) rack.add(legBetween([-2.4, 3.15, z], [2.4, 3.15, z], 0.035, dark)); g.add(rack);
  add(new RoundedBoxGeometry(1.4, 0.9, 0.8, 4, 0.08), std(0x1c1b22, { roughness: 0.8 }), -0.8, 3.65, 0.2);       // amp on the roof
  add(new THREE.CircleGeometry(0.28, 20), std(0x3a3944, { roughness: 0.9 }), -0.8, 3.65, 0.61); g.children[g.children.length - 1].rotation.y = 0;
  const wheels = [];
  for (const [x, z] of [[2.2, 1.36], [2.2, -1.36], [-2.2, 1.36], [-2.2, -1.36]]) { const w = new THREE.Group(), t = new THREE.Mesh(new THREE.CylinderGeometry(0.58, 0.58, 0.5, 32), dark); t.rotation.x = Math.PI / 2; const hub = new THREE.Mesh(new THREE.CylinderGeometry(0.28, 0.28, 0.54, 24), chrome); hub.rotation.x = Math.PI / 2;
    w.add(t, hub); for (let k = 0; k < 5; k++) { const sp = new THREE.Mesh(new THREE.BoxGeometry(0.46, 0.05, 0.56), std(0x8a8e99)); sp.rotation.z = k * Math.PI / 5; w.add(sp); } w.position.set(x, 0.58, z); t.castShadow = true; g.add(w); wheels.push(w); }
  for (const [x, z] of [[2.2, 1.57], [2.2, -1.57], [-2.2, 1.57], [-2.2, -1.57]]) { const a = new THREE.Mesh(new THREE.CylinderGeometry(0.78, 0.78, 0.06, 28), std(0x15131b, { roughness: 0.9 })); a.rotation.x = Math.PI / 2; a.position.set(x, 0.62, z); g.add(a); }
  // stickers + band logo (original) on the side
  const decal = tex(cv(512, 256, (c, w, h) => { c.clearRect(0, 0, w, h); c.fillStyle = '#1fe6d2'; c.font = '900 92px Inter, sans-serif'; c.textAlign = 'center'; c.fillText('HOLLOW', w / 2, 120); c.fillStyle = '#ff2fa0'; c.fillText('VAN', w / 2, 220); }));
  for (const z of [1.58, -1.58]) { const d = new THREE.Mesh(new THREE.PlaneGeometry(2.4, 1.0), new THREE.MeshBasicMaterial({ map: decal, transparent: true })); d.position.set(-0.7, 1.55, z); if (z < 0) d.rotation.y = Math.PI; g.add(d); }
  g.userData.wheels = wheels; return g;
}

// ================= parking lot =================
export function makeLot(scene) {
  const grp = new THREE.Group();
  const ground = new THREE.Mesh(new THREE.PlaneGeometry(140, 140), new THREE.MeshStandardMaterial({ map: asphaltTex([16, 16]), roughness: 0.9 })); ground.rotation.x = -Math.PI / 2; ground.receiveShadow = true; grp.add(ground);
  for (let i = -6; i <= 6; i++) { const l = new THREE.Mesh(new THREE.BoxGeometry(0.12, 0.01, 3.6), std(0xf3efe2, { roughness: 0.8 })); l.position.set(i * 3.4, 0.006, -4.4); grp.add(l); }
  const curb = new THREE.Mesh(new THREE.BoxGeometry(80, 0.5, 1.2), std(0xb7b0b8)); curb.position.set(0, 0.25, -8.6); grp.add(curb); const walk = new THREE.Mesh(new THREE.BoxGeometry(80, 0.5, 5), std(0xd0c8c8)); walk.position.set(0, 0.25, -11.7); grp.add(walk);
  [[-24, 7, 12, 0x6c4f8a, '#5a3f78'], [-12, 10, 9, 0x2f8f8a, '#276f6c'], [-2, 6, 10, 0xd98a52, '#b86f3c'], [10, 12, 8, 0x8a4f7e, '#6e3a63'], [20, 8, 12, 0x3f6fa8, '#2f567f'], [32, 11, 9, 0xc4647a, '#9f4b60']].forEach(([x, h, w, col, wc]) => {
    const t = windowTex('#' + col.toString(16).padStart(6, '0'), wc, [Math.max(1, w / 5), Math.max(1, h / 5)]); const b = new THREE.Mesh(new THREE.BoxGeometry(w, h, 8), new THREE.MeshStandardMaterial({ map: t, roughness: 0.8 })); b.position.set(x, h / 2, -18); grp.add(b); });
  for (const x of [-14, -6.5, 4.5, 14]) { const tr = new THREE.Mesh(new THREE.CylinderGeometry(0.22, 0.28, 2.4, 10), std(0x6b4a34)); tr.position.set(x, 1.7, -10.8); const cr = new THREE.Mesh(new THREE.SphereGeometry(1.6, 20, 16), std(0x4f8f4a, { roughness: 0.9 })); cr.position.set(x, 4.0, -10.8); cr.scale.y = 1.15; grp.add(tr, cr); }
  for (const x of [-9, 7, 17]) { const p = new THREE.Mesh(new THREE.CylinderGeometry(0.09, 0.12, 6.2, 10), std(0x333344)); p.position.set(x, 3.1, -9.2); const l = new THREE.Mesh(new THREE.SphereGeometry(0.3, 12, 10), new THREE.MeshBasicMaterial({ color: 0xffe9b0 })); l.position.set(x, 6.3, -9.2); grp.add(p, l); }
  for (const x of [-7, -3.3, 6.5]) { const b = new THREE.Mesh(new THREE.CylinderGeometry(0.16, 0.18, 0.9, 12), std(0xf2c230, { roughness: 0.5 })); b.position.set(x, 0.45, -7.2); grp.add(b); }   // bollards
  const dump = new THREE.Mesh(new RoundedBoxGeometry(2.2, 1.5, 1.2, 3, 0.08), std(0x2f6f4a)); dump.position.set(-9, 0.75, -9.8); grp.add(dump);
  shadows(grp); scene.add(grp); return grp;
}

// ================= Maple Street (downhill toward the flower stand; camera looks down -z, road falls away) =================
export function makeStreet(scene) {
  const grp = new THREE.Group();
  const road = new THREE.Mesh(new THREE.PlaneGeometry(10, 160), new THREE.MeshStandardMaterial({ map: asphaltTex([3, 40]), roughness: 0.9 })); road.rotation.x = -Math.PI / 2; road.position.set(0, 0, -50); road.receiveShadow = true; grp.add(road);
  for (let i = 0; i < 30; i++) { const l = new THREE.Mesh(new THREE.BoxGeometry(0.16, 0.01, 2.2), std(0xf2c230)); l.position.set(0, 0.01, 8 - i * 4.4); grp.add(l); }
  for (const s of [-1, 1]) { const sw = new THREE.Mesh(new THREE.BoxGeometry(5, 0.35, 160), std(0xd2cac8)); sw.position.set(s * 7.5, 0.18, -50); sw.receiveShadow = true; grp.add(sw); const cb = new THREE.Mesh(new THREE.BoxGeometry(0.4, 0.4, 160), std(0xaaa4ac)); cb.position.set(s * 5.1, 0.2, -50); grp.add(cb);
    const lawn = new THREE.Mesh(new THREE.BoxGeometry(20, 0.3, 160), std(0x5f9e52, { roughness: 1 })); lawn.position.set(s * 20, 0.15, -50); lawn.receiveShadow = true; grp.add(lawn); }
  const cols = [0xf0c8a0, 0xa8d8e0, 0xf2a0a8, 0xc8e0a0, 0xe8d070, 0xb8a8e0], roofC = [0x8a4a3a, 0x4a5a8a, 0x6a4a6a];
  for (const s of [-1, 1]) for (let i = 0; i < 8; i++) { const z = 4 - i * 11, c = cols[(i + (s > 0 ? 3 : 0)) % cols.length]; const h = new THREE.Group();
    const body = new THREE.Mesh(new RoundedBoxGeometry(6.4, 4.2, 5.6, 3, 0.1), std(c, { roughness: 0.8 })); body.position.y = 2.1; h.add(body);
    const roof = new THREE.Mesh(new THREE.ConeGeometry(5.2, 2.4, 4), std(roofC[i % 3], { roughness: 0.8 })); roof.rotation.y = Math.PI / 4; roof.scale.set(1.0, 1, 0.86); roof.position.y = 5.4; h.add(roof);
    const door = new THREE.Mesh(new THREE.BoxGeometry(1.0, 1.9, 0.12), std(0x5a3f6a)); door.position.set(s > 0 ? -3.2 : 3.2, 0.95, 0); door.rotation.y = s > 0 ? Math.PI / 2 : -Math.PI / 2; h.add(door);
    for (const dz of [-1.5, 1.5]) { const w = new THREE.Mesh(new THREE.BoxGeometry(1.1, 1.1, 0.12), new THREE.MeshBasicMaterial({ color: Math.random() < 0.5 ? 0xffe3a0 : 0x6f8fb8 })); w.position.set(s > 0 ? -3.2 : 3.2, 2.5, dz); w.rotation.y = s > 0 ? Math.PI / 2 : -Math.PI / 2; h.add(w); }
    const porch = new THREE.Mesh(new THREE.BoxGeometry(2.4, 0.3, 2.0), std(0xd8c8b0)); porch.position.set(s > 0 ? -3.4 : 3.4, 0.15, 0); h.add(porch);
    h.position.set(s * 17, 0, z); grp.add(h);
    for (let k = 0; k < 7; k++) { const f = new THREE.Mesh(new THREE.BoxGeometry(0.14, 1.0, 0.1), std(0xf4f0e8)); f.position.set(s * 10.2, 0.6, z - 3 + k * 1.0); grp.add(f); }
    const tr = new THREE.Mesh(new THREE.CylinderGeometry(0.2, 0.26, 2.2, 10), std(0x6b4a34)); tr.position.set(s * 9, 1.5, z + 4.2); const cr = new THREE.Mesh(new THREE.SphereGeometry(1.5, 18, 14), std(i % 2 ? 0x4f8f4a : 0x6aa84f, { roughness: 0.9 })); cr.position.set(s * 9, 3.7, z + 4.2); grp.add(tr, cr); }
  const sign = new THREE.Group(); sign.add(legBetween([0, 0, 0], [0, 4.2, 0], 0.07, std(0x777788))); const plate = new THREE.Mesh(new THREE.BoxGeometry(2.6, 0.7, 0.08), std(0x1f8f4a)); plate.position.y = 4.2; sign.add(plate);
  const txt = new THREE.Mesh(new THREE.PlaneGeometry(2.4, 0.55), new THREE.MeshBasicMaterial({ map: tex(cv(512, 128, (c, w, h) => { c.fillStyle = '#1f8f4a'; c.fillRect(0, 0, w, h); c.fillStyle = '#fff'; c.font = '900 84px Inter, sans-serif'; c.textAlign = 'center'; c.fillText('MAPLE ST', w / 2, 94); })) })); txt.position.set(0, 4.2, 0.05); sign.add(txt); sign.position.set(5.9, 0, -2); grp.add(sign);
  const hyd = new THREE.Group(); hyd.add(new THREE.Mesh(new THREE.CylinderGeometry(0.22, 0.26, 0.8, 12), std(0xd23a3a))); hyd.add(OA(new THREE.Mesh(new THREE.SphereGeometry(0.24, 12, 10), std(0xd23a3a)), { position: new THREE.Vector3(0, 0.45, 0) })); hyd.position.set(-5.9, 0.4, -9); grp.add(hyd);
  for (let i = 0; i < 4; i++) { const p = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.16, 8, 8), std(0x5a4a3a)); p.position.set(7.2, 4, -6 - i * 22); grp.add(p); const arm = new THREE.Mesh(new THREE.BoxGeometry(2.4, 0.14, 0.14), std(0x5a4a3a)); arm.position.set(7.2, 7.4, -6 - i * 22); grp.add(arm); }
  shadows(grp); scene.add(grp); return grp;
}

// ================= flower stand =================
export function makeTulips(n, colors, seed = 1) {
  const g = new THREE.Group(); let a = seed; const R = () => { a = (a * 16807) % 2147483647; return a / 2147483647; };
  const stem = new THREE.InstancedMesh(new THREE.CylinderGeometry(0.018, 0.018, 1, 6), std(0x4f8f3a), n), head = new THREE.InstancedMesh(new THREE.SphereGeometry(0.1, 12, 10), std(0xffffff, { roughness: 0.5 }), n), leaf = new THREE.InstancedMesh(new THREE.ConeGeometry(0.06, 0.5, 4), std(0x5aa040), n);
  const m = new THREE.Matrix4(), q = new THREE.Quaternion(), e = new THREE.Euler(), c = new THREE.Color();
  for (let i = 0; i < n; i++) { const ang = R() * 6.283, rr = Math.sqrt(R()) * 0.28, h = 0.55 + R() * 0.35, tilt = 0.25 * rr / 0.28 + R() * 0.12;
    e.set(Math.sin(ang) * tilt, 0, -Math.cos(ang) * tilt); q.setFromEuler(e); const base = new THREE.Vector3(Math.cos(ang) * rr * 0.4, 0, Math.sin(ang) * rr * 0.4);
    m.compose(base.clone().add(new THREE.Vector3(0, h / 2, 0).applyQuaternion(q)), q, new THREE.Vector3(1, h, 1)); stem.setMatrixAt(i, m);
    m.compose(base.clone().add(new THREE.Vector3(0, h + 0.05, 0).applyQuaternion(q)), q, new THREE.Vector3(1, 1.3, 1)); head.setMatrixAt(i, m); head.setColorAt(i, c.set(colors[i % colors.length]));
    m.compose(base.clone().add(new THREE.Vector3(0.08, 0.28, 0).applyQuaternion(q)), q, new THREE.Vector3(1, 1, 1)); leaf.setMatrixAt(i, m); }
  g.add(stem, head, leaf); return g;
}
export function makeStand() {
  const g = new THREE.Group(), wood = std(0x9a6a3a, { roughness: 0.8 }), wood2 = std(0xc08a52, { roughness: 0.8 });
  const add = (geo, m, x, y, z) => { const o = new THREE.Mesh(geo, m); o.position.set(x, y, z); g.add(o); return o; };
  add(new RoundedBoxGeometry(6.2, 1.5, 1.5, 3, 0.06), wood, 0, 0.75, 0); add(new THREE.BoxGeometry(6.4, 0.12, 1.7), wood2, 0, 1.54, 0);
  add(new THREE.BoxGeometry(6.2, 3.8, 0.2), wood, 0, 2.7, -0.8); for (const x of [-3.0, 3.0]) add(new THREE.BoxGeometry(0.22, 4.2, 0.22), wood2, x, 2.1, 0.6);
  const aw = tex(cv(256, 128, (c, w, h) => { for (let i = 0; i < 8; i++) { c.fillStyle = i % 2 ? '#ffffff' : '#e8407a'; c.fillRect(i * 32, 0, 32, h); } }));
  const awn = add(new THREE.BoxGeometry(6.8, 0.1, 2.4), new THREE.MeshStandardMaterial({ map: aw, roughness: 0.7 }), 0, 4.2, 0.1); awn.rotation.x = 0.25;
  const fr = add(new THREE.BoxGeometry(6.8, 0.5, 0.06), new THREE.MeshStandardMaterial({ map: aw, roughness: 0.7 }), 0, 3.85, 1.25);
  const signT = tex(cv(1024, 192, (c, w, h) => { c.fillStyle = '#fff6e0'; c.fillRect(0, 0, w, h); c.strokeStyle = '#e8407a'; c.lineWidth = 12; c.strokeRect(10, 10, w - 20, h - 20); c.fillStyle = '#7a2a5a'; c.font = '900 98px Inter, sans-serif'; c.textAlign = 'center'; c.fillText("NANA DOT'S FLOWERS", w / 2, 128); }));
  add(new THREE.PlaneGeometry(5.0, 0.94), new THREE.MeshBasicMaterial({ map: signT }), 0, 3.2, -0.68);
  const cols = [0xe8407a, 0xffd23f, 0xff7a3a, 0xb06cff, 0xffffff, 0xff3b5c];
  [[-2.5, 0], [-1.45, 0.1], [1.45, 0], [2.5, 0.05]].forEach(([x, z], i) => { const b = new THREE.Group(); const bucket = new THREE.Mesh(new THREE.CylinderGeometry(0.5, 0.42, 0.7, 20), std([0x3a8fd2, 0xd2573a, 0x4aa86a, 0xc9a23a][i], { metalness: 0.5, roughness: 0.4 })); bucket.position.y = 0.35; b.add(bucket); const t = makeTulips(34, cols.slice(i % 3, i % 3 + 3), 3 + i); t.position.y = 0.55; b.add(t); b.position.set(x, 1.6, z + 0.35); g.add(b); });
  const wc = new THREE.Group(); wc.add(new THREE.Mesh(new THREE.CylinderGeometry(0.28, 0.32, 0.5, 16), std(0x2fa8a0, { metalness: 0.6, roughness: 0.35 }))); const sp = legBetween([0.2, 0.2, 0], [0.75, 0.55, 0], 0.045, std(0x2fa8a0, { metalness: 0.6 })); wc.add(sp); wc.add(new THREE.Mesh(new THREE.TorusGeometry(0.2, 0.03, 8, 20, Math.PI), std(0x2fa8a0, { metalness: 0.6 }))); wc.children[2].position.set(0, 0.3, 0); wc.position.set(-2.9, 0.25, 1.3); g.add(wc);
  for (let i = 0; i < 3; i++) add(new RoundedBoxGeometry(0.9, 0.5, 0.7, 2, 0.04), wood2, 2.6 + (i % 2) * 0.1, 0.25 + i * 0.5, 1.3);
  const bulbs = []; for (let i = 0; i < 12; i++) { const t = i / 11; const bu = new THREE.Mesh(new THREE.SphereGeometry(0.07, 8, 6), new THREE.MeshBasicMaterial({ color: 0xffe6a0 })); bu.position.set(-3.2 + t * 6.4, 4.05 - Math.sin(t * Math.PI) * 0.25, 1.3); g.add(bu); }
  shadows(g); return g;
}

// ================= van cab interior (camera sits inside; driver on the -z side faces +x) =================
export function makeCab(scene) {
  const g = new THREE.Group(), vinyl = std(0x2c2a36, { roughness: 0.7 }), seatC = std(0x8a3a4a, { roughness: 0.8 }), dash = std(0x23212b, { roughness: 0.55 }), trim = std(0xd6d9e0, { metalness: 0.8, roughness: 0.3 });
  const add = (geo, m, x, y, z) => { const o = new THREE.Mesh(geo, m); o.position.set(x, y, z); g.add(o); return o; };
  add(new THREE.BoxGeometry(5.2, 0.2, 3.4), vinyl, 0, 0.0, 0);                                                                       // floor
  add(new RoundedBoxGeometry(1.6, 1.0, 3.2, 5, 0.12), dash, 2.0, 1.3, 0);                                                              // dashboard
  add(new THREE.BoxGeometry(0.6, 0.9, 3.3), dash, 2.45, 1.95, 0);
  const gpsT = tex(cv(256, 160, (c, w, h) => { c.fillStyle = '#10243f'; c.fillRect(0, 0, w, h); c.strokeStyle = '#2f6fb8'; c.lineWidth = 6; c.beginPath(); c.moveTo(20, 120); c.lineTo(110, 70); c.lineTo(170, 90); c.lineTo(236, 30); c.stroke(); c.fillStyle = '#ff2fa0'; c.beginPath(); c.arc(236, 30, 12, 0, 7); c.fill(); c.fillStyle = '#fff'; c.font = '700 22px Inter, sans-serif'; c.fillText('NANA DOT\'S FLOWERS', 14, 26); }));
  const gps = add(new RoundedBoxGeometry(0.1, 0.65, 0.95, 3, 0.04), std(0x15141c), 1.6, 2.15, 0.1); const gs = add(new THREE.PlaneGeometry(0.9, 0.56), new THREE.MeshBasicMaterial({ map: gpsT }), 1.54, 2.15, 0.1); gs.rotation.y = -Math.PI / 2; gps.rotation.z = 0;
  const wheel = new THREE.Group(); wheel.add(new THREE.Mesh(new THREE.TorusGeometry(0.62, 0.075, 14, 40), std(0x15141c, { roughness: 0.5 })));
  for (const a of [0, 120, 240]) { const sp = legBetween([0, 0, 0], [Math.sin(a * Math.PI / 180) * 0.6, Math.cos(a * Math.PI / 180) * 0.6, 0], 0.05, std(0x15141c)); wheel.add(sp); } wheel.add(OA(new THREE.Mesh(new THREE.CylinderGeometry(0.16, 0.16, 0.1, 18), trim), { rotation: new THREE.Euler(Math.PI / 2, 0, 0) }));
  wheel.rotation.y = Math.PI / 2; wheel.rotation.x = 0.0; wheel.position.set(1.15, 2.0, -0.9); wheel.rotation.z = 0.5; g.add(wheel); g.userData.wheel = wheel;
  add(new THREE.CylinderGeometry(0.1, 0.1, 0.9, 12), dash, 1.5, 1.8, -0.9).rotation.z = 1.2;
  for (const z of [-0.9, 0.95]) { const seat = new THREE.Group(); seat.add(OA(new THREE.Mesh(new RoundedBoxGeometry(1.4, 0.4, 1.3, 4, 0.12), seatC), { position: new THREE.Vector3(0, 0.6, 0) })); seat.add(OA(new THREE.Mesh(new RoundedBoxGeometry(0.35, 1.7, 1.3, 4, 0.14), seatC), { position: new THREE.Vector3(-0.65, 1.3, 0) })); seat.add(OA(new THREE.Mesh(new RoundedBoxGeometry(0.4, 0.5, 0.9, 3, 0.1), seatC), { position: new THREE.Vector3(-0.7, 2.3, 0) })); seat.position.set(-0.3, 0, z); g.add(seat); }
  add(new RoundedBoxGeometry(0.9, 0.35, 0.9, 4, 0.12), std(0xf0b030, { roughness: 0.8 }), -0.2, 0.95, -0.9);                              // Gig's booster cushion
  add(new THREE.BoxGeometry(0.1, 3.0, 3.4), std(0x1b1a22), 0.6, 2.2, 0).visible = false;
  const win = new THREE.Mesh(new THREE.PlaneGeometry(3.4, 1.6), new THREE.MeshBasicMaterial({ color: 0x9fd0ff, transparent: true, opacity: 0.12, depthWrite: false })); win.position.set(2.8, 2.35, 0); win.rotation.y = -Math.PI / 2 - 0.2; g.add(win);
  for (const z of [-1.7, 1.7]) { add(new THREE.BoxGeometry(5.2, 0.1, 0.14), trim, 0, 3.15, z); add(new THREE.BoxGeometry(5.2, 1.0, 0.1), vinyl, 0, 0.7, z); add(new THREE.BoxGeometry(0.16, 2.3, 0.16), trim, 2.45, 2.0, z); }
  add(new THREE.BoxGeometry(5.2, 0.12, 3.4), std(0xcfc5b0), 0, 3.25, 0);                                                                    // ceiling
  const mir = add(new RoundedBoxGeometry(0.1, 0.3, 0.7, 3, 0.04), dash, 2.5, 3.0, 0); add(new THREE.CylinderGeometry(0.02, 0.02, 0.25, 6), trim, 2.5, 3.1, 0.0).rotation.z = 0;
  const tree = new THREE.Mesh(new THREE.ConeGeometry(0.18, 0.5, 4), std(0x30c86a)); tree.position.set(2.3, 2.7, 0.2); tree.rotation.x = Math.PI; g.add(tree);
  const cup = new THREE.Group(); cup.add(new THREE.Mesh(new THREE.CylinderGeometry(0.17, 0.12, 0.34, 16), std(0xf2f0ea))); cup.add(OA(new THREE.Mesh(new THREE.CylinderGeometry(0.17, 0.17, 0.04, 16), std(0xe8407a)), { position: new THREE.Vector3(0, 0.17, 0) })); cup.add(legBetween([0.0, 0.17, 0], [0.12, 0.45, 0.04], 0.012, std(0xe8d090))); cup.position.set(1.8, 1.85, 0.8); g.add(cup);
  shadows(g); scene.add(g); return g;
}

// ================= props =================
export function makeGuitar() {
  const g = new THREE.Group(), body = std(0xff8a2a, { roughness: 0.3, metalness: 0.1 }), edge = std(0x7a2a0a, { roughness: 0.4 }), neck = std(0xc8975a, { roughness: 0.5 });
  const sh = new THREE.Shape(); sh.moveTo(0, -0.7); sh.bezierCurveTo(0.55, -0.7, 0.75, -0.3, 0.45, 0.0); sh.bezierCurveTo(0.35, 0.1, 0.42, 0.35, 0.3, 0.55); sh.bezierCurveTo(0.12, 0.8, -0.12, 0.8, -0.3, 0.55); sh.bezierCurveTo(-0.42, 0.35, -0.35, 0.1, -0.45, 0.0); sh.bezierCurveTo(-0.75, -0.3, -0.55, -0.7, 0, -0.7);
  const b = new THREE.Mesh(new THREE.ExtrudeGeometry(sh, { depth: 0.14, bevelEnabled: true, bevelThickness: 0.04, bevelSize: 0.04, bevelSegments: 3 }), body); b.position.z = -0.07; g.add(b);
  const guard = new THREE.Mesh(new THREE.ExtrudeGeometry(sh, { depth: 0.01, bevelEnabled: false }), std(0x2fe0a0, { roughness: 0.3 })); guard.scale.set(0.6, 0.5, 1); guard.position.set(0.08, -0.1, 0.1); g.add(guard);
  const nk = new THREE.Mesh(new THREE.BoxGeometry(0.15, 1.5, 0.08), neck); nk.position.set(0, 1.45, 0); g.add(nk); const hd = new THREE.Mesh(new THREE.BoxGeometry(0.22, 0.4, 0.07), edge); hd.position.set(0, 2.38, 0); g.add(hd);
  for (let i = 0; i < 6; i++) { const s = new THREE.Mesh(new THREE.CylinderGeometry(0.004, 0.004, 3.0, 4), std(0xe6e6ee, { metalness: 1, roughness: 0.3 })); s.position.set(-0.05 + i * 0.02, 0.85, 0.07); g.add(s); }
  for (const y of [-0.3, 0.05]) { const pk = new THREE.Mesh(new THREE.BoxGeometry(0.34, 0.07, 0.06), std(0x1a1a22)); pk.position.set(0, y, 0.12); g.add(pk); }
  for (let i = 0; i < 6; i++) { const t = new THREE.Mesh(new THREE.CylinderGeometry(0.025, 0.025, 0.05, 8), std(0xd8dbe2, { metalness: 1 })); t.rotation.z = Math.PI / 2; t.position.set((i % 2 ? 0.1 : -0.1), 2.25 + Math.floor(i / 2) * 0.12, 0); g.add(t); }
  shadows(g); return g;
}
export function makePigeon() {
  const g = new THREE.Group(), gray = std(0x8f95a8, { roughness: 0.9 }), dark = std(0x4a4f64), neck = std(0x6aa88f, { roughness: 0.5, metalness: 0.2 });
  const add = (m) => { g.add(m); return m; };
  add(OA(new THREE.Mesh(new THREE.SphereGeometry(0.32, 14, 10), gray), { scale: new THREE.Vector3(1.4, 0.85, 0.8) }));
  add(OA(new THREE.Mesh(new THREE.SphereGeometry(0.16, 12, 10), gray), { position: new THREE.Vector3(0.42, 0.18, 0) }));
  add(OA(new THREE.Mesh(new THREE.SphereGeometry(0.13, 10, 8), neck), { position: new THREE.Vector3(0.32, 0.1, 0), scale: new THREE.Vector3(1, 1.1, 1.1) }));
  add(OA(new THREE.Mesh(new THREE.ConeGeometry(0.04, 0.12, 6), std(0xf0b050)), { position: new THREE.Vector3(0.6, 0.18, 0), rotation: new THREE.Euler(0, 0, -Math.PI / 2) }));
  add(OA(new THREE.Mesh(new THREE.SphereGeometry(0.025, 8, 6), new THREE.MeshBasicMaterial({ color: 0xffa020 })), { position: new THREE.Vector3(0.52, 0.24, 0.1) }));
  add(OA(new THREE.Mesh(new THREE.ConeGeometry(0.16, 0.5, 6), dark), { position: new THREE.Vector3(-0.55, 0, 0), rotation: new THREE.Euler(0, 0, Math.PI / 2 + 0.2), scale: new THREE.Vector3(1, 1, 0.4) }));
  const wings = []; for (const s of [-1, 1]) { const w = new THREE.Group(); const wm = new THREE.Mesh(new THREE.SphereGeometry(0.3, 12, 8), gray); wm.scale.set(0.9, 0.08, 1.3); wm.position.set(0, 0, s * 0.4); w.add(wm); const tip = new THREE.Mesh(new THREE.SphereGeometry(0.2, 10, 6), dark); tip.scale.set(0.8, 0.06, 1.0); tip.position.set(-0.1, 0, s * 0.85); w.add(tip); w.position.set(0, 0.1, 0); g.add(w); wings.push(w); }
  g.userData.wings = wings; shadows(g); return g;
}
