# Agent Memory Showdown — Smoke Test Results

**Run date:** April 17, 2026
**Infrastructure:** DigitalOcean Droplet (8GB RAM / 4 vCPU, Ubuntu 24.04, BLR1 region)
**LLM:** Claude 4.5 Sonnet via DO Serverless Inference (`anthropic-claude-4.5-sonnet`)
**Embeddings:** Local sentence-transformers (`all-MiniLM-L6-v2`, 384-dim, CPU)

## Test Configuration

| Parameter | Value |
|-----------|-------|
| Backends tested | `buffer`, `summary` |
| Runs per backend | 2 |
| Turns per run | 10 |
| Seed turns | 1, 3, 7 (only 3 of 10 facts within the 10-turn window) |
| Recall probe turns | None triggered (probes are at turns 15, 25, 35, 50 — all beyond 10 turns) |

> **Note:** This was a quick smoke test to validate end-to-end functionality. The Qdrant and pgvector backends were not included. Recall accuracy was not measured because the conversation was too short to reach any probe turns.

---

## Results Summary

| Metric | Buffer | Summary |
|--------|--------|---------|
| Valid runs | 2 | 2 |
| Avg latency per turn | 8,562 ms | 17,443 ms |
| Std dev latency | 2,461 ms | 7,707 ms |
| Avg tokens per run | 16,819 | 24,020 |
| Std dev tokens | 161 | 182 |
| Est. cost / 1K conversations | $100.91 | $144.12 |

---

## Latency Per Turn

### Buffer Backend

| Turn | Avg Latency (ms) |
|------|------------------|
| 1 | 3,136 |
| 2 | 7,996 |
| 3 | 6,382 |
| 4 | 9,361 |
| 5 | 11,781 |
| 6 | 9,627 |
| 7 | 7,776 |
| 8 | 9,273 |
| 9 | 9,826 |
| 10 | 10,465 |

**Trend:** Latency generally increases as the conversation history grows (more tokens sent to the LLM each turn). Turn 1 is fastest (3.1s) since there's minimal history; turn 5 peaks at 11.8s.

### Summary Backend

| Turn | Avg Latency (ms) |
|------|------------------|
| 1 | 6,131 |
| 2 | 12,433 |
| 3 | 9,536 |
| 4 | 14,272 |
| 5 | 15,582 |
| 6 | 16,891 |
| 7 | 18,217 |
| 8 | 24,806 |
| 9 | 24,941 |
| 10 | 31,624 |

**Trend:** Much steeper latency increase. The summary backend makes *extra LLM calls* each turn to compress the conversation summary, roughly doubling the per-turn time. By turn 10, it's 31.6s per turn vs. buffer's 10.5s.

---

## Cost Comparison

| Backend | Avg Tokens/Run | Est. Cost / 1K Conversations (USD) |
|---------|---------------|-------------------------------------|
| buffer | 16,819 | $100.91 |
| summary | 24,020 | $144.12 |

> Cost estimated using Claude 3.5 Sonnet blended rate: 75% input at $0.003/1K tokens + 25% output at $0.015/1K tokens.

**Surprising finding:** Summary uses *more* tokens than buffer in this short test — the summarization LLM calls add overhead that doesn't pay off until conversations are much longer (where buffer's full-history approach would send far more tokens).

---

## Recall Accuracy

**Not measured** — all recall probe turns (15, 25, 35, 50) are beyond the 10-turn conversation length. This is the primary reason a longer test (20+ turns) is needed.

---

## Key Takeaways from Smoke Test

1. **End-to-end pipeline works:** Claude via DO Serverless Inference responds correctly, token counting works, results are saved and visualized.
2. **Buffer is faster than summary** at short conversation lengths — summary's extra summarization calls add significant overhead.
3. **Summary is more expensive at short lengths** — the summarization overhead isn't amortized yet.
4. **Need longer conversations** to see the real story: buffer cost explosion at 50 turns, summary's cost advantage, and vector backends' flat latency/recall curves.
5. **Need Qdrant + pgvector backends** to complete the benchmark — they were not included in this smoke test.

---

## What a Full Benchmark Run Would Show

| What we expect | Buffer | Summary | Qdrant | pgvector |
|---------------|--------|---------|--------|----------|
| Recall at turn 15 | High | Medium | High | High |
| Recall at turn 50 | Low (context overflow) | Low (facts summarized away) | High (semantic search) | High (semantic search) |
| Latency trend | Grows linearly | Grows steeply | Nearly flat | Nearly flat |
| Token cost | Highest | Medium | Lowest | Lowest |

---

## Raw JSON

```json
{
  "buffer": {
    "num_valid_runs": 2,
    "avg_latency_ms": 8562.32,
    "std_latency_ms": 2460.78,
    "avg_latency_per_turn": {
      "1": 3135.82, "2": 7995.51, "3": 6382.41, "4": 9360.92,
      "5": 11781.0, "6": 9627.02, "7": 7776.49, "8": 9272.94,
      "9": 9826.09, "10": 10465.01
    },
    "recall_accuracy_by_probe_turn": {},
    "avg_tokens_per_run": 16818.5,
    "std_tokens_per_run": 160.5,
    "estimated_cost_per_1k_conversations_usd": 100.911
  },
  "summary": {
    "num_valid_runs": 2,
    "avg_latency_ms": 17443.22,
    "std_latency_ms": 7707.22,
    "avg_latency_per_turn": {
      "1": 6131.12, "2": 12433.36, "3": 9535.64, "4": 14272.24,
      "5": 15581.75, "6": 16890.58, "7": 18216.89, "8": 24806.07,
      "9": 24940.65, "10": 31623.92
    },
    "recall_accuracy_by_probe_turn": {},
    "avg_tokens_per_run": 24020.0,
    "std_tokens_per_run": 182.0,
    "estimated_cost_per_1k_conversations_usd": 144.12
  }
}
```

---

## Next Steps

- [ ] Run **1 run, 20 turns, all 4 backends** to validate recall probing + vector backends
- [ ] Run **full benchmark: 5 runs, 50 turns, all 4 backends** (~2.5 hours) for the complete write-up
- [ ] Generate final visualizations (memory decay curve, latency bar chart, cost table)
