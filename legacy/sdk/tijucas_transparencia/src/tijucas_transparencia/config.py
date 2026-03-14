from dataclasses import dataclass

@dataclass(frozen=True)
class APIConfig:
    base_url: str = "https://tijucas.atende.net/api"
    timeout: int = 30
    user_agent: str = "TijucasTransparenciaClient/1.0"
    max_retries: int = 3
