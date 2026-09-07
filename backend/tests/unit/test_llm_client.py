import httpx
import pytest
from unittest.mock import patch

from app.modules.analysis.llm_client import OllamaClient


def make_response(content: str) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "message": {
                "content": content,
            }
        },
        request=httpx.Request(
            "POST",
            "http://localhost:11434/api/chat",
        ),
    )


def test_generate_returns_model_response() -> None:
    client = OllamaClient(
        base_url="http://localhost:11434",
        model="llama3.2:3b",
    )

    with patch(
        "httpx.Client.post",
        return_value=make_response(
            "Military forces were deployed."
        ),
    ):
        result = client.generate(
            system_prompt="You are an analyst.",
            user_prompt="Analyze the evidence.",
        )

    assert result == "Military forces were deployed."


def test_generate_rejects_empty_response() -> None:
    client = OllamaClient(
        base_url="http://localhost:11434",
        model="llama3.2:3b",
    )

    with patch(
        "httpx.Client.post",
        return_value=make_response(""),
    ):
        with pytest.raises(RuntimeError, match="empty response"):
            client.generate(
                system_prompt="System",
                user_prompt="User",
            )


def test_generate_handles_http_error() -> None:
    client = OllamaClient(
        base_url="http://localhost:11434",
        model="llama3.2:3b",
    )

    with patch(
        "httpx.Client.post",
        side_effect=httpx.ConnectError("connection failed"),
    ):
        with pytest.raises(RuntimeError, match="Ollama request failed"):
            client.generate(
                system_prompt="System",
                user_prompt="User",
            )