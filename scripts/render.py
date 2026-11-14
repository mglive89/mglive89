"""Render the WARUM DU? music video.

    python3 scripts/render.py --format h        # 1920x1080 master
    python3 scripts/render.py --format v        # 1080x1920 TikTok/Reels
    python3 scripts/render.py --preview 12.5,60.1 --format h   # PNG stills

Frames are drawn with Cairo, post-processed with OpenCV, piped raw into
FFmpeg (libx264) in parallel chunks, concatenated, then muxed with the
untouched original audio (AAC) with +faststart.
"""
import argparse
import bisect
import json
import os
import subprocess
import sys
import time
from multiprocessing import Process

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mv import scenes  # noqa: E402
from mv.core import FPS, seg, smooth  # noqa: E402
from mv.fx import Post  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIO = os.path.join(ROOT, "assets", "song.m4a")
ANALYSIS = os.path.join(ROOT, "build", "analysis.json")

FORMATS = {"h": (1920, 1080, "Warum_Du_Official_Music_Video.mp4"),
           "v": (1080, 1920, "Warum_Du_Vertical_1080x1920.mp4")}


class Renderer:
    def __init__(self, sw, sh, A):
        self.F = scenes.Frame(sw, sh, A)
        self.post = Post(sw, sh)
        self.S = scenes.timeline(A)
        self.starts = [s["start"] for s in self.S]
        self._luts = {}

    def lut_for(self, g):
        key = (tuple(g.get("tint", (1, 1, 1))), tuple(g.get("lift", (0, 0, 0))), g.get("gamma", 1.0),
               g.get("contrast", 1.0), g.get("exposure", 1.0))
        key = tuple(round(x, 3) if isinstance(x, float) else tuple(round(y, 3) for y in x) for x in key)
        if key not in self._luts:
            self._luts[key] = Post.lut(*key)
            if len(self._luts) > 200:
                self._luts.pop(next(iter(self._luts)))
        return self._luts[key]

    def render_scene(self, sc, t, idx):
        F = self.F
        F.begin(t, idx)
        lt = t - sc["start"]
        d = sc["end"] - sc["start"]
        sc["fn"](F, lt, d, **sc["kw"])
        F.surf.flush()
        w, h = F.sw, F.sh
        arr = np.ndarray((h, F.surf.get_stride() // 4, 4), np.uint8, F.surf.get_data())
        img = np.ascontiguousarray(arr[:, :w, :3])
        g = dict(F.g)
        g["_lut"] = self.lut_for(g)
        return self.post.process(img, g, idx)

    def frame(self, idx):
        t = idx / FPS
        i = max(0, bisect.bisect_right(self.starts, t) - 1)
        sc = self.S[i]
        img = self.render_scene(sc, t, idx)
        tr, xd = sc["tr"], sc["xd"]
        lt = t - sc["start"]
        if i > 0 and xd > 0 and lt < xd:
            k = smooth(seg(lt, 0, xd))
            prev = self.S[i - 1]
            if tr in ("fade", "memory", "whip"):
                a = self.render_scene(prev, t, idx)
                if tr == "whip":
                    kk = int(9 + 140 * np.sin(k * np.pi))
                    a = cv2.blur(a, (kk, 1))
                    img = cv2.blur(img, (kk, 1))
                img = cv2.addWeighted(a, 1 - k, img, k, 0)
                if tr == "memory":
                    w = float(np.sin(k * np.pi)) * 0.55
                    warm = np.full_like(img, (120, 190, 255))
                    img = cv2.addWeighted(img, 1.0, warm, w, 0)
            elif tr == "black":
                if k < 0.5:
                    a = self.render_scene(prev, t, idx)
                    img = cv2.convertScaleAbs(a, alpha=1 - 2 * k)
                else:
                    img = cv2.convertScaleAbs(img, alpha=2 * k - 1)
            elif tr == "white":
                img = cv2.addWeighted(img, 1.0, np.full_like(img, 255), float(1 - k) * 0.9, 0)
        return img


def worker(fmt, a, b, out, A, crf=17):
    sw, sh, _ = FORMATS[fmt]
    R = Renderer(sw, sh, A)
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{sw}x{sh}",
           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", str(crf),
           "-pix_fmt", "yuv420p", "-profile:v", "high", "-threads", "2", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    t0 = time.time()
    for idx in range(a, b):
        img = R.frame(idx)
        p.stdin.write(img.tobytes())
        if (idx - a) % 150 == 0:
            el = time.time() - t0
            print(f"[{fmt} {a}-{b}] frame {idx} ({(idx - a) / max(el, 1e-6):.2f} fps)", flush=True)
    p.stdin.close()
    p.wait()
    if p.returncode != 0:
        raise SystemExit(f"ffmpeg failed for chunk {a}-{b}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--format", default="h", choices=list(FORMATS))
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--preview", default="")
    ap.add_argument("--range", default="", help="seconds a:b (test renders)")
    ap.add_argument("--crf", type=int, default=20)
    args = ap.parse_args()
    with open(ANALYSIS) as f:
        A = json.load(f)
    sw, sh, name = FORMATS[args.format]
    n_frames = int(round(A["duration"] * FPS))

    if args.preview:
        R = Renderer(sw, sh, A)
        os.makedirs(os.path.join(ROOT, "output", "preview"), exist_ok=True)
        for tt in args.preview.split(","):
            idx = int(round(float(tt) * FPS))
            t0 = time.time()
            img = R.frame(idx)
            path = os.path.join(ROOT, "output", "preview", f"{args.format}_{float(tt):07.2f}.jpg")
            cv2.imwrite(path, img, [cv2.IMWRITE_JPEG_QUALITY, 88])
            print(f"{path}  {time.time() - t0:.2f}s")
        return

    a0, a1 = 0, n_frames
    if args.range:
        x, y = args.range.split(":")
        a0, a1 = int(float(x) * FPS), int(float(y) * FPS)
    tmp = os.path.join(ROOT, "build", f"chunks_{args.format}" + ("_test" if args.range else ""))
    os.makedirs(tmp, exist_ok=True)
    nw = max(1, args.workers)
    bounds = [a0 + (a1 - a0) * i // nw for i in range(nw + 1)]
    procs, outs = [], []
    t0 = time.time()
    for i in range(nw):
        out = os.path.join(tmp, f"part_{i:02d}.mp4")
        outs.append(out)
        pr = Process(target=worker, args=(args.format, bounds[i], bounds[i + 1], out, A, args.crf))
        pr.start()
        procs.append(pr)
    for pr in procs:
        pr.join()
        if pr.exitcode != 0:
            raise SystemExit("a render worker failed")
    print(f"rendered {a1 - a0} frames in {time.time() - t0:.0f}s")
    lst = os.path.join(tmp, "list.txt")
    with open(lst, "w") as f:
        for o in outs:
            f.write(f"file '{o}'\n")
    video = os.path.join(tmp, "video.mp4")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy",
                    video], check=True)
    os.makedirs(os.path.join(ROOT, "output"), exist_ok=True)
    final = os.path.join(ROOT, "output", name if not args.range else f"test_{args.format}.mp4")
    cmd = ["ffmpeg", "-y", "-v", "error", "-i", video]
    if args.range:
        cmd += ["-ss", str(a0 / FPS), "-t", str((a1 - a0) / FPS)]
    # the original AAC stream is copied bit-exact: melody, voice and speed untouched
    cmd += ["-i", AUDIO, "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "copy",
            "-movflags", "+faststart", final]
    subprocess.run(cmd, check=True)
    print("wrote", final)


if __name__ == "__main__":
    main()
