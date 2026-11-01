from langchain_core.messages import HumanMessage

from src.fakes import FAKE_ABSTAIN_REPLY, FakeMemoryChatModel, HashingEmbeddings
from src.prompts import render_chat_prompt


def test_fake_answers_only_from_memory():
    llm = FakeMemoryChatModel()
    memory = "Human: My dog's name is Baxter.\nAI: Nice."
    reply = llm.invoke([HumanMessage(content=render_chat_prompt(memory, "What is my dog's name?"))])
    assert "Baxter" in reply.content
    empty = llm.invoke([HumanMessage(content=render_chat_prompt("", "What is my dog's name?"))])
    assert empty.content == FAKE_ABSTAIN_REPLY


def test_fake_ignores_assistant_lines_and_the_question():
    llm = FakeMemoryChatModel()
    memory = "Human: Let's talk about hiking.\nAI: My dog's name is Rex."
    reply = llm.invoke([HumanMessage(content=render_chat_prompt(memory, "What is my dog's name?"))])
    assert reply.content == FAKE_ABSTAIN_REPLY


def test_fake_reports_token_usage_and_overrides():
    reply = FakeMemoryChatModel(input_tokens=100, output_tokens=7).invoke("hello there")
    assert reply.usage_metadata == {"input_tokens": 100, "output_tokens": 7, "total_tokens": 107}
    counted = FakeMemoryChatModel().invoke("one two three")
    assert counted.usage_metadata["input_tokens"] == 3


def test_fake_summary_is_lossy_and_keeps_recent_statements():
    llm = FakeMemoryChatModel(summary_max_sentences=2)
    prompt = (
        "Current summary:\nMy dog's name is Baxter. I'm allergic to shellfish.\n\n"
        "New lines of conversation:\nHuman: My flight is on March 15th. What now?\nAI: ok\n\n"
        "New summary:"
    )
    out = llm.invoke(prompt).content
    assert out == "I'm allergic to shellfish. My flight is on March 15th."


def test_hashing_embeddings_are_deterministic_and_normalised():
    emb = HashingEmbeddings(384)
    a, b = emb.embed_query("My dog's name is Baxter"), emb.embed_query("My dog's name is Baxter")
    assert a == b and len(a) == 384
    assert abs(sum(v * v for v in a) - 1.0) < 1e-9
    near = emb.embed_query("What is my dog's name?")
    far = emb.embed_query("Let's talk about pasta recipes")
    dot = lambda x, y: sum(i * j for i, j in zip(x, y))  # noqa: E731
    assert dot(a, near) > dot(a, far)
