-- ==============================================================================
-- schema.sql (Link/Mirror de PROD_schema.sql)
-- Projeto: DocJourney - Orquestrador de Assinaturas Eletrônicas e Gestão Documental
-- Nomenclatura 100% em Inglês padronizada (Tabelas, Colunas e Índices)
-- ==============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS associates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tax_id VARCHAR(14) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(20),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS processes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS process_configurations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    process_id UUID NOT NULL,
    template_id VARCHAR(255) NOT NULL,
    document_name VARCHAR(255) NOT NULL,
    dispatch_nodes JSONB,
    mandatory BOOLEAN DEFAULT TRUE,
    field_mappings JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_process_config_process FOREIGN KEY (process_id)
        REFERENCES processes (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS journey_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    process_id UUID NOT NULL,
    mongo_id VARCHAR(50) NOT NULL UNIQUE,
    process_number BIGINT NOT NULL,
    initial_id VARCHAR(50),
    fluid_payload JSONB NOT NULL,
    status VARCHAR(50) NOT NULL,
    details TEXT,
    executions INTEGER DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_journey_requests_process FOREIGN KEY (process_id)
        REFERENCES processes (id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS envelopes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id UUID NOT NULL,
    external_envelope_id VARCHAR(100) UNIQUE,
    document_scope_hash VARCHAR(64) NOT NULL,
    envelope_version INTEGER DEFAULT 1,
    provider VARCHAR(50) NOT NULL,
    envelope_status VARCHAR(50) NOT NULL,
    allow_signature_order BOOLEAN DEFAULT FALSE,
    sent_at TIMESTAMP WITH TIME ZONE,
    expired_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_envelopes_request FOREIGN KEY (request_id)
        REFERENCES journey_requests (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    envelope_id UUID NOT NULL,
    associate_id UUID NOT NULL,
    configuration_id UUID,
    file_name VARCHAR(255) NOT NULL,
    source_hash VARCHAR(255) NOT NULL,
    document_type_id INTEGER,
    extension VARCHAR(10) DEFAULT 'pdf',
    version INTEGER DEFAULT 1,
    status VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_documents_envelope FOREIGN KEY (envelope_id)
        REFERENCES envelopes (id) ON DELETE CASCADE,
    CONSTRAINT fk_documents_associate FOREIGN KEY (associate_id)
        REFERENCES associates (id) ON DELETE RESTRICT,
    CONSTRAINT fk_documents_configuration FOREIGN KEY (configuration_id)
        REFERENCES process_configurations (id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS envelope_signers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    envelope_id UUID NOT NULL,
    associate_id UUID NOT NULL,
    external_signer_id VARCHAR(100),
    signer_role VARCHAR(100),
    signature_order INTEGER DEFAULT 1,
    signature_type VARCHAR(50) NOT NULL,
    validation_channel VARCHAR(50) NOT NULL,
    signing_url TEXT,
    signature_status VARCHAR(50) NOT NULL,
    signed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_envelope_signers_envelope FOREIGN KEY (envelope_id)
        REFERENCES envelopes (id) ON DELETE CASCADE,
    CONSTRAINT fk_envelope_signers_associate FOREIGN KEY (associate_id)
        REFERENCES associates (id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS maintenance_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id UUID NOT NULL,
    envelope_id UUID,
    reason_code VARCHAR(50) NOT NULL,
    detailed_description TEXT,
    resolved BOOLEAN DEFAULT FALSE,
    resolved_by VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_maintenance_request FOREIGN KEY (request_id)
        REFERENCES journey_requests (id) ON DELETE CASCADE,
    CONSTRAINT fk_maintenance_envelope FOREIGN KEY (envelope_id)
        REFERENCES envelopes (id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_associates_tax_id ON associates (tax_id);
CREATE INDEX IF NOT EXISTS idx_journey_mongo_id ON journey_requests (mongo_id);
CREATE INDEX IF NOT EXISTS idx_journey_process_number ON journey_requests (process_number);
CREATE INDEX IF NOT EXISTS idx_envelopes_external_id ON envelopes (external_envelope_id);
CREATE INDEX IF NOT EXISTS idx_envelopes_request_scope_hash ON envelopes (request_id, document_scope_hash);
CREATE INDEX IF NOT EXISTS idx_envelopes_expiration ON envelopes (expired_at) WHERE envelope_status = 'PENDING_SIGNATURE';
CREATE INDEX IF NOT EXISTS idx_envelope_signers_associate ON envelope_signers (associate_id);
CREATE INDEX IF NOT EXISTS idx_maintenance_reason ON maintenance_history (reason_code, resolved);
