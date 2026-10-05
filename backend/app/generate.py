"""Grounded generation via Gemini or Groq (chosen by LLM_PROVIDER).

Supports both single-document Q&A and multi-document comparison prompts.
"""

import os

import requests

PROVIDER = os.getenv("LLM_PROVIDER", "gemini").lower()

SYSTEM = (
    "You answer questions using ONLY the context provided below. "
    "Cite every factual claim with [n] referring to the numbered sources. "
    "If the context does not contain the answer, say exactly: "
    "\"I don't have enough information in the provided documents.\" "
    "Do not use outside knowledge."
)

COMPARISON_SYSTEM = (
    "You are comparing information across multiple documents. "
    "Use ONLY the context provided below. "
    "Cite claims with [A1], [A2], ... for Document A sources and [B1], [B2], ... for Document B sources. "
    "Highlight similarities and differences between the documents. "
    "If the context does not contain enough information for comparison, say so explicitly. "
    "Do not use outside knowledge."
)


def build_prompt(question: str, sources: list[dict]) -> str:
    ctx = "\n\n".join(
        f"[{i + 1}] (doc: {s['doc_name']}, page {s['page'] + 1})\n{s['text']}"
        for i, s in enumerate(sources)
    )
    return f"Context:\n{ctx}\n\nQuestion: {question}\n\nAnswer (with citations):"


def build_comparison_prompt(
    question: str,
    doc_a_name: str,
    doc_a_sources: list[dict],
    doc_b_name: str,
    doc_b_sources: list[dict],
) -> str:
    """Build a prompt for comparing content across two documents."""
    ctx_a = "\n\n".join(
        f"[A{i + 1}] (page {s['page'] + 1})\n{s['text']}"
        for i, s in enumerate(doc_a_sources)
    )
    ctx_b = "\n\n".join(
        f"[B{i + 1}] (page {s['page'] + 1})\n{s['text']}"
        for i, s in enumerate(doc_b_sources)
    )
    return (
        f"Document A: \"{doc_a_name}\"\n{ctx_a}\n\n"
        f"Document B: \"{doc_b_name}\"\n{ctx_b}\n\n"
        f"Question: {question}\n\n"
        f"Compare the two documents and answer (with citations like [A1], [B2]):"
    )


def generate_answer(question: str, sources: list[dict]) -> str:
    prompt = build_prompt(question, sources)
    if PROVIDER == "groq":
        return _groq(prompt, SYSTEM)
    return _gemini(prompt)


def generate_comparison(
    question: str,
    doc_a_name: str,
    doc_a_sources: list[dict],
    doc_b_name: str,
    doc_b_sources: list[dict],
) -> str:
    """Generate a comparative answer across two documents."""
    prompt = build_comparison_prompt(
        question, doc_a_name, doc_a_sources, doc_b_name, doc_b_sources
    )
    if PROVIDER == "groq":
        return _groq(prompt, COMPARISON_SYSTEM)
    return _gemini(prompt)


def _gemini(prompt: str) -> str:
    import time

    key = os.environ["GEMINI_API_KEY"]
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-3.8-flash:generateContent?key={key}"
    )
    for attempt in range(5):
        r = requests.post(
            url,
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.2},
            },
            timeout=60,
        )
        if r.status_code == 503 and attempt < 4:
            time.sleep(2 ** attempt)
            continue
        r.raise_for_status()
        return r.json()["candidates"][0]["content"]["parts"][0]["text"]


def _groq(prompt: str, system: str = SYSTEM) -> str:
    key = os.environ["GROQ_API_KEY"]
    import time
    for attempt in range(5):
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={
                "model": "openai/gpt-oss-120b",
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.2,
            },
            timeout=60,
        )
        if r.status_code == 429 and attempt < 4:
            time.sleep(2 + (2 ** attempt))
            continue
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
