-- ====================================================================
-- MIGRATION_PATCH.SQL: Atualizações geradas automaticamente pelo Inspector
-- Adiciona com segurança colunas novas identificadas no schema do microsserviço/PAS
-- ====================================================================

-- Atualizações para a tabela: documents
ALTER TABLE documents ADD COLUMN IF NOT EXISTS mime_type VARCHAR(255);
ALTER TABLE documents ADD COLUMN IF NOT EXISTS size_bytes INTEGER;

-- Atualizações para a tabela: envelopes
ALTER TABLE envelopes ADD COLUMN IF NOT EXISTS old_envelope_id UUID;
ALTER TABLE envelopes ADD COLUMN IF NOT EXISTS new_document_scope_hash VARCHAR(255);
ALTER TABLE envelopes ADD COLUMN IF NOT EXISTS reason_code VARCHAR(255);
ALTER TABLE envelopes ADD COLUMN IF NOT EXISTS detailed_description VARCHAR(255);
ALTER TABLE envelopes ADD COLUMN IF NOT EXISTS new_external_envelope_id VARCHAR(255);
ALTER TABLE envelopes ADD COLUMN IF NOT EXISTS operator_name VARCHAR(255);
ALTER TABLE envelopes ADD COLUMN IF NOT EXISTS comment VARCHAR(255);

-- Atualizações para a tabela: journey_requests
ALTER TABLE journey_requests ADD COLUMN IF NOT EXISTS process_name VARCHAR(255);
ALTER TABLE journey_requests ADD COLUMN IF NOT EXISTS retry_count INTEGER;

-- Atualizações para a tabela: maintenance_history
ALTER TABLE maintenance_history ADD COLUMN IF NOT EXISTS canceled_by VARCHAR(255);
ALTER TABLE maintenance_history ADD COLUMN IF NOT EXISTS expired_count INTEGER;
ALTER TABLE maintenance_history ADD COLUMN IF NOT EXISTS expired_envelope_ids JSONB;
ALTER TABLE maintenance_history ADD COLUMN IF NOT EXISTS processed_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE maintenance_history ADD COLUMN IF NOT EXISTS message VARCHAR(255);
ALTER TABLE maintenance_history ADD COLUMN IF NOT EXISTS total_journeys INTEGER;
ALTER TABLE maintenance_history ADD COLUMN IF NOT EXISTS journeys_by_status JSONB;
ALTER TABLE maintenance_history ADD COLUMN IF NOT EXISTS total_envelopes INTEGER;
ALTER TABLE maintenance_history ADD COLUMN IF NOT EXISTS envelopes_by_status JSONB;
ALTER TABLE maintenance_history ADD COLUMN IF NOT EXISTS unresolved_maintenance_incidents INTEGER;
ALTER TABLE maintenance_history ADD COLUMN IF NOT EXISTS total_maintenance_incidents INTEGER;
ALTER TABLE maintenance_history ADD COLUMN IF NOT EXISTS timestamp TIMESTAMP WITH TIME ZONE;
ALTER TABLE maintenance_history ADD COLUMN IF NOT EXISTS comment VARCHAR(255);

-- Atualizações para a tabela: envelope_signers
ALTER TABLE envelope_signers ADD COLUMN IF NOT EXISTS tax_id VARCHAR(255);
ALTER TABLE envelope_signers ADD COLUMN IF NOT EXISTS name VARCHAR(255);
ALTER TABLE envelope_signers ADD COLUMN IF NOT EXISTS email VARCHAR(255);
ALTER TABLE envelope_signers ADD COLUMN IF NOT EXISTS phone VARCHAR(255);

