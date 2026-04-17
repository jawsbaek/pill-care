"""One-time script: prefetch KURE-v1 embedding model for intent classifier.

Usage:
    uv run python scripts/download_kure_model.py

Warms the default HuggingFace cache (``$HF_HOME`` or
``~/.cache/huggingface``) with ``nlpai-lab/KURE-v1`` so
``pillcare.intent_classifier._load_embedder`` can load the model offline
on subsequent starts. In Docker builds we set ``HF_HOME=/app/hf-cache``
so this script warms that directory, then the runtime stage copies it
and sets the same env var — zero network fetch at cold start.
"""

from __future__ import annotations

EMBED_MODEL_ID = "nlpai-lab/KURE-v1"


def main() -> None:
    from sentence_transformers import (  # type: ignore[import-not-found]
        SentenceTransformer,
    )

    SentenceTransformer(EMBED_MODEL_ID)
    print(f"KURE-v1 ({EMBED_MODEL_ID}) prefetched to HF cache")


if __name__ == "__main__":
    main()
