"""Tests for Critic node (LLM-as-judge self-critique)."""

import random
from unittest.mock import MagicMock


# --- Step 1: Schema tests ---


def test_critic_output_schema():
    from pillcare.schemas import CriticOutput, CriticVerdict

    out = CriticOutput(
        verdict=CriticVerdict.PASS,
        critical_errors=[],
        minor_issues=["인용 부족"],
        dropped_claims=[],
    )
    assert out.verdict == CriticVerdict.PASS
    assert out.minor_issues == ["인용 부족"]


def test_critic_verdict_enum():
    from pillcare.schemas import CriticVerdict

    assert CriticVerdict.PASS.value == "pass"
    assert CriticVerdict.RETRY.value == "retry"
    assert CriticVerdict.ESCALATE.value == "escalate"


# --- Step 4: critic_node tests ---


def test_should_sample_critic_rate(monkeypatch):
    """Roughly 10% sampling rate (within 5%-15%)."""
    from pillcare.critic import should_sample_critic

    random.seed(42)
    sampled = sum(should_sample_critic() for _ in range(1000))
    assert 50 <= sampled <= 150  # 10% ± 5%


def test_critic_node_skips_when_not_sampled(monkeypatch):
    from pillcare.critic import critic_node

    # Force not-sampled: should return PASS without LLM call
    monkeypatch.setattr("pillcare.critic.should_sample_critic", lambda: False)
    llm = MagicMock()
    result = critic_node(
        {"guidance_result": {}, "dur_alerts": [], "drug_infos": []}, llm=llm
    )
    assert result["critic_output"]["verdict"] == "pass"
    llm.with_structured_output.assert_not_called()


def test_critic_node_invokes_llm_when_sampled(monkeypatch):
    from pillcare.critic import critic_node
    from pillcare.schemas import CriticOutput, CriticVerdict

    monkeypatch.setattr("pillcare.critic.should_sample_critic", lambda: True)

    mock_structured = MagicMock()
    mock_structured.invoke.return_value = CriticOutput(
        verdict=CriticVerdict.PASS,
        critical_errors=[],
        minor_issues=[],
        dropped_claims=[],
    )
    llm = MagicMock()
    llm.with_structured_output.return_value = mock_structured

    result = critic_node(
        {
            "guidance_result": {
                "drug_guidances": [{"drug_name": "아스피린", "sections": {}}]
            },
            "dur_alerts": [],
            "drug_infos": [],
        },
        llm=llm,
    )
    assert result["critic_output"]["verdict"] == "pass"
    llm.with_structured_output.assert_called_once()


def test_critic_node_flags_missing_dur_coverage(monkeypatch):
    """When DUR alerts present but guidance lacks warnings, critic must retry."""
    from pillcare.critic import critic_node
    from pillcare.schemas import CriticOutput, CriticVerdict

    monkeypatch.setattr("pillcare.critic.should_sample_critic", lambda: True)

    mock_structured = MagicMock()
    mock_structured.invoke.return_value = CriticOutput(
        verdict=CriticVerdict.RETRY,
        critical_errors=["DUR 경고 1건이 응답에 반영되지 않음"],
        minor_issues=[],
        dropped_claims=[],
    )
    llm = MagicMock()
    llm.with_structured_output.return_value = mock_structured

    state = {
        "guidance_result": {
            "drug_guidances": [
                {
                    "drug_name": "아스피린",
                    "sections": {
                        "효능": {"content": "...", "source_tier": "t1_approved"}
                    },
                }
            ],
            "dur_warnings": [],
        },
        "dur_alerts": [
            {"drug_1": "A", "drug_2": "B", "reason": "...", "cross_clinic": False}
        ],
        "drug_infos": [],
    }
    result = critic_node(state, llm=llm)
    assert result["critic_output"]["verdict"] == "retry"
    assert any("DUR" in e for e in result["critic_output"]["critical_errors"])


def test_critic_prompt_uses_json_serialization(monkeypatch):
    """Prompt must serialize state as JSON (not Python repr)."""
    from pillcare.critic import _build_critic_prompt

    state = {
        "guidance_result": {"summary": "테스트", "cross_clinic": False},
        "dur_alerts": [{"drug_name_1": "A", "drug_name_2": "B", "cross_clinic": True}],
    }
    prompt = _build_critic_prompt(state)
    # JSON uses double quotes and lowercase booleans; Python repr uses single quotes + True/False
    assert "\"summary\"" in prompt
    assert "\"cross_clinic\": false" in prompt or "\"cross_clinic\": true" in prompt
    assert "'summary'" not in prompt
    assert ": False" not in prompt  # Python repr of bool
    assert ": True" not in prompt


def test_critic_node_falls_back_to_pass_on_llm_error(monkeypatch):
    """Network/rate-limit error must NOT bubble up — critic fails open."""
    from pillcare.critic import critic_node

    monkeypatch.setattr("pillcare.critic.should_sample_critic", lambda: True)

    class BrokenLLM:
        def with_structured_output(self, *args, **kwargs):
            raise RuntimeError("simulated API error")

    result = critic_node(
        {"guidance_result": {"summary": "x"}, "dur_alerts": [], "drug_infos": []},
        llm=BrokenLLM(),
    )
    assert result["critic_output"]["verdict"] == "pass"
    assert any(
        "critic unavailable" in msg for msg in result["critic_output"]["minor_issues"]
    )
