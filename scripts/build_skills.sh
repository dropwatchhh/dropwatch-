#!/usr/bin/env bash
# build_skills.sh — Claude Code teaches ITSELF to make videos that look like
# your reference, by finding, vetting and testing open-source tools on GitHub.
# Run on YOUR computer (needs ffmpeg, git, python3; a GPU helps a lot).
#
#   1. Put the reference in ~/video_factory/reference/ (.mp4 or .mov)
#   2. ./build_skills.sh            (run once; re-run to keep improving, up to 3 passes)
#   3. Then use daily_videos.sh daily
#
# Everything it learns is saved as recipes in ~/video_factory/skills/.

set -euo pipefail
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
command -v claude >/dev/null || { echo "claude not found"; exit 1; }
command -v ffmpeg >/dev/null || { echo "install ffmpeg first"; exit 1; }

NICHE="${NICHE:-funny mini-stories about original brick-toy characters in everyday situations}"
PASSES="${PASSES:-3}"
BASE="$HOME/video_factory"
mkdir -p "$BASE"/{reference,skills,tools,work,output,logs}
cd "$BASE"
ls reference/*.mp4 reference/*.mov >/dev/null 2>&1 || { echo "Put the reference video in $BASE/reference/"; exit 1; }
exec > >(tee -a "$BASE/logs/$(date +%F)-build_skills.log") 2>&1

TOOLS="Bash,Read,Write,Edit,Glob,Grep,WebFetch,WebSearch"

RULES="RULES: Original characters and invented stories only. No real people,
celebrities, politicians, real brands/logos/flags, fake news, hate, or graphic
violence. Never copy the reference's footage, audio, voice, characters, text or
story; learn only its VISUAL LOOK, camera, lighting, pacing and caption style.
SAFETY: only install from GitHub/PyPI repos with MIT/Apache-2.0/BSD/CC0
licenses (read LICENSE and the code first; check stars/recent commits). Use
the virtualenv $BASE/.venv and clone into $BASE/tools. Never run curl|bash,
never sudo, never send my files or reference video to any web service, and
never use paid services or API keys unless I put them in the environment."

prompt() { cat <<EOT
You are my self-teaching video-production agent. Work in $BASE.
Goal: make short vertical videos that look as close as possible to the
reference in $BASE/reference/. Niche: $NICHE. This is pass $1 of $PASSES.
$RULES

Read $BASE/skills/README.md and any recipes first if they exist, then continue.

STEP 1 - LOOK. Use ffmpeg to extract a frame every 1-2 s (and a contact
sheet). View them. Describe the look in $BASE/skills/style_guide.md: aspect
ratio, material/texture, lighting, lens/camera moves, shot length, cut rate,
color grade, motion style, hook, captions (font/size/position/animation),
audio (music/voice/sfx), story structure. Also write 8 reusable TEXT PROMPT
TEMPLATES that reproduce this look for an image/video generator (positive and
negative prompts). Transcribe audio if a local open-source STT works.

STEP 2 - CHECK HARDWARE. Record GPU/VRAM/RAM/disk (nvidia-smi, system_profiler,
etc.) in $BASE/skills/hardware.md. Pick only tools that fit it.

STEP 3 - FIND TOOLS ON GITHUB. Use WebSearch/WebFetch (and gh/git if
available) to find the best current free, permissively licensed tools for each
need, comparing at least 3 candidates each:
  a) text-to-video / image-to-video (e.g. Wan, LTX-Video, HunyuanVideo,
     CogVideoX, Mochi, AnimateDiff; run via ComfyUI or diffusers)
  b) image generation for consistent toy/brick-style characters (SDXL/FLUX
     with LoRAs, ComfyUI workflows, IP-Adapter for character consistency)
  c) voice (Piper, Kokoro, F5-TTS), music (MusicGen/CC0 libraries), sfx (CC0)
  d) captions and editing (faster-whisper, MoviePy, ffmpeg, Remotion)
  e) upscaling/interpolation (Real-ESRGAN, RIFE) if the clips look soft
Record each choice with license, repo URL, commit, VRAM need and why.

STEP 4 - INSTALL AND TEST. Install the best fits in $BASE/.venv / $BASE/tools,
download open model weights only from official sources, and generate real test
clips. Save a TESTED recipe per tool as $BASE/skills/<tool>.md containing exact
commands, settings, prompts that worked, runtime, and known failures.

STEP 5 - BUILD A PIPELINE. Write $BASE/skills/make_video.sh (or .py) that takes
an idea/script file and outputs a 1080x1920 .mp4 (20-40 s): shots -> clips ->
edit -> captions -> voice -> music -> mix.

STEP 6 - COMPARE AND SCORE. Make $BASE/work/test_$1.mp4 (20 s original gag).
Extract its frames next to reference frames, and score 1-10 on look, motion,
lighting, captions and audio. Write what is still different and the single most
valuable next improvement to $BASE/skills/gap_report.md.

STEP 7 - Update $BASE/skills/README.md: what works, what is weak, what I must
supply (GPU, keys, models), exact one-line way to run make_video, and the tool
list with licenses. Be honest about quality; do not claim a match you did not
verify from frames.
Print a summary of 8 lines or fewer.
EOT
}

for i in $(seq 1 "$PASSES"); do
  echo "=== pass $i/$PASSES ==="
  claude -p "$(prompt "$i")" --allowedTools "$TOOLS" --permission-mode acceptEdits
done
echo "Done. See $BASE/skills/README.md and gap_report.md"
