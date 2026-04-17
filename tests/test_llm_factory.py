"""Tests for LLM factory."""

import os
from unittest.mock import patch, MagicMock


from pillcare.llm_factory import create_llm


@patch.dict(
    os.environ,
    {
        "LLM_PROVIDER": "gemini",
        "GCP_PROJECT_ID": "test-project",
        "GCP_REGION": "asia-northeast3",
    },
)
@patch("pillcare.llm_factory.ChatGoogleGenerativeAI")
def test_create_gemini_llm(mock_chat_cls):
    mock_chat_cls.return_value = MagicMock()
    create_llm()
    mock_chat_cls.assert_called_once()
    call_kwargs = mock_chat_cls.call_args[1]
    assert call_kwargs["model"] == "gemini-2.5-flash"
    assert call_kwargs["vertexai"] is True
    assert call_kwargs["project"] == "test-project"
    assert call_kwargs["location"] == "asia-northeast3"
    assert call_kwargs["max_output_tokens"] == 5000


@patch.dict(os.environ, {"LLM_PROVIDER": "claude", "ANTHROPIC_API_KEY": "sk-test"})
@patch("pillcare.llm_factory.ChatAnthropic")
def test_create_claude_llm(mock_chat_cls):
    mock_chat_cls.return_value = MagicMock()
    create_llm()
    mock_chat_cls.assert_called_once()
    call_kwargs = mock_chat_cls.call_args[1]
    assert call_kwargs["model"] == "claude-sonnet-4-6"
    assert call_kwargs["max_tokens"] == 4096


@patch.dict(os.environ, {}, clear=True)
@patch("pillcare.llm_factory.ChatGoogleGenerativeAI")
def test_defaults_to_gemini(mock_chat_cls):
    mock_chat_cls.return_value = MagicMock()
    create_llm()
    mock_chat_cls.assert_called_once()
