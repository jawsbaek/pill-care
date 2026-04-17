"""Embedding-similarity intent classifier for paraphrase-bypass defense.

Part of the 5-layer guardrail (Layer 5): defends against cases where a
paraphrase slips past the banned-words regex filter (e.g. "복용량을
절반으로 줄이시는 것이 좋겠습니다" vs. the literal "복용량을 변경").
Each section's content is embedded with KURE-v1 (Korean retrieval SOTA
per Ko-MTEB 2025) and compared against exemplar forbidden-intent
sentences; if the max cosine similarity to any exemplar is at or above
the threshold (0.70), the section is flagged.

Fails open: if the KURE-v1 model cannot be loaded (e.g. environments
without the HF cache warmed via ``scripts/download_kure_model.py``),
``classify_intent`` logs a warning once and returns ``'allowed'`` for
every input so the pipeline still runs. The other four guardrail
layers (banned-words regex, source-tier enforcement, DUR coverage,
closing-phrase / min-section checks) remain active.
"""

from __future__ import annotations

import logging
from functools import lru_cache

import numpy as np

logger = logging.getLogger(__name__)

# Exemplars of clinician-like intents the POC must *never* produce.
#
# Two design notes:
#
# 1. Sentence-form, not noun-phrase. KURE-v1 is a sentence-level encoder;
#    empirically, bare noun-phrase exemplars ("진단 의견을 제시") give a
#    neutral-vs-forbidden gap of only ~0.1, too narrow to threshold.
#    Full sentences push forbidden paraphrases to ~0.76-0.92 while
#    keeping neutral drug-info sentences under 0.66.
#
# 2. Dose-change exemplars are anchored to an existing regimen ("현재
#    복용량을 …", "기존 복용량을 …"). A naive exemplar like "복용량을
#    늘리세요" collides in embedding space with a standard approved-label
#    dosage ("1회 1캡슐, 1일 3회 식후 복용하십시오") because both talk
#    about amount/frequency. The "change relative to current" framing
#    separates "here's a clinician telling you to alter your regimen"
#    from "here's the label's standing dosing instruction".
FORBIDDEN_INTENTS: tuple[str, ...] = (
    "당신은 이 병으로 진단됩니다.",
    "당신의 증상은 이 질환에 해당합니다.",
    "이 약을 처방해 드리겠습니다.",
    "현재 복용량을 절반으로 줄이세요.",
    "지금 복용하는 양보다 더 많이 드세요.",
    "기존 복용량을 변경하시기 바랍니다.",
    "다른 약으로 바꾸시기 바랍니다.",
    "이 치료 방법을 받으시기 바랍니다.",
    "이 병을 확진합니다.",
)

SIMILARITY_THRESHOLD = 0.70

_KURE_MODEL_ID = "nlpai-lab/KURE-v1"


@lru_cache(maxsize=1)
def _load_embedder():
    """Load KURE-v1 or return ``None`` on any failure (fail-open)."""
    try:
        from sentence_transformers import (  # type: ignore[import-not-found]
            SentenceTransformer,
        )

        return SentenceTransformer(_KURE_MODEL_ID)
    except Exception as e:  # noqa: BLE001 — fail-open on any load error
        logger.warning(
            "Intent classifier disabled: KURE-v1 load failed (%s). "
            "Run `uv run python scripts/download_kure_model.py` to enable.",
            type(e).__name__,
        )
        return None


@lru_cache(maxsize=1024)
def _embed(text: str) -> np.ndarray | None:
    """Return a unit-norm embedding for ``text`` or ``None`` when the
    embedder is unavailable.

    Cached so repeated encoding of the fixed FORBIDDEN_INTENTS pool is
    free, and so identical section content across retries isn't
    re-embedded.
    """
    embedder = _load_embedder()
    if embedder is None:
        return None
    emb = embedder.encode(text, normalize_embeddings=True)
    return np.asarray(emb, dtype=np.float32)


def classify_intent(text: str) -> str:
    """Return ``'forbidden'`` or ``'allowed'``.

    ``'forbidden'`` iff the maximum cosine similarity between ``text``
    and any entry in ``FORBIDDEN_INTENTS`` is >= ``SIMILARITY_THRESHOLD``.
    Empty / whitespace-only text short-circuits to ``'allowed'``.  If
    the KURE-v1 embedder is unavailable, classification fails open and
    returns ``'allowed'`` (see module docstring).
    """
    if not text.strip():
        return "allowed"
    if _load_embedder() is None:
        return "allowed"  # fail-open — model unavailable
    query = _embed(text)
    if query is None:
        return "allowed"  # defensive — should not happen once embedder loads
    sims: list[float] = []
    for intent in FORBIDDEN_INTENTS:
        intent_emb = _embed(intent)
        if intent_emb is None:
            return "allowed"
        sims.append(float(np.dot(query, intent_emb)))
    if sims and max(sims) >= SIMILARITY_THRESHOLD:
        return "forbidden"
    return "allowed"
