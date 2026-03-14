"""BlockingDetector — identifies rate limits, captchas, and generic blocks."""

import abc
from dataclasses import dataclass
from typing import Any

from httpx import Response


@dataclass
class BlockState:
    """Represents the operational state of a source request."""
    is_blocked: bool
    block_type: str | None = None  # e.g., 'captcha', 'rate_limit', 'auth_expired'
    message: str | None = None
    requires_human: bool = False


class BlockingDetector(abc.ABC):
    """Abstract detector for source blocks."""

    @abc.abstractmethod
    def detect(self, response: Response | str | Any) -> BlockState:
        """Analyze a response (HTTP or Playwright HTML) to detect blocks.
        
        Args:
            response: HTTPX Response, or raw HTML string, or Playwright Locator

        Returns:
            BlockState indicating if the session is blocked and how.
        """
        ...


class DefaultHttpDetector(BlockingDetector):
    """Standard HTTP status-based block detection."""

    def detect(self, response: Response | str | Any) -> BlockState:
        if isinstance(response, Response):
            if response.status_code == 429:
                return BlockState(is_blocked=True, block_type="rate_limit", message="HTTP 429 Too Many Requests")
            if response.status_code in (401, 403):
                return BlockState(is_blocked=True, block_type="auth_expired", message=f"HTTP {response.status_code} Forbidden/Unauthorized")
            if response.status_code >= 500:
                return BlockState(is_blocked=True, block_type="server_error", message=f"HTTP {response.status_code} Server Error")
        
        return BlockState(is_blocked=False)
