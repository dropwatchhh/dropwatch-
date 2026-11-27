// Animation library for Episode 1 (step 2): pose generators as pure functions of time, plus helpers for Gig (IK paws), Nana Dot, the van, pigeons and tulips.
// Poses use the rig API: sh:[forward,out], el, curl[5], legs hip:[forward,out], knee; extras: pitch/roll (whole body), rootY, phone, bootL/bootR.
const D = Math.PI / 180, OPEN = [0.1, 0.1, 0.1, 0.1, 0.1], FIST = [0.85, 1, 1, 1, 1], RELAX = [0.35, 0.45, 0.5, 0.55, 0.6];
const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v)), lerp = (a, b, t) => a + (b - a) * t, sm = (a, b, x) => { const t = clamp((x - a) / (b - a)); return t * t * (3 - 2 * t); };
const mixv = (a, b, k) => Array.isArray(a) ? a.map((x, i) => mixv(x, b[i], k)) : (a && typeof a === 'object') ? Object.fromEntries(Object.keys(a).map(key => [key, mixv(a[key], b[key] ?? a[key], k)])) : typeof a === 'number' ? lerp(a, b, k) : (k < 0.5 ? a : b);
export const mixPose = mixv;
const base = (o = {}) => ({ yaw: 0, spine: [0, 0, 0], head: [0, 0, 0], L: { sh: [6, 10], el: 14, curl: RELAX }, R: { sh: [4, 10], el: 18, curl: RELAX }, legL: { hip: [4, 3], knee: 8 }, legR: { hip: [-3, 3], knee: 4 }, ...o });

// ---------------- Dex ----------------
// run cycle: p = stride phase (radians). amp scales the stride (1 = jog, 1.3 = sprint)
export function run(p, o = {}) {
  const amp = o.amp ?? 1, leg = (pp) => ({ hip: [(46 * amp) * Math.sin(pp) + 6, 2], knee: 12 + 78 * amp * Math.pow(Math.max(0, Math.cos(pp)), 1.15) });
  const arm = (pp, s) => ({ sh: [(68 * amp) * Math.sin(pp + Math.PI) * s + 14, 6], el: 92 + 22 * Math.sin(pp * s + (s > 0 ? 0 : Math.PI)), curl: FIST });
  const P = base({ yaw: o.yaw ?? 0, spine: [(12 + 7 * (amp - 1) * 3) * (o.lean ?? 1), 5 * Math.sin(p), 0], head: [-9 * (o.lean ?? 1), -3 * Math.sin(p), 0], L: arm(p, 1), R: arm(p, -1), legL: leg(p), legR: leg(p + Math.PI) });
  P.bob = 0.06 * amp * Math.abs(Math.cos(p)) - 0.02;
  if (o.phone) { P.R = { sh: [98, 14], el: 62 + 5 * Math.sin(p * 2), curl: FIST, phone: true, roll: 20 }; P.head = [-4, 4 * Math.sin(p), 0]; }
  return P;
}
// stride phase for a given time and speed in m/s (stride length about 1.5 m for Dex)
export const stridePhase = (t, speed = 4.5) => 2 * Math.PI * (speed / 1.5) * t * 0.5;
// the left boot flies off: quick kick, then hopping on one sock foot with arms flailing. t in 0..1
export function bootLoss(t, p) {
  const kick = sm(0.18, 0.34, t) * (1 - sm(0.34, 0.5, t)), hop = sm(0.5, 0.62, t);
  const P = run(p, { amp: 1 - 0.3 * hop });
  P.legL = mixv(P.legL, { hip: [78, 6], knee: 6 }, kick);                              // the kick
  P.legL = mixv(P.legL, { hip: [28 + 14 * Math.sin(p * 2), 8], knee: 62 }, sm(0.42, 0.6, t));    // dangling after the boot is gone
  P.legR = mixv(P.legR, { hip: [-6, 4], knee: 24 + 22 * Math.abs(Math.sin(p)) }, hop);       // hopping leg
  const flail = hop * (0.6 + 0.4 * Math.sin(p * 2));
  P.L = mixv(P.L, { sh: [150, 40], el: 25, curl: OPEN }, flail); P.R = mixv(P.R, { sh: [135, -10], el: 30, curl: OPEN }, flail);
  P.spine = [8 - 14 * hop, 0, 8 * hop * Math.sin(p)]; P.head = [-4, 0, 0];
  return P;
}
// dive for the bumper then hang/drag. t: 0 crouch, .25 launch, .6 grab, 1 dragged. rootY and pitch included
export function dive(t) {
  const crouch = sm(0, 0.22, t), launch = sm(0.22, 0.6, t);
  const P = base({
    yaw: 180, spine: [lerp(14, 4, launch) + 18 * crouch * (1 - launch), 0, 0], head: [-14 * launch, 0, 0],
    L: mixv({ sh: [60, 14], el: 85, curl: FIST }, { sh: [170, 8], el: 8, curl: [0.4, 0.5, 0.5, 0.5, 0.5] }, launch),
    R: mixv({ sh: [60, 14], el: 85, curl: FIST }, { sh: [170, 8], el: 8, curl: [0.4, 0.5, 0.5, 0.5, 0.5] }, launch),
    legL: mixv({ hip: [46, 4], knee: 78 }, { hip: [-20, 6], knee: 38 }, launch), legR: mixv({ hip: [46, 4], knee: 78 }, { hip: [-26, 6], knee: 52 }, launch),
  });
  P.pitch = 84 * Math.pow(launch, 0.8); P.rootY = 0.95 * Math.sin(Math.PI * Math.min(1, launch * 1.0)) + 0.2 * launch; if (t < 0.22) { delete P.rootY; P.pitch = 0; }
  return P;
}
// dragged belly-down behind the van, both hands on the bumper, legs bouncing, one hand optionally holding the phone selfie-style
export function drag(g, o = {}) {
  const P = base({ yaw: 180, spine: [0, 0, 0], head: [-34, 4 * Math.sin(g * 9), 0],
    L: { sh: [172, 6], el: 6, curl: [0.5, 0.9, 0.9, 0.9, 0.9] }, R: o.selfie ? { sh: [150, 30], el: 70, curl: FIST, phone: true, roll: 10 } : { sh: [172, -6], el: 6, curl: [0.5, 0.9, 0.9, 0.9, 0.9] },
    legL: { hip: [-10 + 14 * Math.sin(g * 11), 6], knee: 30 + 24 * Math.max(0, Math.sin(g * 11)) }, legR: { hip: [-10 + 14 * Math.sin(g * 11 + 2), 6], knee: 30 + 24 * Math.max(0, Math.sin(g * 11 + 2)) } });
  P.pitch = 84; P.rootY = 0.2 + 0.03 * Math.abs(Math.sin(g * 11)); return P;
}
// hanging on to the side of the van while it speeds up: body leaning back, feet scuffing
export function hang(g) {
  const P = base({ yaw: 180, spine: [-10, 0, 0], head: [-12, 0, 0], L: { sh: [150, 14], el: 25, curl: FIST }, R: { sh: [150, -4], el: 25, curl: FIST },
    legL: { hip: [-20 + 22 * Math.sin(g * 9), 6], knee: 40 + 24 * Math.max(0, Math.sin(g * 9)) }, legR: { hip: [-20 + 22 * Math.sin(g * 9 + 3), 6], knee: 40 + 24 * Math.max(0, Math.sin(g * 9 + 3)) } });
  P.pitch = 58; P.rootY = 0.12 + 0.02 * Math.abs(Math.sin(g * 9)); return P;
}
// reaching for the guitar neck with the free hand while hanging on with the other
export function reach(t, g) {
  const P = hang(g); const k = sm(0, 0.7, t); P.R = mixv(P.R, { sh: [165, 24], el: 6, curl: [0.3, 0.5, 0.5, 0.5, 0.5] }, k); P.head = [-6, 14 * k, 0]; return P;
}
export const shock = (t) => base({ yaw: 0, spine: [-6, 0, 0], head: [-6, 0, 0], L: { sh: [60, 60], el: 40, curl: OPEN }, R: { sh: [60, 60], el: 40, curl: OPEN } });

// ---------------- Gig ----------------
export const gigCover = (t) => ({ head: [-4, 0, 0], L: { sh: [150, 10], el: 128, curl: 1 }, R: { sh: [150, 10], el: 128, curl: 1 }, legL: { hip: 85, knee: 80 }, legR: { hip: 85, knee: 80 }, tail: [20, 0] });
export const gigLookCam = (t, yawDeg = 40) => ({ head: [-2, yawDeg * sm(0, 0.4, t), 6 * sm(0, 0.4, t)], L: { sh: [40, 10], el: 60, curl: 1 }, R: { sh: [40, 10], el: 60, curl: 1 }, legL: { hip: 85, knee: 80 }, legR: { hip: 85, knee: 80 }, tail: [20, 0] });
// IK for a paw to a world target (3 joint angles solved numerically); THREE is passed in
export function ikPaw(THREE, gig, key, target, init) {
  const a = gig.j.arms[key], s = a.s; let x = a._ik ?? init ?? [45, 20, 70];
  const apply = (v) => { a.sh.rotation.set(-v[0] * D, 0, s * v[1] * D); a.el.rotation.set(-v[2] * D, 0, 0); gig.root.updateMatrixWorld(true); const q = new THREE.Vector3(0, -0.1, 0); a.wr.localToWorld(q); return q; };
  const det = M => M[0][0] * (M[1][1] * M[2][2] - M[1][2] * M[2][1]) - M[0][1] * (M[1][0] * M[2][2] - M[1][2] * M[2][0]) + M[0][2] * (M[1][0] * M[2][1] - M[1][1] * M[2][0]);
  for (let it = 0; it < 18; it++) {
    const p = apply(x), er = target.clone().sub(p); if (er.length() < 2e-3) break;
    const J = [0, 1, 2].map(i => { const y = x.slice(); y[i] += 1; return apply(y).sub(p); });
    const A = [[0, 0, 0], [0, 0, 0], [0, 0, 0]], bb = [0, 0, 0];
    for (let i = 0; i < 3; i++) { for (let j = 0; j < 3; j++) A[i][j] = J[i].dot(J[j]) + (i === j ? 1e-4 : 0); bb[i] = J[i].dot(er); }
    const d0 = det(A), dx = [0, 1, 2].map(c => det(A.map((row, r) => row.map((v, cc) => cc === c ? bb[r] : v))) / d0);
    x = x.map((v, i) => v + Math.max(-12, Math.min(12, dx[i]))); x[0] = clamp(x[0], -30, 160); x[1] = clamp(x[1], -20, 100); x[2] = clamp(x[2], 0, 150);
  }
  a._ik = x; apply(x); return x;
}

// ---------------- Nana Dot ----------------
export const nanaWatch = (t) => base({ yaw: 0, spine: [4, 0, 0], head: [10 + 2 * Math.sin(t * 3), 0, 0], L: { sh: [8, 10], el: 14, curl: RELAX }, R: { sh: [62, 8], el: 92, curl: FIST, phone: true } });
export function nanaPutDown(t) {   // holding the watering can, bends, sets it down, straightens
  const down = sm(0.1, 0.5, t) * (1 - sm(0.62, 0.95, t));
  return base({ spine: [28 * down, 0, 0], head: [-6 * down, 0, 0], R: { sh: [lerp(24, 52, down), 14], el: lerp(40, 22, down), curl: FIST }, L: { sh: [lerp(8, 30, down), 10], el: lerp(14, 40, down), curl: RELAX }, legL: { hip: [10 * down, 6], knee: 22 * down }, legR: { hip: [10 * down, 6], knee: 22 * down } });
}
export function nanaBrace(t, g) {   // goalkeeper: wide stance, knees bent, arms wide, small side to side shuffle
  const k = sm(0, 0.35, t), sw = Math.sin(g * 7) * 4 * k;
  return base({ yaw: sw, spine: [-6 * k, 0, 0], head: [-4 * k, 0, 0], L: { sh: [lerp(8, 30, k), lerp(10, 78, k)], el: lerp(14, 30, k), curl: lerp(0.5, 0.1, k) ? OPEN : OPEN }, R: { sh: [lerp(8, 30, k), lerp(10, 78, k)], el: lerp(14, 30, k), curl: OPEN }, legL: { hip: [6 * k, 20 * k], knee: 22 * k }, legR: { hip: [6 * k, 20 * k], knee: 22 * k } });
}
export const nanaWave = (t, g) => base({ spine: [2, 0, 4], head: [0, 0, 4], R: { sh: [168, 28], el: 22 + 24 * Math.sin(g * 18), curl: OPEN }, L: { sh: [12, 12], el: 20, curl: RELAX } });
export function nanaDuck(t) {
  const k = sm(0, 0.4, t);
  return base({ spine: [40 * k, 0, 0], head: [22 * k, 0, 0], L: { sh: [150 * k + 6, 20], el: 110 * k + 14, curl: FIST }, R: { sh: [150 * k + 4, 20], el: 110 * k + 18, curl: FIST }, legL: { hip: [50 * k, 8], knee: 82 * k }, legR: { hip: [50 * k, 8], knee: 82 * k } });
}

// ---------------- van, pigeons, tulips ----------------
export function vanState(g) {   // g seconds from the turn onto Maple Street: accelerates downhill, bumps, small steering wobble
  const v = 4 + 3.2 * g + 0.25 * g * g, z = -(4 * g + 1.6 * g * g + 0.0417 * g ** 3);
  return { v, z, y: 0.015 * Math.sin(g * 17) + 0.01 * Math.sin(g * 29), yaw: 0.02 * Math.sin(g * 2.2), pitch: -0.012 + 0.006 * Math.sin(g * 13), wheel: -(-z) / 0.34 };
}
export function pigeonFlock(THREE, makePigeon, n = 11, seed = 3) {
  const grp = new THREE.Group(); let a = seed; const R = () => { a = (a * 16807) % 2147483647; return a / 2147483647; };
  const birds = []; for (let i = 0; i < n; i++) { const b = makePigeon(); b.scale.setScalar(0.55); grp.add(b); birds.push({ b, x0: (R() - 0.5) * 3.6, z0: (R() - 0.5) * 2.4, t0: R() * 0.7, side: (R() - 0.5) * 4.5, up: 1.4 + R() * 2.2, speed: -(3 + R() * 4), ph: R() * 6 }); }
  const update = (tau) => { for (const q of birds) { const u = Math.max(0, tau - q.t0), fly = u > 0; const p = fly ? Math.min(1, u / 1.4) : 0; q.b.position.set(q.x0 + q.side * u * 3.0, 0.12 + q.up * Math.pow(Math.min(u, 1.6), 0.8) * 0.9 + (fly ? 0.0 : 0), q.z0 + q.speed * u * (fly ? 1 : 0)); q.b.rotation.set(fly ? -0.35 : 0, fly ? 0 : Math.PI * 0.5 + q.ph, 0);
    const flap = fly ? Math.sin(u * 38 + q.ph) * 0.9 : 0.05 * Math.sin(tau * 3 + q.ph); q.b.userData.wings?.forEach((w, k) => { w.rotation.x = (k ? 1 : -1) * (0.15 + flap * (fly ? 1 : 0.2)); }); q.b.visible = true; } };
  return { group: grp, update, birds };
}
export function tulipBurst(THREE, n = 46, colors = [0xe8407a, 0xffd23f, 0xff7a3a, 0xb06cff], seed = 5) {
  const grp = new THREE.Group(); let a = seed; const R = () => { a = (a * 16807) % 2147483647; return a / 2147483647; };
  const mats = colors.map(c => new THREE.MeshStandardMaterial({ color: c, roughness: 0.6 })), stemM = new THREE.MeshStandardMaterial({ color: 0x4f8f3a }), items = [];
  for (let i = 0; i < n; i++) { const t = new THREE.Group(); const st = new THREE.Mesh(new THREE.CylinderGeometry(0.008, 0.008, 0.38, 6), stemM); st.position.y = 0.19; const hd = new THREE.Mesh(new THREE.SphereGeometry(0.04, 10, 8), mats[i % mats.length]); hd.scale.y = 1.35; hd.position.y = 0.4; t.add(st, hd); grp.add(t);
    const ang = R() * 6.283, sp = 1.8 + R() * 3.2; items.push({ t, v: [(R() < 0.5 ? -1 : 1) * (1.6 + R() * 3.2), 3.4 + R() * 3.4, -(0.6 + R() * 3.0)], spin: [R() * 8 - 4, R() * 8 - 4, R() * 8 - 4], p0: [(R() < 0.5 ? -1 : 1) * (1.25 + R() * 0.5), 0.55, (R() - 0.5) * 0.5] }); }
  const update = (tau) => { for (const q of items) { const u = Math.max(0, tau); q.t.visible = u > 0; q.t.position.set(q.p0[0] + q.v[0] * u, Math.max(0.02, q.p0[1] + q.v[1] * u - 4.9 * u * u), q.p0[2] + q.v[2] * u); q.t.rotation.set(q.spin[0] * u, q.spin[1] * u, q.spin[2] * u); } };
  return { group: grp, update };
}
