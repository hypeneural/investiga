from .config import APIConfig
from .http_client import BaseHTTPClient
from .endpoints.pessoal import PessoalEndpoint
from .endpoints.dados_abertos import DadosAbertosEndpoint

class TijucasTransparenciaClient:
    def __init__(self, config: APIConfig | None = None):
        self.http = BaseHTTPClient(config=config)
        self.pessoal = PessoalEndpoint(self.http)
        self.dados_abertos = DadosAbertosEndpoint(self.http)
