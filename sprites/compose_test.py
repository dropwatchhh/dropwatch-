"""2.5D sprite compositor for the Dex test. Layers from Blender (aligned, transparent) are stacked per frame.
usage: python3 -I compose_test.py SPRITE_DIR VOICE_DIR OUT.mp4"""
import json, subprocess, sys, time
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

SPR, VD, OUT = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
meta = json.load(open(SPR / "meta.json")); T = json.load(open(VD / "timing.json"))
FPS, N = T["fps"], int(T["total"] * T["fps"]); W, H = 1080, 1920
t_load = time.time()
L = {k: (Image.open(SPR / f"{k}.png").convert("RGBA"), meta[k]["box"]) for k in meta if k not in ("probe_bg", "probe_mouth", "probe_eyes", "probe_brows")}
bgbase = Image.open(SPR / "probe_bg.png").convert("RGBA"); bgbase.alpha_composite(L["base"][0])
BASE = bgbase

l1, l2 = T["spans"]
def segment(t):
    if t < l1[1] + 0.08: return "brag"
    if t < l2[0] - 0.02: return "take"
    if t < l2[1] + 0.06: return "nervous"
    return "smirk"
STATE = {"brag": ("brows_up", "eyes_squint", "mouth_closed_grin"), "take": ("brows_high", "eyes_wide", "mouth_Obig"),
         "nervous": ("brows_worried", "eyes_open", "mouth_closed_worried"), "smirk": ("brows_smirk", "eyes_half", "mouth_closed_smirk")}
BLINKS = [int(1.0 * FPS), int(3.4 * FPS)]; BLINK_SEQ = ["eyes_half", "eyes_closed", "eyes_closed", "eyes_half"]

# visemes from the audio: loudness picks open/closed, spectral centroid picks the vowel-ish shape; hold shapes >= 2 frames
shape, prev, dwell = [], None, 0
for f in range(N):
    o, c = T["rms"][f], T["centroid"][f]
    s = None if o < 0.12 else ("A" if o > 0.5 else ("O" if c < 1200 else "E"))
    if s != prev and prev is not None and s is not None and dwell < 2: s = prev
    dwell = dwell + 1 if s == prev else 1; prev = s; shape.append(s)

def compose(state, f):
    img = BASE.copy(); brows, eyes, mouth = STATE[state]
    for k in range(len(BLINKS)):
        if BLINKS[k] <= f < BLINKS[k] + 4: eyes = BLINK_SEQ[f - BLINKS[k]]
    if state in ("brag", "nervous") and shape[f]: mouth = "mouth_" + shape[f]
    for name in (brows, eyes, mouth):
        im, (x0, y0, x1, y1) = L[name]; img.alpha_composite(im, (x0, y0))
    return img

FONT = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
KW = {"ANYTHING!": (255, 63, 176), "fine.": (31, 230, 210), "roll!": (255, 210, 63)}
def caption(f):
    t = f / FPS; c = next((c for c in T["chunks"] if c["start"] <= t < c["end"]), None)
    if not c: return None
    font = ImageFont.truetype(FONT, 150); words = c["text"].split(" "); sp = 40
    ws = [font.getbbox(w)[2] for w in words]; tw = sum(ws) + sp * (len(words) - 1)
    img = Image.new("RGBA", (tw + 80, 260), (0, 0, 0, 0)); d = ImageDraw.Draw(img); x = 40
    for w, wd in zip(words, ws):
        d.text((x, 40), w, font=font, fill=KW.get(w, (255, 255, 255)) + (255,), stroke_width=18, stroke_fill=(26, 13, 51, 255)); x += wd + sp
    age = t - c["start"]; k = 0.7 + 0.36 * min(1, age / 0.1) - 0.06 * min(1, max(0, (age - 0.1) / 0.08))
    k = min(k, 940 / img.width * 1.0) if img.width * k > 940 else k
    return img.resize((int(img.width * k), int(img.height * k)), Image.LANCZOS)

ff = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", str(VD / "voice.wav"),
                       "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "17", "-c:a", "aac", "-b:a", "192k", "-t", str(T["total"]), OUT], stdin=subprocess.PIPE)
prev_seg, trans_start = None, -99; t_frames = time.time(); frame_times = []
for f in range(N):
    t0 = time.time(); t = f / FPS; sg = segment(t)
    if prev_seg and sg != prev_seg: trans_start, from_seg = f, prev_seg
    prev_seg = sg
    img = compose(sg, f)
    if f - trans_start < 4:                                   # cross-fade between expressions over 4 frames
        a = (f - trans_start + 1) / 5.0; img = Image.blend(compose(from_seg, f), img, a)
    z = 1.0 + 0.04 * (t / T["total"]); bob = -10 * T["rms"][f]                       # slow push-in + loudness bob
    cw, ch = W / z, H / z; cx, cy = W / 2, H / 2 - 40 + bob
    box = (cx - cw / 2, cy - ch / 2 + 40, cx + cw / 2, cy + ch / 2 + 40)
    img = img.crop((int(box[0]), int(box[1]), int(box[2]), int(box[3]))).resize((W, H), Image.BICUBIC)
    cap = caption(f)
    if cap: img.alpha_composite(cap, (int((W - cap.width) / 2), int(1500 - cap.height / 2)))
    ff.stdin.write(img.convert("RGB").tobytes()); frame_times.append(time.time() - t0)
ff.stdin.close(); ff.wait()
print(f"loaded layers {t_frames - t_load:.1f}s | composited {N} frames in {time.time() - t_frames:.1f}s = {(time.time() - t_frames) / N:.3f}s/frame")
