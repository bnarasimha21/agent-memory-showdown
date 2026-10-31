# Agent Memory video — Suggested copy & images (for review)

> **v1 numbers, read before posting.** Every figure in this file comes from the v1 benchmark (April 2026), whose methodology has known limits: recall probes were written back into memory, buffer and summary used a different prompt from the vector backends, two recall turns were never probed, and scoring was a substring check. See *v1 observations* and *Methodology notes and limitations* in the README. Do not post these numbers without that caveat. The numbers below are left as they were published.


---

## 1. Main post copy (X / LinkedIn) — Options

**Option A (benefit-led, recommended)**
> Most chatbots forget what you told them 5 minutes ago.
>
> So we tested 4 ways to give an AI agent memory: a 50-turn conversation with 10 planted facts.
>
> Vector memory matched the brute-force approach on recall, at about 1/10th the cost. 🧵👇

**Option B (stat-led)**
> 82% recall at ~1/10th the cost.
>
> We put 4 AI memory backends (buffer, summary, Qdrant, pgvector) through a 50-turn conversation with 10 planted facts. The results weren't close. 🧵

**Option C (curiosity-led)**
> We gave an AI agent memory 4 different ways, then checked what it remembered 50 turns later.
>
> One approach forgot more than half. One nailed it at a fraction of the cost. 🧵

---

## 2. X thread (after the main post)

_The main post above is tweet 1/. The thread continues from 2/._

**2/** The test: a 50-turn chat with 10 facts planted at exact turns, then probed for recall. Four LangChain backends: Buffer, Summary, Qdrant, and pgvector on Managed Postgres. 1,000+ LLM calls, 5 runs each, all on a single DigitalOcean Droplet.

**3/** Recall at turn 50:
• Buffer 90%
• Qdrant 82%
• pgvector 82%
• Summary 42%
Summary doesn't just forget old facts, it actively destroys them every time it re-compresses the history.
`[IMAGE: recall scoreboard]`

**4/** Now the cost (per 1,000 conversations):
• Buffer $4,303
• Summary $2,256
• Qdrant $418
• pgvector $416
Vector memory is roughly 90% cheaper than buffer, and latency stays flat as the conversation grows.
`[IMAGE: cost per 1,000 conversations]`

**5/** One surprise: every backend "failed" to recall the Wi-Fi password and bank PIN, even buffer, which had them right there in the prompt. That's not a memory bug. It's the model's safety layer declining to repeat sensitive data, and it matters for how you design memory tests.

**6/** Takeaway: if you already run PostgreSQL, pgvector is basically free to add: 82% recall at a fraction of the cost. Building AI agents? Don't guess your memory backend. Measure.
Full breakdown 👉 [link]

---

## 3. Suggested images

All exported in `results/social-images/` (vertical 9:16 stills from the video; can be cropped to 1:1 or 16:9 for the feed).

| File | Use | Why |
|---|---|---|
| `01_hook_50turns.png` | Main post visual (if not attaching the video) | The "50 turns later" chat hook tells the whole story in one frame |
| `02_recall_scoreboard.png` | Thread tweet 3 | The four recall bars, Summary visibly collapsing |
| `03_cost_bars.png` | Thread tweet 4 (strongest single image) | $4,303 towering over $416, with "same recall, ~1/10th the cost" |
| `04_endcard.png` | Optional closing/profile | Clean brand end card with CTA + @digitalocean |

Best single image if only one is used: **`03_cost_bars.png`**.
