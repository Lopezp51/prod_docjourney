# Guia Visual de Relacionamentos do Banco de Dados (PostgreSQL)

Este documento foi criado para ajudar você a visualizar e analisar a estrutura relacional do banco de dados `docjourney_db`, mostrando como as 8 tabelas se conectam e como consultar os dados fictícios que populamos na sua máquina.

---

## 📊 1. Diagrama Entidade-Relacionamento (ERD)

```mermaid
erDiagram
    associados ||--o{ documentos : "1. possui (Visão 360)"
    associados ||--o{ envelope_signatarios : "2. assina"
    processos ||--o{ processos_configuracoes : "3. contém regras"
    processos ||--o{ jornadas_solicitacoes : "4. recebe tarefas"
    jornadas_solicitacoes ||--o{ envelopes : "5. origina clusters"
    jornadas_solicitacoes ||--o{ historico_manutencao : "6. registra auditoria"
    envelopes ||--o{ documentos : "7. contém PDFs do escopo"
    envelopes ||--o{ envelope_signatarios : "8. exige assinaturas"
    envelopes ||--o{ historico_manutencao : "9. monitora falhas"

    associados {
        uuid id PK
        varchar cpf_cnpj "Unique"
        varchar nome
        varchar email
        varchar telefone
    }

    processos {
        uuid id PK
        varchar nome "Unique (ex: Crédito Comercial)"
        varchar descricao
        boolean ativo
    }

    jornadas_solicitacoes {
        uuid id PK
        uuid id_processo FK
        varchar mongo_id "Unique (Idempotência)"
        bigint num_processo "Ex: 1225591"
        jsonb payload_fluid
        varchar status "RECEBIDO / EM_PROCESSAMENTO / INTERVENCAO"
    }

    envelopes {
        uuid id PK
        uuid id_solicitacao FK
        varchar id_envelope_externo "Unique (ID OpenAPI v2)"
        varchar hash_escopo_documentos "Hash SHA256 do Cluster"
        integer versao_envelope "1, 2, 3..."
        varchar provider "CERTISIGN / ADESAO"
        varchar status_envelope "ASSINATURA_PENDENTE / CONCLUIDO / EXPIRADO"
    }

    documentos {
        uuid id PK
        uuid id_envelope FK
        uuid id_associado FK
        varchar nome_arquivo
        varchar hash_origem
        integer tipo_doc_id "Ex: 765 (CCB)"
    }

    envelope_signatarios {
        uuid id PK
        uuid id_envelope FK
        uuid id_associado FK
        varchar papel_assinante "Avalista, Segurado, Titular"
        integer ordem_assinatura "1, 2"
        varchar tipo_assinatura "ELETRONIC / DIGITAL"
        varchar canal_validacao "EMAIL / WHATSAPP"
        varchar status_assinatura
    }

    historico_manutencao {
        uuid id PK
        uuid id_solicitacao FK
        uuid id_envelope FK
        varchar motivo_codigo "Ex: EXPIRADO_60_DIAS"
        text descricao_detalhada
        boolean resolvido
    }
```

---

## 🔍 2. Como as Tabelas se Conectam (Explicação Prática)

1. **`processos` $\rightarrow$ `jornadas_solicitacoes`**:
   - Um tipo de processo (ex.: *"Solicitação de Crédito Comercial V2"*) recebe várias tarefas/pedidos vindos do Fluid (`jornadas_solicitacoes`).
2. **`jornadas_solicitacoes` $\rightarrow$ `envelopes`**:
   - Uma solicitação do Fluid gera **um ou mais envelopes** dependendo da clusterização por escopo documental (`hash_escopo_documentos`).
3. **`envelopes` $\rightarrow$ `documentos` e `envelope_signatarios`**:
   - Cada envelope agrupa os arquivos binários PDFs daquele escopo (`documentos`) e os signatários que devem assiná-los (`envelope_signatarios`).
4. **`associados` (Visão 360 do Cliente)**:
   - A tabela `associados` centraliza a pessoa física ou jurídica por `cpf_cnpj`. Tanto a tabela `documentos` quanto `envelope_signatarios` apontam diretamente para `associados.id`, permitindo consultar rapidamente todos os documentos de um cliente.
5. **`historico_manutencao`**:
   - Registra log auditado de exceções, substituições e expirações de 60 dias vinculadas à solicitação e ao envelope impactado.

---

## 💻 3. Consultas SQL Prontas para Copiar e Colar

Você pode copiar e executar essas queries diretamente no pgAdmin, DBeaver ou VS Code PostgreSQL para visualizar os dados fictícios que populamos na sua máquina:

### 📄 Query 1: Visão Geral de Envelopes Clusterizados por Processo
> Mostra cada envelope gerado, seu status, qual o processo do Fluid e o hash de escopo documental:

```sql
SELECT 
    p.nome AS processo,
    j.num_processo,
    j.status AS status_jornada,
    e.id_envelope_externo,
    e.hash_escopo_documentos,
    e.versao_envelope,
    e.provider,
    e.status_envelope
FROM envelopes e
JOIN jornadas_solicitacoes j ON j.id = e.id_solicitacao
JOIN processos p ON p.id = j.id_processo
ORDER BY j.num_processo, e.versao_envelope;
```

---

### 👤 Query 2: Visão dos Signatários, Canais e Documentos por Envelope
> Exibe quem precisa assinar cada envelope, por qual canal (E-mail ou WhatsApp), qual o papel e qual arquivo PDF está associado:

```sql
SELECT 
    j.num_processo,
    e.id_envelope_externo,
    a.nome AS nome_signatario,
    a.cpf_cnpj,
    es.papel_assinante,
    es.canal_validacao,
    es.status_assinatura,
    d.nome_arquivo,
    d.tipo_doc_id
FROM envelope_signatarios es
JOIN associados a ON a.id = es.id_associado
JOIN envelopes e ON e.id = es.id_envelope
JOIN jornadas_solicitacoes j ON j.id = e.id_solicitacao
JOIN documentos d ON d.id_envelope = e.id
ORDER BY j.num_processo, es.ordem_assinatura;
```

---

### 🌐 Query 3: Visão 360 do Cliente (Consultar tudo de um CPF/CNPJ)
> Traz o histórico completo de um associado independentemente do processo:

```sql
SELECT 
    a.nome AS cliente,
    a.cpf_cnpj,
    p.nome AS processo,
    j.num_processo,
    es.papel_assinante,
    es.canal_validacao,
    d.nome_arquivo,
    e.status_envelope
FROM associados a
JOIN envelope_signatarios es ON es.id_associado = a.id
JOIN envelopes e ON e.id = es.id_envelope
JOIN jornadas_solicitacoes j ON j.id = e.id_solicitacao
JOIN processos p ON p.id = j.id_processo
JOIN documentos d ON d.id_envelope = e.id
WHERE a.cpf_cnpj = '02631353900';
```

---

### 🛠️ Query 4: Auditoria do Histórico de Manutenção e Intervenções
> Exibe os logs de envelopes expirados (> 60 dias) ou com erros que exigiram intervenção:

```sql
SELECT 
    j.num_processo,
    hm.motivo_codigo,
    hm.descricao_detalhada,
    hm.resolvido,
    hm.resolvido_por,
    hm.created_at AS data_ocorrencia
FROM historico_manutencao hm
JOIN jornadas_solicitacoes j ON j.id = hm.id_solicitacao
ORDER BY hm.created_at DESC;
```
