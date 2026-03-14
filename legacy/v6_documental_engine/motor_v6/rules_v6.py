from datetime import date
from typing import List, Optional
from schemas_v6 import (
    PaymentEvent, LiquidationDocument, CompanyProfile, AlertEvent, 
    ClaimType, EvidenceTier, Severity, TargetEvent
)
from normalizers_v6 import cnpj_root, normalize_doc

def detect_beneficiary_triangulation(payment: PaymentEvent, doc: LiquidationDocument) -> List[AlertEvent]:
    """
    Regra 1: Triangulação de Beneficiário.
    Compara o credor macro com o emissor real do documento fiscal.
    """
    alerts = []
    
    macro_doc = normalize_doc(payment.credor_documento_num)
    nf_doc = normalize_doc(doc.credor_documento_num)
    
    if not macro_doc or not nf_doc:
        return alerts
        
    # Match exato - sem alerta
    if macro_doc == nf_doc:
        return alerts
        
    macro_root = cnpj_root(macro_doc)
    nf_root = cnpj_root(nf_doc)
    
    # Caso B: CNPJ diferente, mas mesma raiz (Ex: Matriz vs Filial)
    if macro_root and nf_root and macro_root == nf_root:
        alerts.append(AlertEvent(
            alert_id=f"TRIANG_MED_{payment.payment_id}_{doc.document_id}",
            rule_code="TRIANGULACAO_BENEFICIARIO_MESMA_RAIZ",
            claim_type=ClaimType.PADRAO_SUSPEITO,
            evidence_tier=EvidenceTier.T2,
            severity=Severity.MEDIUM,
            title="Divergência de Filial: Credor Macro diverge da Nota Fiscal",
            description=f"O credor do pagamento ({macro_doc}) diverge do emissor do comprovante ({nf_doc}), porém partilham o mesmo CNPJ Raiz ({macro_root}).",
            explanation="Geralmente se trata de faturamento centralizado de matriz/filial, porém vale auditoria simplificada.",
            score_financeiro=0,
            score_relacional=10,
            payment_id=payment.payment_id,
            document_id=doc.document_id,
            company_cnpj=nf_doc,
            evidence={
                "macro_cnpj": macro_doc,
                "documento_cnpj": nf_doc,
                "macro_nome": payment.credor_nome_raw
            }
        ))
    # Caso C: CNPJ com raiz diferente (Triangulação de Laranja)
    elif macro_root != nf_root:
        alerts.append(AlertEvent(
            alert_id=f"TRIANG_CRIT_{payment.payment_id}_{doc.document_id}",
            rule_code="TRIANGULACAO_BENEFICIARIO_FORTE",
            claim_type=ClaimType.FATO_OBJETIVO,
            evidence_tier=EvidenceTier.T1,
            severity=Severity.CRITICAL,
            title="Triangulação Material: Descasamento de Beneficiário",
            description=f"O documento fiscal foi emitido pelo CNPJ raiz distinto {nf_root}, diverindo inteiramente do credor orçamentário ({macro_root}).",
            explanation="A divergência abrupta de beneficiário aponta para corrupção por interposta pessoa (Empresa Fantasma transferindo saldo) ou falha grave de registro.",
            score_financeiro=80, # Adiciona Risco Severo
            score_relacional=10,
            payment_id=payment.payment_id,
            document_id=doc.document_id,
            company_cnpj=nf_doc,
            evidence={
                "macro_cnpj": macro_doc,
                "documento_cnpj": nf_doc,
                "macro_nome": payment.credor_nome_raw
            }
        ))
        
    return alerts


def detect_nf_before_company_exists(doc: LiquidationDocument, company: CompanyProfile) -> List[AlertEvent]:
    """
    Regra 2: Empresa Inexistente / NF Fria de Fachada na Data da Emissão.
    Compara a data do documento com a data de início de atividade.
    """
    alerts = []
    
    if not doc.data_documento or not company.data_inicio_atividade:
        return alerts
        
    delta = (doc.data_documento - company.data_inicio_atividade).days
    
    # Caso A: Nota emitida ANTES da empresa existir oficialmente (NF FRIA CLÁSSICA)
    if delta < 0:
         alerts.append(AlertEvent(
            alert_id=f"NFFRIA_{doc.document_id}_{company.cnpj}",
            rule_code="NF_FRIA_EMPRESA_INEXISTENTE",
            claim_type=ClaimType.FATO_OBJETIVO,
            evidence_tier=EvidenceTier.T1,
            severity=Severity.CRITICAL,
            title="Nota Fiscal Fria: Emissão Anterior à Abertura da Empresa",
            description=f"O documento n. {doc.numero_documento} tem emissão datada de {doc.data_documento.isoformat()}, porém a empresa {company.cnpj} só foi constituída em {company.data_inicio_atividade.isoformat()}.",
            explanation="Impossibilidade física e jurídica de emissão. Acusa fraude de documentação, desvio contábil gravíssimo ou adulteração forçada de registros do painel.",
            score_financeiro=100, 
            score_relacional=0,
            document_id=doc.document_id,
            company_cnpj=company.cnpj,
            evidence={
                "data_nota_fiscal": doc.data_documento.isoformat(),
                "data_abertura_rfb": company.data_inicio_atividade.isoformat(),
                "dias_de_diferenca": delta
            }
        ))
    # Caso B: Empresa de Prateleira Forte
    elif 0 <= delta <= 180:
         alerts.append(AlertEvent(
            alert_id=f"PRATELER_FORTE_{doc.document_id}_{company.cnpj}",
            rule_code="EMPRESA_PRATELEIRA_FORTE",
            claim_type=ClaimType.PADRAO_SUSPEITO,
            evidence_tier=EvidenceTier.T2,
            severity=Severity.HIGH,
            title="Empresa de Prateleira (Forte): Faturamento Imediato",
            description=f"A empresa faturou sua primeira nota fiscal {delta} dias após sua abertura oficial na Receita Federal.",
            explanation="Empresas criadas poucas semanas antes de receber verbas públicas frequentemente sinalizam arranjos fraudulentos engatilhados.",
            score_financeiro=40, 
            score_relacional=20,
            document_id=doc.document_id,
            company_cnpj=company.cnpj,
            evidence={
                "data_nota_fiscal": doc.data_documento.isoformat(),
                "data_abertura_rfb": company.data_inicio_atividade.isoformat(),
                "dias_de_diferenca": delta
            }
        ))
    # Caso C: Empresa de Prateleira Média
    elif 181 <= delta <= 365:
         alerts.append(AlertEvent(
            alert_id=f"PRATELER_MED_{doc.document_id}_{company.cnpj}",
            rule_code="EMPRESA_PRATELEIRA_MEDIA",
            claim_type=ClaimType.PADRAO_SUSPEITO,
            evidence_tier=EvidenceTier.T2,
            severity=Severity.MEDIUM,
            title="Empresa Nova (Média): Faturamento Acelerado",
            description=f"A empresa faturou para o órgão com {delta} dias de vida comercial registrada.",
            explanation="Padrão não usual para contratação governamental, embora mais fraco do que o nível de Prateleira Imediata. Combina com outros achados.",
            score_financeiro=10, 
            score_relacional=10,
            document_id=doc.document_id,
            company_cnpj=company.cnpj,
            evidence={
                "data_nota_fiscal": doc.data_documento.isoformat(),
                "data_abertura_rfb": company.data_inicio_atividade.isoformat(),
                "dias_de_diferenca": delta
            }
        ))
        
    return alerts


def detect_extreme_synchrony(target: TargetEvent, docs: List[LiquidationDocument]) -> List[AlertEvent]:
    """
    Regra 3: Sincronicidade Extrema Fato/Documento.
    Mede a distância entre a posse do político/assessor e a primeira nota fiscal emitida pelo credor.
    Presume que `docs` são apenas os documentos ligados ao credor previamente associado ao Alvo.
    """
    alerts = []
    if not target.admissao or not docs:
        return alerts
        
    # Ordenar NFs da mais antiga para a mais recente
    valid_docs = [d for d in docs if d.data_documento]
    if not valid_docs:
        return alerts
        
    valid_docs.sort(key=lambda x: x.data_documento)
    first_doc = valid_docs[0]
    
    delta = (first_doc.data_documento - target.admissao).days
    
    # Ignoramos se a nota fiscal ocorreu ANTES da nomeação
    if delta < 0:
        return alerts
        
    # Faixas de Sincronicidade
    if 0 <= delta <= 30:
         alerts.append(AlertEvent(
            alert_id=f"SYNC_FORTE_{target.target_id}_{first_doc.document_id}",
            rule_code="SINCRONICIDADE_EXTREMA_FORTE",
            claim_type=ClaimType.PADRAO_SUSPEITO,
            evidence_tier=EvidenceTier.T2,
            severity=Severity.HIGH,
            title="Sincronicidade Extrema (Forte): NF emitida em até 30 dias após posse",
            description=f"A primeira nota fiscal (NF {first_doc.numero_documento}) da empresa associada ao credor {first_doc.credor_documento_num} foi emitida apenas {delta} dias após a nomeação/admissão do alvo {target.nome}.",
            explanation="Volume alto de faturamento iniciado imediatamente após a posse de um aliado político sinaliza possível loteamento da pasta para favorecimento.",
            score_financeiro=30, 
            score_relacional=40,
            target_id=target.target_id,
            document_id=first_doc.document_id,
            company_cnpj=first_doc.credor_documento_num,
            evidence={
                "data_posse_alvo": target.admissao.isoformat(),
                "data_primeira_nf": first_doc.data_documento.isoformat(),
                "dias_de_diferenca": delta,
                "cargo_alvo": target.cargo
            }
        ))
    elif 31 <= delta <= 90:
         alerts.append(AlertEvent(
            alert_id=f"SYNC_MED_{target.target_id}_{first_doc.document_id}",
            rule_code="SINCRONICIDADE_EXTREMA_MEDIA",
            claim_type=ClaimType.PADRAO_SUSPEITO,
            evidence_tier=EvidenceTier.T2,
            severity=Severity.MEDIUM,
            title="Sincronicidade (Média): NF emitida em até 90 dias após posse",
            description=f"A NF n. {first_doc.numero_documento} da empresa associada foi faturada {delta} dias após a posse do alvo {target.nome}.",
            explanation="Padrão suspeito, indicando que nos primeiros meses do mandato do aliado, a empresa satélite já venceu as licitações ou dispensas.",
            score_financeiro=10, 
            score_relacional=20,
            target_id=target.target_id,
            document_id=first_doc.document_id,
            company_cnpj=first_doc.credor_documento_num,
            evidence={
                "data_posse_alvo": target.admissao.isoformat(),
                "data_primeira_nf": first_doc.data_documento.isoformat(),
                "dias_de_diferenca": delta
            }
        ))
    elif 91 <= delta <= 180:
         alerts.append(AlertEvent(
            alert_id=f"SYNC_CTX_{target.target_id}_{first_doc.document_id}",
            rule_code="SINCRONICIDADE_EXTREMA_CONTEXTUAL",
            claim_type=ClaimType.HIPOTESE_RELACIONAL,
            evidence_tier=EvidenceTier.T3,
            severity=Severity.LOW,
            title="Sincronicidade (Contextual): NF emitida em até 180 dias após posse",
            description=f"O início do faturamento do credor associado ocorreu {delta} dias após o ingresso do alvo no serviço.",
            explanation="Evidência fraca por si só. Apenas serve para agravar o contexto relacional do grafo.",
            score_financeiro=0, 
            score_relacional=10,
            target_id=target.target_id,
            document_id=first_doc.document_id,
            company_cnpj=first_doc.credor_documento_num,
            evidence={
                "data_posse_alvo": target.admissao.isoformat(),
                "data_primeira_nf": first_doc.data_documento.isoformat(),
                "dias_de_diferenca": delta
            }
        ))
        
    return alerts

def detect_smurfing(cnpj_credor: str, docs: List[LiquidationDocument]) -> List[AlertEvent]:
    """
    Regra 4: Smurfing Contábil / Fracionamento Sequencial Físico.
    Detecta se um fornecedor emitiu várias NFs com números próximos em datas próximas.
    docs: Lista de todos os documentos DAQUELE CNPJ.
    """
    alerts = []
    
    # Filtra apenas documentos que possuem data e numero válidos
    valid_docs = []
    for d in docs:
        if d.data_documento and d.numero_documento:
             try:
                 num = int(''.join(c for c in d.numero_documento if c.isdigit()))
                 valid_docs.append((d, num))
             except ValueError:
                 continue
                 
    if len(valid_docs) < 2:
        return alerts
        
    # Ordena por Data, depois por Número da Nota
    valid_docs.sort(key=lambda x: (x[0].data_documento, x[1]))
    
    for i in range(len(valid_docs) - 1):
        doc_a, num_a = valid_docs[i]
        doc_b, num_b = valid_docs[i+1]
        
        # O documento_b sempre terá data igual ou maior que documento_a
        delta_days = (doc_b.data_documento - doc_a.data_documento).days
        delta_num = num_b - num_a
        
        # Smurfing Forte: Emissão na mesma semana E número da nota separado por até 5 posições
        if 0 <= delta_days <= 7 and 1 <= delta_num <= 5:
             
             soma_valor = doc_a.valor_documento + doc_b.valor_documento
             
             alerts.append(AlertEvent(
                alert_id=f"SMURF_{doc_a.document_id}_{doc_b.document_id}",
                rule_code="SMURFING_CONTABIL_FORTE",
                claim_type=ClaimType.PADRAO_SUSPEITO,
                evidence_tier=EvidenceTier.T2,
                severity=Severity.HIGH,
                title="Smurfing Contábil: Fracionamento Físico de Notas Fiscais",
                description=f"A empresa {cnpj_credor} emitiu duas notas fiscais de sequência muito próxima (NF {num_a} e NF {num_b}) num intervalo de apenas {delta_days} dias, somando R$ {soma_valor:.2f}.",
                explanation="Emissão sequencial quase ininterrupta de notas de empenhos fracionados denuncia burla do limite de licitação, cortando um grande serviço em micro-contratos.",
                score_financeiro=40, 
                score_relacional=0,
                company_cnpj=cnpj_credor,
                document_id=doc_a.document_id,
                evidence={
                    "nf_a_numero": num_a,
                    "nf_a_data": doc_a.data_documento.isoformat(),
                    "nf_a_valor": doc_a.valor_documento,
                    "nf_b_numero": num_b,
                    "nf_b_data": doc_b.data_documento.isoformat(),
                    "nf_b_valor": doc_b.valor_documento,
                    "dias_distancia": delta_days,
                    "pulos_de_nota": delta_num,
                    "soma_identificada": soma_valor
                }
            ))
            
    return alerts


def detect_irregular_company(doc: LiquidationDocument, company: CompanyProfile) -> List[AlertEvent]:
    """
    Fase 9 / Regra 5: Empresa Inapta/Baixada recebendo pagamentos.
    Compara a Situação Cadastral no momento com o histórico de faturamento.
    """
    alerts = []
    irregular_status = ["INAPTA", "BAIXADA", "SUSPENSA", "NULA"]
    
    if company.situacao_cadastral and company.situacao_cadastral.upper() in irregular_status:
        alerts.append(AlertEvent(
            alert_id=f"IRREGULAR_{doc.document_id}_{company.cnpj}",
            rule_code="EMPRESA_IRREGULAR_RECEBENDO",
            claim_type=ClaimType.FATO_OBJETIVO,
            evidence_tier=EvidenceTier.T1,
            severity=Severity.CRITICAL,
            title="Recebimento por Empresa Irregular (Inapta/Baixada)",
            description=f"A empresa {company.cnpj} emitiu o documento {doc.numero_documento} cobrando a Prefeitura, mas seu status na Receita Federal encontra-se bloqueado como {company.situacao_cadastral.upper()}.",
            explanation="O uso de CNPJs irregulares ou suspensos em contratações ofende frontalmente a Lei de Licitações, denotando negligência extrema, conluio ou simulação fiscal de fachada.",
            score_financeiro=40,
            score_relacional=0,
            document_id=doc.document_id,
            company_cnpj=company.cnpj,
            evidence={
                "situacao_rfb": company.situacao_cadastral,
                "data_nota_fiscal": doc.data_documento.isoformat() if doc.data_documento else None,
                "faturamento": doc.valor_documento
            }
        ))
    return alerts

def detect_hidden_partner(target: TargetEvent, company: CompanyProfile, docs: List[LiquidationDocument]) -> List[AlertEvent]:
    """
    Fase 9 / Regra 6: Sócio Oculto Cruzado.
    Detecta se o alvo (Político/Servidor) é Sócio do Fornecedor recebedor via CPF parcial.
    """
    alerts = []
    
    if not target.cpf or not company.qsa or not docs:
        return alerts
        
    for qsa in company.qsa:
        socio_cpf = qsa.get("cnpj_cpf_socio", "")
        # Mask matching ***.123.456-**
        if socio_cpf and len(socio_cpf) == 14 and "***" in socio_cpf:
            if socio_cpf[3:11] == target.cpf[3:11]: # Compara o miolo
                 
                 total_faturado = sum(d.valor_documento for d in docs)
                 
                 alerts.append(AlertEvent(
                    alert_id=f"SOCIO_OCULTO_{target.target_id}_{company.cnpj}",
                    rule_code="SOCIETARIA_SOCIO_OCULTO",
                    claim_type=ClaimType.FATO_OBJETIVO,
                    evidence_tier=EvidenceTier.T1,
                    severity=Severity.CRITICAL,
                    title="Autocontratação: Servidor possui vínculo societário com fornecedor",
                    description=f"O servidor {target.nome} ({target.cpf}) coincide deterministicamente com a máscara societária ({socio_cpf}) do fornecedor {company.cnpj}, que faturou R$ {total_faturado:.2f}.",
                    explanation="Servidores ativos participando do QSA de empresas contratadas pelo próprio ente gera evidente conflito de interesses, fraude a licitação e autobenefício.",
                    score_financeiro=50,
                    score_relacional=30,
                    target_id=target.target_id,
                    company_cnpj=company.cnpj,
                    evidence={
                        "funcionario_nome": target.nome,
                        "funcionario_cpf": target.cpf,
                        "socio_nome_qsa": qsa.get("nome_socio", ""),
                        "socio_cpf_mask": socio_cpf,
                        "total_faturado_observado": total_faturado
                    }
                ))
                 break # Basta um match para acender a empresa
    return alerts
    
def detect_direct_employee_supplier(target: TargetEvent, docs: List[LiquidationDocument]) -> List[AlertEvent]:
    """
    Fase 9 / Regra 7: Servidor Ativo Fornecendo Diretamente como PF.
    Compara o credor da NF (PF) e o CPF do Alvo Ativo.
    """
    alerts = []
    
    if not target.cpf or not docs:
        return alerts
        
    for doc in docs:
        # Puxa apenas documentos cujo credor tem exatos 14 chars (CPF puro sem formatação especial ou já formatado igual)
        # Vamos tratar removendo tudo que não for dígito e comparando
        cpf_limpo = "".join(filter(str.isdigit, target.cpf))
        doc_limpo = "".join(filter(str.isdigit, doc.credor_documento_num))
        
        if cpf_limpo and doc_limpo and cpf_limpo == doc_limpo:
             alerts.append(AlertEvent(
                alert_id=f"PF_FORNECEDOR_{target.target_id}_{doc.document_id}",
                rule_code="SERVIDOR_ATIVO_FORNECEDOR_DIRETO",
                claim_type=ClaimType.FATO_OBJETIVO,
                evidence_tier=EvidenceTier.T1,
                severity=Severity.CRITICAL,
                title="Autocontratação Direta: Servidor recebendo como Pessoa Física",
                description=f"O credor PF emissor do documento {doc.numero_documento} (R$ {doc.valor_documento:.2f}) é o próprio servidor lotado: {target.nome}.",
                explanation="Excluídos vínculos trabalhistas e diárias, faturamento extra-folha na veia para o próprio servidor doente fere o princípio de moralidade contábil.",
                score_financeiro=35,
                score_relacional=10,
                target_id=target.target_id,
                document_id=doc.document_id,
                company_cnpj=doc.credor_documento_num, # É um CPF, mas o campo guarda o credor geral
                evidence={
                    "cpf_servidor": target.cpf,
                    "cpf_faturamento": doc.credor_documento_num,
                    "cargo_ativo": target.cargo,
                    "valor_cobrado": doc.valor_documento
                }
            ))
            
    return alerts


def detect_transversal_supplier(company: CompanyProfile, related_payments: List[PaymentEvent]) -> List[AlertEvent]:
    """
    Fase 10 / Regra 8: Credor Transversal Monopolista (T2).
    Se o credor opera com 3 ou mais Secretarias diferentes.
    """
    alerts = []
    if not related_payments:
        return alerts
        
    orgaos_distintos = set([p.orgao_descricao for p in related_payments if p.orgao_descricao])
    
    if len(orgaos_distintos) >= 3:
         total_val = sum(p.valor_pago for p in related_payments)
         orgaos_lista = ", ".join(list(orgaos_distintos)[:3]) + ("..." if len(orgaos_distintos)>3 else "")
         
         alerts.append(AlertEvent(
            alert_id=f"TRANSVERSAL_{company.cnpj}",
            rule_code="CREDOR_TRANSVERSAL_FORTE",
            claim_type=ClaimType.PADRAO_SUSPEITO,
            evidence_tier=EvidenceTier.T2,
            severity=Severity.HIGH,
            title="Credor Transversal: Atuação monopolista em múltiplas pastas",
            description=f"A empresa {company.razao_social or company.cnpj} forneceu para {len(orgaos_distintos)} Órgãos distintos (incluindo {orgaos_lista}), faturando R$ {total_val:.2f}.",
            explanation="Volume alto pulverizado em secretarias ideologicamente e tecnicamente não-relacionadas acusa loteamento e cartelização do fornecedor que se torna 'dono' da prefeitura.",
            score_financeiro=30,
            score_relacional=20,
            company_cnpj=company.cnpj,
            evidence={
                "qtd_orgaos": len(orgaos_distintos),
                "orgaos_envolvidos": list(orgaos_distintos),
                "total_pago": total_val
            }
        ))
    return alerts

def detect_cnae_incompatibility(company: CompanyProfile, payment: PaymentEvent) -> List[AlertEvent]:
    """
    Fase 10 / Regra 9: CNAE Incompatível Material (T2).
    Compara o Ramo de Atividade com o Fundo Pagador.
    """
    alerts = []
    if not company.cnae_principal_codigo or not payment.orgao_descricao:
        return alerts
        
    cnae = company.cnae_principal_codigo
    orgao = payment.orgao_descricao.upper()
    
    incompatibilidade = False
    motivo = ""
    
    # 8230 = Organização de Eventos, 5611 = Restaurantes e Alimentação, 7311 = Agência de Publicidade
    if "SAUDE" in orgao and cnae.startswith(("8230", "7311")):
         incompatibilidade = True
         motivo = "Empresa de Eventos/Publicidade faturando contra Fundo de Saúde."
         
    if "EDUCACAO" in orgao and cnae.startswith(("4771", "4772")): # Medicamentos
         incompatibilidade = True
         motivo = "Empresa de Medicamentos faturando contra Educação."
         
    if incompatibilidade:
         alerts.append(AlertEvent(
            alert_id=f"CNAE_INCOMPAT_{payment.payment_id}",
            rule_code="CNAE_INCOMPATIBILIDADE_MATERIAL",
            claim_type=ClaimType.PADRAO_SUSPEITO,
            evidence_tier=EvidenceTier.T2,
            severity=Severity.HIGH,
            title="Incompatibilidade Material: CNAE diverge da finalidade do Fundo",
            description=f"O pagamento do órgão '{payment.orgao_descricao}' foi destinado à empresa {company.cnpj} cujo CNAE ({cnae}) não condiz com a natureza do repasse institucional.",
            explanation=motivo,
            score_financeiro=25,
            score_relacional=5,
            payment_id=payment.payment_id,
            company_cnpj=company.cnpj,
            evidence={
                "orgao": payment.orgao_descricao,
                "cnae_codigo": cnae,
                "motivo_incompatibilidade": motivo
            }
        ))
    return alerts

def detect_year_end_drain(company: CompanyProfile, docs: List[LiquidationDocument]) -> List[AlertEvent]:
    """
    Fase 10 / Regra 10: Esvaziamento de Fim de Ano (T2).
    Mais de 70% das NFs nas duas últimas semanas de dezembro.
    """
    alerts = []
    if not docs:
        return alerts
        
    total_val = 0.0
    dez_val = 0.0
    
    for d in docs:
        val = d.valor_documento
        total_val += val
        if d.data_documento and d.data_documento.month == 12 and d.data_documento.day >= 15:
            dez_val += val
            
    if total_val > 0 and (dez_val / total_val) > 0.70 and dez_val > 10000:
         pct = (dez_val / total_val) * 100
         alerts.append(AlertEvent(
            alert_id=f"DRAIN_{company.cnpj}",
            rule_code="TEMPORAL_FIM_ANO",
            claim_type=ClaimType.PADRAO_SUSPEITO,
            evidence_tier=EvidenceTier.T2,
            severity=Severity.MEDIUM,
            title="Esvaziamento Orçamentário de Fim de Ano",
            description=f"A empresa faturou {pct:.1f}% (R$ {dez_val:.2f}) de todo o seu volume nas últimas semanas de dezembro.",
            explanation="Gastos massivos concentrados no fechamento do exercício fiscal geralmente apontam uso da dotação remanescente (quebra de orçamento) em contratações aceleradas sem prestação real do serviço.",
            score_financeiro=20,
            score_relacional=5,
            company_cnpj=company.cnpj,
            evidence={
                "total_ano": total_val,
                "total_dezembro_final": dez_val,
                "percentual_acumulado": pct
            }
        ))
    return alerts

def detect_sector_concentration(company: CompanyProfile, related_payments: List[PaymentEvent], sect_totals: dict) -> List[AlertEvent]:
    """
    Fase 10 / Regra 11: Concentração Setorial de Risco (T2).
    Se o fornecedor tem > 40% do orçamento do Órgão.
    sect_totals = {"SECRETARIA A": 1000000.00}
    """
    alerts = []
    if not related_payments:
        return alerts
        
    # Agrupa val recebido por este CNPJ em cada Órgão
    val_por_orgao = {}
    for p in related_payments:
         org = p.orgao_descricao
         if org:
             val_por_orgao[org] = val_por_orgao.get(org, 0.0) + p.valor_pago
             
    for orgao, val_recebido in val_por_orgao.items():
         total_orgao = sect_totals.get(orgao, 0.0)
         if total_orgao > 0:
              pct = (val_recebido / total_orgao) * 100
              if pct > 40.0 and val_recebido > 50000:
                   alerts.append(AlertEvent(
                      alert_id=f"CONCENTRA_{company.cnpj}_{orgao[:10]}",
                      rule_code="CONCENTRACAO_SETORIAL_ALTA",
                      claim_type=ClaimType.PADRAO_SUSPEITO,
                      evidence_tier=EvidenceTier.T2,
                      severity=Severity.MEDIUM,
                      title="Concentração Extrema: Monopólio Setorial",
                      description=f"O credor detém {pct:.1f}% de todo o orçamento rastreado na pasta '{orgao}' (R$ {val_recebido:.2f} de R$ {total_orgao:.2f}).",
                      explanation="Acima de 40% denota forte dependência e quebra do princípio de concorrência e rodízio de publicidade.",
                      score_financeiro=20,
                      score_relacional=0,
                      company_cnpj=company.cnpj,
                      evidence={
                          "orgao": orgao,
                          "valor_arrecadado_credor": val_recebido,
                          "valor_total_orgao": total_orgao,
                          "percentual_monopolio": pct
                      }
                  ))
    return alerts
