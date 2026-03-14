"""OpenRouter implementation of the LlmProvider protocol."""

import json
import logging
import time
from typing import Any

import httpx
from pydantic import BaseModel

from investiga_api.settings import settings
from investiga_connectors.base.blocking import DefaultHttpDetector, BlockState
from investiga_connectors.openrouter.provider import LlmProvider, LlmResponse

logger = logging.getLogger(__name__)


class OpenRouterAdapter(LlmProvider):
    """Adapter for OpenRouter proxy API."""

    def __init__(self, client: httpx.AsyncClient | None = None):
        self._client = client
        self.detector = DefaultHttpDetector()

    @property
    def source_name(self) -> str:
        return "openrouter"

    async def ping(self) -> bool:
        """Check if OpenRouter API is reachable."""
        try:
            async with self._get_client() as client:
                res = await client.get("/models")
                return res.status_code == 200
        except Exception:
            return False

    def _get_client(self) -> httpx.AsyncClient:
        if self._client:
            return self._client
        return httpx.AsyncClient(
            base_url=settings.openrouter_base_url,
            timeout=settings.timeout_openrouter,
            headers={"Authorization": f"Bearer {settings.openrouter_api_key}"},
        )

    # Note: LlmProvider inherits extract() and parse() from SourceAdapter.
    # LLM usually runs chat_completion, but we implement the base for standard auditing.
    async def extract(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError("Use chat_completion() for LLM providers.")

    def parse(self, raw_payload: Any) -> BaseModel | list[BaseModel]:
        raise NotImplementedError("Parsing depends on the specific NLP prompt schema.")

    async def chat_completion(
        self,
        system_prompt: str,
        user_message: str,
        model: str,
        response_format: str = "json_object",
        **kwargs: Any,
    ) -> LlmResponse:
        """Call OpenRouter completions API."""
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            **kwargs,
        }
        
        # Adding json_object format forces models to return JSON
        if response_format == "json_object":
            payload["response_format"] = {"type": "json_object"}

        start_time = time.perf_counter_ns()
        
        async with self._get_client() as client:
            logger.debug(f"Calling OpenRouter model {model}")
            response = await client.post("/chat/completions", json=payload)
            
            # Detect blocks (Rate Limits, Payment Required, etc)
            block_state: BlockState = self.detector.detect(response)
            if block_state.is_blocked:
                from investiga_orchestration.retry.policies import RateLimitError, SourceBlockedError
                if block_state.block_type == "rate_limit":
                    raise RateLimitError(block_state.message)
                raise SourceBlockedError(block_state.message)
                
            response.raise_for_status()
            data = response.json()
            
        latency_ms = (time.perf_counter_ns() - start_time) // 1_000_000
        
        content = data["choices"][0]["message"]["content"]
        
        parsed_json = None
        if response_format == "json_object":
            try:
                # Clean markdown blocks if LLM still wrapped it
                clean_content = content.replace("```json", "").replace("```", "").strip()
                parsed_json = json.loads(clean_content)
            except json.JSONDecodeError:
                logger.error(f"Failed to decode LLM response as JSON. Content: {content}")
        
        usage = data.get("usage", {})
        
        return LlmResponse(
            raw_content=content,
            parsed_json=parsed_json,
            model_used=model,
            usage_input_tokens=usage.get("prompt_tokens", 0),
            usage_output_tokens=usage.get("completion_tokens", 0),
            latency_ms=latency_ms,
        )
