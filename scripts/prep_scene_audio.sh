#!/usr/bin/env bash
# Prep a scene audio file: AIFC → cleaned WAV (Remotion delivery) + 16kHz mono
# WAV (whisper input) + word-level whisper JSON.
#
# Cleanup baked into the conversion:
#   - highpass 80Hz   : removes low-end rumble / desk thumps
#   - afftdn          : light broadband noise reduction (hiss, room tone)
#   - loudnorm -16LUFS: consistent broadcast loudness across all scenes
#   - silenceremove   : trims leading (keeps 0.12s) + trailing (keeps 0.30s) silence
# The 16kHz whisper input is derived from the *cleaned + trimmed* delivery WAV,
# so the word timings (and the animation cues built from them) match exactly
# what ships in the video — no manual cue-shifting needed.
#
# Usage: scripts/prep_scene_audio.sh 02
# Expects:  remotion/public/audio/Scene02.aifc  (case-insensitive)
# Produces: remotion/public/audio/scene02.wav
#           /tmp/scene02_16k.wav
#           /tmp/scene02.json

set -euo pipefail

if [ $# -ne 1 ]; then
  echo "usage: $0 <scene-number>   (e.g. 02)"
  exit 1
fi

NUM="$1"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
AUDIO_DIR="$REPO/remotion/public/audio"

# Find the source file (case-insensitive match for Scene${NUM}.aifc)
SRC="$(find "$AUDIO_DIR" -maxdepth 1 -iname "scene${NUM}.aifc" | head -1)"
if [ -z "$SRC" ]; then
  echo "no scene${NUM}.aifc found in $AUDIO_DIR" >&2
  exit 1
fi

DELIVERY="$AUDIO_DIR/scene${NUM}.wav"
WHISPER_WAV="/tmp/scene${NUM}_16k.wav"
WHISPER_JSON_PREFIX="/tmp/scene${NUM}"
MODEL="$HOME/.cache/whisper-models/ggml-base.en.bin"

# Audio cleanup + silence-trim chain (echo/noise control, consistent loudness,
# and leading/trailing silence trimmed so each scene starts and ends tight).
# Trim: silenceremove keeps 0.12s of head silence; the areverse pair does the
# same for the tail (keeping 0.30s). start_periods=1 = only the edge silence,
# internal pauses are preserved.
CLEAN_FILTERS="highpass=f=80,afftdn=nf=-30,loudnorm=I=-16:TP=-1.5:LRA=11,silenceremove=start_periods=1:start_silence=0.12:start_threshold=-45dB,areverse,silenceremove=start_periods=1:start_silence=0.30:start_threshold=-45dB,areverse"

echo ">> converting + cleaning $SRC"
ffmpeg -y -hide_banner -loglevel error -i "$SRC" -af "$CLEAN_FILTERS" -ar 48000 -ac 1 -c:a pcm_s16le "$DELIVERY"
# whisper input is derived from the cleaned delivery so timings match the video
ffmpeg -y -hide_banner -loglevel error -i "$DELIVERY" -ar 16000 -ac 1 -c:a pcm_s16le "$WHISPER_WAV"

echo ">> transcribing with whisper (word-level)"
whisper-cli -m "$MODEL" -f "$WHISPER_WAV" -ml 1 -oj -of "$WHISPER_JSON_PREFIX" > /dev/null

DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$DELIVERY")
FRAMES=$(python3 -c "import math; print(math.ceil(float('$DUR') * 30))")

echo ""
echo "ready:"
echo "  audio:    $DELIVERY"
echo "  whisper:  ${WHISPER_JSON_PREFIX}.json"
echo "  duration: ${DUR}s  →  ${FRAMES} frames @ 30fps"
