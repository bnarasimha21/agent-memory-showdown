# Agent Memory Showdown — X (Twitter) Short-Form Package

**Draft for review:** Jakub Lukaszczyk, Ari Sigal
**Posting from:** DigitalOcean brand account · **Owner:** Narsi Badrinath
**Status:** DRAFT — copy + storyboard pending approval; video render pending sign-off on the beat sheet.

---

## 1. The video

- **Format:** 45 seconds, vertical **9:16 (1080×1920)**, optimized for the X mobile feed.
- **Two variants to A/B** (same edit, different audio track):
  - **Variant A** — key voiceover (from the original narration) + burned-in captions
  - **Variant B** — burned-in captions + background music, **no voiceover** (silent-autoplay friendly)
- **Source:** the full *Agent Memory Showdown* video (7:02).
- **Link:** _[to be added once rendered and approved]_

---

## 2. 45-second beat sheet (storyboard)

| Time | On-screen | Caption / VO |
|---|---|---|
| 0:00–0:05 | Phone chat: user shares "dog's name is Baxter" / "allergic to shellfish", then asks "What's my dog's name?" → bot blanks | **Caption:** "Most chatbots forget what you told them 5 minutes ago." · **VO:** "Most chatbots can't remember what you said five minutes ago." |
| 0:05–0:11 | 4 backend chips: Buffer · Summary · Qdrant · pgvector. Sub: "50 turns · 10 planted facts · 1,000 LLM calls" | **Caption:** "So we benchmarked 4 ways to give an AI agent memory." · **VO:** "So I built a benchmark to find out." |
| 0:11–0:24 | Bars animate: Buffer 90% · Qdrant 82% · pgvector 82% · Summary crashes to 42% | **Caption:** "Recall at turn 50" → "Summary remembered less than half." · **VO:** "Buffer ninety percent. Qdrant and pgvector, eighty-two. Summary? Forty-two." |
| 0:24–0:36 | Cost bars: Buffer $4,303 towering over Qdrant $418 / pgvector $416 | **Caption:** "Same recall. ~1/10th the cost." · **VO:** "For every dollar on vector memory, you'd spend ten on buffer." |
| 0:36–0:42 | 3 chips: "Vector wins" / "Summary = worst of all worlds" / "Run Postgres? pgvector is ~free" | **Caption:** "Already run PostgreSQL? pgvector is basically free to add." |
| 0:42–0:45 | "Don't guess. Measure." → DigitalOcean logo + "Built on DigitalOcean" + link | **VO:** "Don't guess. Measure." |

_(The "safety behavior" finding is held out of the 45s cut for time — it lives in the thread.)_

---

## 3. X post copy — main tweet (pick one; video attached)

**Option A (benefit-led)**
> Most chatbots forget what you told them 5 minutes ago.
> So we benchmarked 4 ways to give an AI agent memory — recall, speed, and cost.
> Vector memory won: 82% recall at ~1/10th the cost of stuffing the whole history into the prompt. 🧵👇

**Option B (stat-led)**
> 82% recall at ~1/10th the cost.
> We put 4 AI memory architectures (buffer, summary, Qdrant, pgvector) through a 50-turn conversation with 10 planted facts. The results weren't close. 🧵

**Option C (curiosity-led)**
> We gave an AI agent memory four different ways, then tried to break it: a 50-turn conversation with 10 planted facts.
> One approach forgot more than half. One nailed it at a tenth of the cost. 🧵

---

## 4. X thread (follow-up tweets)

**2/** The test: a 50-turn chat with 10 facts planted at exact turns, then probed for recall. Four LangChain backends — Buffer, Summary, Qdrant, pgvector. 1,000+ LLM calls, 5 runs each, all on a single DigitalOcean Droplet.

**3/** Recall @ turn 50:
• Buffer 90%
• Qdrant 82%
• pgvector 82%
• Summary 42%
Summary doesn't just forget old facts — it actively destroys new ones every time it re-compresses.
`[IMAGE: recall scoreboard]`

**4/** Now the cost (per 1,000 conversations):
• Buffer $4,303
• Summary $2,256
• Qdrant $418
• pgvector $416
Vector memory ≈ 90% cheaper than buffer, and latency stays flat. (Summary was 5× slower — 3 hours of wall-clock time.)
`[IMAGE: cost per 1,000 conversations]`

**5/** One surprise: every backend "failed" to recall the Wi-Fi password and bank PIN — even buffer, which had them right there in the prompt. That's not a memory bug. It's Claude's safety layer declining to repeat sensitive data — and it matters for how you design memory benchmarks.
`[IMAGE: "FAILED" sensitive-data tiles]`

**6/** Takeaway: if you already run PostgreSQL, pgvector is basically free to add — 82% recall at a fraction of the cost. Building AI agents? Don't guess your memory backend. Measure.
Full breakdown 👉 `[LINK]`

---

## 5. Suggested images (thread + fallback)

1. **Recall scoreboard** — Buffer 90 / Qdrant 82 / pgvector 82 / Summary 42 (frame from video)
2. **Cost per 1,000 conversations** — $4,303 vs $418/$416 (strongest single image)
3. **The "surprise"** — red "FAILED" tiles for Wi-Fi password + bank PIN
4. **The setup/stack** — DO Droplet → Qdrant + Postgres/pgvector + Claude 4.5 Sonnet

_All are currently 16:9 frames; can be cropped to 1:1 for the feed. Final source files to be attached._

---

## 6. Open items / decisions for review

- **Brand voice:** the original narration is first-person ("I built…"). For the brand account, keep the authentic engineer voice (and credit Narsi), or shift to "we"? (Copy above uses "we"; Variant A VO still says "I.")
- **Music for Variant B:** need a brand-approved / licensed track — please point to a source.
- **Link destination** for "Full breakdown": full video (YouTube?) / GitHub repo / blog — which?
- **Handles/hashtags** per DO brand guidelines (e.g. @digitalocean; #AIagents #LangChain #pgvector #RAG — sparingly).
- **Posting slot / social calendar** — owned by marketing.
- **Claims check:** all numbers match the benchmark (recall 90/82/82/42; cost $4,303/$2,256/$418/$416; ~90% cost reduction; 5× latency). Safe to state as-is.

---

> **Note:** This is the 45s social cut of Narsi's existing *Agent Memory* benchmark video — **separate** from the *Inference Router* video discussed in the Slack thread (different product; needs the Deploy demo footage + Prasad/Salman input). Flagged so the two aren't conflated.
