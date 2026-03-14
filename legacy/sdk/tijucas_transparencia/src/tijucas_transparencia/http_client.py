from __future__ import annotations
from typing import Any, Dict, Optional
import requests
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type

from .config import APIConfig
from .exceptions import APIError, APIResponseError

class BaseHTTPClient:
    def __init__(self, config: Optional[APIConfig] = None):
        self.config = config or APIConfig()
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "User-Agent": self.config.user_agent,
        })

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(1),
        retry=retry_if_exception_type((requests.RequestException, APIResponseError)),
        reraise=True,
    )
    def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        url = f"{self.config.base_url.rstrip('/')}/{path.lstrip('/')}"
        try:
            response = self.session.get(url, params=params, timeout=self.config.timeout)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise APIError(f"Erro HTTP ao acessar {url}: {exc}") from exc
        try:
            return response.json()
        except ValueError as exc:
            raise APIResponseError(
                f"Resposta não é JSON válido em {url}. Status={response.status_code}"
            ) from exc
