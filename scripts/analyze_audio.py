"""Audio analysis for 'Warum du?' — beats, energy curve, structural segments.

Writes build/analysis.json, which the renderer uses to place scene cuts on
real musical boundaries and to drive beat-reactive effects.
"""
import json
import subprocess
import sys

import librosa
import numpy as np

SRC = sys.argv[1] if len(sys.argv) > 1 else "assets/song.m4a"
OUT = sys.argv[2] if len(sys.argv) > 2 else "build/analysis.json"


def ffprobe_duration(path):
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", path])
    return float(out.strip())


def main():
    duration = ffprobe_duration(SRC)
    # librosa can't always read m4a directly; decode with ffmpeg to wav first
    wav = "build/song.wav"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", SRC, "-ac", "1",
                    "-ar", "22050", wav], check=True)
    y, sr = librosa.load(wav, sr=22050, mono=True)
    hop = 512

    tempo, beats = librosa.beat.beat_track(y=y, sr=sr, hop_length=hop)
    beat_times = librosa.frames_to_time(beats, sr=sr, hop_length=hop)
    onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop)
    onsets = librosa.onset.onset_detect(onset_envelope=onset_env, sr=sr,
                                        hop_length=hop, units="time")

    rms = librosa.feature.rms(y=y, hop_length=hop)[0]
    times = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop)

    # Vocal-band energy (roughly 300 Hz - 3.4 kHz) vs total, via harmonic part
    S = np.abs(librosa.stft(y, hop_length=hop))
    freqs = librosa.fft_frequencies(sr=sr)
    vb = (freqs > 300) & (freqs < 3400)
    vocal = S[vb].mean(axis=0)
    low = S[freqs < 150].mean(axis=0)

    # Per-30fps energy curves (normalised) for the renderer
    fps = 30
    n = int(round(duration * fps))
    t30 = np.arange(n) / fps

    def resample(curve):
        c = np.interp(t30, times[:len(curve)], curve)
        c = c - np.percentile(c, 2)
        return np.clip(c / max(np.percentile(c, 98), 1e-9), 0, 1)

    energy = resample(rms)
    smooth = np.convolve(energy, np.ones(45) / 45, mode="same")
    onset30 = resample(onset_env)
    vocal30 = resample(vocal)
    bass30 = resample(low)

    # Structural segmentation: agglomerative clustering over beat-synced features
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=hop)
    mfcc = librosa.feature.mfcc(y=y, sr=sr, hop_length=hop, n_mfcc=13)
    feat = np.vstack([librosa.util.normalize(chroma, axis=1),
                      librosa.util.normalize(mfcc, axis=1)])
    feat_sync = librosa.util.sync(feat, beats, aggregate=np.median)
    k = 12
    bounds = librosa.segment.agglomerative(feat_sync, k)
    bound_beats = [beats[min(b, len(beats) - 1)] for b in bounds]
    seg_times = sorted(set(float(t) for t in librosa.frames_to_time(
        bound_beats, sr=sr, hop_length=hop)))

    # Energy per segment, to label quiet/loud sections
    edges = seg_times + [duration]
    segments = []
    for a, b in zip(edges[:-1], edges[1:]):
        m = (t30 >= a) & (t30 < b)
        segments.append({"start": round(a, 3), "end": round(b, 3),
                         "energy": round(float(energy[m].mean()) if m.any() else 0, 3),
                         "vocal": round(float(vocal30[m].mean()) if m.any() else 0, 3)})

    # First / last audible moments (detect silence at head and tail)
    thr = 0.02 * rms.max()
    audible = np.where(rms > thr)[0]
    first_sound = float(times[audible[0]]) if len(audible) else 0.0
    last_sound = float(times[audible[-1]]) if len(audible) else duration

    data = {
        "duration": duration,
        "fps": fps,
        "frames": n,
        "tempo": float(np.atleast_1d(tempo)[0]),
        "beats": [round(float(b), 3) for b in beat_times],
        "onsets": [round(float(o), 3) for o in onsets],
        "segments": segments,
        "first_sound": first_sound,
        "last_sound": last_sound,
        "energy": [round(float(v), 3) for v in energy],
        "energy_smooth": [round(float(v), 3) for v in smooth],
        "onset": [round(float(v), 3) for v in onset30],
        "vocal": [round(float(v), 3) for v in vocal30],
        "bass": [round(float(v), 3) for v in bass30],
    }
    with open(OUT, "w") as f:
        json.dump(data, f)

    print(f"duration={duration:.3f}s tempo={data['tempo']:.1f} beats={len(beat_times)}")
    print(f"first_sound={first_sound:.2f} last_sound={last_sound:.2f}")
    for s in segments:
        bar = "#" * int(s["energy"] * 40)
        print(f"{s['start']:7.2f}-{s['end']:7.2f}  E={s['energy']:.2f} V={s['vocal']:.2f} {bar}")
    # Coarse energy profile every 4s
    print("energy profile (4s windows):")
    for i in range(0, n, fps * 4):
        e = float(np.mean(energy[i:i + fps * 4]))
        print(f"{i / fps:6.1f}s {'#' * int(e * 50)}")


if __name__ == "__main__":
    main()
