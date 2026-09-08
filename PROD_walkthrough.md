# Registro Técnico de Entregas e Auditoria de Produção (PROD_walkthrough.md)

**Módulos:** Microsserviço Backend (`microservico/`) & Automação RPA (`automacao/`)  
**Data:** 2026-09-07  
**Status:** 100% Homologado e Pronto para Produção

---

## 1. Escopo das Implementações e Entregas

### A. Microsserviço Backend (`microservico/`)
1. **Modelos de Domínio e Enums 100% em Inglês:**
   - `AssociateModel`, `ProcessModel`, `JourneyRequestModel`, `EnvelopeModel`, `DocumentModel`, `EnvelopeSignerModel`, `MaintenanceHistoryModel`.
   - `JourneyStatus`, `EnvelopeStatus`, `SignerStatus`, `DocumentStatus`, `ProviderType`, `SignatureType`, `ValidationChannel`, `MaintenanceReason`.
   - Docstrings completas em português com `Parâmetros`, `Retorno` e `Exceções`.
2. **Repositórios Relacionais Padronizados:**
   - Implementação de `AssociateRepository`, `ProcessRepository`, `JourneyRepository`, `EnvelopeRepository`, `MaintenanceHistoryRepository`, `DocumentRepository`, `EnvelopeSignerRepository`.
   - Consultas SQL direcionadas às tabelas em inglês do PostgreSQL com fallback automático para SQLite em memória nos testes rápidos.
3. **Gerenciador de Banco e Carga Inicial:**
   - `DatabaseManager`: Suporte nativo a `psycopg` (PostgreSQL) e `sqlite3` com conversão de sintaxes DDL.
   - `initialize_database_if_empty`: Executa o `PROD_schema.sql` e insere os processos de catálogo (Seed Data).
4. **Notificação Externa e Mensageria RabbitMQ:**
   - `ExternalStatusNotifierClient`: Disparo de webhooks de atualização de status com fallback resiliente.
   - `RabbitMQClient`: Publicador e consumidor de eventos com fallback para Mock Queue e suporte à visualização via RabbitMQ Management UI (`http://localhost:15672`).

---

### B. Automação RPA (`automacao/`)
1. **Engine de Pré-Validação Antecipada ('Tudo de uma Vez'):**
   - `TaskPayloadValidator`: Valida simultaneamente CPFs (com dígitos verificadores), canais de comunicação (E-mail e WhatsApp) e correspondência de documentos vinculados. Acumula todas as falhas em uma única exceção `BulkValidationError`, gerando parecer HTML padronizado para o Fluid.
2. **Motor de Clusterização por Escopo Documental:**
   - `DocumentScopeClusterizer`: Agrupa signatários pela interseção exata dos documentos que lhes cabe assinar. Gera hash SHA256 determinístico para garantir a integridade exigida pela OpenAPI.
3. **Gestão do Ciclo de Vida e Substituição Seletiva:**
   - `EnvelopeLifecycleManager`: Detecta alterações de escopo documental ou assinantes, cancela envelopes obsoletos (`REPLACED_CANCELED`), cria nova versão incremental e efetua upload multipart dos binários via `POST /files/envelope/:id/files`.
4. **Controlador Orquestrador e Ponto de Entrada:**
   - `OrchestratorController` e `main.py`: Parseamento do payload do MongoDB, orquestração e execução com captura unificada de erros. Correção de bugs de imports faltantes (`json` e `os`).

---

## 2. Validação e Resultados dos Testes Automatizados

| Teste | Comando | Resultado |
| :--- | :--- | :--- |
| **Unitários do Microsserviço** | `.\.venv\Scripts\python.exe microservico/tests/run_tests.py` | ✅ 6/6 testes aprovados (OK) |
| **Unitários da Automação** | `.\.venv\Scripts\python.exe automacao/tests/run_tests.py` | ✅ 4/4 testes aprovados (OK) |
| **Mensageria RabbitMQ** | `.\.venv\Scripts\python.exe microservico/tests/test_rabbitmq.py` | ✅ Publicação, consumo e status validados |
| **Integração PostgreSQL Real** | `.\.venv\Scripts\python.exe microservico/tests/test_postgres_e2e.py` | ✅ Conexão, persistência e integridade validadas |
| **Cenários Interativos (6 fluxos)** | `.\.venv\Scripts\python.exe automacao/tests/test_interactive_scenarios.py` | ✅ 6 cenários validados contra PostgreSQL |
| **Carga de Dados Fictícios** | `.\.venv\Scripts\python.exe PROD_populate_sample_data.py` | ✅ 7 tabelas populadas com dados realistas |

---

## 3. Preservação de Arquivos Raiz
- Nenhum arquivo legado ou descontinuado foi excluído:
  - `bot_adesao_eletronica/`, `envio_assinaturas/`, `documentações/`, `imgs_referencia/`, `diretriz.md`, `levantamento_api.md`, `modelo_conceitual.md`, `rotas e repostas.md`, `tipo de body mongo.md`, `visao geral.md`.
- Todos os arquivos oficiais de produção receberam o prefixo `PROD_`:
  - `PROD_schema.sql`, `PROD_roteiro_de_testes_qa.md`, `PROD_guia_relacionamento_banco.md`, `PROD_populate_sample_data.py`, `PROD_walkthrough.md`.
