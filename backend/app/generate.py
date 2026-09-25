"""Grounded generation via Gemini or Groq (chosen by LLM_PROVIDER)."""

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


def build_prompt(question: str, sources: list[dict]) -> str:
    ctx = "\n\n".join(
        f"[{i + 1}] (doc: {s['doc_name']}, page {s['page'] + 1})\n{s['text']}"
        for i, s in enumerate(sources)
    )
    return f"Context:\n{ctx}\n\nQuestion: {question}\n\nAnswer (with citations):"


def generate_answer(question: str, sources: list[dict]) -> str:
    prompt = build_prompt(question, sources)
    if PROVIDER == "groq":
        return _groq(prompt)
    return _gemini(prompt)


def _gemini(prompt: str) -> str:
    key = os.environ["GEMINI_API_KEY"]
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.0-flash:generateContent?key={key}"
    )
    r = requests.post(
        url,
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2},
        },
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["candidates"][0]["content"]["parts"][0]["text"]


def _groq(prompt: str) -> str:
    key = os.environ["GROQ_API_KEY"]
    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}"},
        json={
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        },
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]
