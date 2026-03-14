"""Base definitions for Atende (Portal Transparência) connector."""

import logging
from typing import Any

import httpx

from investiga_connectors.base.adapter import SourceAdapter
from investiga_connectors.base.blocking import DefaultHttpDetector, BlockState

logger = logging.getLogger(__name__)


class AtendeAdapter(SourceAdapter):
    """Base Adapter for Atende Transparency Portal."""

    def __init__(self, client: httpx.AsyncClient | None = None):
        self._client = client
        self.detector = DefaultHttpDetector()
        self.base_url = "https://atende.net"  # Would be configurable per city

    @property
    def source_name(self) -> str:
        return "atende"

    async def ping(self) -> bool:
        """Check if Atende portal is online."""
        try:
            async with self._get_client() as client:
                res = await client.get("/")
                return res.status_code == 200
        except Exception:
            return False

    def _get_client(self) -> httpx.AsyncClient:
        if self._client:
            return self._client
        return httpx.AsyncClient(
            base_url=self.base_url,
            timeout=30.0,
            verify=False, # Often transparency portals have bad SSL
        )

    async def extract(self, endpoint_path: str, params: dict[str, Any] | None = None) -> Any:
        """Generic extraction for Atende API endpoints."""
        async with self._get_client() as client:
            logger.debug(f"Fetching Atende API: {endpoint_path} with {params}")
            response = await client.get(endpoint_path, params=params)
            
            block_state: BlockState = self.detector.detect(response)
            if block_state.is_blocked:
                # E.g. Cloudflare or Atende-specific Captcha page
                if "captcha" in response.text.lower() or response.status_code == 403:
                    block_state.block_type = "captcha"
                    block_state.requires_human = True
                    
                from investiga_orchestration.retry.policies import RateLimitError, SourceBlockedError
                if block_state.block_type == "rate_limit":
                    raise RateLimitError(block_state.message)
                raise SourceBlockedError(block_state.message)

            response.raise_for_status()
            
            if "application/json" in response.headers.get("Content-Type", ""):
                return response.json()
            return response.text

    def parse(self, raw_payload: Any) -> Any:
        raise NotImplementedError("Parsing is handled by specific Atende endpoint parsers.")
