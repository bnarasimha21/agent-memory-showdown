"""Issue 6: a fresh benchmark run against the real services becomes a site page."""

import html
import json
import re

import pytest

from src.backends.registry import AVAILABLE_BACKENDS
from src.bundle import read_transcript
from src.harness import run_benchmark
from src.site import build as site_build
from src.site import publish
from src.site.data import headline_row, load_bundle, published_bundles

pytestmark = pytest.mark.integration


def test_fresh_run_is_published_and_built_into_the_site(services, tmp_path):
    bundle_path = run_benchmark(
        [AVAILABLE_BACKENDS["qdrant"], AVAILABLE_BACKENDS["pgvector"]], num_runs=1, num_turns=10,
        checkpoints=[5, 10], results_dir=tmp_path, run_label="site-it",
        composition={"extraction": 2, "update": 1, "abstention": 1},
    )
    latest = tmp_path / "latest.json"
    assert publish.publish(bundle_path, latest=latest, runs_dir=tmp_path / "runs",
                           regenerate=False) == [bundle_path.name]
    (bundle,) = published_bundles(latest, tmp_path / "runs")
    assert set(bundle.backends) == {"qdrant", "pgvector"}

    index = site_build.build([bundle], tmp_path / "site").read_text()
    run_dir = tmp_path / "site" / "runs" / bundle.run_id
    for label, data in bundle.backends.items():
        r = headline_row(data)
        row = re.search(rf"<tr><td>{label}</td>(.*?)</tr>", index).group(1)
        assert f">{r['headline_n']}</a>" in row
        assert f'href="runs/{bundle.run_id}/probes-{label}.html"' in row

    # A known probe: its question, the backend's actual response and the retrieved
    # context appear on that backend's probe page, with the final label.
    probe = next(r for r in read_transcript(bundle_path)
                 if r.get("type") == "probe" and r["backend"] == "pgvector")
    page = (run_dir / "probes-pgvector.html").read_text()
    assert html.escape(probe["question"]) in page
    assert html.escape(probe["response"]) in page
    assert html.escape(probe["context"].splitlines()[0]) in page
    final = next(p for p in bundle.aggregate["probes"] if p["backend"] == "pgvector"
                 and p["fact_id"] == probe["fact_id"] and p["checkpoint"] == probe["checkpoint"]
                 and p["run_index"] == probe["run_index"])
    assert f'class="lab-{final["label"]}"' in page
    # the copied bundle is the published one (gzipped transcript) and reloads
    assert load_bundle(run_dir).run_id == bundle.run_id
    assert json.loads((run_dir / "manifest.json").read_text())["backends"] == ["qdrant", "pgvector"]
