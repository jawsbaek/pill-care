"""Intent classifier tests (A6 — Layer 6 of the 6-layer guardrail)."""
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
