import json
import os

class Exporter:
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        
    def export_json(self, filename: str, data: dict | list):
        path = os.path.join(self.output_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Salvo: {path} ({os.path.getsize(path)/1024:.1f} KB)")
        
    def export_markdown(self, filename: str, trees: list):
        path = os.path.join(self.output_dir, filename)
        
        # Sort by total risk (financeiro + relacional) descending
        sorted_trees = sorted(trees, key=lambda x: x.get("scores", {}).get("riscoFinanceiro", 0) + x.get("scores", {}).get("riscoRelacional", 0), reverse=True)
        
        with open(path, "w", encoding="utf-8") as f:
            f.write("# Relatório de Análise de Indícios de Fraude por Alvo Político (V4.1.1)\n\n")
            f.write("> **Nota metodológica**: Este relatório identifica *indícios e hipóteses* a partir de cruzamentos algorítmicos de dados públicos. "
                    "Os montantes globais refletem critérios automáticos de vínculo por sobrenome e documento, e **requerem confirmação manual** "
                    "dos vínculos individuais antes de qualquer conclusão investigativa. Vínculos classificados como FRACO não são contabilizados nos totais.\n\n")
            
            for tree in sorted_trees:
                 alvo = tree["alvo"]
                 scores = tree.get("scores", {})
                 risco_fin = scores.get("riscoFinanceiro", 0)
                 risco_rel = scores.get("riscoRelacional", 0)
                 evid = scores.get("evidencia", 0)
                 
                 # Only render resolved targets
                 if alvo.get("statusResolucao") not in ["encontrado_direto", "encontrado_fuzzy", "EXATO", "FUZZY"]:
                     continue
                 
                 f.write(f"## 🎯 {alvo['nome']} ({alvo.get('cargoInformado', '')})\n")
                 f.write(f"**Risco Financeiro:** {risco_fin}/100 | **Risco Relacional:** {risco_rel}/100 | **Evidência:** {evid}/100\n\n")
                 
                 # Sanity warnings (V4.1.1)
                 sanity = tree.get("sanity_warnings", [])
                 if sanity:
                     f.write("### ⚡ Avisos de Sanidade (V4.1.1)\n")
                     for sw in sanity:
                         f.write(f"- `{sw['tipo']}`: {sw['motivo']}\n")
                     f.write("\n")
                 
                 # V5.1: Separar Alertas por Claim Type e Evidence Tier
                 alertas = tree.get("alertas", [])
                 if alertas:
                     fatos_diretos = [a for a in alertas if a.get("claim_type") == "fato_direto"]
                     padroes_suspeitos = [a for a in alertas if a.get("claim_type") == "padrao_suspeito"]
                     hipoteses = [a for a in alertas if a.get("claim_type") == "inferencia_relacional"]
                     outros = [a for a in alertas if not a.get("claim_type")]
                     
                     if fatos_diretos:
                         f.write("### 🛑 FATOS OBJETIVOS (Evidência T1)\n")
                         for a in fatos_diretos:
                             f.write(f"- **{a['codigo']}**: {a['descricao']}\n")
                         f.write("\n")
                         
                     if padroes_suspeitos:
                         f.write("### ⚠️ PADRÕES COMPORTAMENTAIS SUSPEITOS (Evidência T2)\n")
                         for a in padroes_suspeitos:
                             f.write(f"- **{a['codigo']}**: {a['descricao']}\n")
                         f.write("\n")
                         
                     if hipoteses:
                         f.write("### 🔍 HIPÓTESES RELACIONAIS (Precisam de Validação Humana T3)\n")
                         for a in hipoteses:
                             f.write(f"- `{a['codigo']}`: {a['descricao']}\n")
                         f.write("\n")
                         
                     if outros:
                         f.write("### 📌 Outras Constatações\n")
                         for a in outros:
                             f.write(f"- `{a['codigo']}`: {a['descricao']}\n")
                         f.write("\n")
                 
                 # Funcional
                 df = tree.get("dadosFuncionais", {})
                 f.write("### 📋 Dados Funcionais\n")
                 f.write(f"- Cargo Registrado: {df.get('cargo', 'N/A')}\n")
                 f.write(f"- Centro de Custo: {df.get('centroCusto', 'N/A')}\n")
                 f.write(f"- Salário Base: R$ {df.get('salarioBase', 0):,.2f}\n")
                 
                 mats = df.get("matriculas", [])
                 ativas = [m for m in mats if "TRABALHANDO" in str(m.get('situacao','')).upper()]
                 f.write(f"- Matrículas: {len(mats)} cadastradas, {len(ativas)} ativas\n\n")
                 
                 # Pagamentos Diretos
                 pd = tree.get("pagamentosDiretos", {})
                 val_direto = pd.get("totalPago", 0)
                 if val_direto > 0:
                     f.write("### 💰 Recebimentos Diretos (Pessoa Física)\n")
                     f.write(f"- **Total Pago ao Alvo:** R$ {val_direto:,.2f}\n\n")
                     
                 # Credores do Setor
                 rc = tree.get("redeCredoresDoSetor", {})
                 val_exercicio = rc.get("totalPagoNoSetorExercicio", 0)
                 val_restos = rc.get("totalPagoNoSetorRestos", 0)
                 val_setor = val_exercicio + val_restos
                 
                 if val_setor > 0:
                     f.write(f"### 🏢 Orçamento Distribuído pelo Setor Privado (Total: R$ {val_setor:,.2f})\n")
                     f.write(f"*(Exercício: R$ {val_exercicio:,.2f} | Restos: R$ {val_restos:,.2f})*\n\n")
                     
                     top_cnpjs = rc.get("topCredoresCNPJPrivados", [])
                     if top_cnpjs:
                         f.write("#### Top Credores (CNPJ / MEI / PJ)\n")
                         for c in top_cnpjs[:5]:
                             f.write(f"- **{c['nomeExtraido']}** ({c['documento']}): R$ {c['totalRecebido']:,.2f} ({c['percOrcamento']}%) \n")
                     
                     top_pfs = rc.get("topCredoresPFPrivados", [])
                     if top_pfs:
                         f.write("#### Top Credores (Pessoa Física)\n")
                         for c in top_pfs[:5]:
                             f.write(f"- **{c['nomeExtraido']}** ({c['documento']}): R$ {c['totalRecebido']:,.2f} ({c['percOrcamento']}%) \n")
                             
                     frac = rc.get("alertasFracionamento", [])
                     if frac:
                         f.write("\n#### ⚠️ Alertas de Fracionamento Mensal (Trilha 5)\n")
                         for f_alert in frac[:5]:
                             tag = "🚨 FORTE" if f_alert.get("classificacao") == "FORTE" else "⚠️ MÉDIO"
                             f.write(f"- {tag} | **{f_alert['credorNome']}**: {f_alert['qtdPagamentos']} pagtos no mês {f_alert['mes']} somando R$ {f_alert['somaNoMes']:,.2f}\n")
                             
                     anul = rc.get("alertasAnulacao", [])
                     if anul:
                         f.write("\n#### 📉 Anomalias de Empenho/Liquidação (Trilha 6)\n")
                         for a_alert in anul:
                             f.write(f"- 🚨 **{a_alert['tipo']}**: {a_alert['motivo']}\n")
                             
                     f.write("\n")
                 
                 # ────────────────────────────────────────────────
                 # V4.1.1: REWRITTEN Family/Network section
                 # ────────────────────────────────────────────────
                 rf = tree.get("redeFamiliar", {})
                 nucleos = rf.get("nucleosEncontrados", [])
                 
                 # Determine which surnames belong to the target themselves
                 from analysis.utils import relevant_surnames as _get_target_surnames
                 target_surnames_set = set(_get_target_surnames(alvo["nome"]))
                 
                 if nucleos:
                     f.write("### 👨‍👩‍👧‍👦 Núcleos Familiares Identificados\n")
                     
                     for n in nucleos:
                          forca = n['forcaEvidencia']
                          status = "🚨 FORTE" if forca == "FORTE" else "⚠️ MÉDIA" if forca == "MEDIA" else "🔹 FRACA"
                          
                          # V4.1.1: Determine relationship type
                          nucleo_surnames = set(s.strip() for s in n['sobrenomesCore'].split("+"))
                          is_direct_family = bool(nucleo_surnames & target_surnames_set)
                          
                          if is_direct_family:
                              relationship = "Possível família direta do alvo"
                          else:
                              relationship = "Núcleo orbitante no ecossistema político-administrativo"
                          
                          # V4.1.1: Concentration tag — only for FORTE, softer for MEDIA
                          concentration_tag = ""
                          alert_type = n.get("alertaSanguessuga", False)
                          if alert_type == "CONCENTRACAO_FAMILIAR_MUNICIPAL":
                              concentration_tag = " ⚠️ **[Volume transversal onomástico detectado]**"
                          elif alert_type == "CONCENTRACAO_FAMILIAR_MUNICIPAL_HIPOTESE":
                              concentration_tag = " 📋 **[Hipótese de agrupamento atípico]**"
                          
                          f.write(f"- {status} | **Distribuição relacional '{n['sobrenomesCore']}'** ({n['qtdMembros']} membros) — _{relationship}_{concentration_tag}\n")
                          
                          # V5.1: Trilha 4 details — ONLY for FORTE and MEDIA, with auditable language
                          if forca in ["FORTE", "MEDIA"]:
                              total_desp = n.get('totalDespesasFam', 0)
                              total_desp_exec = n.get('totalDespesasFamExerc', 0)
                              total_desp_restos = n.get('totalDespesasFamRestos', 0)
                              creds_fortes = n.get('qtdCredoresFortes', 0)
                              creds_medios = n.get('qtdCredoresMedios', 0)
                              creds_fracos = n.get('qtdCredoresFracos', 0)
                              
                              f.write(f"  - 🏢 **Impacto estimado na Prefeitura** (Trilha 4):\n")
                              f.write(f"    - *Nota: Montantes máximos estimados por critérios algorítmicos. Requerem confirmação individual dos vínculos.*\n")
                              f.write(f"    - Salários Globais da Rede (Mês Base): até R$ {n.get('totalSalariosMesFam', 0):,.2f}\n")
                              f.write(f"    - Despesas p/ Credores Ligados (Exercício): até R$ {total_desp_exec:,.2f}\n")
                              f.write(f"    - Despesas p/ Credores Ligados (Restos): até R$ {total_desp_restos:,.2f}\n")
                              f.write(f"    - Vínculos credor-família: {creds_fortes} fortes, {creds_medios} médios, {creds_fracos} fracos (descartados)\n")
                              if n.get('qtdOrgaosFaturadosFam', 0) > 0:
                                  f.write(f"    - Órgãos distintos faturados: {n.get('qtdOrgaosFaturadosFam', 0)}\n")
                          
                          # FRACA nuclei: only list members, NO financial data
                          f.write("  - 👥 Membros identificados:\n")
                          for membro in n["membros"]:
                              tag_setor = " (Mesmo Setor)" if membro["mesmoSetor"] else ""
                              f.write(f"    - {membro['nome']} ({membro['cargo']}){tag_setor}\n")
                          f.write("\n")
                          
                 # Ondas de Nomeação
                 ondas = tree.get("redeSetor", {}).get("ondasNomeacao", [])
                 if ondas:
                     f.write("### 🌊 Ondas de Nomeação no Setor (Concentração)\n")
                     for o in ondas:
                         nomes = ', '.join(o['nomes'])
                         f.write(f"- **{o['mes']}**: {o['quantidade']} nomeações ({nomes}...)\n")
                     f.write("\n")
                 
                 # Conexões Cruzadas
                 cc = tree.get("conexoesCruzadas", {}).get("outrosAlvosRelacionados", [])
                 if cc:
                     f.write("### 🔗 Conexões com Outros Alvos\n")
                     for c_con in cc:
                         f.write(f"- Ligação com **{c_con['alvo']}** ({c_con['tipoConexao']}): {c_con['motivo']}\n")
                 f.write("\n")
                         
                 # Investigação Societária (Minha Receita)
                 inv_soc = tree.get("investigacao_societaria", [])
                 if inv_soc:
                     f.write("### 🏢 Investigação Societária (Receita Federal)\n")
                     f.write("*Raio-X de CNPJs suspeitos ligados ao alvo que passaram por dupla-checagem no banco de dados federal.*\n\n")
                     for inv in inv_soc:
                         f.write(f"- **{inv['razao_social']}** (CNPJ: {inv['cnpj']})\n")
                         f.write(f"  - **Abertura:** {inv['abertura']}\n")
                         f.write(f"  - **CNAE Principal:** {inv['cnae']}\n")
                         soc_names = [s.get('nome_socio', '').strip() for s in inv.get('socios', []) if s.get('nome_socio')]
                         if soc_names:
                             f.write(f"  - **Quadro Societário (QSA):** {', '.join(soc_names)}\n")
                     f.write("\n")
                         
                 f.write("---\n\n")
                 
            # V4.2 - Phase 6: Apêndice Auditável
            f.write("# 📚 Apêndice Auditável: Como interpretar os Achados Críticos\n\n")
            f.write("Este apêndice orienta Auditores e membros do Ministério Público sobre como converter os alertas automatizados deste relatório em evidências materiais.\n\n")
            
            f.write("### 🚨 CREDOR_TRANSVERSAL (Suspeita de Cartel)\n")
            f.write("**O que significa?** Uma empresa ou indivíduo está recebendo volumes financeiros expressivos de pastas *diferentes*, controladas por alvos políticos *diferentes*.\n")
            f.write("**Como auditar:** Busque o CNPJ desta empresa no portal da transparência. Se as contratações ocorreram sempre por Dispensa de Licitação ou Carta Convite em diferentes secretarias, há forte indício de loteamento ou apadrinhamento sistêmico.\n\n")

            f.write("### 🚨 SETOR_FRACIONAMENTO_FORTE (Burla à Licitação)\n")
            f.write("**O que significa?** Uma mesma empresa recebeu múltiplos pagamentos mensais (3+) idênticos ou que somados ultrapassam o teto de dispensa.\n")
            f.write("**Como auditar:** Solicite os Processos Licitatórios. Identifique se o objeto contratado é o mesmo (ex: 'serviços de manutenção'). Se sim, o gestor pode estar fatiando a despesa para fugir da obrigação de licitar.\n\n")

            f.write("### 🚨 CONCENTRACAO_FAMILIAR_MUNICIPAL (Sanguessuga)\n")
            f.write("**O que significa?** Membros da família de um alvo político estão recebendo pagamentos elevados espalhados por toda a prefeitura, não apenas na pasta onde o alvo trabalha.\n")
            f.write("**Como auditar:** Levante se as empresas em nome destes familiares possuem capacidade operacional (sede física, funcionários). Frequentemente, parentes abrem empresas de fachada para escoar dinheiro municipal sob influência política do alvo.\n\n")

            f.write("### 🚨 SINCRONICIDADE_PAGAMENTO_POS_NOMEACAO (Reconhecimento de Favor)\n")
            f.write("**O que significa?** Uma empresa da família passou a receber dinheiro do município logo após (até 6 meses) a nomeação do alvo político a um cargo.\n")
            f.write("**Como auditar:** Verifique se esta empresa existia antes da nomeação do alvo e se ela já fornecia para a prefeitura em anos anteriores. Uma criação de CNPJ ou primeira nota fiscal emitida logo após a posse indica nepotismo cruzado.\n\n")

            f.write("### 🚨 TEMPORAL_FIM_ANO (Esvaziamento de Orçamento)\n")
            f.write("**O que significa?** Um credor (com laços cruzados com o alvo ou setor) concentrou de forma atípica a maior parte ou a totalidade do seu recebimento anual nas últimas semanas do exercício (Dezembro).\n")
            f.write("**Como auditar:** Solicite as notas fiscais e processos de liquidação destes pagamentos específicos de Dezembro. Avalie se o serviço tem natureza que justifique concentração de fim de ano (ex: material escolar não seria esperado e sim em Fev/Jul; serviços de consultoria cravados no dia 31/12 indicam frequentemente empenho residual frio). Verifique a existência de sobrepreço.\n\n")

            f.write("### 🚨 SOCIETARIA_PRATELEIRA_FORTE (Empresa de Prateleira)\n")
            f.write("**O que significa?** Um CNPJ passou a facturar no município com menos de 180 dias de fundação.\n")
            f.write("**Como auditar:** Exija provas físicas da prestação do serviço. É comum prefeitos eleitos ou apadrinhados mandarem abrir empresas (frequentemente MEIs ou EIRELI) laranjas apenas com o fito de escoar contratos já garantidos.\n\n")

            f.write("### 🚨 SOCIETARIA_SOCIO_OCULTO (Sócio Oculto na Folha)\n")
            f.write("**O que significa?** A máscara do CPF de um Sócio desta empresa fornecedora bate diretamente com a máscara do CPF do Alvo Político (Servidor).\n")
            f.write("**Como auditar:** Baixe o Quadro Societário Completo da Receita Federal. O servidor é diretamente dono ou sócio da empresa que está prestando serviço ao próprio ente público, o que incorre em proibição do estatuto dos servidores e provável improbidade/peculato.\n\n")

            f.write("### 🚨 SOCIETARIA_INCOMPATIBILIDADE (Desvio de Finalidade Materia)\n")
            f.write("**O que significa?** A atividade principal ou secundária da empresa (CNAE) é completamente estranha à destinação do órgão que a contratou (Ex: Fundo de Saúde pagando empresa de Entretenimento e Shows).\n")
            f.write("**Como auditar:** Exija os processos de empenho e as notas fiscais para inspecionar os produtos listados. Frequentemente, prefeituras drenam fundos engessados (como Saúde e Educação) utilizando empresas laranjas ou de serviços fictícios para pagar despesas não autorizadas.\n")
                 
        print(f"Salvo: {path} ({os.path.getsize(path)/1024:.1f} KB)")
