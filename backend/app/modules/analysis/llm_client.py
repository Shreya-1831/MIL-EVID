"""LangChain Ollama client for MIL-EVID (OPTIMIZED)."""

from __future__ import annotations

import time

from langchain_ollama import ChatOllama


class OllamaClient:
    """Minimal Ollama wrapper with warm-model and output-budget controls."""

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        timeout_seconds: float = 120.0,
        num_predict: int = 300,  # OPTIMIZED: Increased from 220
        keep_alive: str = "24h",
    ) -> None:
        self._model = ChatOllama(
            model=model,
            base_url=base_url,
            temperature=0.3,  # OPTIMIZED: Slightly higher for detail (was 0.2)
            num_predict=num_predict,
            timeout=timeout_seconds,
            keep_alive=keep_alive,
        )

    @property
    def model(self) -> str:
        return self._model.model

    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        """Generate a normal text response and report generation metrics."""

        start = time.perf_counter()

        try:
            response = self._model.invoke(
                [
                    ("system", system_prompt),
                    ("human", user_prompt),
                ]
            )
        finally:
            elapsed = time.perf_counter() - start

            print(
                "[LLM TIMING] generate: "
                f"{elapsed:.2f}s | "
                f"prompt_chars={len(system_prompt) + len(user_prompt):,}"
            )

        content = response.content

        if not isinstance(content, str) or not content.strip():
            raise RuntimeError(
                "Ollama returned an empty response."
            )

        print(
            "[LLM OUTPUT] "
            f"response_chars={len(content):,}"
        )

        return content.strip()

    def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema: dict,
    ) -> dict:
        """Generate a structured response and report request metrics."""

        prompt_chars = len(system_prompt) + len(user_prompt)

        start = time.perf_counter()

        try:
            structured_model = self._model.with_structured_output(
                schema,
                method="json_schema",
            )

            response = structured_model.invoke(
                [
                    ("system", system_prompt),
                    ("human", user_prompt),
                ]
            )
        finally:
            elapsed = time.perf_counter() - start

            print(
                "[LLM TIMING] generate_structured: "
                f"{elapsed:.2f}s | "
                f"prompt_chars={prompt_chars:,}"
            )

        if not isinstance(response, dict):
            raise RuntimeError(
                "Ollama returned an invalid structured response."
            )

        response_text = str(response)

        print(
            "[LLM OUTPUT] "
            f"response_chars={len(response_text):,}"
        )

        return response