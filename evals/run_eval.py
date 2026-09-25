"""RAG eval harness: retrieval recall@k + answer keyword faithfulness.

Usage:
    python evals/run_eval.py --api http://localhost:8000 --set evals/golden_set.json

Each golden item:
    {
      "question": "...",
      "retrieval_keywords": ["phrase that should appear in a retrieved chunk"],
      "must_contain": ["fact that should appear in the answer"]
    }

These are smoke tests, not a full eval suite. When the numbers look good,
graduate to LLM-as-judge faithfulness scoring (see README roadmap).
"""

import argparse
import json

import requests


def run(api: str, items: list[dict], top_k: int, rerank: bool) -> dict:
    retrieval_hits = 0
    answer_hits = 0
    per_item = []

    for item in items:
        resp = requests.post(
            f"{api}/query",
            json={"question": item["question"], "top_k": top_k, "rerank": rerank},
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()

        chunk_texts = " ".join(c["text"].lower() for c in data["citations"])
        ret_hit = any(kw.lower() in chunk_texts for kw in item["retrieval_keywords"])
        ans_hit = all(kw.lower() in data["answer"].lower() for kw in item["must_contain"])

        retrieval_hits += ret_hit
        answer_hits += ans_hit
        per_item.append(
            {
                "question": item["question"],
                "retrieval_hit": ret_hit,
                "answer_hit": ans_hit,
                "answer_preview": data["answer"][:160],
            }
        )

    n = len(items)
    return {
        "n": n,
        "top_k": top_k,
        "rerank": rerank,
        "retrieval_recall@k": round(retrieval_hits / n, 3) if n else 0,
        "answer_keyword_faithfulness": round(answer_hits / n, 3) if n else 0,
        "items": per_item,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default="http://localhost:8000")
    ap.add_argument("--set", default="evals/golden_set.json")
    ap.add_argument("--top-k", type=int, default=5)
    ap.add_argument("--no-rerank", action="store_true")
    args = ap.parse_args()

    with open(args.set) as f:
        items = json.load(f)
    result = run(args.api, items, args.top_k, rerank=not args.no_rerank)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
