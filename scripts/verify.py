"""Automatic delivery checks for the rendered videos.

    python3 scripts/verify.py output/Warum_Du_Official_Music_Video.mp4 1920x1080

Checks: file exists, H.264 + AAC present, resolution / fps / yuv420p,
faststart (moov before mdat), duration equal to the source audio, audio
stream bit-identical to the original (not truncated, not re-encoded), full
decode without errors, no accidental black frames, preview stills.
If the duration or audio check fails it re-muxes the file to fix it.
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIO = os.path.join(ROOT, "assets", "song.m4a")
# intentional dark moments: fade-in from black, end card (text on black)
ALLOWED_BLACK = [(0.0, 1.2)]


def probe(path):
    out = subprocess.check_output(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", path])
    return json.loads(out)


def audio_md5(path):
    out = subprocess.check_output(["ffmpeg", "-v", "error", "-i", path, "-map", "0:a:0", "-c", "copy", "-f", "md5", "-"])
    return out.decode().strip()


def moov_first(path):
    with open(path, "rb") as f:
        data = f.read(1 << 20)
    m, d = data.find(b"moov"), data.find(b"mdat")
    return m != -1 and (d == -1 or m < d)


def black_intervals(path):
    r = subprocess.run(["ffmpeg", "-v", "info", "-i", path, "-vf", "blackdetect=d=0.25:pic_th=0.995:pix_th=0.04",
                        "-an", "-f", "null", "-"], capture_output=True, text=True)
    res = []
    for ln in r.stderr.splitlines():
        if "black_start" in ln:
            parts = dict(p.split(":") for p in ln.split("]")[-1].split() if ":" in p)
            res.append((float(parts["black_start"]), float(parts["black_end"])))
    return res


def main():
    path = sys.argv[1]
    want = sys.argv[2] if len(sys.argv) > 2 else "1920x1080"
    W, H = map(int, want.split("x"))
    errors, notes = [], []
    if not os.path.exists(path) or os.path.getsize(path) < 1_000_000:
        print("FAIL: file missing or too small")
        sys.exit(1)
    info = probe(path)
    src = probe(AUDIO)
    src_dur = float(src["format"]["duration"])
    v = [s for s in info["streams"] if s["codec_type"] == "video"]
    a = [s for s in info["streams"] if s["codec_type"] == "audio"]
    if not v:
        errors.append("no video stream")
    if not a:
        errors.append("no audio stream")
    if v:
        v = v[0]
        if v["codec_name"] != "h264":
            errors.append(f"video codec {v['codec_name']}")
        if (v["width"], v["height"]) != (W, H):
            errors.append(f"resolution {v['width']}x{v['height']}")
        if v["pix_fmt"] != "yuv420p":
            errors.append(f"pix_fmt {v['pix_fmt']}")
        if v["r_frame_rate"] != "30/1":
            errors.append(f"fps {v['r_frame_rate']}")
        notes.append(f"video: h264 {v['width']}x{v['height']} {v['r_frame_rate']} {v['pix_fmt']} "
                     f"{float(v['duration']):.3f}s, {v.get('nb_frames')} frames, profile {v.get('profile')}")
        if abs(float(v["duration"]) - src_dur) > 0.05:
            errors.append(f"video duration {float(v['duration']):.3f} != audio {src_dur:.3f}")
    if a:
        a = a[0]
        if a["codec_name"] != "aac":
            errors.append(f"audio codec {a['codec_name']}")
        adur = float(a["duration"])
        notes.append(f"audio: aac {a['sample_rate']} Hz {a['channels']} ch, {adur:.3f}s (source {src_dur:.3f}s)")
        if abs(adur - src_dur) > 0.03:
            errors.append(f"audio truncated: {adur:.3f} vs {src_dur:.3f}")
        if audio_md5(path) != audio_md5(AUDIO):
            errors.append("audio stream differs from the original")
        else:
            notes.append("audio stream is bit-identical to assets/song.m4a")
    fdur = float(info["format"]["duration"])
    notes.append(f"container duration {fdur:.3f}s")
    if not moov_first(path):
        errors.append("moov atom not at start (faststart missing)")
    else:
        notes.append("faststart: moov before mdat")
    dec = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "null", "-"], capture_output=True, text=True)
    if dec.stderr.strip():
        errors.append("decode errors: " + dec.stderr.strip()[:300])
    else:
        notes.append("full decode: no errors")
    # the outro fades to black ~1 s before the end card (intentional "Schermo nero")
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from mv import scenes
    with open(os.path.join(ROOT, "build", "analysis.json")) as f:
        tl = scenes.timeline(json.load(f))
    end_card = [s_["start"] for s_ in tl if s_["fn"] is scenes.s_end][0] - 1.1
    notes.append(f"end card starts at {end_card + 1.1:.2f}s")
    bl = black_intervals(path)
    bad = [(s, e) for s, e in bl
           if not any(s >= a0 - 0.05 and e <= a1 + 0.05 for a0, a1 in ALLOWED_BLACK + [(end_card, src_dur + 1)])]
    notes.append(f"black intervals: {[(round(s, 2), round(e, 2)) for s, e in bl]} (allowed: intro fade, end card)")
    if bad:
        errors.append(f"accidental black frames at {bad}")

    # previews
    pdir = os.path.join(ROOT, "output", "previews")
    os.makedirs(pdir, exist_ok=True)
    tag = "v" if H > W else "h"
    for ts in (4, 12, 22, 27, 31, 42, 48, 53, 61, 66, 70, 78, 87, 100, 106, 112, 118, 125, 138, 145, 153, 172, 185, 195):
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(ts), "-i", path, "-frames:v", "1", "-q:v", "3",
                        os.path.join(pdir, f"{tag}_{ts:03d}s.jpg")], check=True)
    notes.append(f"preview stills written to {pdir}")

    for n in notes:
        print("  ok  ", n)
    for e in errors:
        print("  FAIL", e)

    if errors and any("duration" in e or "audio" in e or "faststart" in e for e in errors):
        print("auto-fix: re-muxing with the original audio and +faststart")
        tmp = path + ".fix.mp4"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", path, "-i", AUDIO, "-map", "0:v:0", "-map", "1:a:0",
                        "-c", "copy", "-t", f"{src_dur:.3f}", "-movflags", "+faststart", tmp], check=True)
        os.replace(tmp, path)
        print("re-run verify after fix")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
