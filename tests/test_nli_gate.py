"""NLI entailment gate tests (A6 — Layer 5 of the 6-layer guardrail)."""

import pytest


@pytest.mark.slow
def test_nli_gate_passes_entailed_statement():
    from pillcare.nli_gate import check_entailment

    evidence = "아스피린은 혈액 응고를 억제하므로 출혈 위험이 증가할 수 있다."
    claim = "아스피린은 출혈 위험을 증가시킨다."
    score = check_entailment(claim, evidence)
    assert score >= 0.75, f"expected entailment >=0.75, got {score}"


@pytest.mark.slow
def test_nli_gate_rejects_unrelated_claim():
    from pillcare.nli_gate import check_entailment

    evidence = "아스피린은 진통제로 사용된다."
    claim = "아스피린은 당뇨병을 치료한다."
    score = check_entailment(claim, evidence)
    assert score < 0.5, f"expected low entailment, got {score}"


@pytest.mark.slow
def test_passes_nli_gate_threshold():
    from pillcare.nli_gate import passes_nli_gate

    assert (
        passes_nli_gate("A는 B를 유발한다.", "A가 B를 유발한다는 보고가 있다.") is True
    )
    assert passes_nli_gate("A는 B를 치료한다.", "A는 진통제로만 사용된다.") is False


def test_threshold_constant():
    from pillcare.nli_gate import ENTAILMENT_THRESHOLD

    assert ENTAILMENT_THRESHOLD == 0.75


def test_empty_inputs_return_zero():
    """Empty claim or empty evidence should short-circuit to 0.0 (no model load)."""
    from pillcare.nli_gate import check_entailment

    assert check_entailment("", "some evidence") == 0.0
    assert check_entailment("some claim", "") == 0.0
    assert check_entailment("   ", "   ") == 0.0
