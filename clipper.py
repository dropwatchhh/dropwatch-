#!/usr/bin/env python3
"""Cut vertical (9:16) clips from stream VODs/clips using yt-dlp + ffmpeg.

Usage:  python3 clipper.py clips.csv [outdir]
clips.csv columns (header required): url,start,end,name
  start/end like 00:12:30 or 750 (seconds). Max ~60s per clip recommended.

Needs: pip install yt-dlp ; ffmpeg on PATH.
Only clip content you have permission to reuse (or that the platform's
clip/remix features allow). Early-play streams can be taken down.
"""
import csv, subprocess, sys, pathlib, shutil

def run(cmd):
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=True)

def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    for tool in ("yt-dlp", "ffmpeg"):
        if not shutil.which(tool):
            sys.exit(f"{tool} not found on PATH")
    out = pathlib.Path(sys.argv[2] if len(sys.argv) > 2 else "out")
    raw = out / "raw"; raw.mkdir(parents=True, exist_ok=True)

    with open(sys.argv[1], newline="") as f:
        for row in csv.DictReader(f):
            name, url = row["name"], row["url"]
            src = raw / f"{name}.mp4"
            run(["yt-dlp", "-f", "bv*[height<=1080]+ba/b", "--merge-output-format", "mp4",
                 "--download-sections", f"*{row['start']}-{row['end']}",
                 "--force-keyframes-at-cuts", "-o", str(src), url])
            final = out / f"{name}_9x16.mp4"
            # Blurred full-frame background + centered original = clean 1080x1920
            vf = ("[0:v]scale=1080:1920:force_original_aspect_ratio=increase,"
                  "crop=1080:1920,boxblur=25:5[bg];"
                  "[0:v]scale=1080:-2[fg];"
                  "[bg][fg]overlay=(W-w)/2:(H-h)/2,format=yuv420p")
            run(["ffmpeg", "-y", "-i", str(src), "-filter_complex", vf,
                 "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                 "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(final)])
            print("ready:", final)

if __name__ == "__main__":
    main()
