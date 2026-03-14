from typing import List, Dict, Any
from collections import defaultdict
from .utils import parse_value

class TemporalAnalyzer:
    """
    V4.3: Detecção de Anomalias Temporais Estruturais
    Mapeia credores que concentram execuções anormais (empenhos/liquidações/pagamentos)
    nas últimas semanas do exercício (Dezembro), caracterizando possível
    esvaziamento de orçamento ou pagamentos sazonais suspeitos.
    """
    def __init__(self, despesas: list, restos: list):
        self.despesas = despesas
        self.restos = restos
        
    def analyze_end_of_year_anomalies(self) -> dict:
        """
        Analisa todos os credores e retorna aqueles com concentração atípica em Dezembro.
        Retorna: { cpf_cnpj: { "total_ano": X, "total_dezembro": Y, "percentual": Z, "pico_ultimas_semanas": W } }
        """
        credor_ano = defaultdict(float)
        credor_dezembro = defaultdict(float)
        credor_ultimas_duas_semanas = defaultdict(float)
        
        for p in self.despesas + self.restos:
            cnpj = p.get("cpfCnpjCredor", "")
            if not cnpj: continue
            
            # Mapeamos liquidações ou pagamentos (usamos liquidado pois reflete entrega reconhecida)
            valor = parse_value(p.get("valorLiquidado", p.get("valorPago", "")))
            if valor <= 0: continue
            
            credor_ano[cnpj] += valor
            
            # Verifica a data
            dt_liq = p.get("dataLiquidacao", p.get("dataPagamento", p.get("dataEmpenho", "")))
            
            if not dt_liq:
                # Fallback to _mes
                if p.get("_mes") == "12":
                    credor_dezembro[cnpj] += valor
                continue
                
            parts = dt_liq.split("/")
            if len(parts) == 3:
                dia, mes, ano = parts
                if mes == "12":
                    credor_dezembro[cnpj] += valor
                    if int(dia) >= 15:
                        credor_ultimas_duas_semanas[cnpj] += valor
        
        anomalias = {}
        for cnpj, total in credor_ano.items():
            if total < 50000: # Threshold mínimo de materialidade, ignorar peixinhos
                continue
                
            total_dez = credor_dezembro[cnpj]
            total_ultimas = credor_ultimas_duas_semanas[cnpj]
            
            perc_dez = total_dez / total if total > 0 else 0
            perc_ultimas = total_ultimas / total if total > 0 else 0
            
            # Regra da anomalia: Concentra mais de 50% do faturamento anual *apenas* em Dezembro 
            # E teve emissões significativas nas últimas semanas (mais de 40%)
            if perc_dez >= 0.50 or perc_ultimas >= 0.40:
                anomalias[cnpj] = {
                    "total_ano": total,
                    "total_dezembro": total_dez,
                    "total_fim_dez": total_ultimas,
                    "perc_dezembro": round(perc_dez * 100, 2),
                    "perc_fim_dez": round(perc_ultimas * 100, 2),
                    "nome": "" # será enriquecido no principal
                }
                
        # Enriquecer nomes
        for p in self.despesas + self.restos:
            cnpj = p.get("cpfCnpjCredor", "")
            if cnpj in anomalias and not anomalias[cnpj]["nome"]:
                anomalias[cnpj]["nome"] = p.get("nomeCredor", "")
                
        return anomalias
