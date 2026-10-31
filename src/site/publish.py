"""Prepare a finished run bundle for committing and point results/latest.json at it.

    python -m src.site.publish results/runs/<run_id>          # make it the published run
    python -m src.site.publish results/runs/<run_id> --add    # add it as the headline, keep the others

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

from src.bundle import TRANSCRIPT, TRANSCRIPT_GZ, read_transcript, validate_run_id
from src.site import export
from src.site.data import LATEST, RUNS_DIR, Bundle, load_bundle, read_latest


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


def plan_runs(new: Bundle, add: bool, latest: Path, runs_dir: Path) -> tuple[list[str], list[str]]:
    """The run ids latest.json will hold (headline first) and warnings for the user.

    The new run becomes the headline, except that a sample never pushes a real
    run out of first place: it is then listed after the real runs.
    """
    warnings: list[str] = []
    current: list[str] = []
    if latest.exists():
        current = read_latest(latest)
    kept = []
    for run_id in dict.fromkeys(current):  # drops duplicates, keeps the order
        if run_id == new.run_id:
            continue
        try:
            validate_run_id(run_id)
        except ValueError:
            warnings.append(f"dropped invalid run id {run_id!r} from {latest.name}")
            continue
        if not (runs_dir / run_id / "aggregate.json").exists():
            warnings.append(f"dropped {run_id} from {latest.name}: no finished bundle in {runs_dir}")
            continue
        kept.append(run_id)
    real = [r for r in kept if not load_bundle(runs_dir / r).is_sample]
    if not add:
        if new.is_sample and real:
            warnings.append(f"publishing sample {new.run_id} alone replaces the real run(s) "
                            f"{', '.join(real)}; use --add to keep them")
        return [new.run_id], warnings
    if new.is_sample and real:
        warnings.append(f"{new.run_id} is a sample, so it is listed after the real run(s) and "
                        f"{real[0]} stays the headline")
        return kept + [new.run_id], warnings
    return [new.run_id] + kept, warnings


def publish(bundle: str | Path, add: bool = False, latest: Path = LATEST,
            runs_dir: Path = RUNS_DIR, regenerate: bool = True) -> list[str]:
    """Validate and render everything first; only then gzip and write files."""
    bundle = Path(bundle).resolve()
    if bundle.parent != runs_dir.resolve():
        raise ValueError(f"{bundle} is not directly under {runs_dir}; only bundles there are published")
    loaded = load_bundle(bundle)  # fails early on an unfinished bundle
    validate_run_id(loaded.run_id)
    if loaded.run_id != bundle.name:
        raise ValueError(f"manifest run_id {loaded.run_id!r} does not match directory {bundle.name!r}")
    runs, warnings = plan_runs(loaded, add, latest, runs_dir)
    bundles = [loaded if r == loaded.run_id else load_bundle(runs_dir / r) for r in runs]
    generated = export.outputs_for(bundles) if regenerate else {}
    for w in warnings:
        print(f"warning: {w}", file=sys.stderr)
    gzip_transcript(bundle)
    latest.write_text(json.dumps({"runs": runs}, indent=2) + "\n", encoding="utf-8")
    export.write_outputs(generated)
    return runs


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("bundle", help="results/runs/<run_id>")
    parser.add_argument("--add", action="store_true",
                        help="keep the current published runs; this one becomes the headline "
                             "unless it is a sample and a real run is published")
    args = parser.parse_args(argv)
    runs = publish(args.bundle, add=args.add)
    print(f"published: {', '.join(runs)} (results/latest.json); README and benchmarkData.ts regenerated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
