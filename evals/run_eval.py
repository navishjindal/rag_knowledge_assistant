"""RAG eval harness: retrieval recall@k + LLM-as-judge faithfulness.

Usage:
    python evals/run_eval.py --api http://localhost:8000 --set evals/golden_set.json

Each golden item:
    {
      "question": "...",
      "retrieval_keywords": ["phrase that should appear in a retrieved chunk"],
      "must_contain": ["fact that should appear in the answer"]
    }

Supports two faithfulness modes:
  - keyword (default legacy): checks if answer contains expected keywords
  - llm-judge: calls the LLM-as-judge from the /query response
"""

import argparse
import json

import requests


def run(
    api: str,
    items: list[dict],
    top_k: int,
    rerank: bool,
    token: str | None = None,
    mode: str = "llm-judge",
) -> dict:
    retrieval_hits = 0
    keyword_hits = 0
    llm_judge_scores = []
    per_item = []

    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    for item in items:
        for attempt in range(5):
            try:
                resp = requests.post(
                    f"{api}/query",
                    json={
                        "question": item["question"],
                        "top_k": top_k,
                        "rerank": rerank,
                    },
                    headers=headers,
                    timeout=120,
                )
                resp.raise_for_status()
                break
            except requests.exceptions.HTTPError:
                if attempt < 4:
                    import time

                    time.sleep(5 + (2**attempt))
                else:
                    raise
        import time

        time.sleep(2)
        data = resp.json()

        chunk_texts = " ".join(c["text"].lower() for c in data["citations"])
        ret_hit = any(
            kw.lower() in chunk_texts for kw in item["retrieval_keywords"]
        )
        kw_hit = all(
            kw.lower() in data["answer"].lower() for kw in item["must_contain"]
        )

        retrieval_hits += ret_hit
        keyword_hits += kw_hit

        # LLM-as-judge score (returned by the API now)
        faithfulness = data.get("faithfulness", {})
        judge_score = faithfulness.get("faithfulness_score", -1)
        if judge_score >= 0:
            llm_judge_scores.append(judge_score)

        result_item = {
            "question": item["question"],
            "retrieval_hit": ret_hit,
            "keyword_hit": kw_hit,
            "answer_preview": data["answer"][:160],
        }

        if mode == "llm-judge" and judge_score >= 0:
            result_item["llm_judge_score"] = judge_score
            result_item["judge_reasoning"] = faithfulness.get("reasoning", "")
            result_item["citation_verdicts"] = faithfulness.get(
                "citation_verdicts", []
            )

        per_item.append(result_item)

    n = len(items)
    result = {
        "n": n,
        "top_k": top_k,
        "rerank": rerank,
        "mode": mode,
        "retrieval_recall@k": round(retrieval_hits / n, 3) if n else 0,
        "keyword_faithfulness": round(keyword_hits / n, 3) if n else 0,
        "items": per_item,
    }

    if llm_judge_scores:
        avg = sum(llm_judge_scores) / len(llm_judge_scores)
        result["llm_judge_faithfulness"] = round(avg, 3)
        result["llm_judge_items_scored"] = len(llm_judge_scores)

    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default="http://localhost:8000")
    ap.add_argument("--set", default="evals/golden_set.json")
    ap.add_argument("--top-k", type=int, default=5)
    ap.add_argument("--no-rerank", action="store_true")
    ap.add_argument(
        "--token",
        help="JWT auth token (required if auth is enabled)",
        default=None,
    )
    ap.add_argument(
        "--mode",
        choices=["keyword", "llm-judge"],
        default="llm-judge",
        help="Faithfulness scoring mode",
    )
    args = ap.parse_args()

    with open(args.set) as f:
        items = json.load(f)
    result = run(
        args.api,
        items,
        args.top_k,
        rerank=not args.no_rerank,
        token=args.token,
        mode=args.mode,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
