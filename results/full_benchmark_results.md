# Agent Memory Showdown — Full Benchmark Results

**Run date:** April 17, 2026
**Duration:** ~5 hours (11:03–15:55 UTC)
**Infrastructure:** DigitalOcean Droplet (8GB RAM / 4 vCPU, Ubuntu 24.04, BLR1 region)
**LLM:** Claude 4.5 Sonnet via DO Serverless Inference (`anthropic-claude-4.5-sonnet`)
**Embeddings:** Local sentence-transformers (`all-MiniLM-L6-v2`, 384-dim, CPU)
**Vector DBs:** Qdrant (Docker) + PostgreSQL 16 with pgvector, both on the same Droplet

## Test Configuration

| Parameter | Value |
|-----------|-------|
| Backends | `buffer`, `summary`, `qdrant`, `pgvector` |
| Runs per backend | 5 |
| Turns per run | 50 |
| Facts seeded at turns | 1, 3, 7, 12, 18, 25, 30, 35, 40, 45 (10 facts) |
| Recall probed at turns | 15, 50 |
| Scoring | exact match = correct, partial word match = partial, miss = failed |

---

## Headline Results

| Backend | Avg Latency/Turn | Recall @ Turn 15 | Recall @ Turn 50 | Avg Tokens/Run | Cost / 1K Convos |
|---------|-----------------|-------------------|-------------------|---------------|------------------|
| **buffer** | 10,328 ms | **100%** | **90%** | 717,200 | **$4,303** |
| **summary** | 36,027 ms | **100%** | 42% | 375,926 | $2,256 |
| **qdrant** | **7,001 ms** | **100%** | 82% | **69,595** | **$418** |
| **pgvector** | **7,021 ms** | **100%** | 82% | **69,366** | **$416** |

---

## Memory Decay Curve

All backends achieve **100% recall at turn 15** (only 4 facts to remember, seeded recently).

At **turn 50** (10 facts, seeded across the full conversation), the story diverges:

| Backend | Turn 15 | Turn 50 | Drop |
|---------|---------|---------|------|
| buffer | 100% | 90% | -10% |
| summary | 100% | 42% | **-58%** |
| qdrant | 100% | 82% | -18% |
| pgvector | 100% | 82% | -18% |

### Detailed Recall at Turn 50 (by fact seeded at each turn)

| Fact seeded at → | Turn 1 | Turn 3 | Turn 7 | Turn 12 | Turn 18 | Turn 25 | Turn 30 | Turn 35 | Turn 40 | Turn 45 |
|------------------|--------|--------|--------|---------|---------|---------|---------|---------|---------|---------|
| **buffer** | 100% | 100% | 100% | 100% | 100% | 100% | **80%** | 100% | 100% | **20%** |
| **summary** | 100% | 100% | 100% | 100% | **0%** | **0%** | **0%** | **20%** | **0%** | **0%** |
| **qdrant** | 100% | 100% | 100% | 100% | 100% | 100% | **20%** | 100% | 100% | **0%** |
| **pgvector** | 100% | 100% | 100% | 100% | 100% | 100% | **20%** | 100% | 100% | **0%** |

**Key observations:**

- **Buffer** is near-perfect but drops on the Wi-Fi password (turn 30, 80%) and bank PIN (turn 45, 20%). Claude likely refuses to repeat sensitive data even when it remembers it.
- **Summary** collapses after turn 12 — the summarizer aggressively compresses away specific details like dates, names, and passwords. Facts from turns 18–45 are essentially lost.
- **Qdrant and pgvector** are identical — both struggle with the Wi-Fi password (turn 30) and bank PIN (turn 45), same as buffer. This is likely a Claude safety behavior, not a retrieval failure.

---

## Latency Analysis

### Average Latency Per Turn (ms)

| Backend | Turn 1 | Turn 10 | Turn 20 | Turn 30 | Turn 40 | Turn 49 |
|---------|--------|---------|---------|---------|---------|---------|
| buffer | 3,092 | 9,714 | 11,172 | 7,537 | 8,375 | 11,644 |
| summary | 8,696 | 25,342 | 51,540 | 29,394 | 46,598 | 41,911 |
| qdrant | 2,637 | 7,339 | 8,731 | 6,828 | 4,732 | 4,845 |
| pgvector | 4,376 | 7,327 | 6,897 | 6,101 | 4,258 | 7,636 |

**Key observations:**

- **Buffer** latency grows as history accumulates (~3s at turn 1 → ~12s by turn 30+), then fluctuates as the context window fills.
- **Summary** is 3-5x slower than everything else. Each turn requires an additional LLM call to update the running summary, pushing latency to 30-50s per turn.
- **Qdrant and pgvector** stay relatively flat around 5-9s per turn regardless of conversation length — the vector search retrieves only the top-K snippets, keeping the prompt size constant.
- **Qdrant and pgvector actually get faster** in the last 10 turns, possibly due to more efficient retrieval as the vector index matures.

### Time Per Backend (wall clock)

| Backend | Total time (5 runs) |
|---------|-------------------|
| buffer | ~45 min |
| summary | ~3 hours |
| qdrant | ~32 min |
| pgvector | ~32 min |

---

## Token Usage & Cost

| Backend | Avg Tokens/Run | Std Dev | Cost/1K Conversations |
|---------|---------------|---------|----------------------|
| buffer | 717,200 | 47,607 | $4,303 |
| summary | 375,926 | 1,700 | $2,256 |
| qdrant | 69,595 | 14,491 | $418 |
| pgvector | 69,366 | 12,235 | $416 |

> Cost formula: blended rate of 75% input @ $0.003/1K tokens + 25% output @ $0.015/1K tokens (Claude via DO Serverless Inference)

**Key observations:**

- **Buffer** uses **10x more tokens** than vector backends — it sends the entire conversation history every turn, leading to O(n²) token growth.
- **Summary** uses ~5x more than vector backends. The summarization LLM calls add significant token overhead, partially defeating the purpose of compression.
- **Qdrant and pgvector** are virtually identical in cost — both send only 4 relevant snippets per turn, keeping token usage flat.
- Vector backends save **$3,887 per 1,000 conversations** compared to buffer (a **90% reduction**).

---

## Qdrant vs. pgvector Head-to-Head

| Metric | Qdrant | pgvector | Winner |
|--------|--------|----------|--------|
| Avg latency | 7,001 ms | 7,021 ms | Tie |
| Std dev latency | 2,452 ms | 2,368 ms | pgvector (slightly) |
| Recall @ turn 15 | 100% | 100% | Tie |
| Recall @ turn 50 | 82% | 82% | Tie |
| Avg tokens/run | 69,595 | 69,366 | Tie |
| Cost/1K conversations | $418 | $416 | Tie |

**Verdict:** At this scale (50 turns, ~50 vectors per session), there is **no meaningful difference** between Qdrant and pgvector. If you already run PostgreSQL, pgvector adds zero extra infrastructure cost.

---

## Conclusions

1. **Vector-backed memory (qdrant/pgvector) is the best overall choice** — 82% recall at 1/10th the cost of full-buffer, with the flattest latency curve.

2. **Buffer is the accuracy king but wildly expensive** — 90% recall at turn 50, but at $4,303/1K conversations (10x the vector backends). Only viable for short conversations or when cost is irrelevant.

3. **Summary is the worst performer** — 42% recall at turn 50, slowest latency (36s/turn avg), and still expensive ($2,256/1K). The LLM summarizer aggressively drops specific details. Not recommended for fact-retention use cases.

4. **The recall failures at turns 30 and 45 are likely Claude safety behavior**, not memory failures — the Wi-Fi password and bank PIN are sensitive data that Claude may decline to repeat even when provided in context.

5. **pgvector = qdrant at this scale** — no reason to add a separate Qdrant service if you already run PostgreSQL.

---

## Recommendations

| Use case | Recommended backend |
|----------|-------------------|
| Production chatbot (cost-sensitive) | **pgvector** or **qdrant** |
| Short conversations (< 15 turns) | **buffer** (simplest, recall is perfect) |
| Already running PostgreSQL | **pgvector** (zero extra infra) |
| High-scale vector search (millions of vectors) | **qdrant** (purpose-built) |
| NOT recommended | **summary** (lossy, slow, expensive) |
