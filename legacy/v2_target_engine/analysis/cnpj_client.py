import requests
import time
from typing import Any, Dict, Optional, Iterator
from . import company_repository

BASE_URL = "https://minhareceita.org"
TIMEOUT = 20

def _limpar_cnpj(cnpj: str) -> str:
    """Retorna apenas os números do CNPJ."""
    return "".join(ch for ch in cnpj if ch.isdigit())

def buscar_cnpj(cnpj: str, use_cache: bool = True) -> Optional[Dict[str, Any]]:
    """
    Busca os dados de um CNPJ na API Minha Receita.
    Tenta o cache local do repositório SQLite primeiro se `use_cache` for True.
    """
    cnpj_limpo = _limpar_cnpj(cnpj)
    
    # 1. Tentar no cache local SQLite
    if use_cache:
        cached = company_repository.get_company(cnpj_limpo)
        if cached:
            return cached

    # 2. Buscar na API
    url = f"{BASE_URL}/{cnpj_limpo}"
    
    try:
        resp = requests.get(url, timeout=TIMEOUT)
        
        # Lidar com Rate Limit (Minha Receita tipicamente responde com 429)
        if resp.status_code == 429:
            print(f"[API MinhaReceita] Lidar com Rate Limit para {cnpj}. Aguardando 10s...")
            time.sleep(10)
            resp = requests.get(url, timeout=TIMEOUT)
            
        if resp.status_code == 404:
            return None
            
        resp.raise_for_status()
        payload = resp.json()
        
        # 3. Salvar no repositório SQLite
        if payload and "cnpj" in payload:
            company_repository.save_company(payload)
            
        return payload
        
    except requests.RequestException as e:
        print(f"[API MinhaReceita] Falha ao buscar CNPJ {cnpj}: {e}")
        return None

def buscar_empresas_por_socio_qsa(cpf_mascarado: str, uf: str = "SC", limit: int = 100) -> Iterator[dict]:
    """
    Busca iterativamente todas as empresas nas quais o CPF mascarado fornecido atua no QSA.
    O CPF deve vir mascarado no formato da RFB (ex: ***.456.789-** vira ***456789**).
    Faz paginação com o cursor da API.
    """
    cursor = None
    cpf_mascarado_clean = "".join(filter(lambda c: c.isdigit() or c == '*', cpf_mascarado))

    while True:
        params = {
            "cnpf": cpf_mascarado_clean,
            "uf": uf,
            "limit": limit,
        }
        if cursor:
            params["cursor"] = cursor

        try:
            resp = requests.get(f"{BASE_URL}/", params=params, timeout=30)
            
            if resp.status_code == 429:
                 print(f"[API MinhaReceita] Rate Limit em busca de cnpf {cpf_mascarado_clean}. Aguardando 15s...")
                 time.sleep(15)
                 resp = requests.get(f"{BASE_URL}/", params=params, timeout=30)
                 
            resp.raise_for_status()
            payload = resp.json()
            
            items = payload.get("data", [])
            for item in items:
                # Opcional: Se 'item' tiver os dados completos ou suficientes, podemos salvar no repositório.
                # Como a busca paginada muitas vezes retorna um subconjunto de dados, 
                # garantimos o preenchimento chamando `buscar_cnpj` se quisermos o payload full.
                if "cnpj" in item and "razao_social" in item:
                    company_repository.save_company(item)
                yield item

            cursor = payload.get("cursor")
            if not cursor:
                break
                
        except requests.RequestException as e:
            print(f"[API MinhaReceita] Falha ao buscar QSA p/ {cpf_mascarado_clean}: {e}")
            break
