# Arquitetura Técnica 🏗️

Este documento detalha o pipeline de processamento e a engenharia por trás dos motores do **Investiga Tijucas**.

## 1. Pipeline Evolutivo
O projeto não é um monolito, mas uma série de motores que evoluíram em maturidade e profundidade:

- **Legado (V1)**: Script `analise_fraudes.py` operando sobre JSONs brutos. Cálculos estatísticos simples.
- **V2 (Tree-Target)**: Foco em pessoas (Políticos/Servidores). Monta a árvore relacional completa (`main_v2.py`).
- **V6 (Doc-Linker)**: Foco em documentos. Encadeamento entre empenho e nota fiscal.
- **V7 (Mock-Tester)**: Homologação de regras estruturais com dados semeados artificialmente.
- **V8 (National-Context)**: Priorização via flags externas (PEP, Sanções federais).
- **V9.1 (NLP-Dispatcher)**: Camada de IA assíncrona para auditoria semântica.

## 2. Resolução de Identidade (Fuzzy)
Dado que o portal mascara o CPF (`***.123.456-**`), o `IdentityResolver` utiliza classes de evidência para vincular registros:

| Classe | Critério | Confiança |
| :--- | :--- | :--- |
| **EXATO_FORTE** | CPF parcial único + Nome exato | Altíssima |
| **FORTE** | CPF parcial coincide, mas Nome tem variação leve | Alta |
| **MEDIA** | Nome exato único (sem CPF disponível) | Média |
| **AMBIGUA** | CPF parcial coincide com múltiplos registros | Baixa |

## 3. Motor V2: Pipeline de Árvore
1. **Identidade**: Resolve o alvo na folha de pagamento.
2. **Vínculo**: Agrega todas as matrículas e deduplica pagamentos.
3. **Onomástica**: `FamilyNetworkAnalyzer` identifica núcleos familiares por sobrenomes raros.
4. **Financeiro**: `SectorAnalyzer` mapeia dominância de credores no centro de custo do alvo.
5. **Cross-Link**: `CrossTargetGraph` encontra conexões entre diferentes políticos via credores comuns.
6. **Enriquecimento societário**: Consulta cache/API para trazer QSA e CNAE.

## 4. Engenharia de IA (NLP Dispatcher)
A camada de IA (`nlp_dispatcher.py`) é projetada para ser auditável e segura contra rate-limits:
- **Assinatura Habilitada**: Cada tarefa tem um hash (`v9.1|p1|...`) para evitar re-processamento.
- **Fila SQLite**: Armazena tarefas `queued`, `processing` e `done`.
- **Worker Controlado**: Processa um job por vez com backoff em caso de erro do provedor (OpenRouter).
- **Cache Auditável**: O output JSON da IA é persistido no banco e vinculado à despesa original.

## 5. Fluxo Documental V6
Diferente do V2 que é relacional, o V6 é determinístico:
- Tenta o match forte via `liquidacao_sequencia`.
- Fallback para `data + valor` em casos de inconsistência de metadados do portal.
- Garante a rastreabilidade entre o pagamento macro e o documento fiscal extraído via Deep Fetch.
