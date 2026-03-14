# 3. Use Party as Canonical Entity

**Date**: 2024-03-14
**Status**: Accepted
**Context**: The system deals with persons (employees, suppliers PF), organizations (companies, suppliers PJ), and public entities. Previously these were tracked in separate unlinked structures.

## Decision

Adopt `core.parties` as the **unified entity model**. Every person, organization, or public entity is a `party` with type-specific extensions (`core.persons`, `core.organizations`). Documents (CPF/CNPJ) link to parties via `core.party_documents`. All relationships, payments, and alerts reference `party_id`.

## Consequences

- **Positive**: Unified identity across employees, suppliers, and companies
- **Positive**: Graph construction is straightforward (party→party edges)
- **Positive**: Single scoring and alert target
- **Negative**: Requires identity resolution to merge duplicate parties
- **Negative**: Slightly more complex queries (joins to type tables)
