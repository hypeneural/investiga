# 1. Use PostgreSQL as Primary Store

**Date**: 2024-03-14
**Status**: Accepted
**Context**: The project started with SQLite and JSON files for data storage. As the system grew with multiple engines (V1-V8), the data model became fragmented across files and databases.

## Decision

Adopt **PostgreSQL 16+** as the single source of truth with:
- 5 schemas: `raw`, `core`, `enrich`, `risk`, `ops`
- Extensions: `pg_trgm`, `unaccent`, `pgcrypto`
- Future: `pgvector` for embeddings

## Consequences

- **Positive**: Referential integrity, complex joins, materialized views, full-text search, audit trail
- **Positive**: Single migration path via Alembic
- **Negative**: Requires running PostgreSQL (Docker or managed)
- **Negative**: Data migration from SQLite/JSON needed
