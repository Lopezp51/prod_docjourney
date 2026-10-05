# 🏛️ Guia Definitivo de Configuração e Operação — Microsserviço DocJourney

> **Ambiente Corporativo:** Sicredi — Esteira de Assinatura Digital  
> **Tecnologias:** Python 3.10+, FastAPI, PostgreSQL, RabbitMQ, Loguru, Pydantic v2  
> **Versão:** 2.0.0

---

## 📋 Sumário
1. [Visão Geral e Arquitetura](#1-visão-geral-e-arquitetura)
2. [Requisitos do Sistema & Pré-Requisitos](#2-requisitos-do-sistema--pré-requisitos)
3. [Passo a Passo de Instalação no Windows/Linux](#3-passo-a-passo-de-instalação-no-windowslinux)
4. [Configuração de Variáveis de Ambiente (.env)](#4-configuração-de-variáveis-de-ambiente-env)
5. [Configuração do Banco de Dados (PostgreSQL / SQLite)](#5-configuração-do-banco-de-dados-postgresql--sqlite)
6. [Configuração da Mensageria RabbitMQ](#6-configuração-da-mensageria-rabbitmq)
7. [Sistema de Logs Detalhados com Loguru](#7-sistema-de-logs-detalhados-com-loguru)
8. [Como Executar o Microsserviço](#8-como-executar-o-microsserviço)
9. [Catálogo de Endpoints REST & Documentação Interativa](#9-catálogo-de-endpoints-rest--documentação-interativa)
10. [Execução de Testes Automatizados](#10-execução-de-testes-automatizados)
11. [Troubleshooting & Resolução de Problemas Corporativos](#11-troubleshooting--resolução-de-problemas-corporativos)

---

## 1. Visão Geral e Arquitetura

O **Microsserviço DocJourney** é o componente central de governança, persistência e auditoria de jornadas documentais da esteira de assinaturas eletrônicas.

### Papéis Fundamentais:
- **Única Fonte da Verdade:** Toda persistência de jornadas, associados, envelopes e signatários passa pelo microsserviço. O robô RPA e outros sistemas nunca realizam queries SQL diretas no banco relacional.
- **Idempotência por `mongo_id`:** Garante que reprocessamentos de tarefas do Fluid não dupliquem registros de jornada.
- **Auditoria Imutável (`maintenance_history`):** Registra toda ocorrência de governança (cancelamentos, expirações, substituições seletivas e intervenções).
- **Consumo Assíncrono via RabbitMQ:** Atualiza o ciclo de vida dos envelopes em background através de eventos AMQP consumidos pelo Worker.

```
                      ┌───────────────────────────────┐
                      │   Automação RPA (Windows)     │
                      │  (Ingestão, OCR, OpenAPI v2)  │
                      └──────────────┬────────────────┘
                                     │ Chamadas HTTP REST
                                     ▼
         ┌─────────────────────────────────────────────────────────┐
         │          Microsserviço DocJourney (FastAPI)             │
         │                                                         │
         │  /api/v1/journeys      /api/v1/envelopes                │
         │  /api/v1/maintenance   /health                          │
         │  Middleware de Auditoria & Logging (Loguru)             │
         └─────────────┬───────────────────────────┬───────────────┘
                       │                           │
          Consultas /  │               Publicação/ │ Eventos
          Persistência │               Consumo     │ AMQP
                       ▼                           ▼
            ┌────────────────────┐      ┌────────────────────┐
            │   PostgreSQL DB    │      │  RabbitMQ Broker   │
            │ (Schema Relacional)│      │  (docjourney_queue)│
            │  Fallback: SQLite  │      │  Fallback: Mock    │
            └────────────────────┘      └──────────┬─────────┘
                                                   │
                                                   ▼
                                        ┌────────────────────┐
                                        │  Background Worker │
                                        │ (worker.py Daemon) │
                                        └────────────────────┘
```

---

## 2. Requisitos do Sistema & Pré-Requisitos

Antes de iniciar a configuração na sua máquina ou servidor corporativo, certifique-se de dispor dos seguintes pré-requisitos:

| Componente | Versão Mínima | Finalidade |
| :--- | :--- | :--- |
| **Sistema Operacional** | Windows 10/11, Windows Server ou Linux | Ambiente de execução |
| **Python** | 3.10 ou superior (Recomendado: 3.11 / 3.12) | Interpretador da aplicação |
| **PostgreSQL** | 14+ (ou usar SQLite embutido) | Banco relacional corporativo |
| **RabbitMQ** | 3.10+ (ou Docker ou modo Mock em memória) | Broker de eventos AMQP |
| **Git** | 2.30+ | Controle de versão |
| **PowerShell** | 5.1 ou PowerShell 7 | Terminal de linha de comando no Windows |

### Como Verificar o Python na sua Máquina:
Abra o PowerShell ou terminal e execute:
```powershell
python --version
# Deve exibir: Python 3.10.x ou superior

pip --version
# Confirma o instalador de pacotes
```

---

## 3. Passo a Passo de Instalação no Windows/Linux

Siga rigorosamente os passos abaixo para configurar o ambiente de trabalho:

### Passo 1: Abrir o Terminal na Pasta do Projeto
No Windows (PowerShell):
```powershell
cd "c:\Users\<seu_usuario>\...\prod_docjourney"
```

### Passo 2: Liberar Política de Scripts no PowerShell (se necessário)
Se ao tentar rodar scripts você receber a mensagem *"running scripts is disabled on this system"*, execute no PowerShell:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

### Passo 3: Criar o Ambiente Virtual (`.venv`)
É fundamental isolar as dependências do projeto para evitar conflito com bibliotecas do sistema:
```powershell
# Criação do ambiente virtual na raiz do projeto
python -m venv .venv
```

### Passo 4: Ativar o Ambiente Virtual
- **No Windows (PowerShell):**
  ```powershell
  .\.venv\Scripts\Activate.ps1
  ```
  *(Seu prompt passará a exibir `(.venv)` no início da linha).*

- **No Windows (CMD clássico):**
  ```cmd
  .\.venv\Scripts\activate.bat
  ```

- **No Linux / macOS:**
  ```bash
  source .venv/bin/activate
  ```

### Passo 5: Atualizar o Gerenciador Pip
```powershell
python -m pip install --upgrade pip
```

### Passo 6: Instalar as Dependências do Microsserviço
Execute a instalação do arquivo de dependências:
```powershell
pip install -r microservico/requirements.txt
```

> [!TIP]
> **Aviso para Ambiente com Proxy Corporativo / SSL Sicredi:**
> Se o download dos pacotes falhar por bloqueio de certificado ou firewall corporativo, use:
> ```powershell
> pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org -r microservico/requirements.txt
> ```

---

## 4. Configuração de Variáveis de Ambiente (.env)

Crie um arquivo chamado `.env` dentro da pasta `microservico/` (ou na raiz do projeto). O microsserviço carrega automaticamente as variáveis definidas neste arquivo.

### Catálogo de Parâmetros de Configuração:

| Variável | Padrão | Descrição |
| :--- | :--- | :--- |
| `API_HOST` | `0.0.0.0` | Endereço IP onde o FastAPI receberá conexões (`0.0.0.0` aceita chamadas da rede). |
| `API_PORT` | `8000` | Porta TCP do serviço HTTP. |
| `ENVIRONMENT` | `production` | Ambiente ativo (`development`, `staging`, `production`). |
| `DB_HOST` | `localhost` | Host do banco PostgreSQL. |
| `DB_PORT` | `5432` | Porta do PostgreSQL. |
| `DB_NAME` | `docjourney_db` | Nome da base de dados relacional. |
| `DB_USER` | `postgres` | Usuário autenticado no banco. |
| `DB_PASSWORD` | `senha123` | Senha do usuário do banco. |
| `RABBITMQ_HOST` | `localhost` | Endereço do broker RabbitMQ. |
| `RABBITMQ_PORT` | `5672` | Porta AMQP do broker RabbitMQ. |
| `RABBITMQ_USER` | `guest` | Usuário de autenticação no RabbitMQ. |
| `RABBITMQ_PASSWORD` | `guest` | Senha de autenticação no RabbitMQ. |
| `ENABLE_EMBEDDED_WORKER` | `true` | Se `true`, roda o consumidor RabbitMQ em background thread no mesmo processo da API. |
| `LOG_LEVEL` | `INFO` | Nível de detalhamento do Loguru (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |
| `LOG_DIR` | `logs` | Pasta onde os arquivos de log rotativos são gravados. |

---

### Perfil 1: Configuração Rápida para Desenvolvimento Local (Zero Instalações Extras)
Se você **não** tem PostgreSQL nem RabbitMQ instalados na máquina e deseja testar imediatamente, use este `.env`:
```env
# microservico/.env (Modo Standalone / SQLite / Mock RabbitMQ)
API_HOST=0.0.0.0
API_PORT=8000
ENVIRONMENT=development

# Banco de dados: Deixando dados locais ou offline, o sistema ativa SQLite automaticamente
DB_HOST=localhost
DB_PORT=5432
DB_NAME=docjourney_db
DB_USER=postgres
DB_PASSWORD=senha_local

# RabbitMQ: Se offline, o cliente chaveia automaticamente para Mock Queue em memória
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest
ENABLE_EMBEDDED_WORKER=true

# Logs detalhados com Loguru
LOG_LEVEL=DEBUG
LOG_DIR=logs
```

---

### Perfil 2: Configuração de Homologação / Produção Corporativa (PostgreSQL + RabbitMQ Real)
```env
# microservico/.env (Produção / Homologação Sicredi)
API_HOST=0.0.0.0
API_PORT=8000
ENVIRONMENT=production

# PostgreSQL Real
DB_HOST=10.x.x.x  # Ou nome do servidor de banco da cooperativa
DB_PORT=5432
DB_NAME=docjourney_db
DB_USER=usr_docjourney
DB_PASSWORD=SuaSenhaForteSegura_2026!

# RabbitMQ Corporativo
RABBITMQ_HOST=10.x.x.y  # Ou host do cluster RabbitMQ
RABBITMQ_PORT=5672
RABBITMQ_USER=app_docjourney
RABBITMQ_PASSWORD=SenhaRabbit_Sicredi_2026!
ENABLE_EMBEDDED_WORKER=true

# Observabilidade e Logs
LOG_LEVEL=INFO
LOG_DIR=logs
```

---

## 5. Configuração do Banco de Dados (PostgreSQL / SQLite)

### Opção A: PostgreSQL Real (Produção / Homologação)

1. **Criar o Banco e Usuário no PostgreSQL:**
   Abra o `psql` ou pgAdmin como usuário `postgres`:
   ```sql
   -- 1. Criação do banco
   CREATE DATABASE docjourney_db WITH ENCODING 'UTF8';

   -- 2. Criação do usuário corporativo
   CREATE USER usr_docjourney WITH ENCRYPTED PASSWORD 'SuaSenhaForteSegura_2026!';

   -- 3. Concessão de privilégios
   GRANT ALL PRIVILEGES ON DATABASE docjourney_db TO usr_docjourney;
   \c docjourney_db
   GRANT ALL ON SCHEMA public TO usr_docjourney;
   ```

2. **Criação Automática das Tabelas (Idempotente):**
   O microsserviço aplica o schema e os índices automaticamente na inicialização (`lifespan`). Caso prefira executar o script DDL manualmente:
   ```powershell
   psql -h localhost -U usr_docjourney -d docjourney_db -f schema.sql
   ```

3. **Tabelas Geradas:**
   - `processes`: Catálogo dos tipos de processo do Fluid.
   - `journeys`: Registro mestre da jornada de cada solicitação (`mongo_id`).
   - `associates`: Dados cadastrais do associado/cooperado.
   - `envelopes`: Registro dos envelopes, identificador externo OpenAPI, escopo e versão.
   - `envelope_documents`: Metadados e tipos documentais anexados a cada envelope.
   - `envelope_signers`: Signatários com papéis, canais e métodos de assinatura.
   - `maintenance_history`: Auditoria imutável de cancelamentos, substituições e expirações.

### Opção B: Fallback Automático em SQLite (Zero Configuração)
Se o driver `psycopg` não conseguir alcançar o host PostgreSQL definido no `.env`, o `DatabaseManager` ativa **automaticamente** um banco SQLite em memória/local para que os testes e validações rodem perfeitamente sem falhas.

---

## 6. Configuração e Instalação da Mensageria RabbitMQ

O **RabbitMQ** é o broker de mensageria assíncrona utilizado pelo microsserviço para receber notificações de eventos, mudanças de status e auditoria sem onerar a API HTTP principal.

> **Portas de Rede Utilizadas:**
> - `5672`: Porta de comunicação de dados da aplicação (protocolo AMQP utilizado pelo FastAPI e Worker).
> - `15672`: Porta da interface gráfica no navegador (RabbitMQ Management Dashboard).

---

### A. Opções de Instalação no Windows

Escolha a opção que melhor se adapta às permissões e ferramentas da sua máquina de trabalho:

#### Opção 1: Via Docker Desktop (Mais Rápido e Sem Instalar Serviços Locais)
Se você já possui o Docker instalado na sua máquina:
```powershell
docker run -d --name rabbitmq `
  --restart always `
  -p 5672:5672 `
  -p 15672:15672 `
  rabbitmq:3-management
```
*(O container já inicia com o RabbitMQ e o painel web ativos).*

---

#### Opção 2: Via Winget (Nativo no PowerShell Administrador)
Abra o **PowerShell como Administrador** e execute:
```powershell
# 1. Instalar a dependência obrigatória (Erlang/OTP)
winget install Erlang.Erlang --accept-package-agreements --accept-source-agreements

# 2. Instalar o RabbitMQ Server
winget install Pivotal.RabbitMQ --accept-package-agreements --accept-source-agreements

# 3. Feche e reabra o PowerShell como Administrador e ative o painel web:
& "$env:ProgramFiles\RabbitMQ Server\rabbitmq_server-*\sbin\rabbitmq-plugins.bat" enable rabbitmq_management

# 4. Reiniciar o serviço do Windows
Restart-Service -Name "RabbitMQ"
```

---

#### Opção 3: Via Chocolatey (se você utiliza o Choco no trabalho)
Abra o PowerShell como Administrador:
```powershell
choco install rabbitmq -y
```
*(O Chocolatey baixa, configura o Erlang/OTP e registra o serviço do RabbitMQ automaticamente no Windows).*

---

#### Opção 4: Via Instaladores Oficiais (.exe - Sem Gerenciador de Pacotes)
Caso sua empresa não permita Winget/Chocolatey nem Docker:
1. **Passo 1 (Obrigatório - Instalar Erlang):**
   - Acesse: [https://www.erlang.org/patches/otp-26.2.5.3](https://www.erlang.org/patches/otp-26.2.5.3) (ou versão compatível para Windows x64).
   - Baixe e execute o instalador `otp_win64_*.exe` avançando com as opções padrão.
2. **Passo 2 (Instalar o RabbitMQ Server):**
   - Acesse: [https://github.com/rabbitmq/rabbitmq-server/releases/latest](https://github.com/rabbitmq/rabbitmq-server/releases/latest).
   - Baixe o instalador `rabbitmq-server-*-windows.exe`.
   - Execute o instalador. Ele registra e inicia automaticamente o serviço no `services.msc` do Windows.
3. **Passo 3 (Ativar o Painel Gráfico Web):**
   - No Menu Iniciar do Windows, pesquise por **"RabbitMQ Command Prompt (sbin dir)"** e abra como **Administrador**.
   - Digite o comando:
     ```cmd
     rabbitmq-plugins enable rabbitmq_management
     ```
   - Reinicie o serviço no PowerShell:
     ```powershell
     Restart-Service RabbitMQ
     ```

---

### B. Opções de Instalação no Linux (Servidores de Homologação/Produção)

#### 1. Ubuntu / Debian:
```bash
sudo apt-get update
sudo apt-get install -y rabbitmq-server
sudo systemctl enable --now rabbitmq-server
sudo rabbitmq-plugins enable rabbitmq_management
```

#### 2. Red Hat / Rocky Linux / AlmaLinux / CentOS:
```bash
sudo dnf install -y epel-release
sudo dnf install -y rabbitmq-server
sudo systemctl enable --now rabbitmq-server
sudo rabbitmq-plugins enable rabbitmq_management
```

---

### C. Acesso ao Painel Web e Criação de Usuário Corporativo

1. **Acesso ao Painel Web Local:**
   - URL: [http://localhost:15672](http://localhost:15672)
   - Usuário Padrão: `guest`
   - Senha Padrão: `guest`
   - Na aba **Queues**, a fila `docjourney_status_queue` será criada automaticamente pelo microsserviço assim que ele iniciar.

2. **Criar Usuário Administrador Corporativo (Recomendado para Redes de Trabalho):**
   *Por padrão, o usuário `guest` só consegue acessar via `localhost`. Para permitir acesso a partir de outras máquinas da rede corporativa:*
   - No PowerShell como Administrador ou terminal Linux:
     ```powershell
     # Criar usuário
     rabbitmqctl add_user admin_sicredi "SuaSenhaSegura123!"

     # Conceder permissão de Administrador
     rabbitmqctl set_user_tags admin_sicredi administrator

     # Liberar permissões totais no vhost raiz
     rabbitmqctl set_permissions -p / admin_sicredi ".*" ".*" ".*"
     ```

---

### D. Comandos Úteis de Diagnóstico e Gerenciamento

| Ação | Comando no Windows (PowerShell Admin) |
| :--- | :--- |
| **Testar Conectividade** | `rabbitmq-diagnostics ping` |
| **Listar Filas e Mensagens** | `rabbitmqctl list_queues name messages` |
| **Status do Serviço** | `Get-Service -Name "RabbitMQ"` |
| **Reiniciar Serviço** | `Restart-Service -Name "RabbitMQ"` |
| **Parar Serviço** | `Stop-Service -Name "RabbitMQ"` |

---

### E. Modo Fallback em Memória (Se você não puder instalar o RabbitMQ)

> [!NOTE]
> **Zero Bloqueio para Testes e Desenvolvimento:**
> Se a sua máquina de trabalho tiver restrições que impeçam a instalação do RabbitMQ ou se o serviço estiver desligado, **a aplicação NÃO falha nem trava**.  
> O componente `RabbitMQClient` do microsserviço detecta a ausência do broker e ativa automaticamente o modo **Mock Queue em memória**, registrando logs de aviso através do Loguru e permitindo que todas as APIs e testes funcionem normalmente!


---

## 7. Sistema de Logs Detalhados com Loguru

O microsserviço utiliza a biblioteca **Loguru** para observabilidade de alta performance e diagnósticos ricos:

### Estrutura de Diretórios de Logs:
```
prod_docjourney/
└── logs/
    ├── microservico_2026-10-05.log   <-- Log completo do dia (Console + Aplicação)
    └── microservico_errors.log       <-- Log exclusivo para erros de severidade ERROR/CRITICAL
```

### Funcionalidades do Loguru Implementadas:
1. **Console Colorido e Formatado:**
   Exibe data, hora com milissegundos, nível, identificador do serviço, nome do módulo, função, linha e mensagem:
   ```
   2026-10-05 07:10:22.912 | INFO     | DocJourneyMicroservice | microservico.main:log_requests:88 - HTTP POST /api/v1/journeys | Status: 201 | Tempo: 4.15ms
   ```
2. **Rotação Diária & Limite de Tamanho:**
   Os arquivos rotacionam automaticamente ao atingir **20 MB** ou à meia-noite, sendo compactados em formato `.zip`.
3. **Retenção Automática:**
   Logs normais são mantidos por 14 dias; logs de erro são mantidos por 30 dias.
4. **Interceptação Global da Biblioteca Padrão (`logging`):**
   Logs do Uvicorn, FastAPI, Pika e drivers de banco são interceptados pelo `InterceptHandler` e unificados no formato do Loguru.
5. **Diagnóstico Completo de Exceções (`diagnose=True`, `backtrace=True`):**
   Em caso de falha, o Loguru imprime todo o traceback com os valores de cada variável local no momento do erro.

---

## 8. Como Executar o Microsserviço

### Modo 1: Unificado em 1 Único Terminal (Recomendado para Desenvolvimento)
Com `ENABLE_EMBEDDED_WORKER=true`, a API FastAPI e o consumidor RabbitMQ iniciam juntos em um único comando:

```powershell
# Certifique-se de estar com a venv ativada
.\.venv\Scripts\Activate.ps1

# Iniciar servidor Uvicorn com hot-reload
python -m uvicorn microservico.main:app --host 0.0.0.0 --port 8000 --reload
```

### Modo 2: Processos Separados (Terminais Independentes)
Útil caso deseje monitorar o log de mensageria isolado do tráfego HTTP:
1. No seu `.env`, defina: `ENABLE_EMBEDDED_WORKER=false`
2. **Terminal 1 (API HTTP):**
   ```powershell
   python -m uvicorn microservico.main:app --host 0.0.0.0 --port 8000 --reload
   ```
3. **Terminal 2 (Worker RabbitMQ):**
   ```powershell
   python microservico/worker.py
   ```

### Modo 3: Produção como Serviço Windows (via NSSM)
Para manter o microsserviço rodando de forma resiliente após reinicializações do servidor Windows:
```powershell
# 1. Instalar o serviço via NSSM
nssm install DocJourneyAPI "C:\...\prod_docjourney\.venv\Scripts\python.exe" "-m uvicorn microservico.main:app --host 0.0.0.0 --port 8000"

# 2. Definir diretório de trabalho
nssm set DocJourneyAPI AppDirectory "C:\...\prod_docjourney"

# 3. Iniciar o serviço
nssm start DocJourneyAPI
```

---

## 9. Catálogo de Endpoints REST & Documentação Interativa

Após iniciar a aplicação, acesse a documentação interativa gerada pelo FastAPI:
- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **OpenAPI Schema (JSON):** [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

### Principais Endpoints Disponíveis:

| Grupo | Método | Rota | Descrição |
| :--- | :--- | :--- | :--- |
| **Diagnóstico** | `GET` | `/health` | Checa integridade de conexão com o banco e RabbitMQ. |
| **Jornadas** | `POST` | `/api/v1/journeys` | Criação ou recuperação idempotente por `mongo_id`. |
| **Jornadas** | `GET` | `/api/v1/journeys/{mongo_id}` | Consulta detalhes cadastrais da jornada. |
| **Jornadas** | `PATCH` | `/api/v1/journeys/{id}/status` | Atualiza status (`PENDING`, `COMPLETED`, `FAILED`). |
| **Jornadas** | `GET` | `/api/v1/journeys/{id}/envelopes` | Lista todos os envelopes associados à jornada. |
| **Envelopes** | `POST` | `/api/v1/envelopes` | Registra novo envelope com signatários e anexos. |
| **Envelopes** | `GET` | `/api/v1/envelopes/{id}` | Busca envelope por UUID interno ou external ID. |
| **Envelopes** | `POST` | `/api/v1/envelopes/{id}/replace` | **Substituição Seletiva:** marca versão anterior como `REPLACED_CANCELED`, audita e gera nova versão ($v+1$). |
| **Manutenção** | `POST` | `/api/v1/maintenance/cancel` | Cancelamento administrativo de envelope com justificativa auditada. |
| **Manutenção** | `POST` | `/api/v1/maintenance/expire-check`| Varredura e marcação de envelopes pendentes vencidos (`EXPIRED`). |
| **Manutenção** | `GET` | `/api/v1/maintenance/history` | Consulta paginada do histórico de governança. |
| **Manutenção** | `GET` | `/api/v1/maintenance/overview` | Dashboard consolidado de envelopes por status. |

---

## 10. Execução de Testes Automatizados

O repositório possui uma bateria abrangente de testes automatizados com `pytest`:

```powershell
# 1. Rodar todos os testes do microsserviço
python -m pytest microservico/tests/

# 2. Rodar com detalhes e saídas de log
python -m pytest microservico/tests/ -v -s

# 3. Rodar simulador de tráfego em massa no RabbitMQ
python microservico/tests/test_mass_queue_traffic.py
```

---

## 11. Troubleshooting & Resolução de Problemas Corporativos

### 1. `WinError 10061`: Nenhuma conexão pôde ser feita porque a máquina de destino as recusou ativamente
- **Causa:** O PostgreSQL ou o RabbitMQ não estão rodando nas portas configuradas (`5432` ou `5672`).
- **Solução:**
  - Verifique se os serviços estão ativos no Windows:
    ```powershell
    Get-Service -Name "RabbitMQ*", "postgresql*"
    ```
  - Se estiver testando localmente sem esses serviços, mantenha as configurações padrão do `.env`: o sistema ativa automaticamente o **SQLite em memória** e a **Mock Queue**.

### 2. Porta 8000 já está em uso
- **Causa:** Outra instância do Uvicorn ou aplicação web já está ocupando a porta 8000.
- **Solução:**
  - Localizar e encerrar o processo no Windows:
    ```powershell
    Get-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess | Stop-Process -Force
    ```
  - Ou alterar a porta no `.env`: `API_PORT=8005`.

### 3. Falha de SSL / Certificado ao rodar `pip install`
- **Causa:** O firewall ou proxy corporativo intercepta requisições HTTPS com certificado raiz proprietário.
- **Solução:**
  ```powershell
  pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org -r microservico/requirements.txt
  ```

### 4. Permissões de Script no PowerShell
- **Causa:** Diretivas de segurança do Windows impedem a execução de scripts (`.ps1`).
- **Solução:**
  ```powershell
  Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
  ```
