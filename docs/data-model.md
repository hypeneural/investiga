# Modelo de Dados e Persistência 💾

Este documento descreve a estrutura física dos dados consumidos e gerados pelo sistema.

## 1. Bancos de Dados SQLite

### `tijucas_raw.db` (Principal)
Bunker central de dados municipais raspados e normalizados.
- `pagamentos_normalizados`: Base de transações municipais consolidada.
- `detalhes_liquidacao`: Conteúdo bruto (HTML/JSON) extraído via Deep Fetch.
- `nlp_queue`: Fila de tarefas para a camada semântica.
- `expense_semantic_labels`: Classificações geradas pela I.A.

### `company_cache.sqlite` (Enriquecimento)
Cache local dos dados da Receita Federal.
- `company_profiles`: Matriz da empresa (Razão Social, CNAEs, Situação).
- `company_qsa_members`: Quadro de Sócios e Administradores.

### `nlp_cache.db`
Cache de inferências da I.A. para evitar gastos redundantes com tokens.
- `prompt_history`: Assinaturas de prompts e hashes de resposta.

---

## 2. Artefatos de Saída (JSON)

### `output_v2/alvos_arvore.json`
Estrutura hierárquica por alvo político/servidor.
```json
{
  "alvo": { "nome": "...", "cpf": "...", "cargo": "..." },
  "pagamentosDiretos": { "totalPago": 123.45, "detalhesDespesas": [...] },
  "redeFamiliar": { "nucleosEncontrados": [...] },
  "scores": { "riscoFinanceiro": 70, "riscoRelacional": 40, "evidencia": 100 }
}
```

### `dashboard_kpis.json`
Consolidado para o frontend, contendo:
- `total_monitorado`: Volume financeiro total sob análise.
- `alertas_t1`: Contagem de fatos objetivos detectados.
- `top_10_credores_suspeitos`: Lista filtrada por score de risco.

---

## 3. Entidades Python (Modelos)
O sistema utiliza as seguintes representações em memória (especialmente no V6):
- `PaymentEvent`: Representa uma transação financeira única.
- `LiquidationDocument`: Vínculo entre liquidação e nota fiscal.
- `TargetEvent`: Evento ligado a um alvo (Posse, Nomeação).
- `AlertEvent`: Representação padronizada de um achado de auditoria.
