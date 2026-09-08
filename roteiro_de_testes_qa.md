# Roteiro de Testes e Validação por Banco de Dados (Manual de QA & Auditoria SQL)

**Documento Técnico de Engenharia de QA & Banco de Dados**  
**Projeto:** Orquestrador de Assinaturas Eletrônicas (OpenAPI v2 + PostgreSQL + Python RPA)  
**Objetivo:** Guiar desenvolvedores e analistas de QA na execução e auditoria por banco de dados de todas as transações do ciclo de vida de envelopes, versionamento, substituição seletiva, expiração e integridade relacional.

---

## 📋 1. Visão Geral do Ambiente e Convenção de Nomenclatura

Toda a auditoria é feita via consultas diretas SQL no banco PostgreSQL (`docjourney_db`).

### Nomenclatura Padronizada das Tabelas
| Nome da Tabela | Papel no Sistema |
| :--- | :--- |
| `associados` | Cadastro único de Pessoas Físicas e Jurídicas (`cpf_cnpj` UNIQUE). |
| `processos` | Cadastro dos tipos de processo da esteira (ex.: *Solicitação de Crédito Comercial V2*). |
| `jornadas_solicitacoes` | Registro da solicitação vinda do MongoDB/Fluid (`mongo_id` UNIQUE). |
| `envelopes` | Instância do envelope clusterizado na OpenAPI v2 (`hash_escopo_documentos`, `versao_envelope`). |
| `documentos` | Arquivos PDFs vinculados a um envelope. |
| `envelope_signatarios` | Participantes, papéis e canais de notificação (E-mail/WhatsApp) de um envelope. |
| `historico_manutencao` | Auditoria de exceções, substituições e expirações (> 60 dias). |

---

## 📌 CENÁRIO 1: Inclusão e Metadados do Documento/Envelope (Versão Inicial)

### 1.1. Passo a Passo da Ação
1. A automação recebe uma nova tarefa do MongoDB para o processo `#200001` com o signatário **Edilson** vinculado ao arquivo `765 - CCB.pdf`.
2. A automação executa o fluxo e realiza o `POST /v2/envelope/create` e `POST /files/envelope/:envelopeId/files`.

### 1.2. Resultado Esperado
- Registro criado na tabela `jornadas_solicitacoes` com status `RECEBIDO` ou `EM_PROCESSAMENTO`.
- Registro criado na tabela `envelopes` com `versao_envelope = 1` e `status_envelope = 'ASSINATURA_PENDENTE'`.
- Os registros de `documentos` e `envelope_signatarios` são vinculados ao `id` do envelope.

### 1.3. Queries SQL de Auditoria

```sql
-- 1. Auditoria do Envelope Criado e seus Metadados
SELECT 
    e.id AS id_envelope_db,
    e.id_envelope_externo AS id_openapi,
    e.versao_envelope,
    e.status_envelope,
    e.provider,
    e.hash_escopo_documentos,
    e.created_at AS data_criacao
FROM envelopes e
JOIN jornadas_solicitacoes j ON j.id = e.id_solicitacao
WHERE j.num_processo = 200001 AND e.status_envelope = 'ASSINATURA_PENDENTE';

-- 2. Auditoria dos Documentos e Signatários Vinculados ao Envelope
SELECT 
    e.id_envelope_externo,
    a.nome AS signatario,
    a.cpf_cnpj,
    es.papel_assinante,
    es.canal_validacao,
    es.status_assinatura,
    d.nome_arquivo,
    d.tipo_doc_id
FROM envelopes e
JOIN envelope_signatarios es ON es.id_envelope = e.id
JOIN associados a ON a.id = es.id_associado
JOIN documentos d ON d.id_envelope = e.id
WHERE e.id_envelope_externo = 'mock_envelope_f304cbd1'; -- Substituir pelo ID externo gerado
```

---

## 🔄 CENÁRIO 2: Versionamento e Troca de Versão do Documento

### 2.1. Passo a Passo da Ação
1. O operador envia uma **nova versão** do documento `765 - CCB V2 Nova.pdf` para o mesmo processo `#200001`.
2. A automação detecta a alteração de escopo/versão e executa o fluxo de substituição seletiva.

### 2.2. Resultado Esperado
- O envelope versão 1 (`versao_envelope = 1`) tem o status atualizado no banco para **`REEMPLACADO_CANCELADO`**.
- Um **novo envelope** é gerado com **`versao_envelope = 2`** (ou incremental) e status **`ASSINATURA_PENDENTE`**.
- O envelope v1 é cancelado no portal externo via `DELETE /v2/envelope/{id}`.

### 2.3. Queries SQL de Auditoria

```sql
-- Auditoria de Substituição de Versão por Histórico Incremental
SELECT 
    e.versao_envelope,
    e.id_envelope_externo,
    e.status_envelope,
    e.hash_escopo_documentos,
    e.updated_at AS data_alteracao
FROM envelopes e
JOIN jornadas_solicitacoes j ON j.id = e.id_solicitacao
WHERE j.num_processo = 200001
ORDER BY e.versao_envelope ASC;
```
> **Resultado Esperado da Query:**
> - Linha 1: `versao_envelope = 1` | `status_envelope = 'REEMPLACADO_CANCELADO'`
> - Linha 2: `versao_envelope = 2` | `status_envelope = 'ASSINATURA_PENDENTE'`

---

## 👥 CENÁRIO 3: Alteração / Inclusão de Novos Signatários

### 3.1. Passo a Passo da Ação
1. A tarefa é reenviada adicionando um novo signatário (**Aila Franca - Cônjuge Avalista**) ao mesmo processo `#200001`.
2. A automação detecta que a lista de signatários do cluster mudou.

### 3.2. Resultado Esperado
- O envelope versão 2 é descontinuado e atualizado para **`REEMPLACADO_CANCELADO`**.
- Um novo envelope **versão 3** é criado vinculando **ambos os signatários** (Edilson + Aila).

### 3.3. Queries SQL de Auditoria

```sql
-- Auditoria de Signatários Vinculados à Versão Atual do Envelope
SELECT 
    e.versao_envelope,
    e.status_envelope,
    a.nome AS signatario,
    es.papel_assinante,
    es.canal_validacao
FROM envelopes e
JOIN envelope_signatarios es ON es.id_envelope = e.id
JOIN associados a ON a.id = es.id_associado
JOIN jornadas_solicitacoes j ON j.id = e.id_solicitacao
WHERE j.num_processo = 200001 AND e.status_envelope = 'ASSINATURA_PENDENTE'
ORDER BY es.ordem_assinatura ASC;
```
> **Resultado Esperado da Query:** Retorna 2 linhas com Edilson (Titular) e Aila (Cônjuge Avalista) vinculados à versão ativa.

---

## 🚫 CENÁRIO 4: Cancelamento Explícito de Envelope

### 4.1. Passo a Passo da Ação
1. O usuário ou processo origem solicita o cancelamento manual da solicitação ou o robô descobre um cancelamento explícito.
2. A automação aciona a rota `DELETE /v2/envelope/{id}` e atualiza o banco local.

### 4.2. Resultado Esperado
- O status do envelope na tabela `envelopes` muda para **`CANCELADO`**.
- É gravado um log na tabela `historico_manutencao` registrando o motivo e quem executou o cancelamento.

### 4.3. Queries SQL de Auditoria

```sql
-- 1. Verifica o Status do Envelope Cancelado
SELECT id, id_envelope_externo, status_envelope, updated_at 
FROM envelopes 
WHERE id = 'uuid-do-envelope-cancelado';

-- 2. Auditando o Log na Tabela historico_manutencao
SELECT 
    hm.motivo_codigo,
    hm.descricao_detalhada,
    hm.resolvido,
    hm.resolvido_por,
    hm.created_at
FROM historico_manutencao hm
WHERE hm.id_envelope = 'uuid-do-envelope-cancelado';
```

---

## ⏰ CENÁRIO 5: Simulação e Teste Prático da Rotina de Expiração (> 60 Dias ou Vencimento)

### 5.1. Procedimento Prático de Teste
Para testar a rotina de expiração sem precisar aguardar 60 dias reais, forçamos a data de expiração de um envelope de teste para vencer em **2 minutos a partir de agora**.

### 5.2. Script SQL de Preparação do Teste (Forçar Vencimento)

```sql
-- 1. Cria ou identifica um envelope ativo de teste
-- 2. Atualiza a data de expiração para daqui a 2 minutos
UPDATE envelopes 
SET data_expiracao = CURRENT_TIMESTAMP + INTERVAL '2 minutes',
    status_envelope = 'ASSINATURA_PENDENTE'
WHERE id_envelope_externo = 'openapi_env_teste_expiracao';
```

### 5.3. Consulta PRÉ-Execução (Verificar Elegibilidade)

```sql
-- Consulta ANTES da rotina rodar (Envelope deve aparecer como PENDENTE e Elegível quando passar o tempo)
SELECT id, id_envelope_externo, status_envelope, data_expiracao, CURRENT_TIMESTAMP AS hora_atual
FROM envelopes
WHERE status_envelope = 'ASSINATURA_PENDENTE'
  AND data_expiracao <= CURRENT_TIMESTAMP + INTERVAL '2 minutes';
```

### 5.4. Execução da Rotina de Expiração

No terminal, execute o worker de expiração:

```powershell
.\.venv\Scripts\python.exe -c "
from microservico.infrastructure.db import DatabaseManager
from microservico.infrastructure.repositories import EnvelopeRepository, HistoricoManutencaoRepository
from microservico.domain.enums import StatusEnvelope, MotivoManutencaoEnum
import os

db_mgr = DatabaseManager(dsn=f'host={os.getenv(\"DB_HOST\",\"localhost\")} port=5432 dbname=docjourney_db user=postgres password=senha123', use_sqlite=False)
env_repo = EnvelopeRepository(db_mgr)
manut_repo = HistoricoManutencaoRepository(db_mgr)

expirados = env_repo.list_expired_over_60_days()
for env in expirados:
    env_repo.update_external_id(env.id, env.id_envelope_externo, StatusEnvelope.EXPIRADO)
    manut_repo.log_manutencao(env.id_solicitacao, MotivoManutencaoEnum.EXPIRADO_60_DIAS, f'Envelope {env.id_envelope_externo} expirado.', env.id)
print('✅ Rotina de Expiração executada!')
"
```

### 5.5. Consulta PÓS-Execução (Comprovar Alteração de Estado)

```sql
-- 1. Comprova que o status do envelope mudou para 'EXPIRADO'
SELECT id, id_envelope_externo, status_envelope, updated_at
FROM envelopes
WHERE id_envelope_externo = 'openapi_env_teste_expiracao';

-- 2. Comprova a gravação do registro de auditoria na tabela historico_manutencao
SELECT 
    hm.motivo_codigo,
    hm.descricao_detalhada,
    hm.resolvido,
    hm.created_at
FROM historico_manutencao hm
JOIN envelopes e ON e.id = hm.id_envelope
WHERE e.id_envelope_externo = 'openapi_env_teste_expiracao';
```
> **Resultado Esperado:** `status_envelope = 'EXPIRADO'` e registro na `historico_manutencao` com `motivo_codigo = 'EXPIRADO_60_DIAS'`.

---

## ⚠️ CENÁRIO 6: Pré-Validação Agregada ("Tudo de uma Vez")

### 6.1. Passo a Passo da Ação
1. A automação recebe um payload com CPF inválido, e-mail inválido e anexo faltante.
2. A `TaskPayloadValidator` varre todos os itens sem interromper no primeiro erro (No-Fail-Fast).

### 6.2. Resultado Esperado
- A automação lança a `BulkValidationError` contendo a lista com todas as pendências agregadas.
- O resultado retornado traz o campo `parecer_fluid` em HTML estruturado com a lista de erros em vermelho.

---

## 🚀 Execução Automatizada dos 6 Cenários

Você também pode rodar a suíte interativa completa que simula todos esses 6 cenários sequencialmente contra o PostgreSQL:

```powershell
.\.venv\Scripts\python.exe automacao/tests/test_interactive_scenarios.py
```
