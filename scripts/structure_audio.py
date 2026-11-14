"""Find repeated sections (choruses) via chroma self-similarity on a 1s grid."""
import librosa
import numpy as np

y, sr = librosa.load("build/song.wav", sr=22050)
hop = 512
ch = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=hop)
fps = sr / hop
n = int(len(y) / sr)


def grid(F):
    return np.stack([F[:, int(i * fps):int((i + 1) * fps)].mean(axis=1)
                     for i in range(n)], 1)


C = librosa.util.normalize(grid(ch), axis=0)
# For each second, find the best-matching 8 s window elsewhere in the song
W = 8
X = np.stack([C[:, i:i + W].flatten() for i in range(n - W)], 1)
X = X / np.linalg.norm(X, axis=0, keepdims=True)
S = X.T @ X
for i in range(len(S)):
    S[i, max(0, i - 10):i + 10] = 0
best = S.argmax(1)
val = S.max(1)
for t in range(0, n - W, 2):
    print(f"{t:4d}s ->{best[t]:4d}s {val[t]:.2f}")
