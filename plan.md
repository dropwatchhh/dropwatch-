# Plan: Dex Hollow's 30 Days to Showtime (free tools only)

Status: **Dex is NOT approved yet.** Nothing below happens until you say so. This replaces the earlier Pesto plan.

## 0. Ground rule: free only

No paid plans, no paid credits, nothing that needs a credit card, no free trials that can turn into charges. If something cannot be done free, I say so here and give a manual free option.

Already installed, all free: yt-dlp, FFmpeg, whisper.cpp (speech to text and word timings), Piper text-to-speech with the Kristin voice (public domain), three.js 0.170.0 (3D), Pillow, the Inter font (open license). Nothing used so far needed an account, an API key or a card.

## 1. Google Flow free tier: what the official pages say

Source: Google's own Flow help pages (the credits page, the models page, "Where you can use Google Flow"). I read them through a page-reading agent. Google says limits "are subject to change at any time."

| Question | Answer (official) | Confidence |
|---|---|---|
| Free allowance | 50 credits a day with no subscription. Unused credits don't roll over. The day's refresh starts at your first generation. | Official |
| Clips per day | **Veo 3.1 Lite:** 10 credits per clip (4, 6 or 8 s, 720p), so **5 clips a day**. **Omni Flash 1.2:** 3–10 s clips at 360p for 1 credit per second, or 720p for 3 credits per second, so about **5 ten-second clips at 360p or 1 at 720p** a day. | Official |
| Retries | A bad clip still costs credits. | Follows from the rules |
| Peak-hour limit | Roughly 2–5 PM UTC (9 AM–12 PM Eastern in winter), free accounts "may not be able to generate videos." | Official |
| Free features | Text to video, frames to video, "ingredients" (reference images) to video, voice features. Extending clips, 1080p upscaling and 15 s clips are for subscribers. | Official |
| Age | Flow is "available to users ages 18+." That is the only age statement I found. | Official, but thin |
| Region | About 190 countries, including the US. | Official |
| Credit card | No page says the free tier needs one or converts to a charge. The pages do keep pushing "subscribe to a Google AI plan." | Official, absence only |
| **Watermarks, downloading free videos** | **Not stated on any page I could read.** | Unknown |
| **Posting on TikTok and monetizing** | **Not stated on any page I could read.** Google's Labs terms page returned a 404. | **Unknown** |
| Audio in free clips | Not clearly stated. | Unknown |

Two conflicts to be aware of:

- One Labs FAQ search result says Flow is "exclusively for Google AI Pro and Ultra subscribers," which contradicts the help center's 50 free credits a day. The pages may be out of date. Only you can settle it by opening Flow while signed in and **not** upgrading.
- One blog says some Veo models retire on December 5, 2026. I couldn't verify that.

My own background knowledge, not checked here: Google says Veo output carries an invisible SynthID mark, and TikTok asks creators to label realistic AI-generated content. I'd confirm both in the official policies before you rely on Flow for monetized posts.

**The key gap:** I couldn't find anything that says free-tier videos can be posted and monetized. I won't assume it. The manual check, if you want to use Flow, is to read the terms that appear when you sign in, and look for commercial use in the Google Terms of Service and the Flow help center. I can't do that for you.

I also can't sign in to your Google account, and I won't. Any Flow clips would be made by you and sent to me as files.

## 2. Flow free tier vs. free three.js, for one full episode

Assume a **60–70 second episode** (hard minimum 60.0 s) of about 35 shots.

| | Google Flow (free) | three.js (free, local) |
|---|---|---|
| Look | Closest to the reference style: detailed 3D-like faces, motion and lighting | Simple toy-like 3D. Clean and consistent, but clearly simpler |
| Clips needed | About 6–9 clips of 5–8 s, plus retries | About 35 shots, rendered by me, one shot at a time |
| Time to finish | **2 days** at the daily limit with zero retries, realistically **3–4 days** | Same day, once the scenes are built |
| Weekly output | About 350 free credits a week, which is roughly 1 episode a week with retries, borderline for 3 | 3 a week is realistic |
| Character consistency | Depends on the reference images. Unverified | Guaranteed: it's the same model every time |
| Resolution | 360p or 720p, so it will look soft on a 1080×1920 canvas | Full 1080×1920 |
| Control | Prompts only. I can't fix a small mistake | Total: I can fix a caption, a pose or a color |
| Lip-sync, vote card, comment card | Not possible inside a clip. I'd overlay them | Built in |
| Who does the work | You: log in, generate daily, download, send me files | Me |
| Rights to monetize | **Unknown** (see above) | **Yours.** All original and generated here |
| Account / card | Needs your Google account, 18+ | None |

**My recommendation: stay on the free three.js route for the series.** It's the only option I can show is free, consistent and fully yours. Flow gives a better look, but I can't confirm monetization rights, it costs you daily effort, and its quality is capped at 720p. I'd treat Flow as an optional experiment for one or two hero shots, only if you read its terms first.

## 3. The series (unchanged from your picks)

- **Series:** *Dex Hollow's 30 Days to Showtime.* **Catchphrase:** "It's fine. It's rock 'n' roll!" **Vote prompt:** "Your call, crew."
- **Cast:** Dex (neon punk, pending your approval), Nana Dot (older relative who forces him to change), Gig the raccoon (van sidekick), Priya (noodle cart owner, always has his order ready), Lena Cho (promoter, appears only as chat messages).
- **Episode 1: "Live and Rolling."** Dex brags on a livestream that he can play through anything while his van, with his only guitar inside, rolls away with Gig at the wheel. Lena joins the stream and the van heads for Nana Dot's flower stand. Vote: **CHASE** or **PLAY**. Full script and shot plan: `episode1_script.md` (awaiting your approval).

From episode 2 on, the first 3 seconds show the winning comment as a card ("You picked BORROW").

**Posting schedule: one episode every day at 2:00 PM Eastern.** You schedule it in TikTok Studio. Daily is realistic only with the buffer and deadlines below.

| Time (Eastern) | What happens |
|---|---|
| Day D, 2:00 PM | Episode D goes live. Vote opens. |
| Day D, **8:00 PM** | **Comment screenshots due** (6 hours of votes). Send the top comments with like counts. |
| Day D, evening | I send the script and shot list for Episode D+1 in the same reply. |
| Day D+1, **by 9:00 AM** | You approve or edit the script. |
| Day D+1, 9:00–11:00 AM | I render, watch it back, fix problems and send the video. |
| Day D+1, **by 12:30 PM** | You approve the video. |
| Day D+1, **by 1:00 PM** | You schedule or upload it in TikTok Studio for 2:00 PM. This leaves a one-hour safety margin. |

I only work when you message me in this session. I can't act between your messages, so the times above are your deadlines to send things, not times I run on my own.

**Length rule: every episode is at least 60 seconds.** I'll target 62–70 s so there is a safety margin, and I'll check the finished file's duration with ffprobe before showing it to you. A 60+ second episode means roughly 35 shots and about 1,800–2,100 frames at 30 fps (spoken words vary with how action-led it is; Episode 1 has about 105). At the measured ~2 s per frame that is **about 60 minutes of rendering**, so I will render shot by shot and re-render only a shot that needs a fix, not the whole episode. If time gets tight, I can render on twos (every other frame, about 30 minutes) or at 24 fps (about 48 minutes).

**How far ahead we need to work:** the toolkit (final Dex, Nana Dot, Gig, Priya, the van and stage sets, caption and vote-card templates, voice and music) must be finished **before Day 1**, plus **3 banked fallback episodes** that don't depend on a vote (for example "Gig's van tour", "Nana Dot's rules"). A vote-dependent episode can only be made about 18 hours ahead, so the bank is what covers a missed deadline. If the screenshots arrive after 10:00 PM, or an approval is late, you post a banked episode and the vote carries over to the next day.

**Honest cost:** about 30–45 minutes a day from you for 30 days (screenshots, two approvals, upload). A 6-hour vote window means small vote counts at first. If daily proves too heavy, the fallback is every other day with a 24-hour vote window.

## 4. Free-only workflow, with manual fallbacks

| Task | Free method | Can I do it fully? | Manual fallback |
|---|---|---|---|
| Characters and scenes | three.js, rendered locally | Yes | None needed |
| Voice | Piper (Kristin, public domain) with pitch and tone tuned per character, or your own voice | Yes for text-to-speech | **Record your own voice** and send me the file |
| Music | An original loop I synthesize with code (zero license risk, but basic). Or free music added by you in the TikTok app at upload | Partly | **Add a track from TikTok's own free music library** when you post. I'd check the current rules for your account type |
| Sound effects | Simple ones I synthesize, or CC0 only from Freesound | Partly | You add a sound in TikTok |
| Captions | whisper.cpp for word timing, rendered by me | Yes | None needed |
| Editing, 1080×1920 export | FFmpeg | Yes | None needed |
| **Reading comments** | **I can't read TikTok comments for free.** The official API needs an approved app, and I won't use your login or cookies | No | **You send screenshots or paste the top comments with like counts.** I read screenshots. This is the vote source |
| **Posting** | **I can't post for you.** TikTok's API needs approval | No | **You upload in TikTok Studio** and can schedule there. I'd check the current scheduling rules for your account type |
| Labeling AI content | n/a | n/a | You apply TikTok's AI-content label if required. Check TikTok's current policy |

## 5. Steps and approval gates

1. **Dex approval (waiting on you).** You can approve him, ask for changes, or ask me to improve the hair and face first.
2. Design Nana Dot, Gig and Priya in the same 3D style. Show stills. Wait for approval.
3. 5-second test with voice (Piper), captions and one vote card. Show it. Wait for approval.
4. Script and shot list for Episode 1. Show it before I render.
5. Render the 1080×1920 episode, watch it back with the video skill, fix problems, show you.
6. You post it, then send me comment screenshots, and I write Episode 2.

Nothing in these steps costs money or needs an account.

## 6. What I need from you

1. Are you 18+ and do you want to try Flow at all? (Not required: the series works without it.)
2. Approve Dex, or tell me what to change.
3. Voice: my text-to-speech, or your own recorded voice?
4. Music: an original loop from me, or you add a track in the TikTok app?

## 7. Blender test result (free Blender 5.3.0, CPU only)

Installed from the official tarball (407 MB download, **1.3 GB unpacked**, checksum verified, in `/home/user/tools/blender`). The still is `design/dex_blender/dex_still_1080x1920.png`; the script is `blender/dex_portrait.py`.

| Measured on this machine (4 CPU cores, no GPU), 1080×1920, one head-and-bust scene | Time |
|---|---|
| Hero still, 96 samples + denoise | **275 s** |
| Animation-quality frame, 32 samples + denoise | **102 s** |
| Fast real-time engine (EEVEE) | **Does not run** (no EGL/Vulkan on this machine) |

| 62–70 s episode at 102 s per frame | Frames | Render time |
|---|---|---|
| 30 fps | 1,860–2,100 | 53–60 hours |
| 24 fps | 1,488–1,680 | 42–48 hours |
| 15 fps (every other frame) | 930–1,050 | 26–30 hours |
| 12 fps | 744–840 | 21–24 hours |

The daily window for rendering is about 2 hours. **Blender animation cannot meet a daily 2 PM schedule on this machine**, even at 12 fps, and a full scene with a van, street and several characters would be slower than this head-and-bust test (my estimate: 1.5–3×; not measured). three.js renders about 2 s per frame, so a 62–70 s episode takes about 1 hour.

## 8. Sprite test result (Dex, 5 s, Blender layers + compositor)

Files: `output/dex_sprite_test_5s.mp4` (1080×1920, 30 fps, 5.0 s, voice), `output/dex_sprite_test_frames.png`, sprites in `sprites/dex/`, scripts `blender/dex_sprites.py`, `sprites/sprite_voice.py`, `sprites/compose_test.py`.

**How it works:** Blender renders Dex once as a full-frame base (head, hair, jacket) and then as small, perfectly aligned transparent face layers: 5 eye states, 4 brow sets, 7 mouth shapes. A compositor stacks the right layers for each frame from the voice (loudness and spectral centroid pick the mouth shape), adds blinks, cross-fades between expressions, and adds a slow push-in and big captions.

| Measured render time (1080×1920, 64 samples, this machine) | Per item | Total in the test |
|---|---|---|
| Base (head, hair, jacket), full frame | **120 s** | 120 s |
| Background plate | 7.5 s | 7.5 s |
| Eye state (5) | 10–12 s | 55 s |
| Brow set (4) | 8.4–8.6 s | 34 s |
| Mouth shape (7) | 8.0–9.6 s | 60 s |
| **Sprite library for the test** | | **276 s (4.6 min)** |
| Compositing + encoding | **0.067 s per frame** (10 s for 150 frames) | 10 s |

Loudness of the test audio: -19.5 LUFS (a final mix should be raised toward about -14).
