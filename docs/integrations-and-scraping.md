# Integrações e Fluxo de Ingestão 📡

Este documento detalha as APIs externas, as fontes de dados e os processos de raspagem de dados ativos no projeto.

## 1. Portal da Transparência (Atende.net)
O portal da prefeitura de Tijucas é a fonte primária de dados financeiros e funcionais.

- **Serviço**: Sistema IPM / Atende.net
- **Mecanismo**: Scraping via POST requests com payloads JSON complexos.
- **Scripts**: `tijucas_scraper_list.py` (Lista) e `tijucas_scraper_detail.py` (Detalhes).

### Dados Extraídos:
| Granularidade | Campos Principais |
| :--- | :--- |
| **Lista (Base)** | `pagnumero`, `pagdata`, `pagvalor`, `uninomerazao` (Credor), `unicpfcnpj`. |
| **Detalhes** | `historico` (Descrição completa), `numeroDocumento` (NF), `chaveDanfe`, `tipoCompra`. |
| **Pessoas** | Matrícula, cargo, salário base, centro de custo, situação funcional. |

---

## 2. Minha Receita (Enriquecimento Societário)
Utilizada para transformar um CNPJ bruto em um perfil empresarial completo.

- **Serviço**: API Minha Receita (ou similar compatível com o schema da RFB).
- **Finalidade**: Identificar donos reais, tempo de existência da empresa e áreas de atuação.
- **Cache**: Armazenado localmente em `company_cache.sqlite`.

### Dados Trazidos:
- **QSA (Quadro de Sócios)**: Nomes e CPFs parciais dos sócios.
- **CNAEs**: Lista de atividades econômicas (Principal e Secundárias).
- **Status RFB**: Situação cadastral (Ativa, Baixada, Suspensa).
- **Fundação**: Data de abertura (Essencial para a regra de *Empresa de Prateleira*).

---

## 3. OpenRouter (Camada Semântica IA)
Interface unificada para modelos de linguagem (LLMs) como GPT-4 e Claude-3.

- **Integração**: `FraudOpenRouterClient` via `nlp_dispatcher.py`.
- **Fila**: Sistema assíncrono controlado via banco SQLite.

### Dados Trazidos:
- **Classificação**: Categoria da despesa, natureza do objeto e genericidade do texto.
- **Análise de Risco**: Grau de compatibilidade entre o CNAE da empresa e o que ela efetivamente entregou (conforme nota fiscal).
- **Audit Tool**: Checklist de auditoria e resumos narrativos dos casos.

---

## 4. Contexto Nacional Híbrido (V8)
Enriquecimento com bases de dados federais e listas de restrição.

- **Fontes**: CEIS (Empresas Inidôneas), CNEP (Empresas Punidas), Lista PEP (Pessoas Expostas Politicamente).
- **Utilização**: Marcação de risco imediato para fornecedores que já possuem restrições em nível federal.

### Dados Trazidos:
- **Sanções**: Tipo de sanção, órgão aplicador e período de vigência.
- **Flags PEP**: Identificação de vínculos políticos nacionais do sócio ou titular.
- **Lastro**: Comparação entre o volume faturado no município vs. volume faturado em órgãos federais.
