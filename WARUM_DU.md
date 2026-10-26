# WARUM DU? – Animated Music Video

An animated narrative music video for **“Warum du?” – Marco Gallo**, rendered entirely from code.

| File | Format |
|---|---|
| `output/Warum_Du_Official_Music_Video.mp4` | 1920×1080, 16:9, 30 fps, H.264 High, yuv420p, AAC (original stream), faststart |
| `output/Warum_Du_Vertical_1080x1920.mp4` | 1080×1920 TikTok/Reels, each shot re-framed natively (not cropped) |

The audio is the untouched original AAC stream from `assets/song.m4a` (stream-copied, bit-identical:
no re-encode, no change to pitch, voice or tempo). The video length equals the audio length (196.399 s).

## Pipeline

```
./make_video.sh
```

1. `scripts/analyze_audio.py` – FFprobe duration; librosa beat tracking (123 BPM), RMS / vocal / bass
   energy curves, beat-synchronous structural segmentation → `build/analysis.json`.
2. `scripts/structure_audio.py` – chroma self-similarity to find repeated sections (chorus 1 ≈ 59.7 s
   repeats at ≈ 152.0 s).
3. `scripts/render.py` – renders every frame with Cairo (vector), post-processes with OpenCV
   (depth-of-field blur, bloom, colour LUT, vignette, grain, chromatic aberration, flashes),
   pipes raw frames to FFmpeg/libx264 in 4 parallel chunks, concatenates, muxes the audio.
4. `scripts/verify.py` – automated delivery checks (streams, codec, resolution, fps, pix_fmt,
   faststart, duration vs audio, audio bit-identity, full decode, black-frame detection,
   preview stills in `output/previews/`); re-muxes automatically if duration/audio/faststart fail.

## Song structure (from the analysis) → story

| Time | Section | Scenes |
|---|---|---|
| 0:00–0:07.9 | Intro | Camera flies through the sleepless neon city (pseudo-3D street corridor) |
| 0:07.9–0:44.4 | Verse 1 | Walking alone · phone: “Keine neuen Nachrichten” · MEMORY: she arrives on her skateboard · eyes meet, smiles · walking together in golden light · present: same street, cold & blue, her ghost fades · MEMORY: happy evening under string lights |
| 0:44.4–0:59.7 | Pre-hook | She appears, time stops (rain freezes, bokeh) · camera orbits the two · he reaches, she dissolves into light |
| 0:59.7–1:37.0 | Chorus 1 | **WARUM DU?** title hit · eye close-up behind the glasses · her smile (slow) · alone in his room · chat: delivered, no answer · slow-motion rain on the window · separated by a lit street · beat-cut montage |
| 1:37.0–2:08.5 | Verse 2 | 02:30 clock · checking the phone again and again · she’s “online”, “schreibt …”, then stops · he leaves the house into heavy rain · friends in the distance · crossing the city |
| 2:08.5–2:32.0 | Break + Pre-hook 2 | He stops, rain slows · runs towards her while night turns into warm light · hands almost touch · white flash, the memory breaks |
| 2:32.0–3:00.1 | Final chorus | **WARUM DU?** · fast emotional montage · she skates away into the distance, he stays · close-up, tears |
| 3:00.1–3:16.4 | Outro | Rain stops, dawn · bench, last look at the phone: nothing · camera pulls back · black screen: **WARUM DU?** |

All cuts are snapped to detected beats; transitions are cut / crossfade / whip-pan / dip-to-black /
white flash / warm “memory” flash.

## Characters

`scripts/mv/chars.py` contains two cut-out rigs with separate legs, pelvis, torso, arms, hands, neck,
head, ears, eyes (pupils, highlights, lids, blinks, tears), glasses, brows, nose, mouth, hair and cap,
driven by joint angles: walk / run / sit / skate cycles, turning (front ↔ profile), phone holding,
reaching, breathing, wind in hair, expressions (smile, sad, laugh, blush), lighting tint per scene.

- **Boy**: messy chestnut/red-brown hair, big round glasses, blue hoodie under a turquoise jacket,
  dark jeans, white sneakers.
- **Girl**: long orange-red hair, blue cap, dark jacket over a light top, jeans, sneakers,
  green skateboard with yellow wheels.

> Note: no `characters.jpg` reference image was provided with the request (only the audio file), so
> the two characters were designed from the written description. No lyrics file was provided either,
> so sync is driven by the audio analysis only.
