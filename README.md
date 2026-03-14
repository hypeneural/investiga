# Investiga Tijucas

Plataforma de ingestão, cruzamento de dados, enriquecimento e detecção de risco em dados públicos municipais, baseada em arquitetura orquestrada e orientada a domínio (Domain-Driven Design).

## 🎯 Objetivo Arquitetural

Esse repositório foi totalmente reestruturado (Investiga Motor v4) com foco em **resiliência operacional, rastreabilidade e escala**. O projeto abandona as antigas versões procedurais para abraçar um ecossistema baseado em:
1. **Banco de Dados Centralizado (PostgreSQL)** como única fonte da verdade (SSOT).
2. **Orquestração por Filas (RabbitMQ + Dramatiq)** dividindo o processamento em fluxos assíncronos.
3. **Modelo de Domínio Canônico (Entity Resolution)** onde pessoas, empresas e entes públicos convergem em um modelo único (`core.parties`).
4. **Camada Operacional (Ops Layer)** voltada a controlar sessões, bloqueios (ex: CAPTCHAs) e intervenção humana sistêmica, sem perder dados do processo (Retries).

---

## 🛠 Arquitetura do Sistema

O fluxo de dados da aplicação se divide em 5 estágios, que correspondem aos 5 Schemas baseados no PostgreSQL:

1. **RAW (Ingestão de Dados Brutos):** Salva exatamente o payload que a fonte originou (Atende, Receita, APIs). Camada 100% auditável.
2. **CORE (Modelo Canônico):** A normalização (ETL). Transforma dados fragmentados na rede semântica e temporal do projeto (Entidades "Parties", Pessoas, Organizações, Despesas Públicas, Vínculos Ocupacionais).
3. **ENRICH (Enriquecimento):** Dados de perfil de empresa (QSA, CNAEs), classificação por IA (Semântica OpenRouter), checagens PEP e Sanções públicas.
4. **RISK (Motor de Risco & Grafos):** Geração de Alertas, Casos, Scoring (Score Tríplice: Financeiro, Relacional, Evidência) e nós/arestas de relações sociais e financeiras.
5. **OPS (Operacional & Controle):** Sessões de raspagem, controle de Captchas, logs de Heartbeat dos workers de filas, histórico de Jobs, Dead Letter e rate limits. 

---

## 📂 Estrutura do Repositório (Monorepo Modular)

A organização interna do código segue o padrão de pacotes, segmentando as responsabilidades e isolando o negócio da infraestrutura.

```text
investiga/
├── apps/               # Aplicações e Entrypoints
│   ├── api/            # FastAPI (Rotas, Schemas, Services web)
│   ├── workers/        # Consumidores Dramatiq (Consumers)
│   └── cli/            # Comandos de CLI local (Ex: doctor, gerenciar filas)
├── packages/           # Regras de Negócio e Lógica Core
│   ├── domain/         # Entidades puras, regras de negócio e grafos
│   ├── connectors/     # Adaptadores externos (Atende, Receita, OpenRouter)
│   ├── ingestion/      # Fluxos de coleta até a camada RAW
│   ├── normalization/  # Entidades canônicas (Deduplicação, Identificação)
│   ├── enrichment/     # Processos de adição de contexto extra aos dados
│   ├── orchestration/  # Gestão de filas, DLQ, payloads das mensagens
│   ├── repositories/   # SQLAlchemy Models e operações no PostgreSQL
│   └── observability/  # Logs, Métricas, Heartbeat
├── infra/              # Contêineres e DB Scripts
│   ├── docker/         # Docker Compose
│   ├── sql/            # DDL Inicial (Criação do Banco de Dados)
│   └── migrations/     # Setup Alembic para versão do banco
├── data/               # Dados persistentes
│   ├── raw/            # Downloads pontuais, caches e amostras RAW
│   ├── staged/         # Staging/Processing intermediário em JSON (Temporário)
│   ├── exports/        # Destino das exportações locais e relatórios
│   └── fixtures/       # Mock e testes Mocks de data real    
├── docs/               # Documentação Completa do Projeto
├── tests/              # Testes cruzados e Ponta-A-Ponta (E2E)
└── legacy/             # Código Arquivado da v1 até v8, Scrapers antigos, SDK Base (apenas leitura)
```

---

## 🔌 Conectores Suportados (Packages -> Connectors)

A camada de conectores centraliza a comunicação externa, utilizando resiliência nativa (Tenacity para retry assíncrono):

* **Atende (Portal Transparência):** Extração de folhas de pagamentos, empenhos, pagamentos diretos.
* **Minha Receita:** Recuperação em batch de CNPJs, Sócios, CNAEs e Quadro Societário (QSA).
* **OpenRouter / LLMs:** Abstração agnóstica de LLMs (GPT, Claude, etc) para a triagem em linguagem natural, roteamento de despesas, semântica forense, estruturação contextual a partir de extratos irregulares de diários e PDFs. Trabalha integrado à detecção de anomalias textuais.
* **Monitor de Sanções & PEP (Planejado):** Bases punitivas nacionais e indicação em pessoas politicamente expostas.

---

## 🐇 Orquestração do Trabalho (~30 Filas)

A arquitetura usa RabbitMQ para criar pipelines eficientes, desde o download até o scoring final:

* `ingest.atende.payments` / `ingest.atende.employees` -> Traz payloads massivos crus.
* `normalize.parties` -> Resolve o nó de quem pagou/quem recebeu.
* `enrich.company.*` -> Faz trigger sobre dados PJ ausentes (Receita).
* `nlp.classify_expense` -> Joga metadados limpos da despesa na LLM para detectar flag de desvios e classificar semântica.
* `human.review_llm_output` -> Suspende temporariamente uma decisão da LLM se houver incerteza e aguarda aprovação manual do time pelo sistema Ops.
* `risk.detect.*` -> Motores independentes verificando temporalidade, elos societários estranhos, incompatibilidades sistêmicas.

---

## 💻 Tech Stack Atual

| Camada | Tecnologia | Motivo da Adoção |
|---|---|---|
| **API Web & Core** | FastAPI + Pydantic v2 | Documentação OpenAPI nativa, assíncrono e validação forte. |
| **Banco de Dados** | PostgreSQL 16 + SQLAlchemy 2 + Alembic | Joins robustos, integridade relacional entre fluxos vitais e versionamento. Alembic gerencia os Schemas. |
| **Integração HTTP** | HTTPX + Tenacity | Assíncrono para velocidade. Tenacity fornece Retry-Policies (Exponential Backoff) sobre Rate Limits das contas e fontes governamentais. |
| **Web Crawling** | Playwright | Simulação realística de sessão de browser para lidar com portais burocráticos onde API REST não existe e captchas de segurança. |
| **Job Queue** | Dramatiq + RabbitMQ | Confiabilidade superior ao Celery, focado em mensageria estável de long-running/short-running tasks. |
| **Data Lake Temp / Hash**| Redis | Caching transitório, mutexes, rate limiting em conexões locais distribuídas. |
| **Testes e Qualidade**| Pytest + RESPX + Ruff + Mypy | Tipagem estática imposta, formatação forte em Python 3.12+, mock requests limpo. |

---

## 🚀 Como Iniciar e Usar (Quick Start)

### 1. Requisitos Recomendados
- Python 3.12+ (Utilize gerenciador virtualenv tipo Conda, pyenv ou venv)
- Docker Compose
- Banco de Dados via WSL2 se estiver rodando Windows (Padrão)

### 2. Infraestrutura Rápida (DBs / Broker)
A partir do diretório principal, levante o stack da base de dependências:
```bash
make infra
# Irá iniciar os contêineres: investiga-postgres (5432) | investiga-rabbitmq (5672/15672) | investiga-redis (6379)
```

### 3. Configuração do Python e Code Quality
```bash
# Seta sua VENV antes
make install

# Copia o arquivo local da infraestrutura e coloque os tokens reais (ex: OpenRouter API)
cp .env.example .env

# Executa e cria a versão Zero do Banco de Dados no Postgres recém-iniciado
make migrate

# Valida toda pre-configuração antes de abrir conexões (Verifica porta e envs)
make doctor
```

### 4. Executando os Serviços
Em um terminal (Server / Frontend Gateway da API):
```bash
make api
```
Em outro terminal paralelo focado nas tarefas da fila secundária de alto processamento:
```bash
make worker
```
O Dashboard do RabbitMQ ficará acessível em [http://localhost:15672/](http://localhost:15672/) (Usuário: `investiga` / Senha: `investiga_dev`)

### Ferramentas de Manutenção (Makefile)
```bash
make lint        # Passar o Ruff (Linter) + Mypy (Types)
make format      # Aplicar formatação Ruff auto-fix
make test        # Executar os unittests e a flag do Pytest c/ Mock respx
make infra-down  # Derrubar containers infra docker
```

---

## 📚 Encontre as Documentações de Baixo Nível

Toda a teoria dos fluxos de dados, arquiteturas de decisão registradas com motivo do "Porquê foi implementado X frente a Y" está mapeada e persistente na pasta `docs/`. Recomenda-se a leitura na seguinte ordem em caso de dúvidas:
- [Architecture (Regras, fluxos gerais e serviços essenciais)](docs/architecture/)
- [ADRs (Architecture Decision Records) — As bases das decisões fundamentais do repositório](docs/adr/)
- [Queue Catalog (O que corre onde — Documentação oficial das 30 Filas)](docs/queues/)
- [Modelo de Dados Entidade Relacionamento Completo (PostgreSQL)](docs/data-model/)
