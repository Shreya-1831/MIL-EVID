"""LangChain Ollama LLM client."""

from __future__ import annotations
from langchain_ollama import ChatOllama


class OllamaClient:
    """Minimal LangChain wrapper for local Ollama."""

    def __init__(
        self, *, base_url: str, model: str,
        timeout_seconds: float = 300.0,
    ) -> None:
        self._model = ChatOllama(
            model=model, base_url=base_url,
            temperature=0.2, num_predict=300,
            timeout=timeout_seconds,
        )

    @property
    def model(self) -> str:
        return self._model.model

    def generate(self, *, system_prompt: str, user_prompt: str) -> str:
        response = self._model.invoke([
            ("system", system_prompt),
            ("human", user_prompt),
        ])
        content = response.content
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("Ollama returned an empty response.")
        return content.strip()