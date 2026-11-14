#!/usr/bin/env bash
# Full pipeline for the WARUM DU? animated music video.
# Requirements: ffmpeg/ffprobe, python3 with numpy pycairo opencv-python-headless librosa
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p build output

ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 assets/song.m4a
python3 scripts/analyze_audio.py assets/song.m4a build/analysis.json
python3 scripts/render.py --format h
python3 scripts/render.py --format v
python3 scripts/verify.py output/Warum_Du_Official_Music_Video.mp4 1920x1080
python3 scripts/verify.py output/Warum_Du_Vertical_1080x1920.mp4 1080x1920
