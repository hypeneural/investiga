# 2. Use RabbitMQ for Job Brokering

**Date**: 2024-03-14
**Status**: Accepted
**Context**: The system processes data through multiple stages (ingestion, normalization, enrichment, risk detection) that benefit from asynchronous, decoupled execution.

## Decision

Adopt **RabbitMQ** as the message broker with **Dramatiq** as the task framework. Organize ~30 queues by responsibility domain with dedicated DLQ per queue.

## Consequences

- **Positive**: Decoupled workers, retry/DLQ built-in, horizontal scaling
- **Positive**: Dramatiq is simpler than Celery with good reliability
- **Negative**: Requires RabbitMQ instance
- **Negative**: Need to manage queue topology and worker deployment
