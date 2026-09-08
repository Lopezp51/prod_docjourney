# Guia Visual de Relacionamentos do Banco de Dados (PostgreSQL)

**Documento Técnico Oficial de Arquitetura de Dados (PRODUÇÃO)**  
**Projeto:** DocJourney - Orquestrador de Assinaturas Eletrônicas e Gestão Documental  
**Estrutura Relacional:** 8 Tabelas em Inglês com chaves estrangeiras, índices e integridade referencial.

---

## 📊 1. Diagrama Entidade-Relacionamento (ERD)

```mermaid
erDiagram
    associates ||--o{ documents : "1. owns (360 view)"
    associates ||--o{ envelope_signers : "2. signs"
    processes ||--o{ process_configurations : "3. configures rules"
    processes ||--o{ journey_requests : "4. receives tasks"
    journey_requests ||--o{ envelopes : "5. spawns clusters"
    journey_requests ||--o{ maintenance_history : "6. logs audit"
    envelopes ||--o{ documents : "7. contains PDFs"
    envelopes ||--o{ envelope_signers : "8. requires signers"
    envelopes ||--o{ maintenance_history : "9. tracks issues"

    associates {
        uuid id PK
        varchar tax_id "Unique (CPF / CNPJ)"
        varchar name
        varchar email
        varchar phone
    }

    processes {
        uuid id PK
        varchar name "Unique (e.g. Commercial Credit V2)"
        varchar description
        boolean active
    }

    process_configurations {
        uuid id PK
        uuid process_id FK
        varchar template_id
        varchar document_name
        jsonb dispatch_nodes
        boolean mandatory
    }

    journey_requests {
        uuid id PK
        uuid process_id FK
        varchar mongo_id "Unique (Idempotency)"
        bigint process_number "e.g. 1225591"
        jsonb fluid_payload
        varchar status "RECEIVED / IN_PROCESS / COMPLETED"
    }

    envelopes {
        uuid id PK
        uuid request_id FK
        varchar external_envelope_id "Unique (OpenAPI v2 ID)"
        varchar document_scope_hash "SHA256 Cluster Hash"
        integer envelope_version "1, 2, 3..."
        varchar provider "CERTISIGN / ADESAO"
        varchar envelope_status "DRAFT / PENDING_SIGNATURE / COMPLETED"
        timestamp expired_at
    }

    documents {
        uuid id PK
        uuid envelope_id FK
        uuid associate_id FK
        varchar file_name
        varchar source_hash
        integer document_type_id
        varchar extension
    }

    envelope_signers {
        uuid id PK
        uuid envelope_id FK
        uuid associate_id FK
        varchar external_signer_id
        varchar signer_role
        integer signature_order
        varchar signature_type "ELECTRONIC / DIGITAL"
        varchar validation_channel "EMAIL / WHATSAPP"
        varchar signature_status "PENDING_LINK_DELIVERY / SIGNED"
    }

    maintenance_history {
        uuid id PK
        uuid request_id FK
        uuid envelope_id FK
        varchar reason_code "DOC_VERSION_CHANGE / EXPIRED_60_DAYS"
        text detailed_description
        boolean resolved
    }
```

---

## 🔗 2. Como as Tabelas se Relacionam na Prática

### A. Fluxo de Entrada e Idempotência
1. A esteira (Fluid) envia uma tarefa identificada por `mongo_id` e `process_number`.
2. A tabela `processes` garante que o tipo do processo existe ou é catalogado.
3. A tabela `journey_requests` registra a solicitação de forma idempotente: novas tentativas com o mesmo `mongo_id` não geram linhas duplicadas.

### B. Clusterização e Versionamento de Envelopes
1. Para cada combinação única de `[Documentos x Signatários]`, a automação gera um `document_scope_hash` determinístico via SHA256.
2. Na tabela `envelopes`, cada cluster gera um registro com `envelope_version = 1`.
3. Se o processo for reenviado com documentos alterados ou novos signatários, o envelope anterior recebe o status `REPLACED_CANCELED` e o novo envelope é criado com `envelope_version = versao_anterior + 1`.

### C. Cadastro Único do Associado (Visão 360)
1. O associado (`associates`) é único por CPF/CNPJ (`tax_id`).
2. Uma única pessoa pode participar de múltiplos envelopes e processos diferentes, mantendo histórico unificado de assinaturas e documentos.

---

## 🔍 3. Consultas SQL Rápidas para Auditoria Visual

```sql
-- Visão 360: Processo, Envelopes, Signatários e Documentos
SELECT 
    j.process_number,
    p.name AS process_name,
    e.envelope_version,
    e.envelope_status,
    e.external_envelope_id,
    a.name AS signer_name,
    es.signer_role,
    es.validation_channel,
    d.file_name
FROM journey_requests j
JOIN processes p ON p.id = j.process_id
JOIN envelopes e ON e.request_id = j.id
JOIN envelope_signers es ON es.envelope_id = e.id
JOIN associates a ON a.id = es.associate_id
JOIN documents d ON d.envelope_id = e.id
ORDER BY j.process_number, e.envelope_version;
```
