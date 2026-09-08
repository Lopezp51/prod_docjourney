-- ==============================================================================
-- PROD_reset_database.sql: Script SQL para Limpeza e Reset do Banco de Dados
-- Projeto: DocJourney (PostgreSQL)
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- OPÇÃO 1: Limpeza Rápida de Dados Transacionais (Preserva Catálogo e Estrutura)
-- ------------------------------------------------------------------------------
-- Utilize esta opção para apagar todas as jornadas, envelopes, documentos e logs
-- de testes sem precisar recriar as tabelas.
-- ------------------------------------------------------------------------------
TRUNCATE TABLE 
    maintenance_history,
    envelope_signers,
    documents,
    envelopes,
    journey_requests,
    associates
CASCADE;

-- ------------------------------------------------------------------------------
-- OPÇÃO 2: Drop Completo de Todas as Tabelas (Reset Estrutural Total)
-- ------------------------------------------------------------------------------
-- Descomente as linhas abaixo se desejar excluir completamente todas as tabelas:
-- 
-- DROP TABLE IF EXISTS maintenance_history CASCADE;
-- DROP TABLE IF EXISTS envelope_signers CASCADE;
-- DROP TABLE IF EXISTS documents CASCADE;
-- DROP TABLE IF EXISTS envelopes CASCADE;
-- DROP TABLE IF EXISTS journey_requests CASCADE;
-- DROP TABLE IF EXISTS process_configurations CASCADE;
-- DROP TABLE IF EXISTS processes CASCADE;
-- DROP TABLE IF EXISTS associates CASCADE;
-- 
-- Após o DROP, execute o arquivo PROD_schema.sql para recriar a estrutura íntegra.
