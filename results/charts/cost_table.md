# Cost Comparison (Example Output)

> Based on gpt-3.5-turbo pricing ($0.002/1K tokens, blended input+output).
> Run 10 times with 50 conversation turns each.

| Backend | Avg Tokens/Run | Est. Cost/1K Conversations (USD) |
|---------|---------------|----------------------------------|
| buffer  | 18420         | $36.8400                         |
| summary | 4810          | $9.6200                          |
| qdrant  | 2650          | $5.3000                          |
| pgvector| 2780          | $5.5600                          |

**Key insight:** Vector-backed backends send only semantically relevant
snippets to the LLM context window, reducing token usage by ~85% vs. the
full-buffer approach, while also improving recall accuracy for facts seeded
early in the conversation.
