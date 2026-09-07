"""Simple local Ollama LLM client."""

from __future__ import annotations

import httpx


class OllamaClient:
    """Minimal client for Ollama's local chat API."""

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        timeout_seconds: float = 300.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout_seconds

    @property
    def model(self) -> str:
        return self._model

    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        """Generate a response from the configured Ollama model."""

        payload = {
            "model": self._model,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
            "stream": False,
            "options": {
                "temperature": 0.2,
                "num_predict": 300,
            },
        }

        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.post(
                    f"{self._base_url}/api/chat",
                    json=payload,
                )
                response.raise_for_status()

        except httpx.HTTPError as exc:
            raise RuntimeError(
                f"Ollama request failed: {exc}"
            ) from exc

        data = response.json()

        content = data.get("message", {}).get("content", "")

        if not isinstance(content, str) or not content.strip():
            raise RuntimeError(
                "Ollama returned an empty response."
            )

        return content.strip()