# Cost Comparison — Full Benchmark

> Claude 4.5 Sonnet via DO Serverless Inference.
> Blended rate: 75% input @ $0.003/1K tokens + 25% output @ $0.015/1K tokens.
> 5 runs × 50 turns per backend.

| Backend  | Avg Tokens/Run | Est. Cost / 1K Conversations (USD) |
|----------|---------------|-------------------------------------|
| buffer   | 717,200       | $4,303.20                           |
| summary  | 375,926       | $2,255.56                           |
| qdrant   | 69,595        | $417.57                             |
| pgvector | 69,366        | $416.19                             |

**Key insight:** Vector-backed backends (qdrant, pgvector) send only the 4 most
semantically relevant snippets to Claude each turn, reducing token usage by
**90%** vs. the full-buffer approach while maintaining 82% recall accuracy at
turn 50. Summary is not only lossy (42% recall) but also expensive due to
extra LLM calls for summarization each turn.
