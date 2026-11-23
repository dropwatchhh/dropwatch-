#!/usr/bin/env bash
# daily_videos.sh — Claude Code studies a reference video's VISUAL STYLE and
# makes 4 original videos a day, finished before 10:00 AM.
#
# SETUP:
#   1. Put your reference video here:  ~/video_factory/reference/ref.mov
#   2. Edit NICHE below (what the videos are about).
#   3. ./daily_videos.sh learn      (once)
#   4. Schedule at 5:30 AM (computer must be on):  30 5 * * * /full/path/daily_videos.sh daily

set -euo pipefail
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
command -v claude >/dev/null || { echo "claude not found"; exit 1; }

# CHANGE THIS: topic for the videos. Original characters and stories only.
NICHE="funny mini-stories about original brick-toy characters in everyday situations (office, kitchen, pets, school)"

BASE="$HOME/video_factory"
mkdir -p "$BASE"/{reference,skills,output,work,logs}
cd "$BASE"
TOOLS="Bash,Read,Write,Edit,Glob,Grep,WebFetch,WebSearch"
MODE="${1:-daily}"; TODAY="$(date +%F)"
exec > >(tee -a "$BASE/logs/$TODAY-$MODE.log") 2>&1

RULES="CONTENT RULES: Only original characters and invented stories. No real
people, politicians, celebrities, real brands, logos, flags, or fake news
broadcasts. No hateful stereotypes, no violence beyond cartoon slapstick,
PG-13 humor at most. Do not copy the reference video's footage, audio, voice,
characters, text or story. Use only the reference's visual look and pacing."

learn_prompt() { cat <<EOT
You are my video-production agent. Work in $BASE. Niche: $NICHE.
$RULES

1. Study the reference in $BASE/reference/ (an .mp4 or .mov). Use ffmpeg to
   extract about 1 frame every 2 seconds and look at them. Check the audio
   (music vs voice; transcribe with an open-source tool if available).
2. Write $BASE/skills/style_guide.md: aspect ratio, brick-toy look, lighting,
   camera angles, cut rate, hook in the first 2 seconds, caption style
   (font, size, position), music/voice style, and story structure
   (hook / escalation / punchline). Style only, not the political topic.
3. Make a 70-second original test video in this style in $BASE/work/test.mp4.
4. For anything missing (animation, voice, music, captions, images), search
   GitHub and the web for free permissively licensed tools (MIT/Apache/BSD/
   CC0), such as ffmpeg, MoviePy, Remotion, Blender, Piper or edge-tts,
   faster-whisper, ComfyUI/Stable Diffusion, Pexels/Pixabay. Read code and
   licenses first, use a virtualenv at $BASE/.venv, never run curl|bash.
   Save a tested recipe per tool in $BASE/skills/.
5. Write $BASE/skills/README.md: what works, what is weak, what I must supply.
EOT
}

daily_prompt() { cat <<EOT
You are my video-production agent. Work in $BASE. Today is $TODAY.
Niche: $NICHE.
$RULES
Each video must be 60+ seconds, so budget time for rendering. Deadline: 4 finished videos in $BASE/output/$TODAY/ by 9:45 AM local time.
Check \`date\` as you go; simplify rather than miss it. Finish each video
completely before starting the next.
1. Read $BASE/skills/style_guide.md and all recipes in $BASE/skills/. If the
   style guide is missing, stop and say so.
2. Write 4 NEW ideas (not repeats of $BASE/output/*/ideas.md), each with a
   hook, short script, and punchline.
3. Produce vertical 1080x1920 .mp4 files video01..04 with captions and audio.
   Verify each: frames look right, audio present, length MUST be at least 60 seconds (target 65-90 s). Reject and redo any video under 60 s. Plan 8-12 scenes and a story with 3 escalating beats.
4. If a technique fails, find a free open-source fix, add a recipe, continue.
5. Save $BASE/output/$TODAY/ideas.md (title, script, caption, hashtags).
Do not post anywhere. Print the 4 file paths when done.
EOT
}

case "$MODE" in
  learn) claude -p "$(learn_prompt)" --allowedTools "$TOOLS" --permission-mode acceptEdits ;;
  daily) claude -p "$(daily_prompt)" --allowedTools "$TOOLS" --permission-mode acceptEdits ;;
  *) echo "Usage: $0 {learn|daily}"; exit 1 ;;
esac
