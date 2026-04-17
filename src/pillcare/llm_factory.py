"""LLM provider factory — creates Gemini or Claude based on environment."""

import os

from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI


def create_llm():
    """Create LLM instance based on LLM_PROVIDER env var.

    Defaults to Gemini 2.5 Flash on Vertex AI.
    Set LLM_PROVIDER=claude to use Claude Sonnet (requires ANTHROPIC_API_KEY).
    """
    provider = os.environ.get("LLM_PROVIDER", "gemini")

    if provider == "claude":
        return ChatAnthropic(
            model="claude-sonnet-4-6",
            api_key=os.environ.get("ANTHROPIC_API_KEY"),
            max_tokens=4096,
        )

    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        vertexai=True,
        project=os.environ.get("GCP_PROJECT_ID"),
        location=os.environ.get("GCP_REGION", "asia-northeast3"),
        max_output_tokens=5000,
        safety_settings={
            "HARM_CATEGORY_DANGEROUS_CONTENT": "BLOCK_ONLY_HIGH",
            "HARM_CATEGORY_HARASSMENT": "BLOCK_ONLY_HIGH",
        },
    )


def get_critic_llm():
    """Claude Haiku 4.5 for LLM-as-judge critic role (cost-controlled sampling).

    Uses the `claude-haiku-4-5` short alias (langchain-anthropic >= 1.4.0) for
    forward compatibility. Temperature is pinned to 0 for deterministic judging.
    """
    return ChatAnthropic(
        model="claude-haiku-4-5",
        api_key=os.environ.get("ANTHROPIC_API_KEY"),
        temperature=0,
        max_tokens=2048,
    )
