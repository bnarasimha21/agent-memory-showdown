"""Build the static results site from committed run bundles.

    python -m src.site.build                 # bundles in results/latest.json -> site/
    python -m src.site.build --bundle DIR    # any bundle(s), e.g. a fresh run
    make site

No network and no API key: it reads bundles from disk, and the Plotly library
is written next to the page from the installed `plotly` package. Output:

- `index.html`: per run, a headline table with intervals, recall by
  checkpoint and by category, cost vs recall (one point per backend and k),
  latency by component, the probe outcome mix; then the v1 published numbers
  and a methodology section (answering prompt, judge prompt, pricing date,
  dataset, known limitations).
- `runs/<run_id>/`: a copy of the bundle, an `index.html` that shows its
  manifest and links its files, and one probe page per backend with every
  probe's question, retrieved context, response and labels.

Every number on a page links to the bundle page of the run it came from.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import shutil
import sys
from collections import defaultdict
from pathlib import Path

from src.bundle import TRANSCRIPT, TRANSCRIPT_GZ, iter_transcript, validate_run_id
from src.dataset import NON_HEADLINE
from src.site.data import (
    LEGACY_V1, PAGES_URL, REPO_ROOT, Bundle, headline_row, load_bundle, load_legacy,
    published_bundles, seed_pairing,
)
from src.site.export import ci, fmt, k_text, ms, pct, usd

SITE_DIR = REPO_ROOT / "site"
MARKER = ".ams-site"  # build only ever clears a directory it created
BUNDLE_FILES = ("manifest.json", "dataset.json", "scores.jsonl", "scoring.json", "aggregate.json",
                TRANSCRIPT, TRANSCRIPT_GZ)
JUDGE_PROMPT = REPO_ROOT / "src" / "scoring" / "judge_prompt.md"

KNOWN_LIMITATIONS = [
    "One synthetic user and one answering model per run; results say how these backends behave "
    "with this model and this kind of conversation, not in general.",
    "Facts are planted by templates (data/facts_v2.yaml) with distractors and filler; real users "
    "state facts less cleanly.",
    "Probes from one run share a memory and are not independent, so the headline interval is a "
    "Student t interval over per-run recall; the Wilson interval over probes is only approximate "
    "and too narrow. With few runs the t interval is wide, which is the honest answer.",
    "The judge is an LLM; its agreement with the deterministic matcher (Cohen's kappa) is reported "
    "with every judged run, and disagreements are listed in aggregate.json.",
    "Sensitive facts (passwords, PINs) are reported apart from the headline because repeating them "
    "is a safety behaviour of the model, not a memory result.",
    "mem0 runs add-only (no update or delete step in mem0 2.x) and without its optional BM25 and "
    "entity boosts; Graphiti is not included.",
    "Results before and after the LangChain 1.x port (v1 vs v2) are not directly comparable.",
]

CSS = """
body{font:15px/1.5 system-ui,-apple-system,Segoe UI,sans-serif;margin:0;color:#1d2433;background:#fafbfc}
main{max-width:1180px;margin:0 auto;padding:24px}
h1{margin:.2em 0}h2{margin-top:2em;border-bottom:1px solid #dde;padding-bottom:.2em}
table{border-collapse:collapse;margin:1em 0;font-size:14px;background:#fff}
th,td{border:1px solid #dde;padding:4px 8px;text-align:right;vertical-align:top}
th:first-child,td:first-child{text-align:left}
a.num{color:inherit;text-decoration:none;border-bottom:1px dotted #88a}
.banner{background:#fff4d6;border:1px solid #e7c66b;padding:10px 14px;border-radius:6px}
.banner.warning{background:#fde2e1;border-color:#d9534f}
.muted{color:#667}.fig{background:#fff;border:1px solid #dde;margin:1em 0;padding:4px}
pre{white-space:pre-wrap;background:#f3f4f7;padding:8px;border-radius:4px;font-size:13px}
details{border:1px solid #dde;background:#fff;margin:4px 0;padding:4px 8px;border-radius:4px}
summary{cursor:pointer}.lab-correct{color:#2d7d46}.lab-wrong{color:#b8323a}
.lab-partial{color:#8a6d00}.lab-refused{color:#6a4fa3}.lab-abstained{color:#666}
"""


def esc(value) -> str:
    return html.escape("" if value is None else str(value))


def slug(label: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", label)


def page(title: str, body: str, root: str = "") -> str:
    return (
        "<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        f"<title>{esc(title)}</title><style>{CSS}</style>"
        f"<script src=\"{root}plotly.min.js\"></script></head>\n<body><main>\n{body}\n</main></body></html>\n"
    )


class Numbers:
    """Formats a number as a link to the bundle page of the run it came from."""

    def __init__(self, bundle: Bundle, root: str = "") -> None:
        self.href = f"{root}runs/{esc(bundle.run_id)}/index.html"
        self.title = esc(f"run {bundle.run_id}: manifest.json, aggregate.json")

    def __call__(self, text: str) -> str:
        if not text or text == "n/a":
            return esc(text)
        return f'<a class="num" href="{self.href}" title="{self.title}">{esc(text)}</a>'


def figure(fig, caption: str) -> str:
    if fig is None:
        return ""
    return (f'<div class="fig">{fig.to_html(full_html=False, include_plotlyjs=False)}'
            f'<div class="muted">{caption}</div></div>')


# ------------------------------------------------------------------ index.html


def headline_table(bundle: Bundle, num: Numbers) -> str:
    head = ("<tr><th>Backend</th><th>Recall (run mean)</th><th>95% CI (t, over runs)</th>"
            "<th>Per-probe rate [approx. 95% Wilson]</th>"
            "<th>Probes in recall</th><th>Cost / 1K conv</th><th>Cost / correct recall</th>"
            "<th>Latency p50 / p95 (ms)</th><th>Tokens / conv</th><th>Memory at end</th><th></th></tr>")
    rows = []
    for label, data in bundle.backends.items():
        r = headline_row(data)
        probes = f'runs/{esc(bundle.run_id)}/probes-{esc(slug(label))}.html'
        if r["error"]:
            rows.append(f"<tr><td>{esc(label)}</td><td colspan=\"9\">failed: {esc(r['error'])}</td>"
                        f"<td></td></tr>")
            continue
        rows.append(
            f"<tr><td>{esc(label)}</td><td>{num(pct(r['run_mean']))}</td><td>{num(ci(r['run_mean_ci']))}</td>"
            f"<td>{num(pct(r['recall']))} {num(ci(r['recall_ci']))}</td>"
            f"<td>{num(str(r['headline_n']))}</td><td>{num(usd(r['cost_per_1k']))}</td>"
            f"<td>{num(usd(r['cost_per_correct'], 4))}</td>"
            f"<td>{num(ms(r['latency_p50']))} / {num(ms(r['latency_p95']))}</td>"
            f"<td>{num(fmt(r['tokens']))}</td>"
            f"<td>{num(fmt(r['memory_end']))} {esc(r['memory_unit'])}</td>"
            f'<td><a href="{probes}">probes</a></td></tr>'
        )
    return f"<table>{head}{''.join(rows)}</table>"


def category_table(bundle: Bundle, num: Numbers) -> str:
    from src.dataset import CATEGORIES

    present = {c for d in bundle.backends.values() for c in (d.get("recall_by_category") or {})}
    # Known categories in their usual order, then any others (as visualize does).
    cats = [c for c in CATEGORIES if c in present] + sorted(present - set(CATEGORIES))
    head = "<tr><th>Backend</th>" + "".join(
        f"<th>{esc(c)}{' *' if c in NON_HEADLINE else ''}</th>" for c in cats) + "</tr>"
    rows = []
    for label, data in bundle.backends.items():
        by_cat = data.get("recall_by_category") or {}
        cells = []
        for c in cats:
            d = by_cat.get(c)
            cells.append("<td></td>" if not d else
                         f"<td>{num(pct(d['correct_rate']))} <span class=\"muted\">"
                         f"{num(ci(d['correct_ci95']))} n={num(str(d['n']))}</span></td>")
        rows.append(f"<tr><td>{esc(label)}</td>{''.join(cells)}</tr>")
    return (f"<table>{head}{''.join(rows)}</table>"
            "<p class=\"muted\">* not part of the headline recall: abstention facts were never told "
            "(correct means the model said so), sensitive facts test whether it repeats a secret.</p>")


def run_section(bundle: Bundle, headline: bool) -> str:
    from src import visualize as viz

    num = Numbers(bundle)
    m = bundle.manifest
    results = bundle.backends
    src = (f'run <a href="runs/{esc(bundle.run_id)}/index.html">{esc(bundle.run_id)}</a> '
           f'(<a href="runs/{esc(bundle.run_id)}/manifest.json">manifest</a>, '
           f'<a href="runs/{esc(bundle.run_id)}/aggregate.json">aggregate</a>)')
    agreement = bundle.aggregate.get("agreement") or {}
    parts = [
        f"<h2>{'Latest run' if headline else 'Run'}: {esc(bundle.run_id)}</h2>",
    ]
    if bundle.is_sample:
        parts.append(
            '<p class="banner"><b>Sample run, not a benchmark result.</b> Made offline with the fake '
            "chat model and hashing embeddings, to show the bundle format and this page. The numbers "
            "describe the harness, not any model or memory backend.</p>")
    parts.append(
        f"<p>{num(str(m.get('num_runs')))} runs x {num(str(m.get('num_turns')))} turns, checkpoints "
        f"{', '.join(num(str(c)) for c in m.get('checkpoints', []))}; model <code>{esc(m.get('llm_model'))}"
        f"</code>, embeddings <code>{esc(m.get('embedding_model'))}</code>, k = {num(k_text(m.get('k')))}. "
        f"Scored by <code>{esc(bundle.aggregate.get('scoring', {}).get('judge_model') or 'matcher only')}"
        f"</code>"
        + (f", matcher/judge kappa {num(fmt(agreement.get('kappa'), '.3f'))} over "
           f"{num(str(agreement.get('n')))} probes" if agreement.get("kappa") is not None else "")
        + f". Source: {src}.</p>")
    parts.append("<h3>Headline</h3><p class=\"muted\">Recall leaves out the abstention and "
                 "sensitive categories, which are shown on their own below. "
                 "Recall is the mean of the per-run recall rates; its CI is a 95% Student t "
                 "interval over runs (none for a single run). The per-probe rate's Wilson interval "
                 "is approximate, because probes in one run are not independent.</p>")
    pairing = seed_pairing(bundle)
    if pairing and pairing["warning"]:
        parts.append(f'<p class="banner warning"><b>Warning.</b> {esc(pairing["warning"])}</p>')
    if pairing and pairing["kind"] == "paired":
        parts.append(f'<p class="muted">{esc(pairing["text"])}</p>')
    parts.append(headline_table(bundle, num))
    cap = f"Source: {src}."
    parts.append("<h3>Recall by checkpoint</h3>" + figure(viz.fig_memory_decay_curve(results), cap))
    parts.append("<h3>Recall by category</h3>" + category_table(bundle, num)
                 + figure(viz.fig_recall_by_category(results), cap))
    parts.append("<h3>Cost vs recall</h3>" + figure(viz.fig_cost_vs_recall(results), cap))
    parts.append("<h3>Latency by component</h3>" + figure(viz.fig_latency_bar(results), cap)
                 + figure(viz.fig_latency_by_turn(results), cap))
    parts.append("<h3>Probe outcomes</h3>" + figure(viz.fig_label_breakdown(results), cap))
    return "\n".join(parts)


def legacy_section(legacy: dict) -> str:
    c = legacy["constants"]
    href = "legacy/v1_published.json"
    title = esc(f"v1 published numbers, {legacy['published']}")

    def num(text: str) -> str:
        return f'<a class="num" href="{href}" title="{title}">{esc(text)}</a>'

    rows = []
    for b in c["BACKENDS"]:
        cells = [
            fmt(c["RECALL_AT_TURN_15"][b], "", "%"),
            fmt(c["RECALL_AT_TURN_50"][b], "", "%"),
            fmt(c["AVG_LATENCY_MS"][b] / 1000, ".1f", "s"),
            "$" + fmt(c["COST_PER_1K"][b], ","),
            fmt(c["AVG_TOKENS"][b] / 1000, ".0f", "K"),
        ]
        rows.append(f"<tr><td>{esc(b)}</td>" + "".join(f"<td>{num(x)}</td>" for x in cells) + "</tr>")
    rows = "".join(rows)
    limits = "".join(f"<li>{esc(x)}</li>" for x in legacy["limitations"])
    return (
        "<h2>v1 published numbers (v1 methodology, known limits)</h2>"
        f"<p>{esc(legacy['description'])} There is no v1 bundle, so these numbers link to "
        f'<a href="{href}">v1_published.json</a>. They are not comparable with v2.</p>'
        "<table><tr><th>Backend</th><th>Recall @ 15</th><th>Recall @ 50</th><th>Avg latency / turn</th>"
        f"<th>Cost / 1K convos</th><th>Tokens / run</th></tr>{rows}</table>"
        f"<p>Known v1 limits, all fixed in v2:</p><ul>{limits}</ul>"
    )


def methodology_section(bundle: Bundle) -> str:
    m = bundle.manifest
    scoring = bundle.aggregate.get("scoring") or m.get("scoring") or {}
    pricing = bundle.aggregate.get("pricing") or {}
    judge_text = JUDGE_PROMPT.read_text(encoding="utf-8") if JUDGE_PROMPT.exists() else ""
    judge_hash = hashlib.sha256(judge_text.encode("utf-8")).hexdigest() if judge_text else None
    recorded = scoring.get("judge_prompt_hash")
    if recorded and judge_hash == recorded:
        judge_note = f"sha256 {esc(recorded[:12])}, the prompt this run was judged with."
    elif recorded:
        judge_note = (f"The run was judged with prompt sha256 {esc(recorded[:12])}; the file at this "
                      f"commit hashes to {esc((judge_hash or 'missing')[:12])}, so it has changed since.")
    else:
        judge_note = "This run was scored by the matcher only."
    ds = m.get("dataset", {})
    packages = ", ".join(f"{esc(k)} {esc(v)}" for k, v in m.get("packages", {}).items())
    limits = "".join(f"<li>{esc(x)}</li>" for x in KNOWN_LIMITATIONS)
    num = Numbers(bundle)
    composition = ", ".join(f"{esc(c)} {num(str(n))}" for c, n in (ds.get("composition") or {}).items())
    seeds = ", ".join(num(str(s)) for s in m.get("seeds") or [])
    return f"""
<h2>Methodology</h2>
<p>Each run plays a seeded synthetic conversation into a memory backend, then asks read-only probe
questions at checkpoints (memory is fingerprinted before and after each checkpoint to prove probes do
not write). Every backend answers with the same model and prompt; only the Memory section differs.
Each response is labelled correct, partial, wrong, refused or abstained by a deterministic matcher and
an LLM judge.</p>
<h3>Answering prompt</h3><p class="muted">sha256 {esc((m.get('prompt_hash') or '')[:12])}</p>
<pre>{esc(m.get('prompt_template'))}</pre>
<h3>Judge prompt</h3><p class="muted">{judge_note} Judge: {esc(scoring.get('judge_provider'))}
<code>{esc(scoring.get('judge_model'))}</code>, matcher {esc(scoring.get('matcher'))}.</p>
<details><summary>Show the judge prompt</summary><pre>{esc(judge_text)}</pre></details>
<h3>Pricing</h3><p>Model <code>{esc(pricing.get('model'))}</code>: {num(f"${pricing.get('input_per_mtok')}")} per
million input tokens, {num(f"${pricing.get('output_per_mtok')}")} per million output tokens
({esc(pricing.get('currency'))}), source {esc(pricing.get('source'))}, checked on
{num(str(pricing.get('checked_on')))}. Cost = {esc(pricing.get('formula'))}.</p>
<h3>Dataset</h3><p>Fact bank <code>{esc(ds.get('bank'))}</code> ({esc(ds.get('bank_version'))}, sha256
{esc((ds.get('bank_sha256') or '')[:12])}), facts per category {composition},
distractors {esc(ds.get('distractors'))}, seeds {seeds}. Headline excludes
{esc(', '.join(ds.get('headline_excludes', [])))}.</p>
<h3>Software</h3><p class="muted">git {esc((m.get('git') or {}).get('sha'))}
{'(uncommitted changes)' if (m.get('git') or {}).get('dirty') else ''}; {packages}.</p>
<h3>Known limitations</h3><ul>{limits}</ul>
"""


def index_html(bundles: list[Bundle], legacy: dict) -> str:
    body = [
        "<h1>Agent Memory Showdown</h1>",
        "<p>Six agent memory backends (full buffer, rolling summary, Qdrant, pgvector, LangGraph store, "
        "Mem0) run through the same seeded synthetic conversations; probes at checkpoints measure what "
        "each one still recalls, and every turn records latency by component and token cost. "
        f'Source: <a href="https://github.com/bnarasimha21/agent-memory-showdown">GitHub</a>. '
        f'Published at <a href="{PAGES_URL}">{PAGES_URL}</a>.</p>',
    ]
    body += [run_section(b, i == 0) for i, b in enumerate(bundles)]
    body.append(legacy_section(legacy))
    body.append(methodology_section(bundles[0]))
    return page("Agent Memory Showdown results", "\n".join(body))


# -------------------------------------------------------------- bundle pages


def bundle_index_html(bundle: Bundle, files: list[str]) -> str:
    links = "".join(f'<li><a href="{esc(f)}">{esc(f)}</a></li>' for f in files)
    probes = "".join(
        f'<li><a href="probes-{esc(slug(b))}.html">{esc(b)}</a></li>' for b in bundle.backends)
    body = (
        f'<p><a href="../../index.html">Results</a></p><h1>Run {esc(bundle.run_id)}</h1>'
        + ('<p class="banner"><b>Sample run, not a benchmark result</b> (fake LLM and embeddings).</p>'
           if bundle.is_sample else "")
        + f"<h2>Files</h2><ul>{links}</ul><h2>Probe transcripts</h2><ul>{probes}</ul>"
        f"<h2>manifest.json</h2><pre>{esc(json.dumps(bundle.manifest, indent=2, ensure_ascii=False))}</pre>"
    )
    return page(f"Run {bundle.run_id}", body, root="../../")


def probe_records(bundle: Bundle) -> dict[str, list[dict]]:
    """Probe transcript records per backend label, joined with their final labels."""
    labels = {(p["backend"], p["run_index"], p["checkpoint"], p["fact_id"]): p
              for p in bundle.aggregate.get("probes", [])}
    out: dict[str, list[dict]] = defaultdict(list)
    for rec in iter_transcript(bundle.path):
        if rec.get("type") != "probe":
            continue
        key = (rec["backend"], rec["run_index"], rec["checkpoint"], rec["fact_id"])
        out[rec["backend"]].append({**rec, **{k: v for k, v in labels.get(key, {}).items()
                                              if k in ("label", "matcher_label", "judge_label",
                                                       "judge_rationale")}})
    return out


FILTER_JS = """
<script>
function applyFilters(){
  var cat=document.getElementById('f-cat').value, lab=document.getElementById('f-lab').value,
      cp=document.getElementById('f-cp').value, shown=0;
  document.querySelectorAll('details.probe').forEach(function(d){
    var ok=(!cat||d.dataset.cat===cat)&&(!lab||d.dataset.lab===lab)&&(!cp||d.dataset.cp===cp);
    d.style.display=ok?'':'none'; if(ok) shown++;
  });
  document.getElementById('shown').textContent=shown;
}
</script>
"""


def probes_html(bundle: Bundle, label: str, probes: list[dict]) -> str:
    def options(field: str, values) -> str:
        return "".join(f'<option value="{esc(v)}">{esc(v)}</option>' for v in values)

    cats = sorted({p.get("category") or "" for p in probes})
    labs = sorted({p.get("label") or "unscored" for p in probes})
    cps = sorted({p["checkpoint"] for p in probes})
    items = []
    for p in sorted(probes, key=lambda p: (p["run_index"], p["checkpoint"], p.get("order", 0))):
        lab = p.get("label") or "unscored"
        pid = f"r{p['run_index']}-c{p['checkpoint']}-{p['fact_id']}"
        answers = " | ".join(" + ".join(group) for group in p.get("answers") or []) or p.get("answer_key")
        items.append(
            f'<details class="probe" id="{esc(pid)}" data-cat="{esc(p.get("category"))}" '
            f'data-lab="{esc(lab)}" data-cp="{esc(p["checkpoint"])}"><summary>run {esc(p["run_index"])}, '
            f'checkpoint {esc(p["checkpoint"])}, <b>{esc(p["fact_id"])}</b> ({esc(p.get("category"))}): '
            f'<span class="lab-{esc(lab)}">{esc(lab)}</span>: {esc(p.get("question"))}</summary>'
            f"<p><b>Expected:</b> {esc(answers)}"
            + (f" <span class=\"muted\">(stale, must not be given: {esc(', '.join(p['stale']))})</span>"
               if p.get("stale") else "")
            + f"</p><p><b>Response:</b> {esc(p.get('response'))}</p>"
            f"<p class=\"muted\">matcher {esc(p.get('matcher_label'))}, judge {esc(p.get('judge_label'))}"
            + (f": {esc(p.get('judge_rationale'))}" if p.get("judge_rationale") else "")
            + f"; fact planted at turn {esc(p.get('planted_at'))}; retrieve "
            f"{esc(round(p.get('retrieve_ms') or 0, 1))} ms, {esc(p.get('input_tokens'))} input tokens</p>"
            f"<p><b>Retrieved memory context</b></p><pre>{esc(p.get('context'))}</pre></details>"
        )
    body = (
        f'<p><a href="../../index.html">Results</a>, <a href="index.html">run {esc(bundle.run_id)}</a></p>'
        f"<h1>Probes: {esc(label)}</h1>"
        + ('<p class="banner"><b>Sample run, not a benchmark result</b> (fake LLM and embeddings).</p>'
           if bundle.is_sample else "")
        + f'<p>{len(probes)} probes, <span id="shown">{len(probes)}</span> shown. '
        f'Category <select id="f-cat" onchange="applyFilters()"><option value="">all</option>'
        f'{options("cat", cats)}</select> label <select id="f-lab" onchange="applyFilters()">'
        f'<option value="">all</option>{options("lab", labs)}</select> checkpoint '
        f'<select id="f-cp" onchange="applyFilters()"><option value="">all</option>{options("cp", cps)}'
        f"</select></p>{FILTER_JS}" + "\n".join(items)
    )
    return page(f"Probes: {label}", body, root="../../")


# ----------------------------------------------------------------------- build


def prepare_out(out: Path) -> None:
    if out.is_symlink():
        raise FileExistsError(f"{out} is a symlink; refusing to build into it")
    if out.exists():
        if not (out / MARKER).exists() and any(out.iterdir()):
            raise FileExistsError(f"{out} exists and was not made by this builder; refusing to clear it")
        shutil.rmtree(out)
    out.mkdir(parents=True)
    (out / MARKER).write_text("built by python -m src.site.build\n", encoding="utf-8")


def validate(bundles: list[Bundle]) -> None:
    """Everything that would make a link wrong or a page overwrite another, checked up front."""
    if not bundles:
        raise ValueError("no bundles to build from")
    seen = set()
    for bundle in bundles:
        validate_run_id(bundle.run_id)
        if bundle.run_id != bundle.path.name:
            raise ValueError(f"manifest run_id {bundle.run_id!r} does not match the bundle "
                             f"directory {bundle.path.name!r}")
        if bundle.run_id in seen:
            raise ValueError(f"run {bundle.run_id} listed twice")
        seen.add(bundle.run_id)
        slugs: dict[str, str] = {}
        for label in bundle.backends:
            other = slugs.setdefault(slug(label), label)
            if other != label:
                raise ValueError(f"backends {other!r} and {label!r} in run {bundle.run_id} would share "
                                 f"the page probes-{slug(label)}.html")


def render(bundles: list[Bundle], legacy: dict) -> dict[str, str]:
    """Every generated page by its path in the site, rendered before anything is written."""
    pages = {}
    for bundle in bundles:
        files = [f for f in BUNDLE_FILES if (bundle.path / f).exists()]
        pages[f"runs/{bundle.run_id}/index.html"] = bundle_index_html(bundle, files)
        records = probe_records(bundle)
        for label in bundle.backends:
            pages[f"runs/{bundle.run_id}/probes-{slug(label)}.html"] = probes_html(
                bundle, label, records.get(label, []))
    pages["index.html"] = index_html(bundles, legacy)
    return pages


def build(bundles: list[Bundle], out: Path = SITE_DIR, legacy: dict | None = None) -> Path:
    from plotly.offline import get_plotlyjs

    validate(bundles)
    legacy = legacy if legacy is not None else load_legacy()
    pages = render(bundles, legacy)  # a bad bundle fails here, before the old site is removed
    prepare_out(out)
    (out / "plotly.min.js").write_text(get_plotlyjs(), encoding="utf-8")
    (out / "legacy").mkdir()
    shutil.copy2(LEGACY_V1, out / "legacy" / LEGACY_V1.name)
    for bundle in bundles:
        dest = out / "runs" / bundle.run_id
        dest.mkdir(parents=True)
        for f in BUNDLE_FILES:
            if (bundle.path / f).exists():
                shutil.copy2(bundle.path / f, dest / f)
    for rel, text in pages.items():
        (out / rel).write_text(text, encoding="utf-8")
    (out / ".nojekyll").write_text("", encoding="utf-8")
    return out / "index.html"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Build the static results site")
    parser.add_argument("--bundle", action="append", default=None, metavar="DIR",
                        help="bundle directory to publish (repeatable); default: results/latest.json")
    parser.add_argument("--out", default=str(SITE_DIR), help="output directory (default: site/)")
    args = parser.parse_args(argv)
    bundles = [load_bundle(b) for b in args.bundle] if args.bundle else published_bundles()
    index = build(bundles, Path(args.out))
    print(f"site written to {index}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
