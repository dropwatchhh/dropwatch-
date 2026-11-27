// Skinned jeans: one smooth surface per leg that bends at the knee (no tube joints), with fabric creases, ripped-knee patches and boot tuck.
import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
const lerp = (a, b, t) => a + (b - a) * t;
const sm = (a, b, x) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };
function cr(tab, y) {
  const n = tab.length; if (y >= tab[0][0]) return tab[0][1]; if (y <= tab[n - 1][0]) return tab[n - 1][1];
  let i = 0; while (y < tab[i + 1][0]) i++;
  const p0 = tab[Math.max(0, i - 1)][1], p1 = tab[i][1], p2 = tab[i + 1][1], p3 = tab[Math.min(n - 1, i + 2)][1], t = (tab[i][0] - y) / (tab[i][0] - tab[i + 1][0]), t2 = t * t, t3 = t2 * t;
  return 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3);
}
function grid(uSeg, vSeg, fn) {
  const pos = [], idx = [];
  for (let j = 0; j <= vSeg; j++) for (let i = 0; i <= uSeg; i++) { const p = fn(i / uSeg, j / vSeg); pos.push(p.x, p.y, p.z); }
  for (let j = 0; j < vSeg; j++) for (let i = 0; i < uSeg; i++) { const a = j * (uSeg + 1) + i, b = a + 1, c = a + uSeg + 1, d = c + 1; idx.push(a, c, b, b, c, d); }
  const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); g.setIndex(idx); g.computeVertexNormals(); return g;
}
export function buildJeans(rig, mats, opts) {
  const { hipY = 2.0, kneeY = 1.1, bones, rips = true } = opts;   // bones: [hipL, kneeL, hipR, kneeR]
  const YTOP = hipY + 0.05, YBOT = 0.5;
  // leg radius profile (y from top to bottom): thigh, knee bump, calf, tucked into the boot
  const R = [[YTOP, 0.215], [1.78, 0.205], [1.52, 0.185], [1.28, 0.158], [kneeY, 0.152], [0.95, 0.148], [0.78, 0.158], [0.6, 0.168], [YBOT, 0.168]];
  const cloth = mats.jeans.clone(); cloth.side = THREE.DoubleSide; cloth.roughness = 0.82;
  const frags = { cloth: [], skin: [], thread: [] };
  const legW = (s) => (p) => { const hi = s < 0 ? 0 : 2, ki = hi + 1; const wk = sm(kneeY + 0.2, kneeY - 0.22, p.y); return [[hi, 1 - wk], [ki, wk]]; };
  for (const s of [-1, 1]) {
    const cx = s * 0.2;
    const g = grid(56, 90, (u, v) => { const y = lerp(YTOP, YBOT, v), a = u * Math.PI * 2, r = cr(R, y);
      const front = Math.max(0, Math.cos(a)), back = Math.max(0, -Math.cos(a));
      // creases: knee front/back, groin, ankle bunching over the boot
      const kn = Math.exp(-(((y - kneeY) / 0.22) ** 2));
      const crease = 0.009 * Math.sin((y - kneeY) * 40) * kn * front + 0.012 * Math.sin((y - kneeY) * 36) * kn * back + 0.0035 * Math.sin(y * 55 + a * 2) * Math.exp(-(((y - 0.68) / 0.14) ** 2)) + 0.003 * Math.sin(y * 25 + s) * sm(1.45, 1.9, y) * Math.abs(Math.sin(a));
      const rr = r + crease, bow = 0.012 * Math.exp(-(((y - 1.45) / 0.5) ** 2));      // slight natural outward sweep of the thigh
      return new THREE.Vector3(cx + rr * 0.98 * Math.sin(a) + s * bow, y, rr * 1.04 * Math.cos(a) * (1 + 0.04 * back)); });
    g.userData.wf = legW(s); frags.cloth.push(g);
    // seams: outer and inner leg seam + back-yoke line
    for (const a0 of [Math.PI * 0.5, Math.PI * 1.5]) { const sg = grid(1, 70, (u, v) => { const y = lerp(YTOP - 0.04, YBOT + 0.03, v), r = cr(R, y) + 0.004, a = a0 + (u - 0.5) * 0.04; return new THREE.Vector3(cx + r * 0.98 * Math.sin(a), y, r * 1.04 * Math.cos(a)); }); sg.userData.wf = legW(s); frags.thread.push(sg); }
    // ripped knee / thigh patches: skin showing through a worn hole, with white threads
    if (rips) {
      const spots = s < 0 ? [[kneeY + 0.02, 0.0, 0.085, 0.065], [1.66, -0.2, 0.055, 0.04]] : [[1.55, 0.25, 0.07, 0.05]];
      for (const [y0, a0, rx, ry] of spots) {
        const patch = grid(24, 4, (u, v) => { const a = u * Math.PI * 2, rr = v, y = y0 + Math.sin(a) * ry * rr, r = cr(R, y) + 0.004 + 0.002 * v; const ang = a0 + Math.cos(a) * rx * rr / r; return new THREE.Vector3(cx + r * 0.98 * Math.sin(ang), y, r * 1.04 * Math.cos(ang)); });
        patch.userData.wf = legW(s); frags.skin.push(patch);
        for (let k = -1; k <= 1; k++) { const th = grid(1, 6, (u, v) => { const y = y0 + (v - 0.5) * ry * 1.7, r = cr(R, y) + 0.008, ang = a0 + k * rx * 0.45 + (u - 0.5) * 0.012; return new THREE.Vector3(cx + r * 0.98 * Math.sin(ang), y, r * 1.04 * Math.cos(ang)); }); th.userData.wf = legW(s); frags.thread.push(th); }
      }
    }
  }
  const skel = new THREE.Skeleton(bones), out = [];
  const matOf = { cloth, skin: mats.skin, thread: new THREE.MeshStandardMaterial({ color: 0xe9e1cf, roughness: 0.9, side: THREE.DoubleSide }) };
  matOf.skin = mats.skin.clone(); matOf.skin.side = THREE.DoubleSide;
  for (const [kind, list] of Object.entries(frags)) {
    if (!list.length) continue;
    const parts = list.map(g => { const pos = g.attributes.position, n = pos.count, si = new Uint16Array(n * 4), sw = new Float32Array(n * 4);
      for (let i = 0; i < n; i++) { const ws = g.userData.wf({ x: pos.getX(i), y: pos.getY(i), z: pos.getZ(i) }).filter(a => a[1] > 1e-4).sort((a, b) => b[1] - a[1]); const tot = ws.reduce((a, b) => a + b[1], 0) || 1; ws.slice(0, 4).forEach((a, k) => { si[i * 4 + k] = a[0]; sw[i * 4 + k] = a[1] / tot; }); }
      g.setAttribute('skinIndex', new THREE.Uint16BufferAttribute(si, 4)); g.setAttribute('skinWeight', new THREE.Float32BufferAttribute(sw, 4));
      if (!g.attributes.uv) g.setAttribute('uv', new THREE.Float32BufferAttribute(new Float32Array(n * 2), 2)); return g; });
    const merged = mergeGeometries(parts, false); if (kind === 'cloth') merged.computeVertexNormals();
    const mesh = new THREE.SkinnedMesh(merged, matOf[kind]); mesh.castShadow = true; mesh.receiveShadow = true; mesh.frustumCulled = false; out.push(mesh);
  }
  return { meshes: out, skeleton: skel };
}
