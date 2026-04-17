"""Intent classifier tests (Layer 5 of the 5-layer guardrail)."""

import pytest


@pytest.mark.slow
def test_intent_classifier_detects_diagnosis_intent():
    from pillcare.intent_classifier import classify_intent

    text = "당신의 증상으로 볼 때 당뇨병으로 진단됩니다."
    assert classify_intent(text) == "forbidden"


@pytest.mark.slow
def test_intent_classifier_allows_neutral_info():
    from pillcare.intent_classifier import classify_intent

    text = "이 약은 공복 복용이 권장되며, 음식과 함께 복용해도 됩니다."
    assert classify_intent(text) == "allowed"


@pytest.mark.slow
def test_intent_classifier_detects_dose_change_paraphrase():
    from pillcare.intent_classifier import classify_intent

    text = "복용량을 절반으로 줄이시는 것이 좋겠습니다."
    assert classify_intent(text) == "forbidden"


def test_intent_threshold_constant():
    from pillcare.intent_classifier import SIMILARITY_THRESHOLD

    assert SIMILARITY_THRESHOLD == 0.70


def test_empty_text_is_allowed():
    """Empty or whitespace-only text should short-circuit to 'allowed'."""
    from pillcare.intent_classifier import classify_intent

    assert classify_intent("") == "allowed"
    assert classify_intent("   ") == "allowed"


def test_intent_classifier_fail_open_when_model_missing(monkeypatch):
    """P1-3 contract: when KURE-v1 cannot load, classify_intent returns
    ``'allowed'`` for every input rather than raising.

    Covers environments where the HF cache has not been warmed via
    ``scripts/download_kure_model.py`` (or where sentence-transformers
    is entirely absent). We patch ``_load_embedder`` to simulate the
    failure mode and bypass the ``lru_cache`` that would otherwise
    pin the real model.
    """
    from pillcare import intent_classifier

    # Drop cached embedder state from earlier tests in the suite.
    intent_classifier._load_embedder.cache_clear()
    intent_classifier._embed.cache_clear()

    monkeypatch.setattr(intent_classifier, "_load_embedder", lambda: None)

    # Clinician-voice paraphrase that would normally be flagged.
    assert (
        intent_classifier.classify_intent("당신은 당뇨병으로 진단됩니다") == "allowed"
    )
    # And a neutral utterance.
    assert intent_classifier.classify_intent("약을 식후에 복용하세요") == "allowed"
