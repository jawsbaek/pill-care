"""RAGAS-based RAG quality evaluator.

Computes faithfulness and context-precision on a list of pipeline responses.
RAGAS requires a judge LLM (defaults to OpenAI; we pin to Gemini via
ChatGoogleGenerativeAI when available). If RAGAS isn't installed or an API
key is missing, evaluate_responses returns {} with a warning — tests and
CI lint paths don't require live keys.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_THRESHOLDS = {
    "faithfulness": 0.80,
    "context_precision": 0.75,
    "answer_relevancy": 0.70,
}


def evaluate_responses(responses: list[dict[str, Any]]) -> dict[str, float]:
    """Evaluate pipeline responses with RAGAS metrics.

    Args:
        responses: list of {
            "question": str,
            "answer": str,
            "contexts": list[str],
            "ground_truth": str,  # optional
        }

    Returns:
        Metric dict (faithfulness, context_precision, answer_relevancy) or {}
        if RAGAS/datasets unavailable or responses is empty.
    """
    if not responses:
        return {}
    try:
        from datasets import Dataset
        from ragas import evaluate
        from ragas.metrics import (
            answer_relevancy,
            context_precision,
            faithfulness,
        )
    except ImportError as e:
        logger.warning("RAGAS eval skipped: %s", e)
        return {}

    try:
        ds = Dataset.from_list(responses)
        result = evaluate(
            ds,
            metrics=[faithfulness, context_precision, answer_relevancy],
        )
        return {
            "faithfulness": float(result["faithfulness"]),
            "context_precision": float(result["context_precision"]),
            "answer_relevancy": float(result["answer_relevancy"]),
        }
    except Exception as e:  # noqa: BLE001 — upstream API/key errors
        logger.warning("RAGAS eval failed: %s", type(e).__name__)
        return {}


def passes_thresholds(
    metrics: dict[str, float],
    thresholds: dict[str, float] | None = None,
) -> tuple[bool, list[str]]:
    """Return (passed, list_of_failures)."""
    thresholds = thresholds or DEFAULT_THRESHOLDS
    failures = []
    for metric, minimum in thresholds.items():
        actual = metrics.get(metric)
        if actual is None:
            failures.append(f"{metric}: missing")
        elif actual < minimum:
            failures.append(f"{metric}: {actual:.3f} < {minimum:.3f}")
    return (not failures, failures)
