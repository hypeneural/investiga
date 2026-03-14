-- ============================================================
-- Investiga Tijucas — Initial Schema Setup
-- Creates all 5 schemas with core tables
-- Run: psql -U investiga -d investiga_tijucas -f init.sql
-- ============================================================

-- ── Schemas ──────────────────────────────────────────────
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS enrich;
CREATE SCHEMA IF NOT EXISTS risk;
CREATE SCHEMA IF NOT EXISTS ops;

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ══════════════════════════════════════════════════════════
-- RAW — Dados brutos de fonte
-- ══════════════════════════════════════════════════════════

CREATE TABLE raw.source_runs (
    id SERIAL PRIMARY KEY,
    source_name TEXT NOT NULL,
    endpoint TEXT,
    started_at TIMESTAMPTZ DEFAULT now(),
    finished_at TIMESTAMPTZ,
    status TEXT DEFAULT 'running',
    records_count INT DEFAULT 0,
    error_message TEXT
);

CREATE TABLE raw.atende_payments (
    id SERIAL PRIMARY KEY,
    run_id INT REFERENCES raw.source_runs(id),
    external_id TEXT,
    credor_documento TEXT,
    credor_nome TEXT,
    valor_empenhado NUMERIC(15,2),
    valor_liquidado NUMERIC(15,2),
    valor_pago NUMERIC(15,2),
    data_pagamento DATE,
    orgao_descricao TEXT,
    unidade_descricao TEXT,
    fonte_recurso TEXT,
    tipo TEXT,
    payload_json JSONB,
    payload_hash TEXT,
    captured_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE raw.atende_employees (
    id SERIAL PRIMARY KEY,
    run_id INT REFERENCES raw.source_runs(id),
    nome TEXT,
    cpf_masked TEXT,
    matricula TEXT,
    cargo TEXT,
    salario_base NUMERIC(15,2),
    centro_custo TEXT,
    situacao TEXT,
    regime TEXT,
    admissao DATE,
    payload_json JSONB,
    captured_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE raw.minha_receita_payloads (
    id SERIAL PRIMARY KEY,
    run_id INT REFERENCES raw.source_runs(id),
    cnpj TEXT NOT NULL,
    payload_json JSONB NOT NULL,
    payload_hash TEXT,
    captured_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE raw.openrouter_responses (
    id SERIAL PRIMARY KEY,
    run_id INT REFERENCES raw.source_runs(id),
    task_name TEXT NOT NULL,
    input_hash TEXT NOT NULL,
    model_used TEXT,
    response_json JSONB,
    captured_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE raw.source_artifacts (
    id SERIAL PRIMARY KEY,
    source_name TEXT NOT NULL,
    artifact_type TEXT NOT NULL,
    storage_path TEXT,
    content_hash TEXT,
    job_id UUID,
    source_session_id INT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ══════════════════════════════════════════════════════════
-- CORE — Modelo canônico
-- ══════════════════════════════════════════════════════════

CREATE TABLE core.parties (
    id SERIAL PRIMARY KEY,
    party_type TEXT NOT NULL CHECK (party_type IN ('person', 'organization', 'public_entity')),
    canonical_name TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE core.party_documents (
    id SERIAL PRIMARY KEY,
    party_id INT NOT NULL REFERENCES core.parties(id),
    doc_type TEXT NOT NULL,
    doc_value TEXT NOT NULL,
    is_primary BOOLEAN DEFAULT true,
    UNIQUE(doc_type, doc_value)
);

CREATE TABLE core.persons (
    party_id INT PRIMARY KEY REFERENCES core.parties(id),
    full_name TEXT,
    cpf_center TEXT,
    surnames TEXT[]
);

CREATE TABLE core.organizations (
    party_id INT PRIMARY KEY REFERENCES core.parties(id),
    razao_social TEXT,
    nome_fantasia TEXT,
    cnpj TEXT UNIQUE,
    cnae_fiscal INT,
    cnae_descricao TEXT,
    natureza_juridica TEXT,
    capital_social NUMERIC(15,2),
    data_abertura DATE,
    situacao_cadastral TEXT,
    uf TEXT,
    municipio TEXT
);

CREATE TABLE core.public_bodies (
    id SERIAL PRIMARY KEY,
    party_id INT REFERENCES core.parties(id),
    codigo TEXT,
    descricao TEXT NOT NULL,
    tipo TEXT
);

CREATE TABLE core.public_units (
    id SERIAL PRIMARY KEY,
    body_id INT REFERENCES core.public_bodies(id),
    codigo TEXT,
    descricao TEXT NOT NULL
);

CREATE TABLE core.employees (
    id SERIAL PRIMARY KEY,
    person_id INT NOT NULL REFERENCES core.parties(id),
    matricula TEXT,
    cargo TEXT,
    funcao TEXT,
    centro_custo TEXT,
    unit_id INT REFERENCES core.public_units(id),
    salario_base NUMERIC(15,2),
    situacao TEXT,
    regime TEXT,
    admissao DATE,
    raw_id INT
);

CREATE TABLE core.expense_events (
    id SERIAL PRIMARY KEY,
    event_type TEXT NOT NULL,
    counterparty_id INT REFERENCES core.parties(id),
    orgao TEXT,
    unidade TEXT,
    valor_empenhado NUMERIC(15,2),
    valor_liquidado NUMERIC(15,2),
    valor_pago NUMERIC(15,2),
    data_pagamento DATE,
    historico TEXT,
    fonte_recurso TEXT,
    raw_id INT
);

CREATE TABLE core.party_relationships (
    id SERIAL PRIMARY KEY,
    from_party_id INT NOT NULL REFERENCES core.parties(id),
    to_party_id INT NOT NULL REFERENCES core.parties(id),
    rel_type TEXT NOT NULL,
    confidence NUMERIC(3,2),
    evidence_tier TEXT,
    source_rule TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE core.identity_matches (
    id SERIAL PRIMARY KEY,
    party_a_id INT NOT NULL REFERENCES core.parties(id),
    party_b_id INT NOT NULL REFERENCES core.parties(id),
    match_method TEXT,
    confidence NUMERIC(3,2),
    is_confirmed BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ══════════════════════════════════════════════════════════
-- ENRICH — Enriquecimento
-- ══════════════════════════════════════════════════════════

CREATE TABLE enrich.company_profiles (
    id SERIAL PRIMARY KEY,
    party_id INT REFERENCES core.parties(id),
    cnpj TEXT NOT NULL,
    razao_social TEXT,
    nome_fantasia TEXT,
    situacao_cadastral TEXT,
    data_situacao DATE,
    cnae_fiscal INT,
    cnae_descricao TEXT,
    natureza_juridica TEXT,
    capital_social NUMERIC(15,2),
    porte TEXT,
    uf TEXT,
    municipio TEXT,
    logradouro TEXT,
    raw_payload JSONB,
    enriched_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE enrich.company_qsa_members (
    id SERIAL PRIMARY KEY,
    company_profile_id INT REFERENCES enrich.company_profiles(id),
    nome_socio TEXT,
    cnpj_cpf_socio TEXT,
    qualificacao TEXT,
    data_entrada DATE
);

CREATE TABLE enrich.company_cnaes (
    id SERIAL PRIMARY KEY,
    company_profile_id INT REFERENCES enrich.company_profiles(id),
    cnae_codigo INT,
    cnae_descricao TEXT
);

CREATE TABLE enrich.sanctions (
    id SERIAL PRIMARY KEY,
    party_id INT REFERENCES core.parties(id),
    source_list TEXT NOT NULL,
    sanction_type TEXT,
    description TEXT,
    start_date DATE,
    end_date DATE,
    raw_payload JSONB,
    checked_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE enrich.pep_flags (
    id SERIAL PRIMARY KEY,
    party_id INT REFERENCES core.parties(id),
    nome TEXT,
    cpf TEXT,
    cargo TEXT,
    orgao TEXT,
    raw_payload JSONB,
    checked_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE enrich.semantic_labels (
    id SERIAL PRIMARY KEY,
    expense_event_id INT REFERENCES core.expense_events(id),
    label TEXT,
    confidence NUMERIC(3,2),
    grau_genericidade TEXT,
    compatibilidade_cnae TEXT,
    red_flags JSONB,
    labeled_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE enrich.llm_inferences (
    id SERIAL PRIMARY KEY,
    task_name TEXT NOT NULL,
    task_version TEXT,
    prompt_version TEXT,
    input_hash TEXT NOT NULL,
    provider_name TEXT,
    final_model_used TEXT,
    model_attempts JSONB,
    latency_ms INT,
    token_usage_input INT,
    token_usage_output INT,
    cost_estimate NUMERIC(10,6),
    parse_status TEXT,
    parsed_output JSONB,
    raw_response_path TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ══════════════════════════════════════════════════════════
-- RISK — Risco e investigação
-- ══════════════════════════════════════════════════════════

CREATE TABLE risk.cases (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'open',
    priority TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE risk.case_entities (
    id SERIAL PRIMARY KEY,
    case_id INT NOT NULL REFERENCES risk.cases(id),
    party_id INT NOT NULL REFERENCES core.parties(id),
    role TEXT
);

CREATE TABLE risk.alerts (
    id SERIAL PRIMARY KEY,
    alert_code TEXT NOT NULL,
    claim_type TEXT,
    evidence_tier TEXT,
    party_id INT REFERENCES core.parties(id),
    case_id INT REFERENCES risk.cases(id),
    description TEXT,
    score_impact INT,
    source_rule_version TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE risk.scores (
    id SERIAL PRIMARY KEY,
    party_id INT NOT NULL REFERENCES core.parties(id),
    risco_financeiro INT,
    risco_relacional INT,
    evidencia INT,
    calculated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE risk.graph_nodes (
    id SERIAL PRIMARY KEY,
    party_id INT NOT NULL REFERENCES core.parties(id),
    node_type TEXT,
    label TEXT,
    metadata JSONB
);

CREATE TABLE risk.graph_edges (
    id SERIAL PRIMARY KEY,
    from_node_id INT NOT NULL REFERENCES risk.graph_nodes(id),
    to_node_id INT NOT NULL REFERENCES risk.graph_nodes(id),
    edge_type TEXT NOT NULL,
    weight NUMERIC(5,2),
    evidence_json JSONB,
    source_rule TEXT
);

CREATE TABLE risk.rule_executions (
    id SERIAL PRIMARY KEY,
    rule_code TEXT NOT NULL,
    rule_version TEXT,
    target_party_id INT REFERENCES core.parties(id),
    input_snapshot JSONB,
    result_status TEXT,
    alerts_generated INT DEFAULT 0,
    duration_ms INT,
    executed_at TIMESTAMPTZ DEFAULT now()
);

-- ══════════════════════════════════════════════════════════
-- OPS — Operacional
-- ══════════════════════════════════════════════════════════

CREATE TABLE ops.source_sessions (
    id SERIAL PRIMARY KEY,
    source_name TEXT NOT NULL,
    session_mode TEXT NOT NULL,
    status TEXT DEFAULT 'ready',
    browser_profile_name TEXT,
    cookie_version INT DEFAULT 0,
    last_success_at TIMESTAMPTZ,
    last_validation_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    last_error_code TEXT,
    last_error_message TEXT,
    checkpoint_json JSONB,
    metadata_json JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE ops.jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_type TEXT NOT NULL,
    entity_type TEXT,
    entity_id INT,
    idempotency_key TEXT UNIQUE,
    status TEXT DEFAULT 'pending',
    payload JSONB,
    attempt INT DEFAULT 0,
    max_attempts INT DEFAULT 3,
    last_error TEXT,
    next_retry_at TIMESTAMPTZ,
    worker_name TEXT,
    source_session_id INT REFERENCES ops.source_sessions(id),
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE ops.job_events (
    id SERIAL PRIMARY KEY,
    job_id UUID NOT NULL REFERENCES ops.jobs(id),
    event_type TEXT NOT NULL,
    worker_name TEXT,
    attempt INT,
    message TEXT,
    context_json JSONB,
    event_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE ops.human_interventions (
    id SERIAL PRIMARY KEY,
    source_session_id INT REFERENCES ops.source_sessions(id),
    job_id UUID REFERENCES ops.jobs(id),
    intervention_type TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    requested_at TIMESTAMPTZ DEFAULT now(),
    resolved_at TIMESTAMPTZ,
    requested_by TEXT,
    resolved_by TEXT,
    notes TEXT,
    artifacts_json JSONB
);

CREATE TABLE ops.worker_heartbeats (
    id SERIAL PRIMARY KEY,
    worker_name TEXT NOT NULL,
    queue_name TEXT,
    status TEXT DEFAULT 'alive',
    last_beat_at TIMESTAMPTZ DEFAULT now(),
    jobs_processed INT DEFAULT 0,
    jobs_failed INT DEFAULT 0
);

CREATE TABLE ops.rate_limits (
    id SERIAL PRIMARY KEY,
    source_name TEXT NOT NULL,
    endpoint TEXT,
    requests_per_minute INT,
    current_count INT DEFAULT 0,
    window_start TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE ops.dead_letters (
    id SERIAL PRIMARY KEY,
    original_queue TEXT NOT NULL,
    job_id UUID REFERENCES ops.jobs(id),
    payload JSONB,
    failure_type TEXT,
    error_message TEXT,
    attempts INT,
    dead_lettered_at TIMESTAMPTZ DEFAULT now()
);

-- ── Indexes ──────────────────────────────────────────────
CREATE INDEX idx_parties_type ON core.parties(party_type);
CREATE INDEX idx_parties_name_trgm ON core.parties USING gin(canonical_name gin_trgm_ops);
CREATE INDEX idx_party_docs_value ON core.party_documents(doc_value);
CREATE INDEX idx_persons_cpf_center ON core.persons(cpf_center);
CREATE INDEX idx_organizations_cnpj ON core.organizations(cnpj);
CREATE INDEX idx_expense_events_type ON core.expense_events(event_type);
CREATE INDEX idx_expense_events_date ON core.expense_events(data_pagamento);
CREATE INDEX idx_expense_events_counter ON core.expense_events(counterparty_id);
CREATE INDEX idx_relationships_from ON core.party_relationships(from_party_id);
CREATE INDEX idx_relationships_to ON core.party_relationships(to_party_id);
CREATE INDEX idx_relationships_type ON core.party_relationships(rel_type);
CREATE INDEX idx_alerts_party ON risk.alerts(party_id);
CREATE INDEX idx_alerts_code ON risk.alerts(alert_code);
CREATE INDEX idx_jobs_status ON ops.jobs(status);
CREATE INDEX idx_jobs_type ON ops.jobs(job_type);
CREATE INDEX idx_job_events_job ON ops.job_events(job_id);
CREATE INDEX idx_sessions_source ON ops.source_sessions(source_name);
CREATE INDEX idx_sessions_status ON ops.source_sessions(status);
