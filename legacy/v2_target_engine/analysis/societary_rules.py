import re
from datetime import datetime
from typing import Dict, List, Any

# ==============================================================================
# DICIONÁRIOS DE INCOMPATIBILIDADE DE CNAE (V5.2)
# ==============================================================================
CNAES_RESTRITOS_NOMES = [
    "evento", "show", "fest", "entretenimento", "bebida", "tabaco",
    "publicidade", "propaganda", "música", "artístic", "palco"
]

VERTICAIS_ORGAO: Dict[str, List[str]] = {
    "SAUDE": ["saude", "saúde", "hospital", "fms", "sus", "upa", "pronto atendimento"],
    "EDUCACAO": ["educacao", "educação", "escola", "ensino", "creche", "fundeb", "professor"],
    "INFRAESTRUTURA": ["obras", "infraestrutura", "pavimentacao", "transporte", "estradas", "rodovia", "saneamento"],
    "ASSISTENCIA_SOCIAL": ["assistencia social", "fmas", "cras", "creas", "idoso", "crianca"],
    "ESPORTE_CULTURA": ["esporte", "cultura", "fme", "fmc", "lazer", "juventude"],
}

CNAES_COMPATIVEIS: Dict[str, List[str]] = {
    "SAUDE": ["médic", "medic", "hospital", "clínic", "clinic", "fármac", "farmac", "saúde", "saude", "odontol", "enferma", "exame", "diagnóstic"],
    "EDUCACAO": ["livro", "papelaria", "educa", "ensino", "pedagóg", "pedagog", "escola", "curso", "treinamento", "didátic", "didatic"],
    "INFRAESTRUTURA": ["construção", "construcao", "obra", "engenha", "paviment", "terraplenagem", "arquitetura", "manutenção", "manutencao", "material de construção", "cimento", "asfalto"],
    "ASSISTENCIA_SOCIAL": ["cesta básica", "alimento", "funerária", "funeraria", "social", "abrigo"],
    "ESPORTE_CULTURA": ["esport", "eventos esportivos", "quadra", "campo", "artísti", "show", "cultura"],
}

def _clean_str(text: str) -> str:
    """Limpa a string para comparação, removendo acentos e deixando minúscula."""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r'[áàãâä]', 'a', text)
    text = re.sub(r'[éèêë]', 'e', text)
    text = re.sub(r'[íìîï]', 'i', text)
    text = re.sub(r'[óòõôö]', 'o', text)
    text = re.sub(r'[úùûü]', 'u', text)
    text = re.sub(r'[ç]', 'c', text)
    return text

def _extract_cpf_core(cpf_str: str) -> str:
    """
    Extrai o miolo funcional de 6 dígitos de um CPF.
    Ex: '123.456.789-00' -> '456789'
    Ex: '***456789**' -> '456789'
    Ex: '12345678900' -> '456789'
    """
    if not cpf_str:
        return ""
    
    # Se já tem a máscara da receita (11 chars começando com *)
    if cpf_str.startswith("***") and cpf_str.endswith("**"):
        return cpf_str[3:9]
    
    # Limpa formatação comum do CPF (deixa apenas dígitos)
    digits = "".join(filter(str.isdigit, cpf_str))
    
    if len(digits) == 11:
        # Pega do 4º ao 9º dígito (índices 3 a 8)
        str_digits = str(digits)
        return str_digits[3:9]
        
    # Se o formato não é reconhecido, tenta a sorte de tirar asteriscos e pegar 6 digitos
    fallback = "".join(filter(str.isdigit, cpf_str))
    if len(fallback) == 6:
        return str(fallback)
        
    return ""

def avaliar_empresa(payload_cnpj: Dict[str, Any], context: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Avalia a empresa recebida do Minha Receita com base nas heurísticas societárias (V5.2).
    
    Args:
        payload_cnpj: Dicionário vindo do /cnpj da Minha Receita (ou do cache local).
        context: Contexto de execução, contendo:
            - alvo_cpf: str (CPF do alvo se existir)
            - orgaos_pagadores: List[str] (Lista de nomes dos órgãos que pagaram a esta empresa)
            - primeira_data_pagamento: datetime ou str ISO format
            - pagamentos_totais: float
            
    Returns:
        Lista de objetos alerta contendo claim_type, evidence_tier e código.
    """
    alertas = []
    
    razao_social = payload_cnpj.get("razao_social", "Empresa Desconhecida")
    cnpj = payload_cnpj.get("cnpj", "")
    data_inicio_str = payload_cnpj.get("data_inicio_atividade")
    
    # --------------------------------------------------------------------------
    # 1. EMPRESA DE PRATELEIRA (T2)
    # --------------------------------------------------------------------------
    primeira_data_pagamento = context.get("primeira_data_pagamento")
    
    if data_inicio_str and primeira_data_pagamento:
        try:
            if isinstance(primeira_data_pagamento, str):
                primeira_data_pagamento = datetime.fromisoformat(primeira_data_pagamento.replace("Z", ""))
                
            data_inicio = datetime.strptime(data_inicio_str, "%Y-%m-%d")
            delta_days = (primeira_data_pagamento - data_inicio).days
            
            if 0 <= delta_days <= 180:
                alertas.append({
                    "codigo": "SOCIETARIA_PRATELEIRA_FORTE",
                    "descricao": f"A empresa ({cnpj}) obteve seu primeiro empenho/pagamento no município com apenas {delta_days} dias desde sua fundação oficial.",
                    "claim_type": "padrao_suspeito",
                    "evidence_tier": "T2",
                    "manual_review_required": True,
                    "risco_financeiro": 15
                })
            elif 180 < delta_days <= 365:
                alertas.append({
                    "codigo": "SOCIETARIA_PRATELEIRA_MEDIA",
                    "descricao": f"A empresa ({cnpj}) começou a receber recursos entre 6 meses e 1 ano da sua fundação ({delta_days} dias).",
                    "claim_type": "padrao_suspeito",
                    "evidence_tier": "T2",
                    "manual_review_required": True,
                    "risco_financeiro": 5
                })
        except Exception:
            pass
            
    # --------------------------------------------------------------------------
    # 2. SÓCIO OCULTO (T1 Fato)
    # --------------------------------------------------------------------------
    alvo_cpf = context.get("alvo_cpf", "")
    alvo_core = _extract_cpf_core(alvo_cpf)
    
    qsa = payload_cnpj.get("qsa", [])
    if alvo_core and qsa:
        for socio in qsa:
            socio_cpf = socio.get("cnpj_cpf_do_socio", "")
            socio_core = _extract_cpf_core(socio_cpf)
            
            if socio_core and socio_core == alvo_core:
                alertas.append({
                    "codigo": "SOCIETARIA_SOCIO_OCULTO",
                    "descricao": f"Aviso Crítico: O CPF mascarado do sócio '{socio.get('nome_socio')}' ({socio_cpf}) é totalmente compatível com a máscara do CPF do Alvo Político.",
                    "claim_type": "fato_direto",
                    "evidence_tier": "T1",
                    "manual_review_required": True,
                    "risco_financeiro": 80
                })
                break # Apenas um alerta já basta para este CNPJ e este alvo
                
    # --------------------------------------------------------------------------
    # 3. SITUAÇÃO CADASTRAL: RECEBIMENTO POR EMPRESA INATIVA/BAIXADA (T1 Fato)
    # --------------------------------------------------------------------------
    situacao = payload_cnpj.get("descricao_situacao_cadastral", "").upper()
    if situacao and situacao != "ATIVA":
         alertas.append({
            "codigo": "SOCIETARIA_SITUACAO_CADASTRAL",
            "descricao": f"A empresa ({cnpj}) recebeu recursos enquanto constava como '{situacao}' na base da Receita Federal.",
            "claim_type": "fato_direto",
            "evidence_tier": "T1",
            "manual_review_required": True,
            "risco_financeiro": 50
         })

    # --------------------------------------------------------------------------
    # 4. CNAE GENÉRICO OU INCOMPATÍVEL (T2 Padrão)
    # --------------------------------------------------------------------------
    cnae_principal_desc = _clean_str(payload_cnpj.get("cnae_fiscal_descricao", ""))
    secundarios = payload_cnpj.get("cnaes_secundarios", [])
    todas_descricoes = [cnae_principal_desc] + [_clean_str(c.get("descricao", "")) for c in secundarios]
    
    # 4.1 CNAE Curinga / Genérico (Média Suspeição)
    is_generico = any("peça" not in d and "peças" not in d and ("comercio varejista de outros" in d or "servicos de organizacao de feiras" in d or "consultoria" in d) for d in todas_descricoes)
    if is_generico:
         alertas.append({
            "codigo": "SOCIETARIA_CNAE_GENERICO",
            "descricao": f"O objeto empresarial principal ou secundário da {razao_social} orbita de forma genérica ('comércio varejista de outros', etc) ou intangível ('consultoria').",
            "claim_type": "padrao_suspeito",
            "evidence_tier": "T2",
            "manual_review_required": False,
            "risco_financeiro": 5
         })
         
    # 4.2 Restrito / Incompatibilidade Material (Alta Suspeição)
    has_restrito = any(r in d for r in CNAES_RESTRITOS_NOMES for d in todas_descricoes)
    
    orgaos_pagadores = context.get("orgaos_pagadores", [])
    
    for orgao in orgaos_pagadores:
        orgao_clean = _clean_str(orgao)
        
        # Encontra a vertical do orgão
        vertical_encontrada = None
        for vert_name, keywords in VERTICAIS_ORGAO.items():
            if any(k in orgao_clean for k in keywords):
                vertical_encontrada = vert_name
                break
                
        if vertical_encontrada is not None:
            # Verifica se algum CNAE da empresa é compatível com esta vertical
            compatibilidade = False
            for cnae_desc in todas_descricoes:
                if any(k in cnae_desc for k in CNAES_COMPATIVEIS[str(vertical_encontrada)]):
                    compatibilidade = True
                    break
                    
            if not compatibilidade and has_restrito:
                alertas.append({
                    "codigo": "SOCIETARIA_INCOMPATIBILIDADE",
                    "descricao": f"CONFLITO MATERIAL: Empresa {cnpj} possui CNAEs restritos (Eventos/Entretenimento/Publicidade) e prestou serviços a órgão incongruente ({orgao}).",
                    "claim_type": "padrao_suspeito",
                    "evidence_tier": "T2",
                    "manual_review_required": True,
                    "risco_financeiro": 25
                })
                break
                
    return alertas
