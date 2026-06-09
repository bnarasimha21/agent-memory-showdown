#!/usr/bin/env python3
"""Resolve narration anchor phrases to Remotion frame numbers.

Reads a whisper word-level JSON (produced by prep_scene_audio.sh, -ml 1) and,
for each anchor phrase passed on the command line, finds where it starts in the
narration and prints the frame number (start_ms/1000 * fps).

Usage:
  scripts/sync_cues.py /tmp/scene04.json "buffer" "90%" "the only failures"
  scripts/sync_cues.py /tmp/scene04.json --json anchors.json   # {cue: phrase}

An anchor may be suffixed with #N to pick the N-th occurrence (1-based),
e.g. "summary#2".
"""
import json
import re
import sys

FPS = 30


def norm(s: str):
    """Lowercase, keep alphanumerics and %, collapse to word list."""
    s = s.lower().replace("%", " percent ")
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return s.split()


def load_words(path):
    d = json.load(open(path))
    words = []  # (normalized_token, start_ms)
    for seg in d["transcription"]:
        txt = seg.get("text", "").strip()
        if not txt:
            continue
        start_ms = seg["offsets"]["from"]
        for w in norm(txt):
            words.append((w, start_ms))
    return words


def find(words, phrase, occurrence=1):
    target = norm(phrase)
    if not target:
        return None
    hits = []
    n = len(target)
    for i in range(len(words) - n + 1):
        if [w for w, _ in words[i:i + n]] == target:
            hits.append(words[i][1])
    if len(hits) >= occurrence:
        return hits[occurrence - 1]
    return None


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)
    path = args[0]
    words = load_words(path)

    if len(args) >= 3 and args[1] == "--json":
        anchors = json.load(open(args[2]))
        items = list(anchors.items())
    else:
        items = []
        for a in args[1:]:
            if "=" in a:
                name, phrase = a.split("=", 1)
            else:
                name = phrase = a
            items.append((name, phrase))

    for name, phrase in items:
        occ = 1
        m = re.search(r"#(\d+)$", phrase)
        if m:
            occ = int(m.group(1))
            phrase = phrase[: m.start()]
        ms = find(words, phrase, occ)
        if ms is None:
            print(f"{name}: NOT FOUND  ({phrase!r})")
        else:
            frame = round(ms / 1000 * FPS)
            print(f"{name}: {frame}  // {ms/1000:.2f}s  {phrase!r}")


if __name__ == "__main__":
    main()
