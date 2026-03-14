"""Base SourceAdapter Protocol for all external connectors.

All integrations (Atende, Receita, OpenRouter) must implement this protocol
to ensure a unified approach to rate limiting, session management, and error handling.
"""

from abc import abstractmethod
from typing import Any, Protocol, TypeVar

from pydantic import BaseModel


T = TypeVar("T", bound=BaseModel)


class SourceAdapter(Protocol):
    """Unified protocol for external source connectors."""

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Unique identifier for this source (e.g., 'atende', 'minha_receita')."""
        ...

    @abstractmethod
    async def ping(self) -> bool:
        """Healthcheck the source. Returns True if reachable and healthy."""
        ...

    @abstractmethod
    async def extract(self, *args: Any, **kwargs: Any) -> Any:
        """Core extraction method.

        Implementations should:
        1. Parse the specific arguments needed (e.g., CNPJ, or date range).
        2. Execute the request (HTTPX or Playwright).
        3. Return the raw JSON/HTML/XML payload for auditable storage.
        """
        ...

    @abstractmethod
    def parse(self, raw_payload: Any) -> T | list[T]:
        """Convert the raw payload into typed domain models (Pydantic)."""
        ...
