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
const SH = {   // camera keys: Dex stands 3.75 tall with face centre near y=2.85; van sits at z=-5.2
  S1: { pos: [[0.5, 0.9, 7.2], [0.25, 1.1, 6.0]], look: [[-0.1, 2.0, 0], [0, 2.1, 0]], fov: 46 },
  S2: { pos: [[0.25, 2.45, 3.4], [0.12, 2.4, 2.7]], look: [[0, 2.35, 0], [0, 2.3, 0]], fov: 38 },
  S3: { pos: [[1.0, 2.2, 5.6], [0.5, 2.3, 4.9]], look: [[0, 2.35, 0], [0, 2.35, 0]], fov: 44 },
  S4: { pos: [[-4.6, 2.6, 4.4], [-4.2, 2.6, 4.4]], look: [[1.0, 1.7, -2.0], [2.2, 1.7, -2.6]], fov: 44 },
  S5: { pos: [[1.6, 3.1, -1.9], [1.35, 3.05, -1.7]], look: [[-0.9, 2.85, -0.3], [-0.9, 2.85, -0.3]], fov: 50 },
  S7: { pos: [[1.1, 2.4, 5.6], [0.45, 2.45, 4.5]], look: [[0, 2.35, 0], [0.2, 2.4, 0]], fov: 44 },
  S6: { pos: [[-8, 0.7, 3.0], [-7.4, 0.8, 2.8]], look: [[2.5, 1.6, -3], [3.5, 1.6, -3]], fov: 44 },
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
      if (shot === 'S1') { pose = mix(P.wide, P.wideBig, clamp(emph)); pose.head = [pose.head[0] + amp * 3 + wob(0.8, 1.2), wob(0.6, 3), wob(0.5, 3)]; pose.spine = [pose.spine[0] + wob(0.35, 0.8) - amp * 2, wob(0.4, 3), 0]; pose.yaw = wob(0.3, 5); face.brows = emph > .3 ? 'brows_high' : 'brows_up'; face.eyes = blink ? 'eyes_closed' : (emph > .3 ? 'eyes_wide' : 'eyes_open'); }
      else if (shot === 'S2') { pose = mix(P.smug, P.smug, 0); pose.head = [wob(0.5, 1.5) + (k > .3 ? 4 : 0), wob(0.4, 3), 4 + wob(0.6, 2)]; pose.spine = [wob(0.35, 0.6), 0, 2]; face.eyes = blink ? 'eyes_closed' : (k > .35 ? 'eyes_wide' : 'eyes_open'); face.brows = k > .35 ? 'brows_high' : 'brows_smirk'; if (lip.startsWith('mouth_smile') || lip === 'mouth_closed_grin') face.mouth = k > .75 ? 'mouth_closed_grin' : 'mouth_closed_smirk'; }
      else if (shot === 'S3') { const up = ease(clamp((t - 0.35) / 0.35)); pose = mix(P.smug, P.thumb, up); pose.head = [pose.head[0] + amp * 3, pose.head[1] + wob(0.7, 3), pose.head[2]]; pose.spine = [pose.spine[0] + wob(0.4, 0.8), pose.spine[1], pose.spine[2]]; face.brows = 'brows_smirk'; if (lip === 'mouth_smile') face.mouth = 'mouth_closed_grin'; }
      else if (shot === 'S4') { pose = mix(P.idle, P.idle, 0); pose.head = [wob(0.4, 1), -6 + wob(0.3, 2), 2]; pose.spine = [wob(0.35, 0.8), 0, 0]; pose.yaw = 10 + wob(0.25, 3); face.brows = 'brows_smirk'; if (lip === 'mouth_smile') face.mouth = 'mouth_closed_grin'; }
      else if (shot === 'S7') { const turn = ease(clamp(t / 0.55)), pan = ease(clamp((t - 0.55) / 0.5)); pose = mix(P.idle, P.panic, pan); pose.yaw = lerp(4, 36, turn) * (1 - 0.6 * pan) + wob(0.4, 2); pose.head = [pose.head[0] + amp * 3, lerp(0, 18, turn) + wob(0.6, 2), pose.head[2]]; face.brows = pan > 0.3 ? 'brows_worried' : 'brows_up'; face.eyes = blink ? 'eyes_closed' : (turn > 0.5 ? 'eyes_wide' : 'eyes_open'); if (lip === 'mouth_smile') face.mouth = pan > 0.3 ? 'mouth_closed_worried' : 'mouth_closed_grin'; }
      else { pose = mix(P.rock, P.rock, 0); pose.legL = leg(8 + wob(2, 4), 24, 28 + wob(2, 8)); pose.R.sh = [165 + wob(2, 6), 18]; face.mouth = 'mouth_grin_open'; }
      setPose(H.dex, pose); setFace(H.dex, face);
    }
    // ---- Gig (cab shot): driving, chewing a noodle, bumped by the road
    if (shot === 'S5' && H.gig) {
      const ch = Math.floor(g * 6) % 2 ? 'mouth_chitter' : 'mouth_closed';
      setGigFace(H.gig, { eyes: blink ? 'eyes_closed' : 'eyes_wide', mouth: ch });
      const bump = wob(3.1, 4) + wob(5.3, 2);
      setGigPose(H.gig, { spine: [wob(0.9, 2), wob(0.6, 2), 0], head: [wob(1.1, 4) - 4, -4 + wob(0.5, 6) + 12 * e, wob(0.7, 4)], L: { sh: [78 + bump, 6], el: 32, curl: 1 }, R: { sh: [78 - bump, 6], el: 32, curl: 1 }, legL: { hip: 85, knee: 80 + wob(2.2, 8) }, legR: { hip: 85, knee: 80 }, tail: [20 + wob(2.2, 12), wob(1.2, 6)] });
    }
    // ---- camera: eased move + hand-held drift
    const c = SH[shot]; const L = (a, b) => a.map((x, i) => lerp(x, b[i], e));
    let pos = L(c.pos[0], c.pos[1]), look = L(c.look[0], c.look[1]);
    pos[0] += wob(0.7, 0.012); pos[1] += wob(0.9, 0.01); look[1] += wob(0.6, 0.01);
    if (f.camTest) { pos = f.camTest[0]; look = f.camTest[1]; c.fov = f.camTest[2]; }
    camera.fov = c.fov; camera.updateProjectionMatrix(); camera.position.set(...pos); camera.lookAt(...look);
    if (f.roll) camera.rotateZ(f.roll * Math.PI / 180);
    camera.updateMatrixWorld(); renderer.render(scene, camera);
  };
}
