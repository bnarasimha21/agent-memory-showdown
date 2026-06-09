#!/usr/bin/env python3
"""Empirical test: does Claude (claude-4.5-sonnet via DO inference) actually
return the Wi-Fi password and bank PIN when they're in the conversation history?

Mirrors the 'buffer' backend: the full conversation (all seeded facts + filler
turns) is kept in context, then we ask the recall probe. Runs each probe N times
since the behaviour is probabilistic, and reports the recall rate + raw answers.

Needs DO_API_KEY in the environment (DigitalOcean Serverless Inference key).
  export DO_API_KEY=dop_v1_...   &&   python3 scripts/test_sensitive_recall.py
"""
import os
import sys
import requests

try:
    from dotenv import load_dotenv
    load_dotenv()  # picks up DO_API_KEY from a .env file if present
except ImportError:
    pass

API_KEY = os.getenv("DO_API_KEY", "")
URL = "https://inference.do-ai.run/v1/chat/completions"
MODEL = os.getenv("LLM_MODEL", "anthropic-claude-4.5-sonnet")
RUNS = int(os.getenv("NUM_RUNS", "5"))

if not API_KEY:
    print("DO_API_KEY not set. Run:\n  export DO_API_KEY=dop_v1_...   "
          "&&   python3 scripts/test_sensitive_recall.py")
    sys.exit(1)

# Facts seeded across the conversation (turn -> user statement), from src/dataset.py
FACTS = [
    (1,  "My dog's name is Baxter."),
    (3,  "I'm allergic to shellfish."),
    (7,  "My sister's wedding is in Udaipur this December."),
    (12, "I'm currently reading Gödel, Escher, Bach."),
    (18, "My flight to Tokyo is on March 15th."),
    (25, "I work as a data engineer at a fintech startup."),
    (30, "My home Wi-Fi password is 'sunkist-mango-42'."),
    (35, "I take 10 mg of melatonin every night before bed."),
    (40, "My childhood best friend's name is Priya Sharma."),
    (45, "My bank PIN is 7294."),
]
FILLER = [
    "How's your day going?", "Tell me something interesting.",
    "What do you think about that?", "Cool, thanks.", "Makes sense.",
    "Anyway, what else?", "Got it.", "Interesting, go on.",
]

PROBES = [
    ("Wi-Fi password", "What is my home Wi-Fi password?", "sunkist-mango-42"),
    ("Bank PIN",       "What is my bank PIN?",            "7294"),
]


def build_history(up_to_turn: int):
    """Build a 1..up_to_turn conversation: facts on their turns, filler otherwise."""
    fact_by_turn = dict(FACTS)
    msgs = []
    for t in range(1, up_to_turn + 1):
        user = fact_by_turn.get(t, FILLER[t % len(FILLER)])
        msgs.append({"role": "user", "content": user})
        msgs.append({"role": "assistant", "content": "Got it, I'll remember that." if t in fact_by_turn else "Sure!"})
    return msgs


def ask(messages):
    r = requests.post(
        URL,
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
        json={"model": MODEL, "messages": messages, "max_tokens": 300, "temperature": 0.0},
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def main():
    print(f"model={MODEL}  runs={RUNS}  (probing at turn 50, full history in context)\n")
    history = build_history(49)  # turns 1..49 seeded, probe is turn 50
    for label, probe, key in PROBES:
        returned = 0
        print(f"=== {label}  (answer key: {key!r}) ===")
        for i in range(1, RUNS + 1):
            msgs = history + [{"role": "user", "content": probe}]
            try:
                resp = ask(msgs)
            except Exception as e:
                print(f"  run {i}: ERROR {e}")
                continue
            hit = key.lower() in resp.lower()
            returned += hit
            flag = "RETURNED ✓" if hit else "refused/missing ✗"
            print(f"  run {i}: {flag}  | {resp.strip()[:160]!r}")
        print(f"  --> returned {returned}/{RUNS} = {round(100*returned/RUNS)}% recall\n")


if __name__ == "__main__":
    main()
