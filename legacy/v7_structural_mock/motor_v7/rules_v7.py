from typing import List, Dict, Any
from schemas_v7 import EmissaoEmpenho, AlertV7, EvidenceTier, Severity, ClaimType

def rule_conta_bancaria_compartilhada(empenhos: List[EmissaoEmpenho]) -> List[AlertV7]:
    """
    Tier 1 / Regra H:
    Procura contas bancárias que receberam empenhos destinados a CNPJs diferentes.
    """
    alerts = []
    
    # Agrupa por conta corrente
    conta_agrupada = {}
    for e in empenhos:
        chave = e.conta_bancaria_chave
        if chave:
            if chave not in conta_agrupada:
                conta_agrupada[chave] = {"cnpjs": set(), "empenhos": []}
            conta_agrupada[chave]["cnpjs"].add(e.credor_cnpj)
            conta_agrupada[chave]["empenhos"].append(e)
            
    # Avalia se a mesma conta bancária tem > 1 CNPJ
    for chave, data in conta_agrupada.items():
        if len(data["cnpjs"]) > 1:
            total_val = sum(x.valor_empenho for x in data["empenhos"])
            
            alerts.append(AlertV7(
                regra="CONTA_BANCARIA_COMPARTILHADA",
                severidade=Severity.CRITICAL,
                tier=f"{EvidenceTier.T1}/{EvidenceTier.T2}",
                titulo="Conta bancária associada a múltiplos credores",
                descricao=f"A conta bancária [{chave}] foi informada no pagamento de {len(data['cnpjs'])} CNPJs distintos.",
                evidencias={
                    "banco_agencia_conta": chave,
                    "quantidade_cnpjs_diferentes": len(data["cnpjs"]),
                    "cnpjs_recebedores": list(data["cnpjs"]),
                    "valor_comum_pago": total_val
                },
                acao_auditoria=[
                    "Validar se pertencem ao mesmo grupo econômico / Matriz e Filial.",
                    "Verificar contrato social e dados bancários do processo.",
                    "Solicitar documentação de empenhamentos e procurações bancárias."
                ]
            ))
            
    return alerts


def rule_fracionamento_textual(empenhos: List[EmissaoEmpenho]) -> List[AlertV7]:
    """
    Tier 2 / Regra B: Fracionamento de Objeto
    Identifica vários empenhos na mesma despesa, no mesmo mês, com exato CNPJ e texto de histórico igual.
    """
    alerts = []
    
    # Cluster agrupando: Mês | Ação/Despesa | CNPJ | Hash_Histórico Textual
    clusters = {}
    
    for e in empenhos:
        # Se for dispensa de licitação ou outro termo que permita quebra manual de verba
        mes = e.ano_mes_emissao
        acao_despesa = f"{e.acao}_{e.despesa}"
        cnpj = e.credor_cnpj
        hash_txt = e.historico_hash
        
        if not mes or not hash_txt or not e.modalidade:
             continue
             
        cluster_key = f"{mes}|{acao_despesa}|{cnpj}|{hash_txt}"
        
        if cluster_key not in clusters:
             clusters[cluster_key] = []
        clusters[cluster_key].append(e)
        
    for key, lista in clusters.items():
         # Dispara caso haja 3 ou mais empenhos iguais exatos num curtíssimo período
         if len(lista) >= 3:
              soma_val = sum(x.valor_empenho for x in lista)
              
              if soma_val > 10000.0: # Filter minimal relevance
                  exemplo_historico = lista[0].historico
                  alerts.append(AlertV7(
                      regra="FRACIONAMENTO_OBJETO_PERIODO",
                      severidade=Severity.HIGH,
                      tier=EvidenceTier.T2,
                      titulo="Fracionamento de Contratação (Clone Textual)",
                      descricao=f"Fornecedor quebrou {len(lista)} faturamentos quase idênticos no mesmo mês e rubrica orçamentária somando R$ {soma_val:.2f}.",
                      evidencias={
                          "quantidade_faturada": len(lista),
                          "soma_burla": soma_val,
                          "intervalo_mensal": lista[0].ano_mes_emissao,
                          "credor_alvo": lista[0].credor_cnpj,
                          "exemplo_texto_empenho": exemplo_historico[:150]
                      },
                      acao_auditoria=[
                          "Requisitar NFs para entender se o serviço foi loteado artificialmente para fugir do procedimento licitatório.",
                          "Verificar a data exata dos documentos liquidados.",
                          "Avaliar dotação original se sofreu quebra proposital de modalidade Dispensa."
                      ]
                  ))
    return alerts

def rule_aditivo_precoce(empenhos: List[EmissaoEmpenho]) -> List[AlertV7]:
    """
    Tier 2 / Regra D: Aditivos suspeitos que ocorrem pouco após a homologação
    ou quantidade excessiva de empenhos apontando aditivos sob um mesmo contrato central.
    """
    alerts = []
    
    contratos = {}
    for e in empenhos:
        if e.contrato_numero:
            if e.contrato_numero not in contratos:
                contratos[e.contrato_numero] = {"aditivos": set(), "empenhos": []}
            
            if e.aditivo_numero and str(e.aditivo_numero).strip() not in ('0', 'None', '', 'null'):
                 contratos[e.contrato_numero]["aditivos"].add(str(e.aditivo_numero))
                 
            contratos[e.contrato_numero]["empenhos"].append(e)
            
    for contrato_str, tracker in contratos.items():
         if len(tracker["aditivos"]) >= 3:
              total_pago = sum(x.valor_empenho for x in tracker["empenhos"])
              alerts.append(AlertV7(
                 regra="ADITIVO_PRECOCE_OU_REPETIDO",
                 severidade=Severity.HIGH,
                 tier=EvidenceTier.T2,
                 titulo="Descalabro Contratual via Aditivos",
                 descricao=f"O respectivo contrato {contrato_str} gerou mais de {len(tracker['aditivos'])} sequências de aditivos diferentes.",
                 evidencias={
                     "contrato_base": contrato_str,
                     "quantidade_aditivos_rastreados": len(tracker["aditivos"]),
                     "aditivos": list(tracker["aditivos"]),
                     "valor_acumulado": total_pago
                 },
                 acao_auditoria=[
                     "Comprovar justificativa orçamentária que fundamentou o Aditivo Executivo.",
                     "Verificar limites da Lei 8.666 (Máx 25% para compras convencionais ou 50% em reformas)."
                 ]
              ))
              
    return alerts

def rule_retencao_atipica(empenhos: List[EmissaoEmpenho]) -> List[AlertV7]:
    """
    Tier 2 / Regra E: Retenção Atípica
    Cata retenções (tributárias/contratuais) anormalmente altas na boca do caixa.
    """
    alerts = []
    
    for e in empenhos:
        pct = e.percentual_retido
        if pct > 45.0 and e.valor_empenho > 5000: # Retendo virtualmente metade de todo pagamento
            alerts.append(AlertV7(
                 regra="RETENCAO_ATIPICA",
                 severidade=Severity.MEDIUM,
                 tier=EvidenceTier.T2,
                 titulo="Retenção de Empenho Anormal",
                 descricao=f"No empenho de R$ {e.valor_empenho:.2f}, {pct:.1f}% foram integralmente retidos (R$ {e.valor_retido:.2f}).",
                 evidencias={
                     "documento_alvo": e.empenho_numero,
                     "credor_cnpj": e.credor_cnpj,
                     "valor_bruto": e.valor_empenho,
                     "valor_retido": e.valor_retido,
                     "percentual_sugado": pct
                 },
                 acao_auditoria=[
                     "Investigar nos processos contábeis por que quase metade do dinheiro pago foi arrestado via retenção/recolhimento",
                     "Avaliar repasses a institutos ou tributos massivos não-justificados (INSS/IRRF absurdos)."
                 ]
              ))
    return alerts
