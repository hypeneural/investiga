import logging
import re
from datetime import datetime
from .cnpj_client import buscar_cnpj
from . import societary_rules

logger = logging.getLogger(__name__)

class SocietaryAnalyzer:
    """
    Analisa vínculos societários e anomalias de CNPJ.
    Usa o CnpjClient para buscar dados na Receita de forma cacheada.
    """
    def __init__(self, tree: dict):
        self.tree = tree
        self.societary_alerts = []
        
        self.target_cpf_masked = self.tree.get("alvo", {}).get("cpf", "")

    def extract_cpf_core(self, cpf_mascarado: str) -> str:
        return societary_rules._extract_cpf_core(cpf_mascarado)
        
    def extract_cnpj_from_string(self, text: str) -> str:
        """Extrai o primeiro CNPJ válido encontrado em uma string."""
        if not text or text == "None":
            return ""
            
        text_str = str(text)
        
        # 1. Look for formatted CNPJ (XX.XXX.XXX/YYYY-ZZ)
        match_fmt = re.search(r'\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}', text_str)
        if match_fmt:
            return "".join(c for c in match_fmt.group(0) if c.isdigit())
            
        # 2. Look for 14 continuous digits
        match_plain = re.search(r'\b\d{14}\b', text_str)
        if match_plain:
            return match_plain.group(0)
            
        # 3. Last resort: strip all non-digits and check if exactly 14
        clean = "".join(c for c in text_str if c.isdigit())
        if len(clean) == 14:
            return clean
            
        return ""

    def _get_first_payment_date(self, cnpj: str):
        # Para saber o primeiro pagamento, procuramos na rede familiar
        primeiro_pgto = None
        rf = self.tree.get("redeFamiliar", {}).get("nucleosEncontrados", [])
        for nucleo in rf:
            for c, info in nucleo.get("credoresDetalhes", {}).items():
                if cnpj in str(c):
                    p_str = info.get("primeiroPagamento")
                    if p_str:
                        try:
                            primeiro_pgto = datetime.strptime(p_str, "%d/%m/%Y").isoformat()
                        except:
                            pass
        return primeiro_pgto

    def analyze(self):
        """
        Executa o enriquecimento societário apenas nos credores suspeitos.
        """
        logger.info("[Societary] Iniciando análise societária V5.2...")
        target_core = self.extract_cpf_core(self.target_cpf_masked)
        
        # 1. Obter lista de CNPJs prioritários da árvore
        cnpjs_to_check = self._select_priority_cnpjs()
        print(f"  > [Societary] Alvo {self.tree.get('alvo',{}).get('nome','')} -> CNPJs extraídos pré-filtro: {len(cnpjs_to_check)} válidos")
        if not cnpjs_to_check:
            self.tree["societary_alerts"] = self.societary_alerts
            return
            
        print(f"  > Selecionados {len(cnpjs_to_check)} CNPJs para API Minha Receita.")

        self.tree["investigacao_societaria"] = []
        
        for cnpj in cnpjs_to_check:
            payload = buscar_cnpj(cnpj)
            if not payload:
                continue
                
            nome_fantasia = payload.get("nome_fantasia") or payload.get("razao_social")
            
            # Save raw investigative data for the final Markdown report
            self.tree["investigacao_societaria"].append({
                "cnpj": cnpj,
                "razao_social": payload.get("razao_social"),
                "nome_fantasia": nome_fantasia,
                "abertura": payload.get("data_inicio_atividade"),
                "cnae": payload.get("cnae_fiscal_descricao"),
                "situacao": payload.get("descricao_situacao_cadastral"),
                "socios": payload.get("qsa", [])
            })
            
            # Extract the organs that paid this CNPJ
            paying_organs = self._get_paying_organs_for_cnpj(cnpj)
            primeira_data = self._get_first_payment_date(cnpj)
            
            context = {
                "alvo_cpf": self.target_cpf_masked,
                "orgaos_pagadores": list(paying_organs),
                "primeira_data_pagamento": primeira_data
            }
            
            alertas_gerados = societary_rules.avaliar_empresa(payload, context)
            
            # Formatar os alertas para a compatibilidade com a árvore principal
            for a in alertas_gerados:
                a["cnpj"] = cnpj
                a["empresa"] = nome_fantasia
                self.societary_alerts.append(a)
                
        # Atualiza a árvore com as anomalias societárias
        self.tree["societary_alerts"] = self.societary_alerts

    def _get_paying_organs_for_cnpj(self, target_cnpj: str) -> set:
        """Coleta todos os nomes de órgãos/unidades que empenharam valores para este CNPJ."""
        organs = set()
        
        # 1. Pelo setor dominado / Foco principal
        centro_custo = self.tree.get("dadosFuncionais", {}).get("centroCusto", "")
        if centro_custo:
            organs.add(centro_custo.upper())
            
        # 2. Pelos pagamentos diretos capturados
        pd = self.tree.get("pagamentosDiretos", {})
        for item in pd.get("detalhesDespesas", []) + pd.get("detalhesRestos", []):
            desp = item.get("despesa", {})
            doc = self.extract_cnpj_from_string(desp.get("cpfCnpjCredor", ""))
            if doc == target_cnpj:
                orgao = desp.get("orgaoDescricao", "").upper()
                unidade = desp.get("unidadeDescricao", "").upper()
                if orgao: organs.add(orgao)
                if unidade: organs.add(unidade)
                
        return organs

    def _select_priority_cnpjs(self) -> set:
        """Retorna CNPJs que merecem gasto de requisição na API."""
        priorities = set()
        
        # 1. Pagamentos Diretos (Top despesas)
        pd = self.tree.get("pagamentosDiretos", {})
        for item in pd.get("detalhesDespesas", []) + pd.get("detalhesRestos", []):
            desp = item.get("despesa", {})
            val_str = desp.get("valorLiquidado") or desp.get("valorPago") or "0"
            try:
                val = float(val_str)
            except ValueError:
                val = 0
            if val > 20000:
                priorities.add(str(desp.get("cpfCnpjCredor", "")))
                
        # 2. Credores do Núcleo Familiar (MUITO IMPORTANTE)
        rf = self.tree.get("redeFamiliar", {}).get("nucleosEncontrados", [])
        for nucleo in rf:
            for cnpj in nucleo.get("credoresFortes", []) + nucleo.get("credoresMedios", []):
                 priorities.add(str(cnpj))
                 
        # 3. Top Credores do Setor
        top_cred = self.tree.get("redeCredoresDoSetor", {}).get("topCredoresCNPJPrivados", [])
        for c in top_cred[:5]:
            priorities.add(str(c.get("documento")))
                 
        # 4. Anomalias Temporais (Fim de Ano)
        for anomaly in self.tree.get("temporal_alerts", []):
             credor = anomaly.get("cnpj") or anomaly.get("nome", "")
             priorities.add(str(credor))
                 
        # Filter out CPFs (len != 14 digits)
        valid_cnpjs = set()
        for doc in priorities:
            if not doc or doc == "None": continue
            extracted = self.extract_cnpj_from_string(doc)
                 
            if extracted and len(extracted) == 14:
                valid_cnpjs.add(extracted)
                
        return valid_cnpjs
