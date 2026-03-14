class APIError(Exception):
    """Erro genérico da API."""

class APIResponseError(APIError):
    """Resposta inválida ou inesperada da API."""

class APIValidationError(APIError):
    """Erro de validação de parâmetros."""
