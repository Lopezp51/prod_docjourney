# Roteiro de Testes e Validação por Banco de Dados (Manual de QA & Auditoria SQL)

**Documento Técnico Oficial de Engenharia de QA & Banco de Dados (PRODUÇÃO)**  
**Projeto:** DocJourney - Orquestrador de Assinaturas Eletrônicas e Gestão Documental  
**Objetivo:** Guiar desenvolvedores, arquitetos e analistas de QA na execução e auditoria direta por banco de dados de todas as transações do ciclo de vida de envelopes, versionamento incremental, substituição seletiva, expiração e integridade relacional.

---

## 📋 1. Visão Geral do Ambiente e Convenção de Nomenclatura

Toda a auditoria é feita via consultas diretas SQL no banco PostgreSQL (`docjourney_db`). Todas as tabelas, colunas e identificadores utilizam a nomenclatura padronizada 100% em inglês.

### Tabela de Mapeamento de Entidades
| Nome da Tabela | Papel no Sistema | Chaves Principais |
| :--- | :--- | :--- |
| `associates` | Cadastro central de pessoas físicas e jurídicas. | `tax_id` (CPF/CNPJ UNIQUE), `id` (PK) |
| `processes` | Catálogo de tipos de processos homologados. | `name` (UNIQUE), `id` (PK) |
| `process_configurations` | Regras de template e nós de envio por processo. | `process_id` (FK), `template_id` |
| `journey_requests` | Solicitações documentais vindas do Fluid/MongoDB. | `mongo_id` (UNIQUE), `process_number` |
| `envelopes` | Envelopes clusterizados por escopo documental. | `request_id` (FK), `document_scope_hash`, `external_envelope_id` |
| `documents` | Arquivos PDFs vinculados ao envelope. | `envelope_id` (FK), `source_hash` |
| `envelope_signers` | Participantes, papéis e canais de autenticação. | `envelope_id` (FK), `associate_id` (FK) |
| `maintenance_history` | Auditoria de intervenções, substituições e expirações. | `request_id` (FK), `envelope_id` (FK), `reason_code` |

---

## 📌 CENÁRIO 1: Inclusão e Metadados do Documento/Envelope (Versão Inicial)

### 1.1. Passo a Passo da Ação
1. A automação recebe uma nova tarefa do MongoDB para o processo `#200001` com o signatário **Edilson** vinculado ao arquivo `765 - CCB.pdf`.
2. A automação executa o fluxo e realiza o `POST /v2/envelope/create` e `POST /files/envelope/:envelopeId/files`.

### 1.2. Resultado Esperado
- Registro criado na tabela `journey_requests` com status `RECEIVED` ou `IN_PROCESS`.
- Registro criado na tabela `envelopes` com `envelope_version = 1` e `envelope_status = 'PENDING_SIGNATURE'`.
- Os registros de `documents` e `envelope_signers` são vinculados ao `id` do envelope.

### 1.3. Queries SQL de Auditoria

```sql
-- 1. Auditoria do Envelope Criado e seus Metadados
SELECT 
    e.id AS envelope_db_id,
    e.external_envelope_id,
    e.envelope_version,
    e.envelope_status,
    e.provider,
    e.document_scope_hash,
    e.created_at AS creation_date
FROM envelopes e
JOIN journey_requests j ON j.id = e.request_id
WHERE j.process_number = 200001 AND e.envelope_status = 'PENDING_SIGNATURE';

-- 2. Auditoria dos Documentos e Signatários Vinculados ao Envelope
SELECT 
    e.external_envelope_id,
    a.name AS signer_name,
    a.tax_id,
    es.signer_role,
    es.validation_channel,
    es.signature_status,
    d.file_name,
    d.document_type_id
FROM envelopes e
JOIN envelope_signers es ON es.envelope_id = e.id
JOIN associates a ON a.id = es.associate_id
JOIN documents d ON d.envelope_id = e.id
WHERE e.external_envelope_id = 'mock_envelope_0dd136f6'; -- Substituir pelo ID retornado
```

---

## 🔄 CENÁRIO 2: Versionamento e Troca de Versão do Documento (Substituição Seletiva)

### 2.1. Passo a Passo da Ação
1. O operador envia uma **nova versão** do documento `765 - CCB V2 Nova.pdf` para o mesmo processo `#200001`.
2. A automação detecta a alteração de escopo/versão e executa o fluxo de substituição seletiva.

### 2.2. Resultado Esperado
- O envelope versão 1 (`envelope_version = 1`) tem o status atualizado no banco para **`REPLACED_CANCELED`**.
- Um **novo envelope** é gerado com **`envelope_version = 2`** e status **`PENDING_SIGNATURE`**.
- O envelope v1 é cancelado no portal externo via `DELETE /v2/envelope/{id}`.

### 2.3. Queries SQL de Auditoria

```sql
-- Auditoria de Substituição de Versão por Histórico Incremental
SELECT 
    e.envelope_version,
    e.external_envelope_id,
    e.envelope_status,
    e.document_scope_hash,
    e.updated_at AS change_date
FROM envelopes e
JOIN journey_requests j ON j.id = e.request_id
WHERE j.process_number = 200001
ORDER BY e.envelope_version ASC;
```
> **Resultado Esperado da Query:**
> - Linha 1: `envelope_version = 1` | `envelope_status = 'REPLACED_CANCELED'`
> - Linha 2: `envelope_version = 2` | `envelope_status = 'PENDING_SIGNATURE'`

---

## 👥 CENÁRIO 3: Alteração / Inclusão de Novos Signatários

### 3.1. Passo a Passo da Ação
1. A tarefa é reenviada adicionando um novo signatário (**Aila Franca - Cônjuge Avalista**) ao mesmo processo `#200001`.
2. A automação detecta que a lista de signatários do cluster mudou.

### 3.2. Resultado Esperado
- O envelope versão 2 é descontinuado e atualizado para **`REPLACED_CANCELED`**.
- Um novo envelope **versão 3** é criado vinculando **ambos os signatários** (Edilson + Aila).

### 3.3. Queries SQL de Auditoria

```sql
-- Auditoria de Signatários Vinculados à Versão Atual Ativa do Envelope
SELECT 
    e.envelope_version,
    e.envelope_status,
    a.name AS signer_name,
    a.tax_id,
    es.signer_role,
    es.validation_channel
FROM envelopes e
JOIN envelope_signers es ON es.envelope_id = e.id
JOIN associates a ON a.id = es.associate_id
JOIN journey_requests j ON j.id = e.request_id
WHERE j.process_number = 200001 AND e.envelope_status = 'PENDING_SIGNATURE'
ORDER BY es.signature_order ASC;
```
> **Resultado Esperado da Query:** Retorna 2 linhas com Edilson (Titular) e Aila (Cônjuge Avalista) vinculados à versão ativa v3.

---

## 🚫 CENÁRIO 4: Cancelamento Explícito de Envelope

### 4.1. Passo a Passo da Ação
1. O usuário ou processo origem solicita o cancelamento manual da solicitação.
2. A automação aciona a rota `DELETE /v2/envelope/{id}` e atualiza o banco local.

### 4.2. Resultado Esperado
- O status do envelope na tabela `envelopes` muda para **`CANCELED`**.
- É gravado um log na tabela `maintenance_history` registrando o motivo e quem executou o cancelamento.

### 4.3. Queries SQL de Auditoria

```sql
-- 1. Verifica o Status do Envelope Cancelado
SELECT id, external_envelope_id, envelope_status, updated_at 
FROM envelopes 
WHERE id = 'uuid-do-envelope-cancelado';

-- 2. Auditando o Log na Tabela maintenance_history
SELECT 
    mh.reason_code,
    mh.detailed_description,
    mh.resolved,
    mh.resolved_by,
    mh.created_at
FROM maintenance_history mh
WHERE mh.envelope_id = 'uuid-do-envelope-cancelado';
```

---

## ⏰ CENÁRIO 5: Rotina de Expiração (> 60 Dias ou Vencimento)

### 5.1. Procedimento Prático de Teste
Para auditar envelopes que ultrapassaram a janela de 60 dias sem assinatura:

```sql
-- Consulta Envelopes Elegíveis para Expiração (> 60 Dias ou Vencidos)
SELECT 
    id,
    external_envelope_id,
    envelope_status,
    expired_at,
    CURRENT_TIMESTAMP AS current_time
FROM envelopes
WHERE envelope_status = 'PENDING_SIGNATURE'
  AND expired_at <= CURRENT_TIMESTAMP;
```

### 5.2. Consulta PÓS-Execução da Rotina de Expiração

```sql
-- 1. Comprova que o status do envelope mudou para 'EXPIRED'
SELECT id, external_envelope_id, envelope_status, updated_at
FROM envelopes
WHERE external_envelope_id = 'openapi_env_expirado_legado';

-- 2. Comprova a gravação do registro de auditoria na tabela maintenance_history
SELECT 
    mh.reason_code,
    mh.detailed_description,
    mh.resolved,
    mh.created_at
FROM maintenance_history mh
JOIN envelopes e ON e.id = mh.envelope_id
WHERE e.external_envelope_id = 'openapi_env_expirado_legado';
```
> **Resultado Esperado:** `envelope_status = 'EXPIRED'` e registro em `maintenance_history` com `reason_code = 'EXPIRED_60_DAYS'`.

---

## ⚠️ CENÁRIO 6: Pré-Validação Agregada ("Tudo de uma Vez")

### 6.1. Passo a Passo da Ação
1. A automação recebe um payload com CPF inválido, e-mail inválido e anexo faltante.
2. A `TaskPayloadValidator` varre todos os itens sem interromper no primeiro erro (No-Fail-Fast).

### 6.2. Resultado Esperado
- A automação lança a `BulkValidationError` contendo a lista com todas as pendências agregadas.
- O resultado retornado traz o campo `parecer_fluid` em HTML estruturado com a lista de erros em vermelho.

---

## 🚨 CENÁRIO 7: Detecção de Documentos Quebrados/Corrompidos (Instabilidade AWS/Fluid)

### 7.1. Passo a Passo da Ação
1. A automação recebe um payload onde o anexo do documento possui **0 bytes** (arquivo vazio) ou **hash vazio** (vaga criada no Fluid sem arquivo físico anexado devido a instabilidade na AWS).
2. O método `TaskPayloadValidator._validate_attachment_integrity` detecta a inconsistência nominalmente.

### 7.2. Resultado Esperado
- A automação lança a exceção [`CorruptedDocumentError`](file:///c:/Users/lopes/OneDrive/Área%20de%20Trabalho/Programação/Sicredi/docjourney/automacao/domain/exceptions.py) com código `CORRUPTED_DOCUMENT_ERROR`.
- O parecer HTML orienta expressamente:
  `"Identificamos que o documento 'X' está corrompido, vazio ou com falha de carregamento no Fluid/AWS... Por favor, acesse o processo no Fluid, EXCLUA o documento corrompido e anexe novamente o arquivo PDF correto em questão."`
- Ocorrência gravada na tabela `maintenance_history` com `reason_code = 'CORRUPTED_DOCUMENT'`.

### 7.3. Consulta SQL de Validação no Banco
```sql
SELECT 
    jr.process_number,
    mh.reason_code,
    mh.detailed_description,
    mh.created_at
FROM maintenance_history mh
JOIN journey_requests jr ON jr.id = mh.request_id
WHERE mh.reason_code = 'CORRUPTED_DOCUMENT'
ORDER BY mh.created_at DESC
LIMIT 1;
```

---

## 🚀 Execução Automatizada dos Cenários

Você pode rodar a suíte interativa completa que simula todos os 7 cenários sequencialmente contra o PostgreSQL:

```powershell
.\.venv\Scripts\python.exe automacao/tests/test_interactive_scenarios.py
```
