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
    if (H.van && s.vanX !== undefined) { H.van.position.x = s.vanX; H.van.userData.wheels.forEach(w => { w.rotation.z = -s.vanX / 0.33; }); }
    else if (H.van && H.dex) {   // van state for chase animations
      const vs = A.vanState(s.vanG ?? 0); H.van.position.set(0, vs.y, vanZ0 + (s.vanZ ?? 0)); H.van.rotation.z = vs.pitch; H.van.userData.wheels.forEach(w => { w.rotation.z = -(s.vanZ ?? 0) / 0.34; });
    }
    if (H.dex) H.dex.root.visible = !s.hideDex;
    if (H.vguitar && H.van) H.vguitar.position.set(-0.3, 1.0, H.van.position.z + 2.4);
    const vz = H.van ? H.van.position.z : 0, rear = rearOf(vz);
    const face = s.face ?? {};
    if (H.pigeons) H.pigeons.group.visible = s.anim === 'van'; if (H.tulips) H.tulips.group.visible = s.anim === 'van';
    if (H.van && ['run', 'selfie', 'boot', 'boot2', 'gait'].includes(s.anim) && !s.keepVan) H.van.visible = false; else if (H.van) H.van.visible = true;
    switch (s.anim) {
      case 'hand': {   // close-up of a hand (phone grip tests): pose from spec, camera relative to the wrist
        setPose(H.dex, s.pose); setFace(H.dex, s.face ?? { mouth: 'mouth_smile' }); scene.updateMatrixWorld(true);
        const arm = H.dex.j.arms[s.side ?? 'R']; const w = V(0, -0.25, 0); arm.wr.localToWorld(w); focus = w;
        if (s.debug) { const hg = arm.fingers[0][0].parent; const out = {}; arm.fingers.forEach(([f1, f2], i) => { const p1 = V(0, 0, 0), p2 = V(0, 0, 0), tip = V(0, -0.09, 0); f1.localToWorld(p1); f2.localToWorld(p2); f2.localToWorld(tip); out['f' + i] = [p1, p2, tip].map(q => hg.worldToLocal(q.clone()).toArray().map(v => +v.toFixed(3))); }); const th = arm.th[1]; const t = V(0, -0.08, 0); th.localToWorld(t); out.thumbTip = hg.worldToLocal(t).toArray().map(v => +v.toFixed(3)); out.phone = arm.phone.position.toArray().map(v => +v.toFixed(3)); console.error('HANDDBG ' + JSON.stringify(out)); }
        break; }
      case 'boot2': {   // jog; the left boot flies off at k=0.34, then arms fling up while the sock foot keeps jogging
        const S = H.dex.root.scale.x, k = clampT(s.k), gt = A.gait(t, 'jog', S), P = gt.pose, fl = sm(0.45, 0.7, k) * (0.6 + 0.4 * Math.sin(t * 14));
        P.L = A.mixPose(P.L, { sh: [150, 40], el: 25, curl: [0.1, 0.1, 0.1, 0.1, 0.1] }, fl); P.R = A.mixPose(P.R, { sh: [135, -10], el: 30, curl: [0.1, 0.1, 0.1, 0.1, 0.1] }, fl);
        P.spine[0] = P.spine[0] * (1 - 0.8 * fl) - 5 * fl; const dr = s.dir ?? [0, -1], p0 = s.p0 ?? [0, 0]; P.yaw = Math.atan2(dr[0], dr[1]) * 180 / Math.PI + gt.yaw; setPose(H.dex, P); const z0 = p0[1] + dr[1] * gt.v * t, x0 = p0[0] + dr[0] * gt.v * t; H.dex.root.position.set(x0, gt.rootY, z0); H.dex.root.updateMatrixWorld(true); { const fm0 = footMin(H.dex); if (fm0 < 0) H.dex.root.position.y -= fm0; }
        setBoot(H.dex, 'L', k < 0.34); setFace(H.dex, { eyes: 'eyes_wide', brows: 'brows_worried', mouth: s.mouth ?? 'mouth_shout' });
        const b = H.boot; if (k >= 0.34) { const u = (k - 0.34) * (s.dur ?? 1.4); b.visible = true; b.position.set(x0 + dr[0] * (0.3 + 2.6 * u) + 0.2 * (1 - Math.abs(dr[0])), 0.5 + 2.2 * u - 4.9 * u * u, z0 + dr[1] * (0.3 + 2.6 * u)); b.rotation.set(6 * u, 1.2 * u, 3 * u); if (b.position.y < 0.05) b.position.y = 0.05; } else b.visible = false;
        focus = V(x0, 0.9, z0); break; }
      case 'face': {   // close-up of Dex talking: viseme from spec, small head motion
        setPose(H.dex, { yaw: 0, spine: [2, 0, 0], head: [1 + 2 * Math.sin(t * 1.4), 5 * Math.sin(t * 0.9), 3 * Math.sin(t * 0.8)], L: { sh: [6, 10], el: 14, curl: [0.35, 0.45, 0.5, 0.55, 0.6] }, R: { sh: [6, 10], el: 14, curl: [0.35, 0.45, 0.5, 0.55, 0.6] }, legL: { hip: [4, 3], knee: 8 }, legR: { hip: [-3, 3], knee: 4 } });
        setFace(H.dex, { eyes: s.eyes ?? 'eyes_open', brows: s.brows ?? 'brows_smirk', mouth: s.mouth ?? 'mouth_grin_open' }); scene.updateMatrixWorld(true); const hp2 = V(0, 0, 0); H.dex.j.neck.getWorldPosition(hp2); hp2.y += 0.2; focus = hp2; break; }
      case 'lena': {   // Lena at her desk: dry and minimal; fingers drum, one eyebrow, slow lean-in, small head tilt
        const L = H.lena, k = sm(0.35, 0.85, t / (s.dur ?? 4)), br = Math.sin(t * 2.0);
        const drum = (i) => 0.55 + 0.35 * Math.max(0, Math.sin(t * 9 - i * 0.9));
        const P = { yaw: 0, spine: [2 + 14 * k + 0.6 * br, 1.5 * Math.sin(t * 0.8), 1.2 * Math.sin(t * 0.7)], head: [2 + 6 * k, 3 * Math.sin(t * 0.9) * (1 - k), 4 * Math.sin(t * 0.6) + 5 * k],
          L: { sh: [38 + 8 * k, 10], el: 66 - 10 * k, curl: [0.4, 0.55, 0.55, 0.6, 0.6] }, R: { sh: [38 + 8 * k, 10], el: 66 - 10 * k, curl: [0.4, drum(0), drum(1), drum(2), drum(3)] },
          legL: { hip: [85, 4], knee: 85 }, legR: { hip: [85, 4], knee: 85 } };
        setPose(L, P); L.root.position.y = -0.14; const blink = (t % 3.1) < 0.12; setFace(L, { eyes: blink ? 'eyes_closed' : (k > 0.5 ? 'eyes_wide' : 'eyes_half'), brows: k > 0.5 ? 'brows_up' : 'brows_smirk', mouth: k > 0.5 ? 'mouth_closed_worried' : 'mouth_closed_smirk' });
        scene.updateMatrixWorld(true); const hp = V(0, 0, 0); L.j.neck.getWorldPosition(hp); focus = hp; console.error('LENADBG ' + JSON.stringify({ neck: hp.toArray(), root: L.root.position.toArray(), vis: L.root.visible, scale: L.root.scale.x, nanCheck: L.j.chest.rotation.toArray() })); break; }
      case 'gait': {   // IK walk/jog: feet planted (no sliding), measured every frame
        const mode = s.mode ?? 'walk', S = H.dex.root.scale.x, gt = A.gait(t, mode, S); const P = gt.pose; const dr = s.dir ?? [0, -1], p0 = s.p0 ?? [0, 3.5]; P.yaw = Math.atan2(dr[0], dr[1]) * 180 / Math.PI + (s.faceYaw ?? 0) + gt.yaw;
        if (s.phone) { P.R = { sh: [62, 16], el: 108, curl: [0.45, 1.1, 1.12, 1.14, 1.15], phone: true, roll: -35 }; P.head = [P.head[0] + 4, P.head[1], 0]; }
        setPose(H.dex, P); H.dex.root.position.set(p0[0] + dr[0] * gt.v * t + gt.lat * dr[1], gt.rootY, p0[1] + dr[1] * gt.v * t); const z0 = H.dex.root.position.z; H.dex.root.updateMatrixWorld(true);
        setFace(H.dex, { eyes: 'eyes_open', brows: 'brows_up', mouth: s.mouth ?? 'mouth_smile' });
        const ft = { L: V(0, -0.225, 0.1), R: V(0, -0.225, 0.1) }; H.dex.j.legL.ank.localToWorld(ft.L); H.dex.j.legR.ank.localToWorld(ft.R);
        { const fm0 = footMin(H.dex); if (fm0 < 0) { H.dex.root.position.y -= fm0; H.dex.root.updateMatrixWorld(true); } }
        console.error('GAITCHK ' + JSON.stringify({ t, mode, stance: gt.stance, L: ft.L.toArray().map(v => +v.toFixed(4)), R: ft.R.toArray().map(v => +v.toFixed(4)), min: +footMin(H.dex).toFixed(4) }));
        focus = V(H.dex.root.position.x, 0.9, z0); break; }
      case 'run': case 'selfie': {
        const sp = s.speed ?? 4.2, p = A.stridePhase(t, sp); setPose(H.dex, A.run(p, { amp: s.amp ?? 1, phone: s.anim === 'selfie', yaw: 180 })); H.dex.root.position.set(0, H.dex.root.position.y, -sp * t); fixGround(H.dex); setFace(H.dex, { eyes: 'eyes_wide', brows: 'brows_up', mouth: s.mouth ?? 'mouth_shout', ...face }); focus = V(0, 1.0, -sp * t); break; }
      case 'boot': {
        const sp = 4.2, p = A.stridePhase(t * 1.0, sp); { const P = A.bootLoss(clampT(s.k), p); P.yaw = 180; setPose(H.dex, P); } setBoot(H.dex, 'L', clampT(s.k) < 0.34); setFace(H.dex, { eyes: 'eyes_wide', brows: 'brows_worried', mouth: s.mouth ?? 'mouth_shout' });
        const z0 = -sp * t; H.dex.root.position.set(0, H.dex.root.position.y, z0); fixGround(H.dex); focus = V(0, 1.0, z0);
        const b = H.boot, k = clampT(s.k); if (k >= 0.34) { const u = (k - 0.34) * (s.dur ?? 1.4); b.visible = true; b.position.set(-0.1 + 0.2 * u, 0.5 + 2.6 * u - 4.9 * u * u * 1.0, z0 + 0.4 - 4.2 * u); b.rotation.set(6 * u, 1.2 * u, 3 * u); if (b.position.y < 0.05) b.position.y = 0.05; } else b.visible = false; break; }
      case 'act': {   // unified Maple Street action: jog -> plant -> jump -> grab -> drag -> reach -> crash-hang. s: {m, tt, g, vanOff, focus, mouth, reach, ti}
        const D2R = Math.PI / 180; const m = s.m, S = H.dex.root.scale.x, vz = H.van.position.z, g = s.g ?? 0, th = s.pitch ?? 36, ti = s.ti ?? -1;
        const gripL = V(0.24, 0.9, vz + 2.77), gripR = V(-0.24, 0.9, vz + 2.77), neck = V(-0.3, 1.02, vz + 3.0);
        const FIST = [0.75, 0.9, 0.92, 0.94, 0.95], GUIT = [0.55, 0.85, 0.88, 0.9, 0.92];
        const shoulders = () => { const a = V(0, 0, 0), c = V(0, 0, 0); H.dex.j.arms.L.sh.getWorldPosition(a); H.dex.j.arms.R.sh.getWorldPosition(c); return a.add(c).multiplyScalar(0.5); };
        const dragPose = (reach, bounce) => ({ yaw: 180, pitch: th, spine: [-4, 2 * Math.sin(g * 5), 0], head: [-36 - 6 * reach, 3 * Math.sin(g * 6), 0],
          L: { sh: [150, 10], el: 40, curl: FIST }, R: { sh: [150, 10], el: 40, curl: reach > 0.05 ? GUIT : FIST },
          legL: { hip: [-8 + 14 * Math.sin(g * 9), 5], knee: 28 + 24 * Math.max(0, Math.sin(g * 9)), foot: -th * 0.8 }, legR: { hip: [-8 + 14 * Math.sin(g * 9 + 2.6), 5], knee: 28 + 24 * Math.max(0, Math.sin(g * 9 + 2.6)), foot: -th * 0.8 } });
        const placeDrag = (P, shZ, shY) => { setPose(H.dex, P); H.dex.root.rotation.y = Math.PI; H.dex.root.position.set(0.0, 0, vz + 3.9); H.dex.root.updateMatrixWorld(true);
          for (let k = 0; k < 2; k++) { const sh = shoulders(); H.dex.root.position.z += shZ - sh.z; H.dex.root.updateMatrixWorld(true); fixGround(H.dex); } };
        let focusPt = V(0, 0.9, vz + 3);
        if (m === 'drag' || m === 'reach' || m === 'crash') {
          const reach = m === 'reach' ? sm2(0.0, 0.8, s.k ?? 1) : (m === 'crash' ? 0.6 : 0);
          let pit = th; if (m === 'crash' && ti > 0) pit = th - 26 * sm2(0, 0.3, ti) + 3 * Math.sin(ti * 14) * Math.exp(-ti * 3);
          const P = dragPose(reach, 0); P.pitch = pit; placeDrag(P, vz + 3.15, 0);
          const e1 = A.ikArm(THREE, H.dex, 'L', gripL, -0.2); const tR = reach > 0.02 ? V(lerpN(-0.24, -0.37, reach), lerpN(0.9, 0.95, reach), lerpN(vz + 2.77, vz + 3.08, reach)) : gripR;
          const e2 = A.ikArm(THREE, H.dex, 'R', tR, -0.2);
          if (s.dbgR) { const shR = V(0, 0, 0); H.dex.j.arms.R.sh.getWorldPosition(shR); const pr = V(0, -0.2, 0); H.dex.j.arms.R.wr.localToWorld(pr); console.error('RDBG ' + JSON.stringify({ shR: shR.toArray().map(v => +v.toFixed(2)), tgt: tR.toArray().map(v => +v.toFixed(2)), palm: pr.toArray().map(v => +v.toFixed(2)), err: +e2.toFixed(3), d: +shR.distanceTo(tR).toFixed(3) })); }
          { const fm = footMin(H.dex); if (fm < 0) H.dex.root.position.y -= fm; }
          { const shL = V(0, 0, 0); H.dex.j.arms.L.sh.getWorldPosition(shL); const wr = V(0, -0.2, 0); H.dex.j.arms.L.wr.localToWorld(wr); const elb = V(0, 0, 0); H.dex.j.arms.L.el.getWorldPosition(elb); console.error('ACTCHK ' + JSON.stringify({ m, eL: +e1.toFixed(3), eR: +e2.toFixed(3), foot: +footMin(H.dex).toFixed(3), shL: shL.toArray().map(v => +v.toFixed(2)), el: elb.toArray().map(v => +v.toFixed(2)), palm: wr.toArray().map(v => +v.toFixed(2)), grip: gripL.toArray().map(v => +v.toFixed(2)), UA: +shL.distanceTo(elb).toFixed(3), rootZ: +H.dex.root.position.z.toFixed(2), vz: +vz.toFixed(2), rot: H.dex.j.arms.L.sh.rotation.toArray().slice(0, 3).map(v => +(v / D2R).toFixed(0)) })); }
          focusPt = V(0, 0.85, vz + 2.9);
        } else if (m === 'jog') {
          const gt = A.gait(s.tt, 'jog', S), P = gt.pose; P.yaw = 180 + gt.yaw; if (s.phone) { P.R = { sh: [62, 16], el: 108, curl: [0.45, 1.1, 1.12, 1.14, 1.15], phone: true, roll: -35 }; P.head = [P.head[0] + 4, P.head[1], 0]; }
          setPose(H.dex, P); H.dex.root.position.set(0, gt.rootY, s.dz); H.dex.root.updateMatrixWorld(true); { const fm = footMin(H.dex); if (fm < 0) H.dex.root.position.y -= fm; }
          focusPt = V(0, 0.9, s.dz + (s.focusDz ?? 0));
        } else if (m === 'jump') {   // plant (0..0.3), flight (0.3..1) to the bumper
          const a = s.a, pl = Math.min(1, a / 0.3), fl = Math.max(0, (a - 0.3) / 0.7), e = fl * fl * (3 - 2 * fl);
          const gt = A.gait(1.6, 'jog', S), P = gt.pose; P.yaw = 180;
          const crouchP = { spine: [22, 0, 0], head: [-10, 0, 0], L: { sh: [70, 10], el: 90, curl: [0.8, 1, 1, 1, 1] }, R: { sh: [70, 10], el: 90, curl: [0.8, 1, 1, 1, 1] }, legL: { hip: [52, 4], knee: 92 }, legR: { hip: [52, 4], knee: 92 } };
          const flyP = dragPose(0, 0); flyP.pitch = th; flyP.L.sh = [170, 8]; flyP.R.sh = [170, 8]; flyP.L.el = 10; flyP.R.el = 10;
          let Q = fl <= 0 ? A.mixPose(P, { ...P, ...crouchP, yaw: 180 }, sm2(0, 1, pl)) : A.mixPose({ ...P, ...crouchP, yaw: 180 }, flyP, e);
          Q.yaw = 180; Q.pitch = fl <= 0 ? 0 : th * e; setPose(H.dex, Q); H.dex.root.rotation.y = Math.PI;
          const zP = s.dz, zE = vz + 3.9, z = fl <= 0 ? zP : lerpN(zP, zE, Math.pow(fl, 1.4)); H.dex.root.position.set(0, 0, z); H.dex.root.updateMatrixWorld(true); fixGround(H.dex);
          if (fl > 0) { H.dex.root.position.y += 0.9 * 4 * fl * (1 - fl) * (1 - 0.3 * fl); H.dex.root.updateMatrixWorld(true);
            const w = Math.pow(fl, 2), sh = shoulders(); const tL = V(0, 0, 0).lerpVectors(sh.clone().add(V(-0.2, 0.1, -0.5)), gripL, w), tR2 = V(0, 0, 0).lerpVectors(sh.clone().add(V(0.2, 0.1, -0.5)), gripR, w); A.ikArm(THREE, H.dex, 'L', tL, -0.2); A.ikArm(THREE, H.dex, 'R', tR2, -0.2); }
          focusPt = V(0, 0.9, H.dex.root.position.z);
        }
        setFace(H.dex, { eyes: s.eyes ?? 'eyes_wide', brows: s.brows ?? 'brows_angry', mouth: s.mouth ?? 'mouth_shout' });
        // crash bits: bucket flight, tulips, Nana dodge
        if (s.dbgNana && H.nana) { const q = V(0, 0, 0); H.nana.root.getWorldPosition(q); console.error('NANADBG ' + JSON.stringify({ pos: q.toArray().map(v => +v.toFixed(2)), vis: H.nana.root.visible, sc: H.nana.root.scale.x, stand: H.stand.position.toArray() })); }
        if (m === 'crash' || s.nanaDodge !== undefined) { const nn = H.nana; if (nn) { const d = Math.max(0, (s.nanaDodge ?? ti) + 0.35); setPose(nn, A.nanaDuck(Math.min(1, d / 0.5), g)); setFace(nn, { eyes: d > 0.05 ? 'eyes_closed' : 'eyes_wide', brows: 'brows_worried', mouth: 'mouth_shout' }); } }
        if (H.stand && H.stand.userData.buckets) for (const bk of H.stand.userData.buckets) { if (!bk.userData.p0) { bk.updateMatrixWorld(true); scene.attach(bk); bk.userData.p0 = bk.position.clone(); bk.userData.q0 = bk.quaternion.clone(); bk.userData.side = bk.position.x > H.stand.position.x ? 1 : -1; bk.userData.mid = Math.abs(bk.position.x - H.stand.position.x) < 1.2; }
          const u = Math.max(0, ti), p0 = bk.userData.p0, side = bk.userData.side, k = bk.userData.mid ? 1 : 0.6;
          if (u > 0) { bk.position.set(p0.x + side * 4.4 * k * u, p0.y + 5.6 * k * u - 4.9 * u * u, p0.z - 0.3 * u); if (bk.position.y < 0.2) { bk.position.y = 0.2; } bk.rotation.set(5 * u * side, 2 * u, 8 * u * side); } else { bk.position.copy(p0); bk.quaternion.copy(bk.userData.q0); } }
        if (H.tulips) { H.tulips.group.visible = true; H.tulips.group.position.set(H.stand.position.x, 0, H.stand.position.z + 0.15); H.tulips.update(Math.max(-1, ti) * 1.0); }
        if (H.pigeons) H.pigeons.group.visible = false;
        if (s.mode2 === undefined) { const mm = s.focusOverride; if (mm === 'van') focusPt = V(0, 1.0, vz); else if (mm === 'nose') focusPt = V(0, 1.0, vz - 2.6); else if (mm === 'stand') focusPt = V(H.stand.position.x, 0.9, H.stand.position.z); else if (mm === 'nana') focusPt = V(-2.1, 0.9, H.stand.position.z + 0.4); else if (mm === 'hands') focusPt = V(0, 0.85, vz + 2.8); else if (mm === 'neck') focusPt = V(0.3, 1.1, vz + 3.2); }
        focus = focusPt; break; }
      case 'chase': {   // IK jog up behind the moving van, plant, jump, grab the bumper, get dragged (continuous, with overlapping head/arm lag)
        const tt = s.tt, S = H.dex.root.scale.x, bump = H.van.position.z + 2.88, vJog = A.GAITS.jog.v, GAP = 3.0;
        const zRun = (q) => (-6 + (s.vanZ0 ?? 0) + 2.88 + GAP) - vJog * Math.min(q, 1.6);   // Dex ground track while jogging (the van drives away at its own speed)
        const poseAt = (q) => {
          let u; if (q < 1.6) u = 0.25 * q / 1.6; else if (q < 1.95) u = 0.25 + 0.1 * (q - 1.6) / 0.35; else if (q < 2.75) u = 0.35 + 0.43 * (q - 1.95) / 0.8; else u = 0.78 + 0.22 * sm2(2.75, 3.2, q);
          const P = A.dive(u); const g = A.gait(Math.min(q, 1.6), 'jog', S); const rw = 1 - sm2(0.2, 0.3, u);
          const Q = rw > 0.001 ? A.mixPose(P, g.pose, rw) : P; if (q >= 2.75) { const dr = A.drag(q, {}); Q.legL = dr.legL; Q.legR = dr.legR; } return { Q, P, g, u };
        };
        const cur = poseAt(tt), lagH = poseAt(Math.max(0, tt - 0.07)), lagA = poseAt(Math.max(0, tt - 0.04));
        const Q = cur.Q; Q.head = lagH.Q.head; Q.spine = [lerpA(cur.Q.spine[0], lagA.Q.spine[0], 0.5), cur.Q.spine[1], cur.Q.spine[2]]; Q.L = { ...Q.L, el: lagA.Q.L.el, curl: lagA.Q.L.curl }; Q.R = { ...Q.R, el: lagA.Q.R.el, curl: lagA.Q.R.curl };
        const z0 = zRun(tt) - (tt > 1.6 ? 1.2 * Math.min(1, (tt - 1.6) / 0.35) : 0); const a = (tt - 1.95) / 0.8; const u = cur.u;
        const place = (pitch) => { Q.yaw = 180; Q.pitch = pitch; setPose(H.dex, Q); H.dex.root.rotation.y = Math.PI; H.dex.root.position.set(0, tt < 1.6 ? cur.g.rootY : H.dex.root.position.y, z0);
          if (tt >= 1.6 && tt < 1.95) { H.dex.root.updateMatrixWorld(true); fixGround(H.dex); }
          else if (tt >= 1.95 && tt < 2.75) { H.dex.root.position.y = 0.05 + 0.95 * Math.sin(Math.PI * Math.max(0, a)) * (1 - 0.35 * a) + 0.28 * a; }
          const hm = handMid(H.dex), w = tt < 1.95 ? 0 : (tt < 2.75 ? Math.pow(Math.min(1, a), 1.6) : 1);
          H.dex.root.position.z += w * (bump - hm.z); if (tt >= 2.55) H.dex.root.position.y += sm2(2.55, 2.85, tt) * (0.5 - handMid(H.dex).y);
          H.dex.root.updateMatrixWorld(true); return footMin(H.dex); };
        if (tt >= 2.75) { let lo = 30, hi = 84; for (let i = 0; i < 9; i++) { const mid = (lo + hi) / 2, fm = place(mid); if (fm > 0.02) hi = mid; else lo = mid; } const fm = place((lo + hi) / 2); if (fm < 0) { H.dex.root.position.y -= fm; } }
        else { place(Q.pitch ?? 0); const fm = footMin(H.dex); if (fm < 0) H.dex.root.position.y -= fm; }
        if (tt < 1.6) H.dex.root.rotation.y = Math.PI + cur.g.yaw * Math.PI / 180;
        setFace(H.dex, { eyes: 'eyes_wide', brows: 'brows_angry', mouth: s.mouth ?? 'mouth_shout' }); const hmx = handMid(H.dex); if (tt >= 2.75) console.error('GRABCHK ' + JSON.stringify({ tt, dz: +(hmx.z - bump).toFixed(3), dy: +(hmx.y - 0.5).toFixed(3), foot: +footMin(H.dex).toFixed(3) }));
        focus = V(0, 0.6, tt >= 2.4 ? (bump + H.dex.root.position.z) / 2 : H.dex.root.position.z - 0.8); break; }
      case 'dive': {
        H.dex.root.position.set(0, 0, rear + lerp(3.4, 1.9, sm(0.18, 0.68, t))); H.dex.root.rotation.y = Math.PI; setPose(H.dex, A.dive(t)); H.dex.root.rotation.y = Math.PI; setFace(H.dex, { eyes: 'eyes_wide', brows: 'brows_angry', mouth: 'mouth_shout' }); focus = V(0, 0.7, rear + 1.2); break; }
      case 'drag': {
        H.dex.root.position.set(0, 0, rear + 1.85); setPose(H.dex, A.drag(g, { selfie: s.selfie })); setFace(H.dex, { eyes: 'eyes_wide', brows: 'brows_worried', mouth: 'mouth_shout' }); focus = V(0, 0.4, rear + 0.9); break; }
      case 'split': {   // hands on the bumper (left) and fingers on a guitar neck that sticks out of the van's back window (right)
        const vz0 = H.van.position.z, rr = vz0 + 2.8; H.dex.root.position.set(0.1, 0, rr + 1.5); const P = A.reach(1, s.g ?? 0); setPose(H.dex, P); H.dex.root.position.x = 0.1; H.dex.root.rotation.y = Math.PI; H.dex.root.rotation.y = Math.PI;
        setFace(H.dex, { eyes: 'eyes_wide', brows: 'brows_up', mouth: s.mouth ?? 'mouth_closed_worried' }); scene.updateMatrixWorld(true);
        const hp = V(0, -0.2, 0); H.dex.j.arms.R.wr.localToWorld(hp); const g = H.vguitar; if (g) { scene.attach(g); g.scale.setScalar(0.6); g.rotation.set(Math.PI / 2, 0, 0); g.position.set(hp.x, hp.y, hp.z + 0.12 - 1.25); }
        focus = V(0.1, 0.8, rr + 0.9); break; }
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
          setGigPose(gig, { spine: [1.4 * Math.sin(t * 2.3) + (s.what === 'horn' ? 5 : 0), 0, 0], head: [-3 + 2 * Math.sin(t * 2.1 - 0.4) + (s.what === 'horn' ? 3 : 0), 4 * Math.sin(t * 1.3), 3 * Math.sin(t * 0.9)], L: { sh: [40, 10], el: 60, curl: 1 }, R: { sh: [40, 10], el: 60, curl: 1 }, legL: { hip: 85, knee: 80 }, legR: { hip: 85, knee: 80 }, tail: [20 + 14 * Math.sin(t * 2.6 - 0.8), 10 * Math.sin(t * 1.9)] }); scene.updateMatrixWorld(true);
          const press = s.what === 'horn' ? Math.max(0, Math.sin(t * 2 * Math.PI * 2.2 - 1.2)) : 0;
          w.rotation.z = 0.5; scene.updateMatrixWorld(true);
          A.ikPaw(THREE, gig, 'L', w.localToWorld(V(0.62 * Math.cos(2.85), 0.62 * Math.sin(2.85), 0)));
          if (s.what === 'horn') A.ikPaw(THREE, gig, 'R', w.localToWorld(V(0, 0.02, 0.1 - 0.08 * press)), [60, 10, 80]); else A.ikPaw(THREE, gig, 'R', w.localToWorld(V(0.62 * Math.cos(0.3), 0.62 * Math.sin(0.3), 0)));
          setGigFace(gig, { eyes: 'eyes_wide', mouth: s.what === 'horn' && press > 0.3 ? 'mouth_open' : 'mouth_smile' });
        }
        const wp = V(0, 0, 0), hp = V(0, 0, 0); w.getWorldPosition(wp); gig.j.head.getWorldPosition(hp); focus = wp.clone().add(hp).multiplyScalar(0.5); break; }
      case 'van': { if (s.pigeonZ !== undefined && H.pigeons) H.pigeons.group.position.set(0, 0, s.pigeonZ); H.pigeons?.update(s.pigeonT ?? -1); H.tulips?.update(s.tulipT ?? -1); focus = V(0, 1, vz); break; }
    }
    if (s.pigeonT !== undefined) H.pigeons?.update(s.pigeonT); if (s.tulipT !== undefined) H.tulips?.update(s.tulipT);
    if (H.sun) { H.sun.target.position.set(focus.x, 0, focus.z); H.sun.position.set(focus.x + 10, 22, focus.z + 12); H.sun.target.updateMatrixWorld(); }
    scene.updateMatrixWorld(true);
    const c = s.cam; if (c.rel) { camera.position.set(focus.x + c.pos[0], focus.y + c.pos[1], focus.z + c.pos[2]); camera.lookAt(focus.x + (c.look?.[0] ?? 0), focus.y + (c.look?.[1] ?? 0), focus.z + (c.look?.[2] ?? 0)); } else { camera.position.set(...c.pos); camera.lookAt(...c.look); }
    camera.fov = c.fov ?? 40; camera.updateProjectionMatrix(); camera.updateMatrixWorld(); renderer.render(scene, camera);
  };
}
const lerpA = (a, b2, t) => a + (b2 - a) * t, lerpN = lerpA;
const clampT = (k) => Math.min(1, Math.max(0, k ?? 0)), lerp = (a, b, t) => a + (b - a) * t, sm = (a, b, x) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };
