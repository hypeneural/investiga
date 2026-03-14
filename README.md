# Investiga Tijucas

Plataforma de ingestão, enriquecimento e detecção de risco em dados públicos municipais.

## Stack

| Camada | Tecnologia |
|---|---|
| API | FastAPI + Pydantic v2 |
| Banco | PostgreSQL 16 + SQLAlchemy 2 + Alembic |
| HTTP | HTTPX + Tenacity |
| Browser | Playwright |
| Filas | Dramatiq + RabbitMQ |
| Observability | structlog + Prometheus + Sentry |
| Testes | pytest + RESPX + pytest-xdist |
| Qualidade | Ruff + mypy |

## Quick Start

```bash
# 1. Subir infraestrutura
make infra

# 2. Instalar dependências
make install

# 3. Rodar migrações
make migrate

# 4. Verificar saúde
make doctor

# 5. Rodar API
make api

# 6. Rodar workers
make worker
```

## Estrutura

```
apps/           → API, Workers, CLI
packages/       → Domain, Connectors, Ingestion, Normalization,
                  Enrichment, Repositories, Orchestration, Observability
infra/          → Docker, Migrations, SQL, RabbitMQ
data/           → Raw, Staged, Exports, Fixtures
docs/           → Architecture, Data Model, Queues, Rules, ADRs, Runbooks
tests/          → E2E, Fixtures, Smoke
legacy/         → Código antigo preservado (V1-V8, scrapers, SDK, frontend)
```

## Schemas PostgreSQL

| Schema | Conteúdo |
|---|---|
| `raw` | Dados brutos de fontes (Atende, Minha Receita, OpenRouter) |
| `core` | Modelo canônico (parties, employees, expenses, relationships) |
| `enrich` | Enriquecimento (CNPJ, QSA, sanções, PEP, NLP) |
| `risk` | Risco (alertas, cases, scores, grafo) |
| `ops` | Operacional (jobs, sessões, intervenções, heartbeats, DLQ) |

## Documentação

- [Architecture](docs/architecture/)
- [Data Model](docs/data-model/)
- [Queue Catalog](docs/queues/)
- [Connectors](docs/connectors/)
- [Rules](docs/rules/)
- [ADRs](docs/adr/)
- [Runbooks](docs/runbooks/)
