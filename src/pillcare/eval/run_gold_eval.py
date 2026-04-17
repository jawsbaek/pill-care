"""CLI: run pipeline on guidance gold set, compute RAGAS metrics.

Usage:
    uv run python -m pillcare.eval.run_gold_eval --threshold-faith 0.80
"""

from __future__ import annotations

import argparse
import json
import sys

from pillcare.eval.gold_set import load_guidance_gold
from pillcare.eval.ragas_eval import (
    DEFAULT_THRESHOLDS,
    evaluate_responses,
    passes_thresholds,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--threshold-faith", type=float, default=DEFAULT_THRESHOLDS["faithfulness"]
    )
    parser.add_argument(
        "--threshold-cp", type=float, default=DEFAULT_THRESHOLDS["context_precision"]
    )
    parser.add_argument(
        "--threshold-ar", type=float, default=DEFAULT_THRESHOLDS["answer_relevancy"]
    )
    parser.add_argument("--max-cases", type=int, default=0, help="0 = all")
    args = parser.parse_args()

    gold = load_guidance_gold()
    if not gold:
        print("ERROR: guidance gold set empty or missing", file=sys.stderr)
        return 1

    if args.max_cases > 0:
        gold = gold[: args.max_cases]

    # Pipeline invocation deferred: for now run a stub dataset.
    # TODO(A5/A6 integration): build responses from run_pipeline outputs
    responses: list[dict] = []
    for case in gold:
        responses.append(
            {
                "question": case["context"] or f"복약 안내: {case['drug_name']}",
                "answer": "",  # placeholder — wire run_pipeline in follow-up
                "contexts": [],
                "ground_truth": "",
            }
        )

    metrics = evaluate_responses(responses)
    passed, failures = passes_thresholds(
        metrics,
        {
            "faithfulness": args.threshold_faith,
            "context_precision": args.threshold_cp,
            "answer_relevancy": args.threshold_ar,
        },
    )

    print(json.dumps(metrics, indent=2, ensure_ascii=False))
    if not passed:
        print("FAIL:", failures, file=sys.stderr)
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
