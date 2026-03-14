"""LLM Provider Protocol defining specific NLP methods."""

from abc import abstractmethod
from typing import Any, Protocol

from pydantic import BaseModel

from investiga_connectors.base.adapter import SourceAdapter


class LlmResponse(BaseModel):
    """Standardized response from any LLM provider."""
    raw_content: str
    parsed_json: dict[str, Any] | None = None
    model_used: str
    usage_input_tokens: int = 0
    usage_output_tokens: int = 0
    latency_ms: int = 0


class LlmProvider(SourceAdapter, Protocol):
    """Protocol extending SourceAdapter specifically for LLM text generation."""

    @abstractmethod
    async def chat_completion(
        self,
        system_prompt: str,
        user_message: str,
        model: str,
        response_format: str = "json_object",
        **kwargs: Any,
    ) -> LlmResponse:
        """Standardized interface for LLM calls (OpenAI-like)."""
        ...
