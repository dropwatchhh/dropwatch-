"""Piper voice for the sprite test: two lines, re-pitched for Dex, plus caption chunks and per-frame audio features (rms, centroid).
usage: python3 -I sprite_voice.py OUT_DIR"""
import json, subprocess, sys, wave
from pathlib import Path
import numpy as np

W = Path(sys.argv[1]); W.mkdir(parents=True, exist_ok=True)
MODEL = "/home/user/dropwatch-/voice/en_US-kristin-medium.onnx"
PITCH, FPS, LEAD, GAP, TOTAL = 0.92, 30, 0.10, 0.50, 5.0
TEMPO = 1.10     # Dex talks fast
LINES = ["Chat, I can play through anything!", "It's fine. It's rock and roll!"]
CHUNKS = [["Chat,", "I can play", "through", "ANYTHING!"], ["It's fine.", "It's rock", "'n' roll!"]]

def run(cmd, **kw): return subprocess.run(cmd, check=True, capture_output=True, text=True, **kw)
clips = []
for i, line in enumerate(LINES):
    raw, fin = W / f"l{i}_raw.wav", W / f"l{i}.wav"
    subprocess.run(["/root/.local/bin/piper", "-m", MODEL, "-f", str(raw)], input=line, text=True, check=True, capture_output=True)
    af = (f"silenceremove=start_periods=1:start_threshold=-45dB,areverse,silenceremove=start_periods=1:start_threshold=-45dB,areverse,"
          f"asetrate=22050*{PITCH},aresample=44100,atempo={1/PITCH*TEMPO:.4f},loudnorm=I=-16:TP=-1.5:LRA=7")
    run(["ffmpeg", "-y", "-v", "error", "-i", str(raw), "-af", af, "-ar", "44100", "-ac", "1", str(fin)])
    with wave.open(str(fin)) as w: clips.append((fin, w.getnframes() / w.getframerate()))
t = LEAD; spans = []
for (p, d) in clips: spans.append((t, t + d)); t += d + GAP
inputs, filt = [], []
for i, (p, d) in enumerate(clips):
    inputs += ["-i", str(p)]; filt.append(f"[{i}:a]adelay={int(spans[i][0]*1000)}|{int(spans[i][0]*1000)}[a{i}]")
mix = "".join(f"[a{i}]" for i in range(len(clips))) + f"amix=inputs={len(clips)}:normalize=0,apad=whole_dur={TOTAL},atrim=0:{TOTAL}[o]"
voice = W / "voice.wav"
run(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", ";".join(filt) + ";" + mix, "-map", "[o]", "-ar", "44100", "-ac", "1", str(voice)])

chunks = []
for (s, e), cs in zip(spans, CHUNKS):
    wts = [len(c.replace(" ", "")) + 2 for c in cs]; tot = sum(wts); cur = s
    for c, wgt in zip(cs, wts): d = (e - s) * wgt / tot; chunks.append({"text": c, "start": round(cur, 3), "end": round(cur + d, 3)}); cur += d
for i, c in enumerate(chunks): c["end"] = round(chunks[i + 1]["start"] if i + 1 < len(chunks) and chunks[i + 1]["start"] - c["end"] < 0.6 else c["end"] + 0.05, 3)

with wave.open(str(voice)) as w: sr = w.getframerate(); x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
n = int(TOTAL * FPS); rms, cen = [], []
for f in range(n):
    seg = x[int(f / FPS * sr): int((f + 1) / FPS * sr)]
    if len(seg) < 64: rms.append(0.0); cen.append(0.0); continue
    rms.append(float(np.sqrt(np.mean(seg ** 2))))
    spec = np.abs(np.fft.rfft(seg * np.hanning(len(seg)))); fr = np.fft.rfftfreq(len(seg), 1 / sr)
    cen.append(float((spec * fr).sum() / (spec.sum() + 1e-9)))
r = np.array(rms); r = np.clip(r / (np.percentile(r, 95) + 1e-9), 0, 1.2)
json.dump({"fps": FPS, "total": TOTAL, "spans": spans, "chunks": chunks, "rms": [round(float(v), 3) for v in r], "centroid": [round(c) for c in cen]}, open(W / "timing.json", "w"))
print("spans", [(round(a, 2), round(b, 2)) for a, b in spans], "chunks", len(chunks))
