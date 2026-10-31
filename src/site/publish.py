"""Prepare a finished run bundle for committing and point results/latest.json at it.

    python -m src.site.publish results/runs/<run_id>          # make it the published run
    python -m src.site.publish results/runs/<run_id> --add    # publish next to the current ones

The transcript is gzipped (`transcript.jsonl.gz`, reproducible: no timestamp
or file name in the header) after checking that it decompresses to the same
records; every reader accepts either form. Charts are not part of a published
bundle (they are rebuilt by `make site`). Finally the README results block and
`remotion/src/data/benchmarkData.ts` are regenerated.
"""

from __future__ import annotations

import argparse
import gzip
import io
import json
import sys
from pathlib import Path

from src.bundle import TRANSCRIPT, TRANSCRIPT_GZ, read_transcript
from src.site import export
from src.site.data import LATEST, RUNS_DIR, load_bundle


def gzip_transcript(bundle: Path) -> Path:
    """Replace transcript.jsonl with a byte-for-byte equivalent transcript.jsonl.gz."""
    plain, packed = bundle / TRANSCRIPT, bundle / TRANSCRIPT_GZ
    if not plain.exists():
        if packed.exists():
            return packed
        raise FileNotFoundError(f"{bundle} has no {TRANSCRIPT}")
    raw = plain.read_bytes()
    buf = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=buf, mtime=0, compresslevel=9) as gz:
        gz.write(raw)
    if gzip.decompress(buf.getvalue()) != raw:
        raise RuntimeError(f"gzip round trip of {plain} failed")
    before = read_transcript(bundle)
    packed.write_bytes(buf.getvalue())
    plain.unlink()
    if read_transcript(bundle) != before:  # pragma: no cover (guarded by the byte check)
        raise RuntimeError(f"{packed} does not read back as the original transcript")
    return packed


def publish(bundle: str | Path, add: bool = False, latest: Path = LATEST,
            runs_dir: Path = RUNS_DIR, regenerate: bool = True) -> list[str]:
    bundle = Path(bundle).resolve()
    if bundle.parent != runs_dir.resolve():
        raise ValueError(f"{bundle} is not directly under {runs_dir}; only bundles there are published")
    loaded = load_bundle(bundle)  # fails early on an unfinished bundle
    if loaded.run_id != bundle.name:
        raise ValueError(f"manifest run_id {loaded.run_id!r} does not match directory {bundle.name!r}")
    gzip_transcript(bundle)
    runs = [loaded.run_id]
    if add and latest.exists():
        current = json.loads(latest.read_text(encoding="utf-8")).get("runs", [])
        runs = [r for r in current if r != loaded.run_id] + runs
    latest.write_text(json.dumps({"runs": runs}, indent=2) + "\n", encoding="utf-8")
    if regenerate:
        export.write_all(latest, runs_dir)
    return runs


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("bundle", help="results/runs/<run_id>")
    parser.add_argument("--add", action="store_true",
                        help="keep the current published runs and add this one after them")
    args = parser.parse_args(argv)
    runs = publish(args.bundle, add=args.add)
    print(f"published: {', '.join(runs)} (results/latest.json); README and benchmarkData.ts regenerated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
