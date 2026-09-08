import pytest
from unittest.mock import Mock, patch

from app.modules.analysis.llm_client import OllamaClient


def test_generate_returns_model_response():
    client = OllamaClient(
        base_url="http://localhost:11434",
        model="llama3.2:3b",
    )

    response = Mock()
    response.content = "Military forces were deployed."

    with patch(
        "app.modules.analysis.llm_client.ChatOllama.invoke",
        return_value=response,
    ):
        result = client.generate(
            system_prompt="You are an analyst.",
            user_prompt="Analyze the evidence.",
        )

    assert result == "Military forces were deployed."


def test_generate_rejects_empty_response():
    client = OllamaClient(
        base_url="http://localhost:11434",
        model="llama3.2:3b",
    )

    response = Mock()
    response.content = ""

    with patch(
        "app.modules.analysis.llm_client.ChatOllama.invoke",
        return_value=response,
    ):
        with pytest.raises(RuntimeError, match="empty response"):
            client.generate(
                system_prompt="System",
                user_prompt="User",
            )