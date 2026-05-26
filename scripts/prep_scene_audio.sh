#!/usr/bin/env bash
# Prep a scene audio file: AIFC → WAV (Remotion delivery) + 16kHz mono WAV
# (whisper input) + word-level whisper JSON.
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

echo ">> converting $SRC"
ffmpeg -y -hide_banner -loglevel error -i "$SRC" -ar 48000 -ac 1 -c:a pcm_s16le "$DELIVERY"
ffmpeg -y -hide_banner -loglevel error -i "$SRC" -ar 16000 -ac 1 -c:a pcm_s16le "$WHISPER_WAV"

echo ">> transcribing with whisper (word-level)"
whisper-cli -m "$MODEL" -f "$WHISPER_WAV" -ml 1 -oj -of "$WHISPER_JSON_PREFIX" > /dev/null

DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$DELIVERY")
FRAMES=$(python3 -c "import math; print(math.ceil(float('$DUR') * 30))")

echo ""
echo "ready:"
echo "  audio:    $DELIVERY"
echo "  whisper:  ${WHISPER_JSON_PREFIX}.json"
echo "  duration: ${DUR}s  →  ${FRAMES} frames @ 30fps"
