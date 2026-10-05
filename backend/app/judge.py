"""LLM-as-judge: faithfulness scoring and citation verification.

Instead of keyword matching, we ask the LLM to judge whether:
  1. The answer is faithful to the provided source passages (0–1 score).
  2. Each cited source actually supports the claim it's attached to.
"""

import json
import os
import re

import requests

PROVIDER = os.getenv("LLM_PROVIDER", "gemini").lower()

JUDGE_PROMPT = """\
You are an impartial judge evaluating a RAG (retrieval-augmented generation) system.

**Question**: {question}

**Sources provided to the system** (numbered):
{sources}

**System's answer**:
{answer}

---

Evaluate the answer and respond with **valid JSON only** (no markdown fences):

{{
  "faithfulness_score": <float 0.0–1.0: how much of the answer is supported by the sources>,
  "reasoning": "<1–2 sentence explanation>",
  "citation_verdicts": [
    {{
      "citation_number": <int>,
      "claim_in_answer": "<the specific claim that cites this source>",
      "supported": <true|false>,
      "explanation": "<why it is or isn't supported>"
    }}
  ]
}}

Rules:
- faithfulness_score = 1.0 if every claim in the answer is directly supported by the sources.
- faithfulness_score = 0.0 if the answer is entirely fabricated or contradicts the sources.
- Only evaluate citations that actually appear in the answer (e.g. [1], [2]).
- If the answer says "I don't have enough information", score 1.0 (honest refusal is faithful).
"""


def _format_sources(sources: list[dict]) -> str:
    parts = []
    for i, s in enumerate(sources):
        parts.append(
            f"[{i + 1}] (doc: {s['doc_name']}, page {s['page'] + 1})\n{s['text']}"
        )
    return "\n\n".join(parts)


def judge_answer(
    question: str, answer: str, sources: list[dict]
) -> dict:
    """Call the LLM to judge the faithfulness of an answer.

    Returns:
        {
            "faithfulness_score": float,
            "reasoning": str,
            "citation_verdicts": [
                {"citation_number": int, "claim_in_answer": str,
                 "supported": bool, "explanation": str}
            ]
        }
    """
    prompt = JUDGE_PROMPT.format(
        question=question,
        sources=_format_sources(sources),
        answer=answer,
    )

    try:
        if PROVIDER == "groq":
            raw = _groq_judge(prompt)
        else:
            raw = _gemini_judge(prompt)
        return _parse_judge_response(raw)
    except Exception:
        # Graceful fallback — don't let judge failures break the query
        return {
            "faithfulness_score": -1,
            "reasoning": "Judge evaluation failed — could not parse LLM response.",
            "citation_verdicts": [],
        }


def _parse_judge_response(raw: str) -> dict:
    """Extract JSON from the LLM judge response, tolerating markdown fences."""
    # Strip markdown code fences if present
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    cleaned = re.sub(r"\s*```$", "", cleaned)
    data = json.loads(cleaned)
    # Validate structure
    score = float(data.get("faithfulness_score", 0))
    score = max(0.0, min(1.0, score))
    return {
        "faithfulness_score": score,
        "reasoning": str(data.get("reasoning", "")),
        "citation_verdicts": data.get("citation_verdicts", []),
    }


def _gemini_judge(prompt: str) -> str:
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
                "generationConfig": {"temperature": 0.0},
            },
            timeout=60,
        )
        if r.status_code == 503 and attempt < 4:
            time.sleep(2**attempt)
            continue
        r.raise_for_status()
        return r.json()["candidates"][0]["content"]["parts"][0]["text"]


def _groq_judge(prompt: str) -> str:
    import time

    key = os.environ["GROQ_API_KEY"]
    for attempt in range(5):
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={
                "model": "openai/gpt-oss-120b",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a precise JSON-only evaluation judge.",
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.0,
            },
            timeout=60,
        )
        if r.status_code == 429 and attempt < 4:
            time.sleep(2 + (2**attempt))
            continue
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
