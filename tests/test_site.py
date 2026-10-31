"""Issue 6: publishing bundles, the generated README block and benchmarkData.ts, and the site.

These run offline: the bundle is a real fake-LLM run of the two backends that
need no services (buffer, summary), and the site build runs with sockets
disabled.
"""

from __future__ import annotations

import gzip
import json
import re
import shutil
import socket
import subprocess
from pathlib import Path

import pytest

from src.backends.registry import AVAILABLE_BACKENDS
from src.bundle import TRANSCRIPT, TRANSCRIPT_GZ, read_transcript, transcript_path
from src.harness import run_benchmark
from src.site import build as site_build
from src.site import export, publish
from src.site.data import (
    LEGACY_V1, headline_row, load_bundle, load_legacy, published_bundles, read_latest,
)

NODE = shutil.which("node")


@pytest.fixture(scope="module")
def made_bundle(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("results")
    return run_benchmark(
        [AVAILABLE_BACKENDS["buffer"], AVAILABLE_BACKENDS["summary"]], num_runs=2, num_turns=10,
        checkpoints=[5, 10], results_dir=out, run_label="site-test",
        composition={"extraction": 2, "update": 1, "abstention": 1, "sensitive": 1},
    )


@pytest.fixture
def runs(tmp_path, made_bundle):
    """A results/ layout in tmp: runs/<id> (a copy of the bundle) and latest.json."""
    runs_dir = tmp_path / "runs"
    shutil.copytree(made_bundle, runs_dir / made_bundle.name)
    return runs_dir, tmp_path / "latest.json", runs_dir / made_bundle.name


@pytest.fixture
def no_network(monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("the site build tried to use the network")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)


# ------------------------------------------------------------------ publishing


def test_gzip_transcript_round_trips_and_is_reproducible(runs):
    _, _, bundle = runs
    before = read_transcript(bundle)
    raw = (bundle / TRANSCRIPT).read_bytes()
    packed = publish.gzip_transcript(bundle)
    assert packed == bundle / TRANSCRIPT_GZ and not (bundle / TRANSCRIPT).exists()
    assert gzip.decompress(packed.read_bytes()) == raw
    assert read_transcript(bundle) == before
    assert transcript_path(bundle) == packed
    first = packed.read_bytes()
    (bundle / TRANSCRIPT).write_bytes(raw)
    packed.unlink()
    assert publish.gzip_transcript(bundle).read_bytes() == first  # no timestamp in the header
    assert publish.gzip_transcript(bundle) == packed  # already packed: a no-op
    packed.unlink()
    with pytest.raises(FileNotFoundError):
        transcript_path(bundle)


def test_publish_sets_latest_and_add_appends(runs, made_bundle):
    runs_dir, latest, bundle = runs
    assert publish.publish(bundle, latest=latest, runs_dir=runs_dir, regenerate=False) == [bundle.name]
    assert json.loads(latest.read_text()) == {"runs": [bundle.name]}
    assert (bundle / TRANSCRIPT_GZ).exists()

    other = runs_dir / "20990101T000000000000Z-other"
    shutil.copytree(made_bundle, other)
    manifest = json.loads((other / "manifest.json").read_text())
    manifest["run_id"] = other.name
    (other / "manifest.json").write_text(json.dumps(manifest))
    assert publish.publish(other, add=True, latest=latest, runs_dir=runs_dir,
                           regenerate=False) == [bundle.name, other.name]
    assert [b.run_id for b in published_bundles(latest, runs_dir)] == [bundle.name, other.name]
    # republishing without --add makes it the only (headline) run
    assert publish.publish(other, latest=latest, runs_dir=runs_dir, regenerate=False) == [other.name]


def test_publish_refuses_bundles_it_cannot_link(runs, tmp_path, made_bundle):
    runs_dir, latest, bundle = runs
    with pytest.raises(ValueError, match="not directly under"):
        publish.publish(made_bundle, latest=latest, runs_dir=runs_dir, regenerate=False)
    renamed = runs_dir / "renamed"
    shutil.copytree(made_bundle, renamed)
    with pytest.raises(ValueError, match="does not match"):
        publish.publish(renamed, latest=latest, runs_dir=runs_dir, regenerate=False)
    unfinished = runs_dir / "unfinished"
    unfinished.mkdir()
    (unfinished / "manifest.json").write_text("{}")
    with pytest.raises(FileNotFoundError):
        publish.publish(unfinished, latest=latest, runs_dir=runs_dir, regenerate=False)
    assert not latest.exists()


def test_latest_json_is_validated(tmp_path):
    latest = tmp_path / "latest.json"
    with pytest.raises(FileNotFoundError):
        read_latest(latest)
    for bad in ({"runs": []}, {"runs": [""]}, {}):
        latest.write_text(json.dumps(bad))
        with pytest.raises(ValueError):
            read_latest(latest)
    latest.write_text(json.dumps({"runs": ["../escape"]}))
    with pytest.raises(ValueError, match="invalid run id"):
        published_bundles(latest, tmp_path)


# ------------------------------------------------------- README and TS export


def test_readme_block_carries_every_backend_with_intervals(runs):
    _, _, bundle_path = runs
    bundle = load_bundle(bundle_path)
    legacy = load_legacy()
    block = export.readme_block([bundle], legacy)
    assert "Sample run, not a benchmark result" in block
    for label, data in bundle.backends.items():
        r = headline_row(data)
        row = next(line for line in block.splitlines() if line.startswith(f"| {label} |"))
        assert export.pct(r["recall"]) in row and export.ci(r["recall_ci"]) in row
        assert f"| {r['headline_n']} |" in row
    # v1 numbers come from the legacy file, labelled as v1
    assert "v1 methodology" in block
    for b in legacy["constants"]["BACKENDS"]:
        assert f"{legacy['constants']['RECALL_AT_TURN_50'][b]}%" in block


def test_render_readme_replaces_only_the_block_and_detects_drift(tmp_path):
    text = f"intro\n{export.BEGIN}\nold\n{export.END}\noutro\n"
    once = export.render_readme(text, "NEW")
    assert once.startswith("intro\n") and once.endswith("outro\n") and "old" not in once
    assert export.render_readme(once, "NEW") == once
    with pytest.raises(ValueError):
        export.render_readme("no markers here", "NEW")
    path = tmp_path / "README.md"
    path.write_text(once)
    assert export.stale({path: once}) == []
    path.write_text(once.replace("NEW", "edited by hand"))
    (diff,) = export.stale({path: once})
    assert "edited by hand" in diff


def test_export_check_exits_nonzero_when_stale(monkeypatch, tmp_path):
    target = tmp_path / "README.md"
    target.write_text("committed\n")
    monkeypatch.setattr(export, "outputs", lambda *a, **k: {target: "generated\n"})
    monkeypatch.setattr(export, "_rel", lambda p: p.name)
    assert export.main(["--check"]) == 1
    target.write_text("generated\n")
    assert export.main(["--check"]) == 0


def test_benchmark_data_ts_has_v1_constants_and_latest_run(runs):
    _, _, bundle_path = runs
    bundle = load_bundle(bundle_path)
    ts = export.render_benchmark_data_ts(load_legacy(), bundle)
    assert ts.startswith("// GENERATED by `python -m src.site.export`")
    for name in load_legacy()["constants"]:
        assert re.search(rf"^export const {name}\b", ts, re.M)
    assert "export type Backend = (typeof BACKENDS)[number];" in ts
    assert f'runId: "{bundle.run_id}"' in ts and "isSample: true" in ts


@pytest.mark.skipif(NODE is None, reason="node is not installed")
def test_benchmark_data_ts_evaluates_to_the_legacy_values(runs, tmp_path):
    _, _, bundle_path = runs
    bundle = load_bundle(bundle_path)
    legacy = load_legacy()
    (tmp_path / "data.ts").write_text(export.render_benchmark_data_ts(legacy, bundle))
    (tmp_path / "dump.mjs").write_text(
        'const m = await import("./data.ts"); process.stdout.write(JSON.stringify(m));')
    out = subprocess.run([NODE, "--experimental-strip-types", "--no-warnings", "dump.mjs"],
                         cwd=tmp_path, capture_output=True, text=True, check=True, timeout=60)
    values = json.loads(out.stdout)
    for name, value in legacy["constants"].items():
        assert values[name] == value, name
    expected = export.latest_run_summary(bundle)
    assert values["LATEST_RUN"] == json.loads(json.dumps(expected))
    labels = [row["label"] for row in values["LATEST_RUN"]["backends"]]
    assert labels == list(bundle.backends)


# ------------------------------------------------------------------- the site


def _probe_records(bundle: Path) -> list[dict]:
    return [r for r in read_transcript(bundle) if r.get("type") == "probe"]


def test_site_builds_offline_and_links_every_number(runs, tmp_path, no_network):
    _, _, bundle_path = runs
    bundle = load_bundle(bundle_path)
    out = tmp_path / "site"
    index = site_build.build([bundle], out)
    page = index.read_text()
    run = bundle.run_id

    assert "Sample run, not a benchmark result" in page
    assert (out / "plotly.min.js").stat().st_size > 1_000_000
    assert "cdn.plot.ly" not in page and "https://cdn" not in page
    assert (out / "legacy" / LEGACY_V1.name).exists()
    for f in ("manifest.json", "aggregate.json", "scores.jsonl", TRANSCRIPT):
        assert (out / "runs" / run / f).exists()

    # Headline table: every cell after the label is a link to the run's page.
    table = page.split("<h3>Headline</h3>", 1)[1].split("</table>", 1)[0]
    for label, data in bundle.backends.items():
        row = re.search(rf"<tr><td>{re.escape(label)}</td>(.*?)</tr>", table).group(1)
        cells = re.findall(r"<td>(.*?)</td>", row)
        assert len(cells) == 10
        for cell in cells[:-1]:
            assert cell.startswith('<a class="num" href="runs/'), cell
        r = headline_row(data)
        assert f">{export.pct(r['recall'])}</a>" in row and f">{r['headline_n']}</a>" in row
    # no bare number anywhere in a table cell of the run section
    run_section = page.split("<h2>v1 published", 1)[0]
    for cell in re.findall(r"<td>([^<]*)</td>", run_section):
        assert not re.search(r"\d", cell), cell

    for heading in ("Recall by checkpoint", "Recall by category", "Cost vs recall",
                    "Latency by component", "Probe outcomes", "Methodology", "Answering prompt",
                    "Judge prompt", "Pricing", "Known limitations", "v1 published numbers"):
        assert heading in page
    assert page.count('class="fig"') >= 5
    assert "the prompt this run was judged with" in page
    pricing = bundle.aggregate["pricing"]
    for value in (f"${pricing['input_per_mtok']}", f"${pricing['output_per_mtok']}", pricing["checked_on"],
                  *map(str, bundle.manifest["seeds"])):
        assert f">{value}</a>" in page, value


def test_probe_pages_show_every_probe_with_context(runs, tmp_path, no_network):
    _, _, bundle_path = runs
    probes = _probe_records(bundle_path)
    hostile = "<script>alert('x')</script>"
    # A response with markup must be shown as text, never run.
    records = read_transcript(bundle_path)
    for rec in records:
        if rec.get("type") == "probe" and rec["backend"] == "buffer":
            rec["response"] = hostile
            break
    (bundle_path / TRANSCRIPT).write_text("".join(json.dumps(r) + "\n" for r in records))
    bundle = load_bundle(bundle_path)
    site_build.build([bundle], tmp_path / "site")
    run_dir = tmp_path / "site" / "runs" / bundle.run_id

    labels = {p["fact_id"]: p for p in bundle.aggregate["probes"] if p["backend"] == "summary"}
    for label in bundle.backends:
        html_text = (run_dir / f"probes-{label}.html").read_text()
        mine = [p for p in probes if p["backend"] == label]
        assert html_text.count('<details class="probe"') == len(mine) > 0
        assert all(f'data-cp="{p["checkpoint"]}"' in html_text for p in mine)
        assert "applyFilters" in html_text
        if label == "summary":
            p = mine[0]
            assert p["question"].replace("'", "&#x27;") in html_text
            assert f'class="lab-{labels[p["fact_id"]]["label"]}"' in html_text
    buffer_page = (run_dir / "probes-buffer.html").read_text()
    assert hostile not in buffer_page and "&lt;script&gt;alert(" in buffer_page
    index_page = (run_dir / "index.html").read_text()
    assert bundle.run_id in index_page and 'href="manifest.json"' in index_page


def test_site_build_only_clears_its_own_output(runs, tmp_path):
    _, _, bundle_path = runs
    bundle = load_bundle(bundle_path)
    precious = tmp_path / "precious"
    precious.mkdir()
    (precious / "notes.txt").write_text("keep me")
    with pytest.raises(FileExistsError):
        site_build.build([bundle], precious)
    assert (precious / "notes.txt").read_text() == "keep me"
    out = tmp_path / "site"
    site_build.build([bundle], out)
    (out / "stale.html").write_text("old")
    site_build.build([bundle], out)  # a previous build is replaced
    assert not (out / "stale.html").exists()
    with pytest.raises(ValueError, match="twice"):
        site_build.build([bundle, bundle], out)


def test_site_build_cli_takes_bundle_dirs(runs, tmp_path, no_network):
    _, _, bundle_path = runs
    out = tmp_path / "cli-site"
    assert site_build.main(["--bundle", str(bundle_path), "--out", str(out)]) == 0
    assert (out / "index.html").exists()


# --------------------------------------------------------- the committed outputs


def test_committed_readme_and_ts_match_the_published_bundles():
    """What CI checks with `python -m src.site.export --check`."""
    assert export.stale(export.outputs()) == []


def test_committed_sample_is_labelled_and_builds(tmp_path, no_network):
    (bundle,) = published_bundles()
    assert bundle.is_sample and bundle.manifest["llm_provider"] == "fake"
    assert (bundle.path / TRANSCRIPT_GZ).exists() and not (bundle.path / TRANSCRIPT).exists()
    assert not bundle.manifest["git"]["dirty"]
    page = site_build.build([bundle], tmp_path / "site").read_text()
    assert page.count("Sample run, not a benchmark result") == 1
    assert all(f"<td>{label}</td>" in page for label in bundle.backends)
