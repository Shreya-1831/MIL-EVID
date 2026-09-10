"""LangChain Ollama LLM client."""

from __future__ import annotations

from langchain_ollama import ChatOllama


class OllamaClient:
    """Minimal LangChain wrapper for local Ollama."""

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        timeout_seconds: float = 300.0,
    ) -> None:
        self._model = ChatOllama(
            model=model,
            base_url=base_url,
            temperature=0.2,
            num_predict=500,
            timeout=timeout_seconds,
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
        response = self._model.invoke(
            [
                ("system", system_prompt),
                ("human", user_prompt),
            ]
        )

        content = response.content

        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("Ollama returned an empty response.")

        return content.strip()

    def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema: dict,
    ) -> dict:
        """Generate a response constrained to the supplied JSON schema."""

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

        if not isinstance(response, dict):
            raise RuntimeError(
                "Ollama returned an invalid structured response."
            )

        return response