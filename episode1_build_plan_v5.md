# Episode 1: what is still unfinished, and build and render estimates (v5: one voice)

## Approved and locked (do not change)
Voice A for Dex, the black spike hair and black eyebrows, adult proportions (Dex 1.78 m), the fitted leather jacket, 12 fps frame-blended to 24 fps, 1080x1920, -14 LUFS, original synthesized music and effects.

## Already built (used in the approved test v4)
Dex (rig, face, hands, jacket, hair), Gig (rig, IK paws on the wheel), parking lot at human scale, van (outside and the cab), tripod, ring light and phone, chat/banner/caption overlays, lip-sync from audio, camera and timeline system, Piper-free voice pipeline (Qwen3-TTS).

## Unfinished 3D characters
| Item | State | Work needed |
|---|---|---|
| Lena (on a video call) | Head, body and fabric blazer exist; her room (desk, shelves, poster) was built for the old giant scale | Rescale the room to human size, pose her at the desk, arms-crossed and leaning-in poses, 2 camera angles, lip-sync and expressions |
| Nana Dot | Head, body and bowling jacket exist (the jacket still has no varsity stripes) | Place her at the stand, poses: watching on the phone, setting down the watering can, goalkeeper brace, waving, ducking; lip-sync and expressions |
| Priya | Cut as a character (a chat message only) | None |

## Unfinished 3D locations
| Item | State | Work needed |
|---|---|---|
| Maple Street | Built at the old giant scale | Rescale: road, houses, hill, street sign, curb, trees, lamp posts; downhill slope |
| Nana Dot's flower stand | Built at the old giant scale | Rescale to about 0.6x: counter, awning, sign, buckets, tulips |
| Lena's room | See above | Rescale |
| Lot, cab, van | Done | None |

## Unfinished props and animation
- **Props:** pigeon flock (small birds, wing flap, 9 of them), GPS unit (screen text), tulips and buckets (small, scatter and fly), watering can, brake cable, Dex's flying boot, street sign, flower-stand sign.
- **Dex animations:** run cycle, sprint, boot loss, selfie-phone running, dive and grab the bumper, being dragged, hanging on, reaching for the guitar, huge grin, ducking not needed.
- **Gig animations:** horn press (x2), reacting, covering his eyes, looking at the camera.
- **Nana Dot animations:** brace, wave, duck, put down the can.
- **Van:** motion down Maple Street (hill, bumps, speeding up), dragging Dex, nose reaching the tulips.
- **Shots:** split-screen CHASE/PLAY, freeze frame, vote card with pop-in text and counter.

## Unfinished audio
- **No extra voices.** Lena, Nana Dot and the GPS get no voice. Their words are reported by the one voice (voice A) and shown as captions.
- **Dex's new lines:** generate in the locked voice A (same description, seed 3, one pass per scene, then trim pauses).
- **Music:** extend the loop to 66 s, drop at the freeze frame.
- **New effects:** horn, boot clang, pigeon wings, tulip bucket rattle, GPS ding, record scratch.

## Known visual weaknesses (will remain unless you want more time spent)
Dex's legs are plain tubes with a hard knee step and a stiff stance; leather is smooth with few wrinkles; hands look rubbery; Gig's fur reads as fine tufts and his cap looks like a beret; no subsurface skin, no cloth simulation, no ambient occlusion; the hair's strand texture disappears at phone size.

## Build estimate (my working steps; I only work while you message me)
1. Rescale street, stand and Lena's room; place Nana Dot and Lena; stills for you to check: **1 step**.
2. Animation library: Dex run, dive, drag and the rest; Gig and Nana Dot poses; pigeons; stills or a short preview to check: **1.5–2 steps**.
3. ~~Voices for Lena, Nana Dot and GPS~~ **removed**. (Voice A lines for the whole episode are generated in step 4.)
4. Author the 35-shot timeline, chat and captions, split screen, freeze frame and vote card, audio mix: **1 step**.
5. Quality check at low resolution, fix, then the final render, blend and delivery: **0.5–1 step**.
**Total about 3.5–5 steps** (was 4.5–6; the voice step is gone). You approve the stills, the generated audio, and the finished episode.

## Render estimate (measured on this machine, 4 CPU cores, two renderers in parallel)
- Measured on test v4: 144 frames at 12 fps in **7.8 min** (832 s of frame time, 5.8 s per frame per renderer, 3.2 s effective), plus 36 s overlays and blend.
- Full episode: about **685 unique 3D frames** (57 s of action at 12 fps; the 9 s vote card is a held frame).
  - Frames: about 685 x 3.2 s = **37 min**. Street, stand and pigeon shots may be 20–40% heavier, so **40–55 min**.
  - Scene builds for about 38 shots: about 3 min.
  - Overlays and blend: about 3 min.
  - Audio (one voice, about 133 words, about 55 s of speech): about 4–6 min.
- **Total about 52–70 min.** The 2-hour daily window fits at 12 fps. At full 24 fps it would be about twice the frame time (100–130 min), which does not fit, so 12 fps blended stays.
- **Risk:** the first full episode has no spare time for a second full re-render on the same day, so I would first check every new shot at low resolution (about 2 s per frame) and fix problems before the final render.
