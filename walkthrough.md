# Guia Passo a Passo: Como Testar Todo o Orquestrador

Este guia fornece o passo a passo completo sobre como testar tanto no modo **Rápido (sem instalar nada)** quanto no modo **PostgreSQL Real**.

---

## 💻 1. O que ter instalado na máquina

### Requisitos Obrigatórios:
1. **Python 3.10 ou superior**:
   - Verifique com: `python --version`

### Requisitos para Teste com PostgreSQL Real:
1. **PostgreSQL 14+** (Instalado localmente ou via Docker).
2. **Pacote `psycopg` instalado no Python**:
   ```bash
   pip install "psycopg[binary]" pydantic httpx python-dotenv
   ```

---

## ⚙️ 2. Configuração do PostgreSQL Real

Se você já tem o PostgreSQL rodando na sua máquina:

1. **Crie um Banco de Dados**:
   - Nome sugerido: `docjourney_db`

2. **Configure as Variáveis de Ambiente**:
   No terminal (ou em um arquivo `.env` na raiz do repositório):

   **PowerShell (Windows)**:
   ```powershell
   $env:DB_HOST="localhost"
   $env:DB_PORT="5432"
   $env:DB_NAME="docjourney_db"
   $env:DB_USER="postgres"
   $env:DB_PASSWORD="sua_senha_aqui"
   ```

   **Bash (Linux/Mac)**:
   ```bash
   export DB_HOST="localhost"
   export DB_PORT="5432"
   export DB_NAME="docjourney_db"
   export DB_USER="postgres"
   export DB_PASSWORD="sua_senha_aqui"
   ```

---

## 🧪 3. Executando os Testes (2 Opções)

### 🟢 **Opção A: Teste Rápido em Memória (Sem precisar do Postgres rodando)**
Você pode testar **100% da lógica** (schema, repositórios, clusterização, pré-validação "tudo de uma vez" e ciclo de vida) usando o banco isolado em memória nativo do Python:

```powershell
# 1. Teste das tabelas, repositórios e notificador (Fase 1)
python microservico/tests/run_tests.py

# 2. Teste da pré-validação, clusterização e orquestrador RPA (Fase 2)
python automacao/tests/run_tests.py
```

---

### 🟢 **Opção B: Teste E2E no seu PostgreSQL Real**
Com o PostgreSQL rodando e as variáveis de ambiente configuradas, execute o script de teste E2E:

```powershell
python microservico/tests/test_postgres_e2e.py
```

#### O que este script faz automaticamente:
1. Conecta no seu PostgreSQL real (`localhost:5432/docjourney_db`).
2. Executa o [schema.sql](file:///c:/Users/lopes/OneDrive/Área%20de%20Trabalho/Programação/Sicredi/docjourney/schema.sql) criando todas as 8 tabelas e índices (`CREATE TABLE IF NOT EXISTS`).
3. Insere os processos de seed iniciais caso a tabela esteja vazia.
4. Processa uma tarefa válida do MongoDB através do fluxo completo da automação RPA.
5. Grava e valida os registros de `associados`, `jornadas_solicitacoes` e `envelopes` no seu PostgreSQL.

---

## 🔍 4. Como Validar o Resultado no PostgreSQL

Após rodar o script `test_postgres_e2e.py`, você pode abrir seu cliente PostgreSQL preferido (pgAdmin, DBeaver, VS Code PostgreSQL) e consultar os dados inseridos:

```sql
-- Consultar o associado criado
SELECT * FROM associados;

-- Consultar a jornada cadastrada
SELECT id, mongo_id, num_processo, status, created_at FROM jornadas_solicitacoes;

-- Consultar os envelopes criados por escopo documental
SELECT id, id_solicitacao, hash_escopo_documentos, versao_envelope, provider, status_envelope FROM envelopes;

-- Consultar os processos de seed
SELECT * FROM processos;
```
