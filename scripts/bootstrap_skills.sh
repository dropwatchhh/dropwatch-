#!/usr/bin/env bash
# bootstrap_skills.sh — Claude Code teaches itself (from free open-source
# projects and GitHub) how to watch/hear a reference video and produce
# original videos in its visual style.
#
# Run once BEFORE daily_videos.sh:   ./bootstrap_skills.sh
# Needs: claude CLI logged in, internet, Python 3.10+, ffmpeg, git.
# A GPU makes generation fast; without one it falls back to lighter methods.

set -euo pipefail
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
command -v claude >/dev/null || { echo "claude not found"; exit 1; }

BASE="$HOME/video_factory"
mkdir -p "$BASE"/{reference,skills,work,output,logs}
cd "$BASE"
exec > >(tee -a "$BASE/logs/bootstrap-$(date +%F).log") 2>&1

PROMPT=$(cat <<EOF
You are my video-production engineer. Work in $BASE. Goal: gain, from free
open-source projects and GitHub, every skill needed to (A) watch and listen
to the reference video in $BASE/reference/ and (B) make original videos in
its visual style. Do not stop at the first failure; try another tool.

CONTENT RULES: original characters and invented stories only. No real
people, politicians, celebrities, brands, logos, flags or fake news formats.
PG-13 at most. Copy only the reference's look and pacing, never its footage,
audio, characters, text or message.

SAFETY RULES: install only into a virtualenv at $BASE/.venv. Prefer
MIT/Apache-2.0/BSD/CC0 projects. Read the README, license and code of any
repo before running it. Never run curl|bash or unreviewed install scripts.
Never paste or request secrets. Download model weights only from the
project's official page or Hugging Face repo.

PHASE 0 — CHECK THE MACHINE
Record OS, CPU, RAM, free disk, GPU/VRAM (nvidia-smi or equivalent), Python
and ffmpeg versions in $BASE/skills/machine.md. Choose heavy or light tools
to match (e.g. no GPU: use small models, short clips, and procedural
animation).

PHASE 1 — SKILL: SEE THE VIDEO
- Frame extraction with ffmpeg (1 frame per 2 s) plus scene-change detection
  (PySceneDetect).
- Frame understanding with an open vision-language model (e.g. Qwen2-VL,
  moondream, LLaVA, or SmolVLM via transformers/ollama). Produce a text
  description of each frame and the overall visual style.
- Verify by describing 5 frames and checking them against the images.

PHASE 2 — SKILL: HEAR THE VIDEO
- Speech-to-text with faster-whisper or whisper.cpp; save a transcript with
  timestamps. Detect language. Separate music from voice if possible
  (demucs).
- Verify on the reference and note the pace (words per minute).

PHASE 3 — SKILL: MAKE THE VISUALS
Find and test open-source image/video generation that can produce a
brick-toy diorama look: ComfyUI, diffusers with Stable Diffusion / SDXL /
FLUX.1-schnell, and image-to-video such as LTX-Video, Wan 2.1, CogVideoX or
Stable Video Diffusion; or Blender (bpy) for real 3D brick-style scenes.
Pick what fits this machine. Make 3 test images and 1 test clip. Save the
working recipe.

PHASE 4 — SKILL: VOICE, MUSIC, CAPTIONS, EDITING
- Voice: Piper, Kokoro or Coqui TTS (check each license).
- Music/SFX: only CC0 or self-generated sources.
- Captions: faster-whisper word timestamps burned in with ffmpeg/Pillow.
- Assembly: MoviePy or ffmpeg, vertical 1080x1920, EVERY video at least 60 s (target 65-90 s), 8-12 scenes, 3 escalating beats.

PHASE 5 — PROVE IT
Produce one finished original video of at least 60 s (target 70 s) at $BASE/work/test.mp4 using the
learned skills: hook in 2 s, escalation, punchline, captions, voice, music.
Extract frames and listen/transcribe to verify it. Fix problems and repeat.

PHASE 6 — SAVE WHAT YOU LEARNED
For every tool you adopted write $BASE/skills/<tool>.md: purpose, license,
exact install commands, tested example, known limits. Write
$BASE/skills/style_guide.md (visual style only) and
$BASE/skills/README.md summarizing what works, what is slow or weak, and
anything I must provide. Print a 5-line summary at the end.
EOF
)

claude -p "$PROMPT" \
  --allowedTools "Bash,Read,Write,Edit,Glob,Grep,WebFetch,WebSearch" \
  --permission-mode acceptEdits
