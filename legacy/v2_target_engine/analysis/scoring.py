from .identity_resolution import MatchClass
from datetime import datetime

def _parse_date(dstr):
    if not dstr: return None
    try:
        return datetime.strptime(dstr, "%d/%m/%Y")
    except Exception:
        pass
    try:
        return datetime.strptime(dstr, "%Y-%m-%d")
    except Exception:
        pass
    return None

class TripleScorer:
    def __init__(self, target_tree: dict):
        self.tree = target_tree
        self.risco_financeiro = 0
        self.risco_relacional = 0
        self.evidencia = 100
        self.alertas = []

    def calculate_scores(self) -> dict:
        """Calculates financial risk, relational risk, and evidence quality."""
        self._score_payments()
        self._score_sector_financials()
        self._score_family()
        self._score_multiple_jobs()
        self._score_functional_coherence()
        self._score_cross_connections()
        self._score_transversals()  # V4.2
        self._score_timeline()      # V4.2
        self._score_temporal()      # V4.3
        self._score_societary()     # V5.0 (Bugfix 6.1)
        self._score_evidence_quality()
        
        # Cap risks at 100
        self.risco_financeiro = min(100, self.risco_financeiro)
        self.risco_relacional = min(100, self.risco_relacional)
        self.evidencia = max(0, min(100, self.evidencia))
        
        return {
            "risco_financeiro": self.risco_financeiro,
            "risco_relacional": self.risco_relacional,
            "evidencia": self.evidencia,
            "alertas": self.alertas
        }

    def _add_alert(self, points_fin, points_rel, msg, code, claim_type="padrao_suspeito", evidence_tier="T2"):
        # Regra de Risco Financeiro V5.1: Nunca sobe com Inferência Fraca (T3)
        if evidence_tier == "T3":
            points_fin = 0
            # Força o teto relacional se for T3 (ex: sobrenome)
            points_rel = min(points_rel, 15)
            
        if points_fin > 0:
            self.risco_financeiro += points_fin
        if points_rel > 0:
            self.risco_relacional += points_rel
            
        self.alertas.append({
             "codigo": code,
             "pontos_fin": points_fin,
             "pontos_rel": points_rel,
             "descricao": msg,
             "claim_type": claim_type,
             "evidence_tier": evidence_tier,
             "manual_review_required": evidence_tier == "T3" or claim_type == "inferencia_relacional"
        })

    def _score_payments(self):
        pd = self.tree.get("pagamentosDiretos", {})
        total_pago = pd.get("totalPago", 0.0)
        
        if total_pago == 0:
            return

        salario = self.tree.get("dadosFuncionais", {}).get("salarioBase", 0.0)
        salario_anual = max(salario * 13, 1000) # Prevents division by zero
        
        situacao = self.tree.get("dadosFuncionais", {}).get("situacao", "").upper()
        
        if "TRABALHANDO" in situacao and total_pago > 0:
            self._add_alert(20, 10, "Funcionário ativo recebendo pagamentos diretos", "PAGAMENTO_DIRETO_ATIVO", claim_type="fato_direto", evidence_tier="T1")
            
        if total_pago > salario_anual * 2:
             self._add_alert(30, 0, f"Recebimento direto > 2 salários anuais ({round(total_pago/salario_anual,1)}x)", "PAGAMENTO_ALTO_VALOR_2X", claim_type="fato_direto", evidence_tier="T1")
        elif total_pago > salario_anual:
             self._add_alert(15, 0, f"Recebimento direto > 1 salário anual ({round(total_pago/salario_anual,1)}x)", "PAGAMENTO_ALTO_VALOR_1X", claim_type="fato_direto", evidence_tier="T1")

    def _score_sector_financials(self):
        rede_cred = self.tree.get("redeCredoresDoSetor", {})
        
        # Trilha 5: Fracionamento
        alertas_frac = rede_cred.get("alertasFracionamento", [])
        fortes = 0
        medios = 0
        for f in alertas_frac:
            if f.get("classificacao") == "FORTE": fortes += 1
            if f.get("classificacao") == "MEDIO": medios += 1
            
        if fortes > 0:
            self._add_alert(min(50, fortes * 20), 10, f"Padrão compatível com fracionamento MENSAL em {fortes} credor(es) privados no setor.", "SETOR_FRACIONAMENTO_FORTE", claim_type="padrao_suspeito", evidence_tier="T2")
        if medios > 0:
            self._add_alert(min(30, medios * 10), 0, f"Indício moderado de fracionamento em {medios} credor(es) privados do setor.", "SETOR_FRACIONAMENTO_MEDIO", claim_type="padrao_suspeito", evidence_tier="T2")
            
        # Trilha 6: Anulações / Retenções Ocultas
        alertas_anu = rede_cred.get("alertasAnulacao", [])
        for a in alertas_anu:
            tipo = a.get("tipo", "")
            if tipo == "ANULACAO_ATIPICA_SETOR":
                self._add_alert(30, 0, a.get("motivo", "Alta taxa de anulação frente ao empenhado no setor"), "ANULACAO_ATIPICA_SETOR", claim_type="padrao_suspeito", evidence_tier="T2")
            elif tipo == "RETENCAO_ATIPICA_SETOR":
                self._add_alert(20, 0, a.get("motivo", "Alta taxa de retenção financeira no setor (trava de pagamentos)"), "RETENCAO_ATIPICA_SETOR", claim_type="padrao_suspeito", evidence_tier="T2")
            
        # Top Credores Concentration
        # If the top 1 creditor consumes more than 40% of the budget and it's a high budget (> 100k)
        total_setor = rede_cred.get("totalPagoNoSetorExercicio", 0.0) + rede_cred.get("totalPagoNoSetorRestos", 0.0)
        top_cnpjs = rede_cred.get("topCredoresCNPJPrivados", [])
        if total_setor > 100000 and top_cnpjs:
            top_cred = top_cnpjs[0]
            if top_cred.get("percOrcamento", 0) > 40:
                self._add_alert(25, 0, f"Concentração Setorial: Credor principal {top_cred['nomeExtraido']} reteve {top_cred['percOrcamento']}% do orçamento distribuído.", "SETOR_CONCENTRACAO_ALTA", claim_type="padrao_suspeito", evidence_tier="T2")

    def _score_family(self):
        rf = self.tree.get("redeFamiliar", {}).get("nucleosEncontrados", [])
        if not rf:
            return
            
        for nucleo in rf:
            forca = nucleo.get("forcaEvidencia", "FRACA")
            qtd = nucleo.get("qtdMembros", 0)
            
            # V4.1.1: Trilha 4 Sanguessuga — GATED by evidence strength
            alert_type = nucleo.get("alertaSanguessuga", False)
            if alert_type == "CONCENTRACAO_FAMILIAR_MUNICIPAL":
                # Only for FORTE nuclei — full weight
                self._add_alert(30, 40, f"Núcleo onomástico expandido com faturamento em multiplos eixos municipais.", "CONCENTRACAO_FAMILIAR_MUNICIPAL", claim_type="padrao_suspeito", evidence_tier="T2")
            elif alert_type == "CONCENTRACAO_FAMILIAR_MUNICIPAL_HIPOTESE":
                # V4.1.1: MEDIA nuclei get reduced scoring
                self._add_alert(10, 15, f"Hipótese de agrupamento onomástico em eixos secundários.", "CONCENTRACAO_FAMILIAR_HIPOTESE", claim_type="inferencia_relacional", evidence_tier="T3")
            # FRACA nuclei: NO alert emitted at all
            
            if forca == "FORTE":
                 self._add_alert(5, 30, f"Agrupamento nominal com similaridades fortes: {qtd} membros ({nucleo['sobrenomesCore']})", "NUCLEO_FAMILIAR_FORTE", claim_type="inferencia_relacional", evidence_tier="T2")
            elif forca == "MEDIA":
                 self._add_alert(0, 15, f"Possível rede onomástica orbitante: {qtd} membros ({nucleo['sobrenomesCore']})", "NUCLEO_FAMILIAR_MEDIO", claim_type="inferencia_relacional", evidence_tier="T3")

        # Ondas de Nomeação in sector
        ondas = self.tree.get("redeSetor", {}).get("ondasNomeacao", [])
        if ondas:
            msg = f"{len(ondas)} meses com clusters sintéticos atípicos de nomeação simultânea no setor (>4)"
            self._add_alert(0, 20, msg, "SETOR_ONDA_NOMEACAO", claim_type="padrao_suspeito", evidence_tier="T2")

    def _score_multiple_jobs(self):
        mats = self.tree.get("dadosFuncionais", {}).get("matriculas", [])
        ativas = [m for m in mats if "TRABALHANDO" in m.get("situacao", "").upper()]
        
        if len(ativas) >= 2:
            self._add_alert(10, 10, f"Acúmulo Funcional: {len(ativas)} matrículas ativas listadas em remuneração paralela.", "ACUMULO_CARRGOS", claim_type="fato_direto", evidence_tier="T1")

    def _score_functional_coherence(self):
        mats = self.tree.get("dadosFuncionais", {}).get("matriculas", [])
        
        # Tags that strongly indicate a political, advisory, or administrative role not tied to specialized technical delivery
        political_roles = ["ASSESSOR", "GABINETE", "PARLAMENTAR", "APOIO", "COORDENADOR"]
        
        # Tags that indicate protected/technical funds
        technical_sources = ["SAUDE", "F.M.S", "ESF", "FUNDEB", "ASSISTENCIA SOCIAL", "F.M.A.S", "VIGILANCIA"]
        
        for m in mats:
            if "TRABALHANDO" not in str(m.get("situacao", "")).upper():
                continue
                
            cargo = str(m.get("cargo", "")).upper()
            centro = str(m.get("centroCusto", "")).upper()
            classificacao = str(m.get("classificacao", "")).upper()
            local = str(m.get("localTrabalho", "")).upper()
            
            # Strict exclusions to avoid false positives
            if "SECRETARIO" in cargo or "SECRETÁRIO" in cargo or "MEDICO" in cargo or "PROFESSOR" in cargo or "ENFERMEIRO" in cargo:
                continue
                
            is_political = any(r in cargo for r in political_roles)
            if not is_political and str(m.get("formaInvestidura", "")).upper() == "CARGO COMISSIONADO":
                 is_political = True
                 
            if not is_political:
                continue
                
            source_str = f"{centro} {classificacao} {local}"
            
            matched_tech = [t for t in technical_sources if t in source_str]
            if matched_tech:
                # Prevent false positive: e.g., "COORDENADOR DA VIGILANCIA SANITARIA" is in Vigilancia.
                # If the exact technical source is in the job title, it's coherent.
                if matched_tech[0] in cargo:
                    continue
                    
                self._add_alert(20, 10, f"Coerência Funcional: Cargo de viés de assessoria ({m.get('cargo')}) em empenho técnico ({matched_tech[0]}).", "DESVIO_FUNCAO_FONTE", claim_type="padrao_suspeito", evidence_tier="T2")

    def _score_cross_connections(self):
        cc = self.tree.get("conexoesCruzadas", {}).get("outrosAlvosRelacionados", [])
        
        shared_creditors = sum(1 for c in cc if c.get("tipoConexao") == "shared_creditor")
        shared_surnames = sum(1 for c in cc if c.get("tipoConexao") == "shared_surname")
        
        if shared_creditors > 0:
            self._add_alert(25, 20, f"Rede financeira transversal: {shared_creditors} credores recorrentes deste setor também faturam em setores de outros Alvos.", "CONEXAO_CREDOR_CRUZADO", claim_type="padrao_suspeito", evidence_tier="T2")
            
            
        if shared_surnames > 0:
            self._add_alert(0, 15, f"Intersecção Onomástica: Rede relacional ligada via sobrenomes a {shared_surnames} outros alvos.", "CONEXAO_FAMILIA_CRUZADA", claim_type="inferencia_relacional", evidence_tier="T3")

    def _score_transversals(self):
        trans = self.tree.get("transversal_alerts", [])
        for a in trans:
            if a.get("tipo") == "CREDOR_TRANSVERSAL":
                self._add_alert(40, 30, f"Extrema Transversalidade (ALERTA): {a.get('credor')} faturou ativamente em domínios de {a.get('qtd_alvos')} Alvos Distintos e {a.get('qtd_setores')} pastas.", "CREDOR_TRANSVERSAL", claim_type="padrao_suspeito", evidence_tier="T2")

    def _score_temporal(self):
        temp_alerts = self.tree.get("temporal_alerts", [])
        for a in temp_alerts:
            origem = a.get("origem", "")
            perc = a.get("perc_dezembro", 0)
            self._add_alert(30, 15, f"Sazonalidade Externa (Teto Anual): {a.get('nome')} reteve {perc}% da verba inteira na liquidação residual de Dezembro.", "TEMPORAL_FIM_ANO", claim_type="padrao_suspeito", evidence_tier="T2")

    def _score_societary(self):
        soc_alerts = self.tree.get("societary_alerts", [])
        for a in soc_alerts:
            codigo = a.get("codigo", a.get("tipo", "SOCIETARIA_DESCONHECIDA"))
            desc = a.get("descricao", f"Alerta societário identificado: {codigo}")
            risco_fin = a.get("risco_financeiro", 20)
            claim = a.get("claim_type", "padrao_suspeito")
            tier = a.get("evidence_tier", "T2")
            
            # O motor de regras (societary_rules) já constrói as inferências de T1/T2
            # O impacto relacional de CNPJ geralmente mapeia zero pra T1 material e pode ter impacto indireto nas redes.
            # Fixaremos em 5 para manter constância no Relacional em anomalias de empresa.
            self._add_alert(risco_fin, 5, desc, codigo, claim_type=claim, evidence_tier=tier)

    def _score_timeline(self):
        mats = self.tree.get("dadosFuncionais", {}).get("matriculas", [])
        admissoes = []
        for m in mats:
            dt = _parse_date(m.get("admissao", ""))
            if dt: admissoes.append(dt)
            
        if not admissoes: return
        primeira_admissao = min(admissoes)
        
        # Check family network for synchronization
        rf = self.tree.get("redeFamiliar", {}).get("nucleosEncontrados", [])
        for nucleo in rf:
            detalhes = nucleo.get("credoresDetalhes", {})
            for cnpj, ninfo in detalhes.items():
                pdt = _parse_date(ninfo.get("primeiroPagamento", ""))
                if pdt:
                    diff_days = (pdt - primeira_admissao).days
                    if 0 <= diff_days <= 30:
                        self._add_alert(40, 30, f"Sincronicidade Imediata: Entidade autuada ({ninfo.get('nome')}) passou a faturar somente {diff_days} dias desde a admissão pública do Alvo.", "SINCRONICIDADE_PAGAMENTO_POS_NOMEACAO", claim_type="padrao_suspeito", evidence_tier="T2")
                    elif 30 < diff_days <= 90:
                        self._add_alert(30, 20, f"Sincronicidade Tátil: Faturamento iniciado {diff_days} após posse pública do Alvo.", "SINCRONICIDADE_PAGAMENTO_POS_NOMEACAO", claim_type="padrao_suspeito", evidence_tier="T2")
                    elif 90 < diff_days <= 180:
                        self._add_alert(20, 10, f"Aceleração de Carteira de Recebimentos {diff_days} dias pós posse.", "SINCRONICIDADE_PAGAMENTO_POS_NOMEACAO", claim_type="padrao_suspeito", evidence_tier="T2")

    def _score_evidence_quality(self):
        # Base 100.
        # Penalize if exact target person wasn't found perfectly
        status_res = self.tree.get("alvo", {}).get("statusResolucao")
        if status_res != "EXATO":
            self.evidencia -= 30
            
        # BUG A FIX: Penalize heavily for ambiguous payment matches
        pd = self.tree.get("pagamentosDiretos", {})
        ambiguos = pd.get("qtdMatchesAmbiguos", 0)
        fracos = pd.get("qtdMatchesMedios", 0) # Treating FRACA/MEDIA as slight penalty
        
        if ambiguos > 0:
            self.evidencia -= min(40, ambiguos * 10)
        if fracos > 0:
            self.evidencia -= min(20, fracos * 5)
