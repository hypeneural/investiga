"""Queue name catalog.

Single source of truth for all RabbitMQ queue names.
Convention: <domain>.<action>.<object>

All workers reference this module instead of hardcoding strings.
"""


# ── Ingestão ──────────────────────────────────────────────
INGEST_ATENDE_PAYMENTS = "ingest.atende.payments"
INGEST_ATENDE_PAYMENT_DETAILS = "ingest.atende.payment_details"
INGEST_ATENDE_EMPLOYEES = "ingest.atende.employees"

# ── Normalização ──────────────────────────────────────────
NORMALIZE_PARTIES = "normalize.parties"
NORMALIZE_EXPENSE_EVENTS = "normalize.expense_events"
NORMALIZE_EMPLOYMENT_LINKS = "normalize.public_employment_links"
NORMALIZE_DOCUMENTS = "normalize.documents"

# ── Enriquecimento Empresarial ────────────────────────────
ENRICH_COMPANY_PROFILE = "enrich.company.profile"
ENRICH_COMPANY_QSA = "enrich.company.qsa"
ENRICH_COMPANY_CNAES = "enrich.company.cnaes"

# ── Enriquecimento Externo ────────────────────────────────
ENRICH_SANCTIONS = "enrich.sanctions"
ENRICH_PEP = "enrich.pep"

# ── NLP / LLM ────────────────────────────────────────────
NLP_CLASSIFY_EXPENSE = "nlp.classify_expense"
NLP_PRIORITIZE_CASE = "nlp.prioritize_case"

# ── Revisão Humana ────────────────────────────────────────
HUMAN_REVIEW_LLM_OUTPUT = "human.review_llm_output"

# ── Risco / Detecção ─────────────────────────────────────
RISK_DETECT_DOCUMENTARY = "risk.detect.documentary"
RISK_DETECT_SOCIETARY = "risk.detect.societary"
RISK_DETECT_FAMILY_NETWORK = "risk.detect.family_network"
RISK_DETECT_TEMPORAL = "risk.detect.temporal"
RISK_DETECT_TRANSVERSAL = "risk.detect.transversal"
RISK_RECALCULATE_SCORES = "risk.recalculate_scores"
RISK_REBUILD_GRAPH = "risk.rebuild_graph"

# ── Exportação ────────────────────────────────────────────
EXPORT_FRONTEND = "export.frontend"
EXPORT_REPORT_MARKDOWN = "export.report_markdown"
EXPORT_CASE_BUNDLE = "export.case_bundle"


# ── DLQ (Dead Letter Queue) ──────────────────────────────
def dlq(queue_name: str) -> str:
    """Generate DLQ name for a given queue."""
    return f"dlq.{queue_name}"


# ── All queues (for setup/registration) ──────────────────
ALL_QUEUES = [
    # Ingestão
    INGEST_ATENDE_PAYMENTS,
    INGEST_ATENDE_PAYMENT_DETAILS,
    INGEST_ATENDE_EMPLOYEES,
    # Normalização
    NORMALIZE_PARTIES,
    NORMALIZE_EXPENSE_EVENTS,
    NORMALIZE_EMPLOYMENT_LINKS,
    NORMALIZE_DOCUMENTS,
    # Enriquecimento
    ENRICH_COMPANY_PROFILE,
    ENRICH_COMPANY_QSA,
    ENRICH_COMPANY_CNAES,
    ENRICH_SANCTIONS,
    ENRICH_PEP,
    # NLP
    NLP_CLASSIFY_EXPENSE,
    NLP_PRIORITIZE_CASE,
    # Humano
    HUMAN_REVIEW_LLM_OUTPUT,
    # Risco
    RISK_DETECT_DOCUMENTARY,
    RISK_DETECT_SOCIETARY,
    RISK_DETECT_FAMILY_NETWORK,
    RISK_DETECT_TEMPORAL,
    RISK_DETECT_TRANSVERSAL,
    RISK_RECALCULATE_SCORES,
    RISK_REBUILD_GRAPH,
    # Export
    EXPORT_FRONTEND,
    EXPORT_REPORT_MARKDOWN,
    EXPORT_CASE_BUNDLE,
]
