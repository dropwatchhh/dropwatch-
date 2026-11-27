// Animation layer for the 10-second test: per-frame poses/camera for each shot. Builds on stage_anim.html handles (window.H).
const OPEN = [0.1, 0.1, 0.1, 0.1, 0.1], FIST = [0.8, 1, 1, 1, 1], THUMB = [0.0, 1, 1, 1, 1], RELAX = [0.35, 0.45, 0.5, 0.55, 0.6];
const ease = k => k * k * (3 - 2 * k), lerp = (a, b, k) => a + (b - a) * k, clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));
const mix = (a, b, k) => Array.isArray(a) ? a.map((x, i) => mix(x, b[i], k)) : (typeof a === 'object' && a) ? Object.fromEntries(Object.keys(a).map(key => [key, mix(a[key], b[key], k)])) : typeof a === 'number' ? lerp(a, b, k) : b;
const leg = (h0, h1, k) => ({ hip: [h0, h1], knee: k });
const body = (o) => ({ yaw: 0, spine: [0, 0, 0], head: [0, 0, 0], L: { sh: [6, 10], el: 14, curl: RELAX }, R: { sh: [4, 10], el: 18, curl: RELAX }, legL: leg(4, 3, 8), legR: leg(-3, 3, 4), ...o });
const P = {
  wide: body({ spine: [-3, 0, 0], head: [-2, 0, 0], L: { sh: [15, 82], el: 12, curl: OPEN }, R: { sh: [15, 82], el: 12, curl: OPEN }, legL: leg(4, 12, 8), legR: leg(-2, 12, 6) }),
  wideBig: body({ spine: [-8, 0, 0], head: [-9, 0, 0], L: { sh: [30, 105], el: 8, curl: OPEN }, R: { sh: [30, 105], el: 8, curl: OPEN }, legL: leg(6, 16, 14), legR: leg(-2, 16, 10) }),
  smug: body({ spine: [-2, 0, 3], head: [0, 0, 6], L: { sh: [8, 14], el: 20, curl: RELAX }, R: { sh: [10, 16], el: 24, curl: RELAX } }),
  thumb: body({ yaw: 6, spine: [-3, 6, 0], head: [-3, -4, 6], L: { sh: [4, 42], el: 108, curl: FIST }, R: { sh: [78, 16], el: 92, curl: THUMB }, legL: leg(4, 8, 10), legR: leg(-3, 8, 6) }),
  panic: { yaw: -6, spine: [-8, 0, 4], head: [-8, 0, -6], L: { sh: [110, 44], el: 30, curl: OPEN }, R: { sh: [125, 36], el: 25, curl: OPEN }, legL: leg(30, 6, 60), legR: leg(4, 8, 20) },
  idle: body({ yaw: 4, head: [0, 0, 2] }),
  rock: body({ yaw: -10, spine: [-6, -12, 0], head: [-6, 8, -8], L: { sh: [8, 38], el: 105, curl: OPEN }, R: { sh: [165, 18], el: 25, curl: [0.9, 0, 1, 1, 0] }, legL: leg(8, 24, 28), legR: leg(-6, 22, 20) }),
};
const SH = {   // camera keys for a 1.78 m Dex (face centre about y=1.58), van 5.3 m long at z=-5.2
  S1: { pos: [[0.4, 0.55, 4.1], [0.2, 0.7, 3.5]], look: [[-0.1, 1.0, 0], [0, 1.05, 0]], fov: 46 },
  S9: { pos: [[0.75, 1.66, -0.15], [0.55, 1.63, 0.2]], look: [[-1.25, 1.55, 2.6], [-1.25, 1.56, 2.6]], fov: 24 },
  S8: { pos: [[0.75, 0.75, 3.1], [0.45, 0.95, 2.4]], look: [[0, 1.3, 0], [0, 1.45, 0]], fov: 44 },
  S2: { pos: [[0.1, 1.62, 1.7], [0.06, 1.62, 1.25]], look: [[0, 1.6, 0], [0, 1.6, 0]], fov: 36 },
  S3: { pos: [[0.5, 1.2, 3.0], [0.25, 1.25, 2.5]], look: [[0, 1.25, 0], [0, 1.28, 0]], fov: 44 },
  S4: { pos: [[-3.0, 1.35, 3.0], [-2.8, 1.35, 3.0]], look: [[4.1, 0.9, -2.7], [5.4, 0.9, -3.2]], fov: 44 },
  S7: { pos: [[0.6, 1.25, 3.0], [0.3, 1.3, 2.3]], look: [[0, 1.2, 0], [0.1, 1.25, 0]], fov: 44 },
  S5: { pos: [[0.9, 1.6, -0.9], [0.75, 1.55, -0.8]], look: [[0.1, 1.4, -0.3], [0.1, 1.4, -0.3]], fov: 50 },
  S6: { pos: [[-4.2, 0.45, 1.8], [-3.8, 0.5, 1.7]], look: [[2.0, 0.9, -1.5], [3.0, 0.9, -1.9]], fov: 44 },
};
export function install(E) {
  const { camera, renderer, scene, getH, setPose, setFace, setGigPose, setGigFace } = E;
  const vanX = g => -2.6 + 0.9 * g;
  window.frame = (f) => {
    const H = getH(), { shot, t, g, dur, lip, blink, amp = 0, emph = 0, mood } = f, k = clamp(t / dur), e = ease(k);
    const wob = (s, a, ph = 0) => Math.sin(g * s * 6.283 + ph) * a;
    // ---- van (lot shots)
    if (H.van && shot !== 'S5') { const x = vanX(g); H.van.position.x = x; H.van.position.y = 0.012 + Math.abs(wob(1.7, 0.012)); H.van.rotation.z = wob(1.3, 0.006); H.van.userData.wheels.forEach(w => w.rotation.z = -x / 0.33); }
    // ---- Dex
    if (H.dex) {
      let pose, face = { eyes: blink ? 'eyes_closed' : 'eyes_open', brows: 'brows_up', mouth: lip };
      if (shot === 'S1' || shot === 'S8' || shot === 'S9') { pose = mix(P.wide, P.wideBig, clamp(emph)); pose.head = [pose.head[0] + amp * 3 + wob(0.8, 1.2), wob(0.6, 3), wob(0.5, 3)]; pose.spine = [pose.spine[0] + wob(0.35, 0.8) - amp * 2, wob(0.4, 3), 0]; pose.yaw = wob(0.3, 5); face.brows = emph > .3 ? 'brows_high' : 'brows_up'; face.eyes = blink ? 'eyes_closed' : (emph > .3 ? 'eyes_wide' : 'eyes_open'); }
      else if (shot === 'S2') { pose = mix(P.smug, P.smug, 0); pose.head = [wob(0.5, 1.5) + (k > .3 ? 4 : 0), wob(0.4, 3), 4 + wob(0.6, 2)]; pose.spine = [wob(0.35, 0.6), 0, 2]; face.eyes = blink ? 'eyes_closed' : (k > .35 ? 'eyes_wide' : 'eyes_open'); face.brows = k > .35 ? 'brows_high' : 'brows_smirk'; if (lip.startsWith('mouth_smile') || lip === 'mouth_closed_grin') face.mouth = k > .75 ? 'mouth_closed_grin' : 'mouth_closed_smirk'; }
      else if (shot === 'S3') { const up = ease(clamp((t - 0.35) / 0.35)); pose = mix(P.smug, P.thumb, up); pose.head = [pose.head[0] + amp * 3, pose.head[1] + wob(0.7, 3), pose.head[2]]; pose.spine = [pose.spine[0] + wob(0.4, 0.8), pose.spine[1], pose.spine[2]]; face.brows = 'brows_smirk'; if (lip === 'mouth_smile') face.mouth = 'mouth_closed_grin'; }
      else if (shot === 'S4') { pose = mix(P.idle, P.idle, 0); pose.head = [wob(0.4, 1), -6 + wob(0.3, 2), 2]; pose.spine = [wob(0.35, 0.8), 0, 0]; pose.yaw = 10 + wob(0.25, 3); face.brows = 'brows_smirk'; if (lip === 'mouth_smile') face.mouth = 'mouth_closed_grin'; }
      else if (shot === 'S7') { const turn = ease(clamp(t / 0.55)), pan = ease(clamp((t - 0.55) / 0.5)); pose = mix(P.idle, P.panic, pan); pose.yaw = lerp(4, 36, turn) * (1 - 0.6 * pan) + wob(0.4, 2); pose.head = [pose.head[0] + amp * 3, lerp(0, 18, turn) + wob(0.6, 2), pose.head[2]]; face.brows = pan > 0.3 ? 'brows_worried' : 'brows_up'; face.eyes = blink ? 'eyes_closed' : (turn > 0.5 ? 'eyes_wide' : 'eyes_open'); if (lip === 'mouth_smile') face.mouth = pan > 0.3 ? 'mouth_closed_worried' : 'mouth_closed_grin'; }
      else { pose = mix(P.rock, P.rock, 0); pose.legL = leg(8 + wob(2, 4), 24, 28 + wob(2, 8)); pose.R.sh = [165 + wob(2, 6), 18]; face.mouth = 'mouth_grin_open'; }
      setPose(H.dex, pose); setFace(H.dex, face);
    }
    // ---- Gig (cab shot): seated, both paws gripping the wheel rim (IK) as it turns, eyes on the road
    if (shot === 'S5' && H.gig) {
      const T = E.THREE, D = Math.PI / 180, ch = Math.floor(g * 1.5) % 2 ? 'mouth_smile' : 'mouth_closed';
      setGigFace(H.gig, { eyes: blink ? 'eyes_closed' : 'eyes_open', mouth: ch });
      const steer = 0.5 + 0.55 * Math.sin(g * 1.6) + 0.15 * Math.sin(g * 5.3);
      if (H.wheel) H.wheel.rotation.z = steer;
      setGigPose(H.gig, { spine: [-4 + wob(1.1, 1.2), 0, 0], head: [-3 + wob(1.3, 1.5), wob(0.4, 1.2), 0], L: { sh: [40, 10], el: 60, curl: 1 }, R: { sh: [40, 10], el: 60, curl: 1 }, legL: { hip: 85, knee: 80 }, legR: { hip: 85, knee: 80 }, tail: [20 + wob(2.2, 8), wob(1.2, 6)] });
      scene.updateMatrixWorld(true);
      for (const [k, th] of [['L', 2.85], ['R', 0.3]]) {
        const a = H.gig.j.arms[k], s = a.s;
        const target = H.wheel.localToWorld(new T.Vector3(0.62 * Math.cos(th), 0.62 * Math.sin(th), 0));
        let x = a._ik ?? [45, 20, 70];
        const apply = (v) => { a.sh.rotation.set(-v[0] * D, 0, s * v[1] * D); a.el.rotation.set(-v[2] * D, 0, 0); H.gig.root.updateMatrixWorld(true); const p = new T.Vector3(0, -0.1, 0); a.wr.localToWorld(p); return p; };
        for (let it = 0; it < 18; it++) {
          const p = apply(x), er = target.clone().sub(p); if (er.length() < 2e-3) break;
          const J = [0, 1, 2].map(i => { const y = x.slice(); y[i] += 1; return apply(y).sub(p); });
          const A = [[0, 0, 0], [0, 0, 0], [0, 0, 0]], bb = [0, 0, 0];
          for (let i = 0; i < 3; i++) { for (let j = 0; j < 3; j++) A[i][j] = J[i].dot(J[j]) + (i === j ? 1e-4 : 0); bb[i] = J[i].dot(er); }
          const det = M => M[0][0] * (M[1][1] * M[2][2] - M[1][2] * M[2][1]) - M[0][1] * (M[1][0] * M[2][2] - M[1][2] * M[2][0]) + M[0][2] * (M[1][0] * M[2][1] - M[1][1] * M[2][0]);
          const d0 = det(A), dx = [0, 1, 2].map(c => det(A.map((row, r) => row.map((v, cc) => cc === c ? bb[r] : v))) / d0);
          x = x.map((v, i) => v + Math.max(-12, Math.min(12, dx[i])));
          x[0] = Math.max(-30, Math.min(150, x[0])); x[1] = Math.max(-20, Math.min(100, x[1])); x[2] = Math.max(0, Math.min(150, x[2]));
        }
        a._ik = x; const pf = apply(x); if (f.n % 12 === 0) console.error('IKERR', k, (target.distanceTo(pf) * 1000).toFixed(1), 'mm(local units *1000)', x.map(v => v.toFixed(0)).join(','));
      }
    }
    // ---- camera: eased move + hand-held drift
    const c = SH[shot]; const L = (a, b) => a.map((x, i) => lerp(x, b[i], e));
    let pos = L(c.pos[0], c.pos[1]), look = L(c.look[0], c.look[1]);
    pos[0] += wob(0.7, 0.012); pos[1] += wob(0.9, 0.01); look[1] += wob(0.6, 0.01);
    if (shot === 'S5' && H.wheel && H.gig) { const W = new E.THREE.Vector3(), G = new E.THREE.Vector3(); H.wheel.getWorldPosition(W); H.gig.j.head.getWorldPosition(G); const mid = W.clone().add(G).multiplyScalar(0.5); const o = f.camOff ?? [-0.55 + 0.12 * e, 0.45, -0.75 + 0.1 * e]; look = [mid.x, mid.y - 0.05, mid.z]; pos = [mid.x + o[0] - 0.1 * e, mid.y + o[1], mid.z + o[2]]; c.fov = f.fov ?? 38; }
    if (f.camTest) { pos = f.camTest[0]; look = f.camTest[1]; c.fov = f.camTest[2]; }
    camera.fov = c.fov; camera.updateProjectionMatrix(); camera.position.set(...pos); camera.lookAt(...look);
    if (f.roll) camera.rotateZ(f.roll * Math.PI / 180);
    camera.updateMatrixWorld(); renderer.render(scene, camera);
  };
}
