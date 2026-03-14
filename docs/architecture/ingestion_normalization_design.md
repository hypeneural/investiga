# Design Arquitetural: Ingestão e Normalização (Fases 4 e 5)

Este documento descreve a estratégia técnica e arquitetural para a implementação das Fases 4 (Ingestão) e 5 (Normalização) da Plataforma Investiga Tijucas. Ele servirá de base para a equipe de desenvolvimento propor melhorias e entender os padrões estabelecidos.

---

## 🏗️ 1. Fase 4: Ingestão de Dados (Ingestion Layer)

**Objetivo:** Capturar dados das fontes oficiais (Atende, Minha Receita) usando os conectores já desenvolvidos na Fase 3, e salvá-los **exatamente como vieram** no banco de dados (`raw`), para auditoria e reprocessamento futuro.

### 1.1 Fluxo de Trabalho (Orquestração via Dramatiq)

Toda ingestão começa como uma mensagem em uma fila RabbitMQ.

1. **Trigger:** Um Scheduler cron ou um endpoint manual da API dispara uma mensagem para a fila (ex: `ingest.atende.payments`). O payload inicial contém os parâmetros da busca (ex: `{"mes": "10", "ano": "2023"}`).
2. **Worker Job:** O consumidor do Dramatiq recebe a mensagem. Ele usa as funções de orquestração para recuperar ou iniciar uma sessão na tabela `ops.source_sessions`.
3. **Extração:** O connector adequado (ex: `AtendeAdapter`) é instanciado. Ele executa o request HTTPX via Tenacity.
4. **Armazenamento RAW:** 
   * Se os dados são retornados com sucesso, insere-se um novo registro em `raw.source_runs` e os registros detalhados (ex: `raw.atende_payments`) com a cópia exata do JSON e um `payload_hash` (para evitar duplicatas fáceis).
5. **Enfileiramento Downstream:** Para cada registro ingerido, o worker dispara uma *nova* mensagem para a etapa seguinte (Fase 5). Exemplo: `normalize.expense_events` recebendo o ID do `raw.atende_payments`.

### 1.2 Estrutura do Código (`packages/ingestion/`)

* `src/investiga_ingestion/jobs/`
  * `atende_jobs.py` -> Funções marcadas com `@dramatiq.actor` para filas locais. Ex: `fetch_atende_expenses()`.
  * `minha_receita_jobs.py` -> Puxa CNPJs sob demanda ou em batch.
* `src/investiga_ingestion/pipelines/`
  * Classes ou funções que orquestram multiplas requisições encadeadas (ex: recuperar lista de funcionários, iterar na paginação).
* `src/investiga_ingestion/raw_storage/`
  * Padrão Repository: Operações assíncronas no banco de dados para salvar os dados crus (schema `raw`). Pega a sessão SQLAlchemy a partir do banco.

### 1.3 Lógica de Controle de Erro

Se ocorrer 429 (Too Many Requests) -> O Tenacity pausa por N segundos.
Se detectar um Captcha (Via `BlockState`) -> O worker interrompe! Joga erro pro Dramatiq que encaminhará para as filas de DLQ e atualizará o `ops.source_sessions` como "BLOCKED".

---

## 🧩 2. Fase 5: Normalização (ETL & Entity Resolution)

**Objetivo:** Transformar os modelos crus da camada `raw` no dicionário canônico e robusto do projeto (schema `core`), limpando nomes estruturados e resolvendo vinculações (quem é quem).

### 2.1 Entity Resolution (O Core do Problema)

O sistema lida com *Parties* (Entidades). Quando a prefeitura paga um "Posto de Combustível X" (CNPJ x) e a Minha Receita tem o perfil do "Auto Posto X LTDA" (mesmo CNPJ), eles são a mesma pessoa jurídica. Quando aparece um pagamento para um funcionário por CPF mascarado (ex: `***.123.456-**`), ele é uma pessoa física.

#### Lógica de Resolução e Identidade Única
1. **O Worker de Normalização da Despesa (`normalize.expense_events`):**
   * Lê o evento da despesa na tabela RAW.
   * Aciona a classe `Resolvers`.
   * Pega os dados do recebedor (nome, documento se tiver).
   * **Identifica ou Cria a Party:** 
     * Se existe um CNPJ associado claro, busca na tabela `core.organizations` se esse party já existe. Se não existir, cria o `core.parties` e o `core.organizations`.
     * Recebimentos com nome limpo devem sofrer `canonicalizers` (lower case, remoção de pontuação).
2. **Registro Financeiro:**
   * Grava a despesa `core.expense_events` apontando para o `counterparty_id` da Party resolvida.

### 2.2 Estrutura do Código (`packages/normalization/`)

* `src/investiga_normalization/mappers/`
  * Transforma Pydantic DTOs dos Conectores (Ex: `AtendePaymentDto`) em SQLAlchemy Models (Ex: `ExpenseEvent`).
* `src/investiga_normalization/canonicalizers/`
  * Utilitários para padronizar nomes de empresas, regras de formatação de CPFs, extração de radicais de nome de funcionário.
* `src/investiga_normalization/resolvers/`
  * Identificação de Identidade. "Dado esse Credor, retorne o `party_id` correspondente".
  * Usa consultas de texto do PostgreSQL (`pg_trgm`) ou exatidão de documento.
* `src/investiga_normalization/dedup/`
  * Enfileira tarefas para caso sejam dectectados "Possíveis Duplicados".

### 2.3 Fluxo de Trabalho (Tratamento Ocupacional)

No ingestion de servidores e folhas de pagamentos:
1. Trabalhador é lido do `raw.atende_employees`.
2. Busca a party_id na `core.persons` do trabalhador. (Cria se não existir, guardando o hash dos 6 digitos centrais do CPF + first_name).
3. Atualiza ou insere o cargo e salário na tabela `core.employees`.

---

## 📝 Pontos para a Equipe de Desenvolvedores Atentar/Sugerir

1. **Transaction Boundaries:** Quando criamos Parties em lote a partir do ETL da despesa, precisamos garantir atomicidade. Se rolar uma falha na dedup, devemos falhar o transacional inteiro da despesa para que o RabbitMQ retente depois? (Sugestão atual: SIM. O SQLAlchemy commit ocorre no fim da task do Consumer).
2. **Resolvers Complexos (CPFs):** Transparência muitas vezes mascara CPFs. A heurística projetada é `Nome + 6 Digitos Centrais do CPF` = *EntityMatch*. Devemos ajustar isso para tolerar typos? As sugestões do time são vitais aqui no pacote de `canonicalizers`.
3. **Idempotência no Dramatiq:** Garantir que se o servidor cair na hora de rodar um `normalize.expense_events`, a reexecução do Job não duplique a criação de registros em `core.expense_events`. Sugere-se usar o campo ID da raw concatenado com o action como hash idempotente na checagem antes de salvar (já modelado em `ops.jobs.idempotency_key`).
