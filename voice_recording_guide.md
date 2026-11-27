# Backup plan: you record Dex's lines yourself

## Recording (phone is fine)
1. **Place:** a small, soft room (closet with clothes, or a bed with a duvet over you). Turn off fans, AC and fridge noise. Phone in airplane mode.
2. **Mic:** phone voice-memo app, held about a fist-and-a-half (15 cm) from your mouth, slightly to the side so "p" and "b" don't pop. Record in WAV or the highest quality available.
3. **Do a 10-second silence take first** (room tone). I use it to remove noise.
4. **Do 3 takes of every line**, standing up, with big energy. Cocky means slight smile, chin up, and a bit more pitch swing than feels normal. Leave 1 second of silence before and after each take.
5. **Clap once** at the start of each take (helps me find the start).
6. **Send the files** in line order, named like `dex_01_take1.wav`. Do not add effects or auto-tune.

## Cleanup (free tools I already have)
- Pick the best take per line, trim to the breath before the line.
- FFmpeg: high-pass at about 80 Hz, `afftdn` noise reduction trained on the room-tone take, gentle de-ess, light compressor (about 3:1), then `loudnorm` to the series target of -14 LUFS.
- Pitch/speed changes only if you want them; I will not touch your timbre by default.
- Music is ducked 8–10 dB while he speaks.

## Mouth sync
- Run whisper.cpp (already installed) on each take to get word timings.
- Rhubarb Lip Sync (MIT, needs your OK to download) gives mouth shapes A–H and X (rest) per 1/24 s.
- Map those shapes to Dex's mouth variants, add a short smoothing so the mouth doesn't flicker, and open the jaw a bit more on emphasised words.
- Without Rhubarb I would drive the mouth from the loudness envelope plus whisper's word timings. It is simpler and less exact.
