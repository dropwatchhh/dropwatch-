// Animation lab: poses everything in the lab_street or cab scene from a spec and renders one preview frame.
import * as A from './anim_lib.mjs';
export function install(E) {
  const { THREE, camera, renderer, scene, getH, setPose, setFace, setBoot, setGigPose, setGigFace } = E;
  const V = (x, y, z) => new THREE.Vector3(x, y, z);
  const footMin = (rig) => { rig.root.updateMatrixWorld(true); let m = 1e9; for (const k of ['legL', 'legR']) { const ank = rig.j[k].ank; for (const z of [-0.2, 0.4]) { const v = V(0, -0.225, z); ank.localToWorld(v); m = Math.min(m, v.y); } } return m; };
  const fixGround = (rig, h = 0) => { rig.root.position.y -= footMin(rig) - h; rig.root.updateMatrixWorld(true); };
  const handMid = (rig) => { const a = V(0, -0.2, 0), c = V(0, -0.2, 0); rig.j.arms.L.wr.localToWorld(a); rig.j.arms.R.wr.localToWorld(c); return a.add(c).multiplyScalar(0.5); };
  const sm2 = (a, b2, x) => { const t = Math.min(1, Math.max(0, (x - a) / (b2 - a))); return t * t * (3 - 2 * t); };
  window.lab = (s) => {
    const H = getH(), t = s.t ?? 0, g = s.g ?? t; let focus = V(0, 1, 0);
    scene.updateMatrixWorld(true);
    const vanZ0 = -6, rearOf = (z) => z + 2.7;
    if (H.van && H.dex) {   // van state for chase animations
      const vs = A.vanState(s.vanG ?? 0); H.van.position.set(0, vs.y, vanZ0 + (s.vanZ ?? 0)); H.van.rotation.z = vs.pitch; H.van.userData.wheels.forEach(w => { w.rotation.z = -(s.vanZ ?? 0) / 0.34; });
    }
    const vz = H.van ? H.van.position.z : 0, rear = rearOf(vz);
    const face = s.face ?? {};
    if (H.pigeons) H.pigeons.group.visible = s.anim === 'van'; if (H.tulips) H.tulips.group.visible = s.anim === 'van';
    if (H.van && (s.anim === 'run' || s.anim === 'selfie' || s.anim === 'boot')) H.van.visible = false;
    switch (s.anim) {
      case 'run': case 'selfie': {
        const sp = s.speed ?? 4.2, p = A.stridePhase(t, sp); setPose(H.dex, A.run(p, { amp: s.amp ?? 1, phone: s.anim === 'selfie', yaw: 180 })); H.dex.root.position.set(0, H.dex.root.position.y, -sp * t); fixGround(H.dex); setFace(H.dex, { eyes: 'eyes_wide', brows: 'brows_up', mouth: s.mouth ?? 'mouth_shout', ...face }); focus = V(0, 1.0, -sp * t); break; }
      case 'boot': {
        const sp = 4.2, p = A.stridePhase(t * 1.0, sp); { const P = A.bootLoss(clampT(s.k), p); P.yaw = 180; setPose(H.dex, P); } setBoot(H.dex, 'L', clampT(s.k) < 0.34); setFace(H.dex, { eyes: 'eyes_wide', brows: 'brows_worried', mouth: s.mouth ?? 'mouth_shout' });
        const z0 = -sp * t; H.dex.root.position.set(0, H.dex.root.position.y, z0); fixGround(H.dex); focus = V(0, 1.0, z0);
        const b = H.boot, k = clampT(s.k); if (k >= 0.34) { const u = (k - 0.34) * (s.dur ?? 1.4); b.visible = true; b.position.set(-0.1 + 0.2 * u, 0.5 + 2.6 * u - 4.9 * u * u * 1.0, z0 + 0.4 - 4.2 * u); b.rotation.set(6 * u, 1.2 * u, 3 * u); if (b.position.y < 0.05) b.position.y = 0.05; } else b.visible = false; break; }
      case 'chase': {   // run up behind the moving van, plant, jump, grab the bumper, get dragged (continuous)
        const tt = s.tt, Z0 = -6 + 2.8 + 4.0, vzNow = H.van.position.z, bump = vzNow + 2.88;
        let u, z0 = Z0 - 4.2 * Math.min(tt, 1.6) - 2.6 * Math.max(0, Math.min(tt, 1.95) - 1.6);
        if (tt < 1.6) u = 0.25 * tt / 1.6; else if (tt < 1.95) u = 0.25 + 0.1 * (tt - 1.6) / 0.35; else if (tt < 2.75) u = 0.35 + 0.43 * (tt - 1.95) / 0.8; else u = 0.78 + 0.22 * sm2(2.75, 3.2, tt);
        const P = A.dive(u); const run = A.run(A.stridePhase(tt, 4.2), { amp: 1.15, yaw: 180 }); const a = (tt - 1.95) / 0.8;
        const rw = 1 - sm2(0.2, 0.3, u); const Q = rw > 0.001 ? A.mixPose(P, run, rw) : P; Q.yaw = 180;
        if (tt >= 2.75) { const dr = A.drag(tt, {}); Q.legL = dr.legL; Q.legR = dr.legR; }
        const place = (pitch) => { Q.pitch = pitch; setPose(H.dex, Q); H.dex.root.rotation.y = Math.PI; H.dex.root.position.set(0, H.dex.root.position.y, z0);
          if (tt < 1.95) fixGround(H.dex);
          else if (tt < 2.75) { H.dex.root.position.y = 0.05 + 0.95 * Math.sin(Math.PI * Math.max(0, a)) * (1 - 0.35 * a) + 0.28 * a; }
          const hm = handMid(H.dex), w = tt < 1.95 ? 0 : (tt < 2.75 ? Math.pow(Math.min(1, a), 1.6) : 1);
          H.dex.root.position.z += w * (bump - hm.z); if (tt >= 2.55) H.dex.root.position.y += sm2(2.55, 2.85, tt) * (0.5 - handMid(H.dex).y);
          H.dex.root.updateMatrixWorld(true); return footMin(H.dex); };
        if (tt >= 2.75) { let lo = 30, hi = 84; for (let i = 0; i < 9; i++) { const mid = (lo + hi) / 2, fm = place(mid); if (fm > 0.02) hi = mid; else lo = mid; } const fm = place((lo + hi) / 2); if (fm < 0) { H.dex.root.position.y -= fm; } }
        else { place(P.pitch); const fm = footMin(H.dex); if (fm < 0) H.dex.root.position.y -= fm; }
        setFace(H.dex, { eyes: 'eyes_wide', brows: 'brows_angry', mouth: s.mouth ?? 'mouth_shout' }); focus = V(0, 0.6, H.dex.root.position.z - 0.8); break; }
      case 'dive': {
        H.dex.root.position.set(0, 0, rear + lerp(3.4, 1.9, sm(0.18, 0.68, t))); H.dex.root.rotation.y = Math.PI; setPose(H.dex, A.dive(t)); H.dex.root.rotation.y = Math.PI; setFace(H.dex, { eyes: 'eyes_wide', brows: 'brows_angry', mouth: 'mouth_shout' }); focus = V(0, 0.7, rear + 1.2); break; }
      case 'drag': {
        H.dex.root.position.set(0, 0, rear + 1.85); setPose(H.dex, A.drag(g, { selfie: s.selfie })); setFace(H.dex, { eyes: 'eyes_wide', brows: 'brows_worried', mouth: 'mouth_shout' }); focus = V(0, 0.4, rear + 0.9); break; }
      case 'hang': case 'reach': {
        H.dex.root.position.set(0.55, 0, rear + 1.5); setPose(H.dex, s.anim === 'reach' ? A.reach(t, g) : A.hang(g)); H.dex.root.position.x = 0.55; setFace(H.dex, { eyes: 'eyes_wide', brows: 'brows_up', mouth: s.mouth ?? 'mouth_closed_worried' }); focus = V(0.3, 0.9, rear + 0.8); break; }
      case 'nana': {
        const n = H.nana, nx = n.root.position.x, nz = n.root.position.z, fn = s.what;
        const P = fn === 'put' ? A.nanaPutDown(t) : fn === 'brace' ? A.nanaBrace(t, g) : fn === 'wave' ? A.nanaWave(t, g) : fn === 'duck' ? A.nanaDuck(t, g) : A.nanaWatch(t);
        setPose(n, P); setFace(n, { eyes: fn === 'duck' ? 'eyes_closed' : 'eyes_wide', brows: fn === 'put' || fn === 'watch' ? 'brows_flat' : 'brows_angry', mouth: fn === 'brace' || fn === 'wave' ? 'mouth_closed_worried' : 'mouth_closed_smirk', ...face });
        scene.updateMatrixWorld(true); const can = H.can;
        if (fn === 'put') { can.visible = true; if (t < 0.5) { const w = V(0, 0, 0); n.j.arms.R.wr.getWorldPosition(w); can.position.set(w.x, w.y - 0.2, w.z + 0.06); can.rotation.set(0, 0, 0.0); } else { can.position.set(nx + 0.3, 0.0, nz + 0.25); can.rotation.set(0, 0.4, 0); } } else can.visible = false;
        focus = V(nx, 0.8, nz); break; }
      case 'cab': {   // Gig actions in the cab scene
        const gig = H.gig, w = H.wheel; setGigFace(gig, { eyes: s.eyes ?? 'eyes_open', mouth: s.mouth ?? 'mouth_closed' });
        if (s.what === 'cover') { setGigPose(gig, A.gigCover(t)); setGigFace(gig, { eyes: 'eyes_closed', mouth: 'mouth_open' }); }
        else if (s.what === 'look') { setGigPose(gig, A.gigLookCam(t, s.yaw ?? 42)); setGigFace(gig, { eyes: 'eyes_wide', mouth: 'mouth_smile' }); }
        else {
          setGigPose(gig, { head: [-3, 0, 0], L: { sh: [40, 10], el: 60, curl: 1 }, R: { sh: [40, 10], el: 60, curl: 1 }, legL: { hip: 85, knee: 80 }, legR: { hip: 85, knee: 80 }, tail: [20, 0] }); scene.updateMatrixWorld(true);
          const press = s.what === 'horn' ? Math.max(0, Math.sin(t * 2 * Math.PI * 2.2 - 1.2)) : 0;
          w.rotation.z = 0.5; scene.updateMatrixWorld(true);
          A.ikPaw(THREE, gig, 'L', w.localToWorld(V(0.62 * Math.cos(2.85), 0.62 * Math.sin(2.85), 0)));
          if (s.what === 'horn') A.ikPaw(THREE, gig, 'R', w.localToWorld(V(0, 0.02, 0.1 - 0.08 * press)), [60, 10, 80]); else A.ikPaw(THREE, gig, 'R', w.localToWorld(V(0.62 * Math.cos(0.3), 0.62 * Math.sin(0.3), 0)));
          setGigFace(gig, { eyes: 'eyes_wide', mouth: s.what === 'horn' && press > 0.3 ? 'mouth_open' : 'mouth_smile' });
        }
        const wp = V(0, 0, 0), hp = V(0, 0, 0); w.getWorldPosition(wp); gig.j.head.getWorldPosition(hp); focus = wp.clone().add(hp).multiplyScalar(0.5); break; }
      case 'van': { H.pigeons?.update(s.pigeonT ?? -1); H.tulips?.update(s.tulipT ?? -1); focus = V(0, 1, vz); break; }
    }
    if (s.pigeonT !== undefined) H.pigeons?.update(s.pigeonT); if (s.tulipT !== undefined) H.tulips?.update(s.tulipT);
    scene.updateMatrixWorld(true);
    const c = s.cam; if (c.rel) { camera.position.set(focus.x + c.pos[0], focus.y + c.pos[1], focus.z + c.pos[2]); camera.lookAt(focus.x + (c.look?.[0] ?? 0), focus.y + (c.look?.[1] ?? 0), focus.z + (c.look?.[2] ?? 0)); } else { camera.position.set(...c.pos); camera.lookAt(...c.look); }
    camera.fov = c.fov ?? 40; camera.updateProjectionMatrix(); camera.updateMatrixWorld(); renderer.render(scene, camera);
  };
}
const clampT = (k) => Math.min(1, Math.max(0, k ?? 0)), lerp = (a, b, t) => a + (b - a) * t, sm = (a, b, x) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };
