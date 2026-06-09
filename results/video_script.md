# Agent Memory Showdown: Video Script

**Estimated length:** 8–10 minutes
**Tone:** Technical but accessible, data-driven storytelling
**Target audience:** AI engineers, LangChain developers, backend architects

---

## SCENE 1: The Hook (0:00 – 0:45)

**[VISUAL: Quick montage of chatbot UIs, then a user typing "What's my dog's name?" and getting a blank stare from the bot]**

**NARRATION:**

> Most chatbots can't remember what you said five minutes ago.

> You tell it your dog's name is Baxter. You tell it you're allergic to shellfish. You share your flight details. And twenty turns later? It's forgotten everything.

> The question isn't whether memory matters. It's *which* memory architecture actually works. So I built a benchmark to find out.

> This is the Agent Memory Showdown.

---

## SCENE 2: The Problem (0:45 – 1:45)

**[VISUAL: Simple diagram showing a user ↔ LLM conversation with a growing chat history. Animate the context window filling up and overflowing.]**

**NARRATION:**

> For this experiment, I'm using LangChain.

> LangChain gives you four ways to handle conversation memory. Each makes a different trade-off between recall, speed, and cost.

> **Buffer Memory:** the naive approach. Just pass the entire conversation history into the prompt. Works great until your context window explodes and your API bill goes through the roof.

> **Summary Memory:** an LLM compresses the conversation into a running summary after every turn. Sounds clever. But what happens when the summarizer decides your flight date isn't worth keeping?

> **Vector Memory with Qdrant:** embed every message into a vector database. At query time, pull back only the most semantically relevant snippets. Surgical, efficient.

> **Vector Memory with pgvector:** same idea, but using PostgreSQL with the pgvector extension instead of a dedicated vector database. One less service to manage.

> The question: when you push these to 50 turns with 10 planted facts, who survives?

---

## SCENE 3: The Setup (1:45 – 3:00)

**[VISUAL: Architecture diagram from README, animating data flow from config → harness → backends → LLM → results. Show the DO Droplet, Qdrant container, and PostgreSQL.]**

**NARRATION:**

> Here's how the benchmark works.

> I spun up a DigitalOcean Droplet: 8 gigs of RAM, 4 vCPUs, Ubuntu 24.04, running in Bangalore. On it: a Qdrant container and PostgreSQL 16 with the pgvector extension.

> The LLM is Claude 4.5 Sonnet, accessed through DigitalOcean's Serverless Inference API. Embeddings are computed locally using sentence-transformers: the all-MiniLM-L6-v2 model, 384 dimensions.

> The benchmark generates a synthetic 50-turn conversation. It covers travel planning, tech preferences, personal details, work projects, normal chatbot territory.

> But hidden inside the conversation are 10 specific facts, planted at precise turns.

**[VISUAL: Timeline showing turns 1–50 with fact markers at turns 1, 3, 7, 12, 18, 25, 30, 35, 40, 45. Highlight each fact as it's mentioned.]**

> Turn 1: "My dog's name is Baxter."
> Turn 3: "I'm allergic to shellfish."
> Turn 7: "My flight to Tokyo is March 15th."
> Turn 12: "Project deadline is April 30th."
> Turn 18: "My sister's wedding is in Lake Como."
> Turn 25: "I'm reading Gödel, Escher, Bach."
> Turn 30: "My Wi-Fi password is sunkist-mango-42."
> Turn 35: "I take 10 mg of melatonin before bed."
> Turn 40: "My childhood best friend is Priya Sharma."
> Turn 45: "My bank PIN is 7294."

> At turns 15 and 50, the benchmark pauses and quizzes the AI on every fact it should know. This builds the **memory decay curve**: how much does each backend forget over time?

> Each backend runs 5 times for statistical reliability. That's 4 backends × 5 runs × 50 turns = 1,000 LLM calls minimum.

---

## SCENE 4: The Results: Recall Accuracy (3:00 – 4:45)

**[VISUAL: Show `memory_decay_curve.png`, animating lines drawing from turn 15 to turn 50]**

**NARRATION:**

> Let's start with the most important metric. Can it remember?

> At turn 15, all four backends achieve **100% recall**. Only 4 facts have been planted, they're recent, and the conversation is short. No challenge here.

> But at turn 50, after 10 facts spread across the full conversation, the story changes dramatically.

**[VISUAL: Animate the numbers appearing in a scoreboard]**

> **Buffer: 90%.** Nearly perfect. It has the entire conversation in its prompt, so of course it remembers. The only failures are on the Wi-Fi password and bank PIN. And we'll come back to this later.

> **Qdrant and pgvector: 82%.** Solid performance. The vector search finds the relevant snippets most of the time.

> And then... **Summary: 42%.** Less than half.

**[VISUAL: Show `recall_by_seed_turn.png`, the grouped bar chart]**

> Look at this breakdown. Summary remembers facts from turns 1 through 12 perfectly. But everything after turn 18? Zero. The summarizer compressed away your sister's wedding location, the book you're reading, your supplement dosage. All gone.

> The summary backend doesn't just forget old things. It **actively destroys new information** as it compresses.

---

## SCENE 5: The Results: Latency (4:45 – 6:00)

**[VISUAL: Show `latency_per_turn.png`, the line chart. Animate each backend's line drawing across turns.]**

**NARRATION:**

> Now let's talk speed. This chart shows latency per turn across the full conversation.

> **Qdrant and pgvector** stay flat, around 7 seconds per turn regardless of conversation length. They only retrieve the top-K relevant snippets, so prompt size stays constant.

> **Buffer** starts at 3 seconds but climbs to 12+ seconds by turn 30 as the entire conversation history grows in the prompt.

> But look at **Summary**. It starts at 9 seconds and rockets to 50 seconds per turn by turn 20. Why? Because every single turn requires *two* LLM calls: one to respond, and one to update the running summary. That doubles the latency *and* the summary itself keeps growing.

**[VISUAL: Show `latency_bar.png`, the bar chart with error bars]**

> On average: vector backends at 7 seconds. Buffer at 10 seconds. Summary at a whopping **36 seconds per turn**. Five times slower.

> The total wall-clock time tells the same story: qdrant and pgvector finished in 32 minutes each. Buffer took 45 minutes. Summary? **Three hours.**

---

## SCENE 6: The Results: Cost (6:00 – 7:00)

**[VISUAL: Show `cost_bar.png`, animating bars growing with dollar amounts]**

**NARRATION:**

> Here's where it gets really interesting. Let's extrapolate to 1,000 conversations.

> **Buffer: $4,303.** It sends the *entire* conversation history every turn. That's O(n²) token growth. By turn 50, you're sending 50 turns of history with every message.

> **Summary: $2,256.** Better than buffer, but the extra summarization calls eat up tokens. You're paying twice per turn.

> **Qdrant: $418. pgvector: $416.** That's a **90% cost reduction** compared to buffer. Vector backends send only 4 relevant snippets per turn, keeping token usage flat regardless of conversation length.

> Put another way: for every dollar you spend on vector memory, you'd spend ten dollars on buffer memory for the same number of conversations.

---

## SCENE 7: Qdrant vs. pgvector (7:00 – 7:45)

**[VISUAL: Side-by-side comparison table animating each metric]**

**NARRATION:**

> The elephant in the room: does it matter which vector database you choose?

> At this scale? **No.**

> Qdrant: 7,001 ms latency. pgvector: 7,021 ms. Recall? Both 82%. Cost? $418 vs $416. Tokens per run? Nearly identical.

> If you already run PostgreSQL (and most production systems do), just add the pgvector extension. Zero extra infrastructure, zero extra operational burden.

> If you're building a system that needs to scale to millions of vectors across many users, then Qdrant's purpose-built architecture may give you an edge. But for per-session conversational memory? pgvector is the pragmatic choice.

---

## SCENE 8: The Surprise Finding (7:45 – 8:30)

**[VISUAL: Highlight the sensitive data recall failures in the breakdown chart at turns 30 and 45]**

**NARRATION:**

> There's one finding I didn't expect.

> Every backend, including buffer, which has the data right there in the prompt, failed to recall the Wi-Fi password and bank PIN at turn 50.

> This isn't a memory problem. It's a **safety behavior**. Claude recognizes sensitive data like passwords and PINs and declines to repeat them, even when they're explicitly provided in the conversation history.

> This matters for benchmark design. If you're evaluating memory backends and your test facts include sensitive data, you'll get misleading recall scores. The failure isn't in the memory. It's in the LLM's safety layer.

---

## SCENE 9: Recommendations (8:30 – 9:15)

**[VISUAL: Decision flowchart animating based on use case]**

**NARRATION:**

> So what should you actually use?

> **For production chatbots where cost matters** (and it almost always does), use pgvector or Qdrant. 82% recall at one-tenth the cost of buffer memory.

> **For short conversations under 15 turns,** buffer is fine. It's the simplest to implement, recall is perfect, and the cost hasn't had time to explode.

> **If you already run PostgreSQL,** pgvector. No contest. Add the extension, done.

> **If you need to scale vector search to millions of vectors,** Qdrant. It's purpose-built for that.

> And **summary memory?** I'd skip it. It's the slowest, the most expensive after buffer, and it destroys the specific details your users shared. A 42% recall rate at turn 50 means it's forgotten more than it remembers.

---

## SCENE 10: Closing (9:15 – 9:45)

**[VISUAL: GitHub repo link, the architecture diagram, and the five benchmark charts in a grid]**

**NARRATION:**

> That's the Agent Memory Showdown. Four LangChain memory backends, 1,000 LLM calls, five hours of benchmarking on a $48/month DigitalOcean Droplet.

> The full code, raw results, and all charts are open-source on GitHub. Link in the description.

> If you're building AI agents and haven't benchmarked your memory backend, you're guessing. The difference between the best and worst choice here is 10x cost, 5x latency, and 2x recall accuracy.

> Don't guess. Measure.

---

## APPENDIX: Visual Assets Needed

| Timestamp | Visual | Source |
|-----------|--------|--------|
| 0:00 | Chatbot montage | Stock footage / screen recording |
| 0:45 | Context window overflow animation | Motion graphics |
| 1:45 | Architecture diagram (animated) | `README.md` mermaid diagram |
| 3:00 | Fact timeline (turns 1–50) | Custom animation |
| 3:00 | `memory_decay_curve.png` | `results/charts/` |
| 4:00 | `recall_by_seed_turn.png` | `results/charts/` |
| 4:45 | `latency_per_turn.png` | `results/charts/` |
| 5:30 | `latency_bar.png` | `results/charts/` |
| 6:00 | `cost_bar.png` | `results/charts/` |
| 7:00 | Qdrant vs pgvector comparison table | Custom graphic |
| 7:45 | Sensitive data highlight | Annotated `recall_by_seed_turn.png` |
| 8:30 | Decision flowchart | Custom graphic |
| 9:15 | GitHub repo + charts grid | Screen capture |

## Key Numbers for On-Screen Graphics

| Metric | Buffer | Summary | Qdrant | pgvector |
|--------|--------|---------|--------|----------|
| Recall @ Turn 50 | 90% | 42% | 82% | 82% |
| Avg Latency/Turn | 10.3s | 36.0s | 7.0s | 7.0s |
| Cost / 1K Convos | $4,303 | $2,256 | $418 | $416 |
| Total Tokens/Run | 717K | 376K | 70K | 69K |
| Wall Clock (5 runs) | 45 min | 3 hrs | 32 min | 32 min |
