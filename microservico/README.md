# Microsserviço DocJourney (Backend REST API & Mensageria)

Microsserviço corporativo de alta disponibilidade responsável pela persistência relacional, governança de ciclo de vida de documentos, histórico de auditoria e integração assíncrona de esteiras de assinatura digital (Sicredi).

Construído com **FastAPI**, **Pydantic v2**, **PostgreSQL** (com suporte a **SQLite** para testes rápidos) e mensageria assíncrona **RabbitMQ**.

---

## 🏛️ Arquitetura e Papel no Ecossistema

O microsserviço atua como a **única fonte da verdade e guardião da persistência**:
- **Desacoplamento Total:** A automação RPA e sistemas terceiros nunca acessam o banco de dados diretamente via SQL. Toda comunicação é realizada via API RESTful padronizada ou eventos via RabbitMQ.
- **Auditoria Centralizada:** Registro imutável de todas as ocorrências de governança na tabela `maintenance_history` (cancelamentos, substituições de versão, expirações e intervenções manuais).
- **Idempotência Garantida:** Tratamento rigoroso de unicidade para jornadas de negócio (`mongo_id` / tarefas Fluid).
- **Substituição Seletiva e Versionamento:** Controle rigoroso de versões incrementais de envelopes por escopo documental.

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
         └─────────────┬───────────────────────────┬───────────────┘
                       │                           │
          Consultas /  │               Publicação/ │ Eventos
          Persistência │               Consumo     │
                       ▼                           ▼
            ┌────────────────────┐      ┌────────────────────┐
            │   PostgreSQL DB    │      │  RabbitMQ Broker   │
            │ (Schema Relacional)│      │  (docjourney_queue)│
            └────────────────────┘      └──────────┬─────────┘
                                                   │
                                                   ▼
                                        ┌────────────────────┐
                                        │  Background Worker │
                                        │ (worker.py Daemon) │
                                        └────────────────────┘
```

---

## 📚 Documentação Interativa da API (Swagger / OpenAPI)

A API gera documentação interativa completa e padronizada automaticamente:
- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **OpenAPI JSON:** [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

---

## 🔌 Catálogo de Endpoints REST

### 1. Healthcheck e Observabilidade
| Método | Endpoint | Descrição |
| :--- | :--- | :--- |
| `GET` | `/health` | Verifica a conectividade com o banco de dados e o broker RabbitMQ em tempo real. |

### 2. Gestão de Jornadas (`/api/v1/journeys`)
| Método | Endpoint | Descrição |
| :--- | :--- | :--- |
| `POST` | `/api/v1/journeys` | Cria ou recupera de forma idempotente uma jornada por `mongo_id`. Se já existir, retorna o registro existente. |
| `GET` | `/api/v1/journeys/{mongo_id}` | Consulta detalhes de uma jornada pelo ID de origem do MongoDB. |
| `PATCH` | `/api/v1/journeys/{id}/status` | Atualiza o status do processo da jornada (`PENDING`, `PROCESSING`, `COMPLETED`, `ERROR`, `INTERVENTION`). |
| `GET` | `/api/v1/journeys/{id}/envelopes` | Lista todos os envelopes associados a uma jornada, ordenados por data. |

### 3. Gestão de Envelopes (`/api/v1/envelopes`)
| Método | Endpoint | Descrição |
| :--- | :--- | :--- |
| `POST` | `/api/v1/envelopes` | Registra um envelope com seus documentos e signatários associados. |
| `GET` | `/api/v1/envelopes/{id}` | Recupera os dados cadastrais do envelope por ID interno ou UUID da OpenAPI. |
| `PATCH` | `/api/v1/envelopes/{id}/status` | Altera o status do envelope (`PENDING_SIGNATURE`, `COMPLETED`, `CANCELED`, etc.). |
| `POST` | `/api/v1/envelopes/{id}/replace` | Executa a substituição seletiva: marca o envelope antigo como `REPLACED_CANCELED`, registra histórico de manutenção e cria o novo envelope incremental ($v_{nova} = v_{antiga} + 1$). |

### 4. Manutenção, Auditoria e Governança (`/api/v1/maintenance`)
| Método | Endpoint | Descrição |
| :--- | :--- | :--- |
| `POST` | `/api/v1/maintenance/cancel` | Realiza o cancelamento administrativo de um envelope, registrando o operador e justificativa em `maintenance_history`. |
| `POST` | `/api/v1/maintenance/expire-check` | Executa a varredura automática de envelopes pendentes vencidos (`expired_at <= NOW()`), marcando-os como `EXPIRED` e auditando a ocorrência. |
| `GET` | `/api/v1/maintenance/history` | Consulta paginada do histórico de manutenção com filtros (`reason_code`, `resolved`, `envelope_id`, `request_id`). |
| `PATCH` | `/api/v1/maintenance/history/{id}/resolve` | Marca uma pendência operacional como resolvida pelo operador. |
| `GET` | `/api/v1/maintenance/overview` | Retorna o dashboard consolidado com totais de envelopes por status e pendências abertas. |

---

## ⚙️ Configuração e Variáveis de Ambiente

Crie um arquivo `.env` na pasta `microservico/` ou defina as variáveis no ambiente:

```env
# Configurações do Servidor HTTP
API_HOST=0.0.0.0
API_PORT=8000
ENVIRONMENT=production

# Banco de Dados PostgreSQL (Produção / Homologação)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=docjourney_db
DB_USER=postgres
DB_PASSWORD=sua_senha_segura
DB_POOL_MIN=2
DB_POOL_MAX=10

# Mensageria RabbitMQ
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest
RABBITMQ_QUEUE=docjourney_queue

# Webhooks Externos
NOTIFIER_WEBHOOK_URL=https://api-mock.sicredi.local/webhook/status
```

---

## 🐰 Guia Completo de Instalação do RabbitMQ (Windows & Linux)

O **RabbitMQ** é o broker de mensageria assíncrona utilizado pelo microsserviço. Ele opera em segundo plano como um serviço do sistema operacional, sem necessidade de manter terminais de comando abertos.

> **Portas de Rede Padrão:**
> - `5672`: Porta de comunicação de dados da aplicação (protocolo AMQP utilizado pelo FastAPI e Worker).
> - `15672`: Porta da interface gráfica no navegador (RabbitMQ Management Dashboard).

---

### A. Instalação no Windows

Você pode instalar no Windows de forma nativa ou via Docker:

#### Opção 1: Via Winget (Mais Rápido e Automático no PowerShell)
Abra o **PowerShell como Administrador** e execute:
```powershell
# 1. Instalar a dependência obrigatória (Erlang/OTP)
winget install Erlang.Erlang --accept-package-agreements --accept-source-agreements

# 2. Instalar o RabbitMQ Server
winget install Pivotal.RabbitMQ --accept-package-agreements --accept-source-agreements

# 3. Feche e reabra o PowerShell como Administrador e ative o painel web:
& "$env:ProgramFiles\RabbitMQ Server\rabbitmq_server-*\sbin\rabbitmq-plugins.bat" enable rabbitmq_management

# 4. Reinicie o serviço do Windows
Restart-Service -Name "RabbitMQ"
```

#### Opção 2: Via Chocolatey (se você utiliza o Choco)
```powershell
choco install rabbitmq -y
```
*(O Chocolatey baixa, configura o Erlang/OTP e registra o serviço do RabbitMQ automaticamente).*

#### Opção 3: Instaladores Gráficos Oficiais (.exe)
1. **Passo 1 (Obrigatório):** Baixe e instale o **Erlang/OTP**:
   - Link de Download: [https://www.erlang.org/patches/otp-26.2.5.3](https://www.erlang.org/patches/otp-26.2.5.3) (ou versão compatível).
   - Execute o instalador `otp_win64_*.exe` avançando com as opções padrão.
2. **Passo 2:** Baixe e instale o **RabbitMQ Server**:
   - Link de Download: [https://github.com/rabbitmq/rabbitmq-server/releases/latest](https://github.com/rabbitmq/rabbitmq-server/releases/latest) (arquivo `rabbitmq-server-*-windows.exe`).
   - Execute o instalador. Ele registra e inicia automaticamente o serviço no `services.msc` do Windows.
3. **Passo 3: Ativar o Painel Web:**
   - No menu Iniciar, abra o **"RabbitMQ Command Prompt (sbin dir)"** como Administrador.
   - Execute:
     ```cmd
     rabbitmq-plugins enable rabbitmq_management
     ```
   - Reinicie o serviço no PowerShell: `Restart-Service RabbitMQ`.

#### Opção 4: Via Docker (Zero Instalação de Arquivos Locais)
Se você já possui o **Docker Desktop** instalado no Windows:
```powershell
docker run -d --name rabbitmq --restart always -p 5672:5672 -p 15672:15672 rabbitmq:3-management
```

---

### B. Instalação no Linux (Produção / Ubuntu / Debian / RHEL)

#### 1. Ubuntu / Debian (Nativo via APT):
```bash
# 1. Atualizar lista de pacotes e instalar utilitários
sudo apt-get update
sudo apt-get install -y curl gnupg apt-transport-https

# 2. Instalar o servidor RabbitMQ (já inclui Erlang automaticamente nas distros atuais)
sudo apt-get install -y rabbitmq-server

# 3. Habilitar o serviço para iniciar sozinho com o boot do servidor
sudo systemctl enable --now rabbitmq-server

# 4. Ativar o painel gráfico web
sudo rabbitmq-plugins enable rabbitmq_management

# 5. Verificar se está ativo e rodando
sudo systemctl status rabbitmq-server
```

#### 2. Red Hat / Rocky Linux / AlmaLinux / CentOS (via DNF):
```bash
sudo dnf install -y epel-release
sudo dnf install -y rabbitmq-server
sudo systemctl enable --now rabbitmq-server
sudo rabbitmq-plugins enable rabbitmq_management
```

#### 3. Linux via Docker:
```bash
docker run -d --name rabbitmq \
  --restart always \
  -p 5672:5672 \
  -p 15672:15672 \
  -v rabbitmq_data:/var/lib/rabbitmq \
  rabbitmq:3-management
```

---

### C. Acesso ao Painel Gráfico Web e Configuração de Usuário

1. **Acesso Local pelo Navegador:**
   - URL: [http://localhost:15672](http://localhost:15672)
   - Usuário Padrão: `guest`
   - Senha Padrão: `guest`

2. **Permitir Acesso de Outras Máquinas / Rede Interna (Obrigatório em Linux):**
   *Por segurança, o RabbitMQ bloqueia o usuário `guest` fora do `localhost`. Para acessar o painel pelo IP do servidor corporativo, crie um usuário administrador:*
   ```bash
   # Criar novo usuário
   sudo rabbitmqctl add_user admin_sicredi "SuaSenhaSegura123!"

   # Definir permissão de administrador
   sudo rabbitmqctl set_user_tags admin_sicredi administrator

   # Liberar permissões totais no vhost raiz
   sudo rabbitmqctl set_permissions -p / admin_sicredi ".*" ".*" ".*"
   ```

---

### D. Comandos Úteis de Verificação e Diagnóstico

| Ação | Windows (PowerShell Admin) | Linux (Bash) |
| :--- | :--- | :--- |
| **Testar Conexão** | `rabbitmq-diagnostics ping` | `sudo rabbitmq-diagnostics ping` |
| **Listar Filas e Mensagens** | `rabbitmqctl list_queues name messages` | `sudo rabbitmqctl list_queues name messages` |
| **Verificar Status Geral** | `Get-Service -Name "RabbitMQ"` | `sudo systemctl status rabbitmq-server` |
| **Reiniciar Serviço** | `Restart-Service -Name "RabbitMQ"` | `sudo systemctl restart rabbitmq-server` |

---

## 🚀 Como Executar o Microsserviço

### 1. Execução em Desenvolvimento (Modo Unificado em 1 Único Terminal - Recomendado)
Por padrão, o microsserviço já vem configurado com **Worker Embutido no Lifespan** (`ENABLE_EMBEDDED_WORKER=true`). Isso significa que a API FastAPI e o consumidor RabbitMQ iniciam juntos no mesmo terminal:

```bash
# Ativar o ambiente virtual
# Windows: .\.venv\Scripts\Activate.ps1
# Linux: source .venv/bin/activate

# Instalar dependências
pip install -r microservico/requirements.txt

# Iniciar tudo em um único comando (API + Consumidor RabbitMQ)
python -m uvicorn microservico.main:app --host 0.0.0.0 --port 8000 --reload
```
*(Ao rodar o comando acima, você verá nos logs a inicialização do banco, o disparo da thread paralela do worker e o servidor web pronto para receber requisições).*

---

### 2. Execução com Terminais Separados (Modo Standalone Opcional)
Se você preferir rodar o consumidor do RabbitMQ em uma janela separada para visualizar os logs de mensageria isolados:
1. No seu `.env`, defina: `ENABLE_EMBEDDED_WORKER=false`
2. **Terminal 1 (FastAPI):**
   ```bash
   python -m uvicorn microservico.main:app --port 8000 --reload
   ```
3. **Terminal 2 (Worker RabbitMQ Standalone):**
   ```bash
   python microservico/worker.py
   ```

### 3. Implantação em Produção Linux (systemd)

Para manter a API e o Worker rodando como serviços resilientes do sistema operacional:

#### Serviço da API (`/etc/systemd/system/docjourney-api.service`):
```ini
[Unit]
Description=DocJourney FastAPI Microservice
After=network.target postgresql.service rabbitmq-server.service

[Service]
User=appuser
Group=appuser
WorkingDirectory=/opt/docjourney/microservico
EnvironmentFile=/opt/docjourney/microservico/.env
ExecStart=/opt/docjourney/.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

#### Serviço do Worker RabbitMQ (`/etc/systemd/system/docjourney-worker.service`):
```ini
[Unit]
Description=DocJourney RabbitMQ Background Worker
After=network.target rabbitmq-server.service

[Service]
User=appuser
Group=appuser
WorkingDirectory=/opt/docjourney/microservico
EnvironmentFile=/opt/docjourney/microservico/.env
ExecStart=/opt/docjourney/.venv/bin/python worker.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Ative e inicie ambos os serviços:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now docjourney-api docjourney-worker
sudo systemctl status docjourney-api docjourney-worker
```

### 4. Implantação com Docker
```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 🧪 Execução de Testes Automatizados

```bash
# Rodar todos os testes de repositórios e mensageria
python microservico/tests/run_tests.py

# Rodar testes de integração da API REST (FastAPI TestClient)
python -m unittest microservico/tests/test_api.py

# Rodar teste ponta a ponta com PostgreSQL real (quando disponível)
python microservico/tests/test_postgres_e2e.py
```

---

## 📖 Manual Passo a Passo: Como Adicionar uma Nova Rota no Microsserviço

Para manter a arquitetura limpa, manutenível e extensível, siga este guia prático sempre que precisar adicionar uma nova rota à API.

### Fluxo Geral:
```
1. Schema (Pydantic) ──► 2. Repository / Domain ──► 3. Router (Endpoint) ──► 4. Registro (main.py) ──► 5. Teste
```

---

### Passo 1: Definir os Contratos de Dados (Schemas Pydantic)
Abra `microservico/api/schemas.py` e crie as classes que representam o **Payload de Entrada (Request)** e o **Formato de Resposta (Response)**:

```python
# microservico/api/schemas.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class RelatorioAuditoriaRequest(BaseModel):
    data_inicio: datetime = Field(..., description="Data de início do período de auditoria")
    data_fim: datetime = Field(..., description="Data de término do período de auditoria")
    cooperativa_codigo: Optional[str] = Field(None, max_length=10, description="Código opcional da cooperativa")

class RelatorioAuditoriaResponse(BaseModel):
    total_processados: int
    total_cancelados: int
    total_expirados: int
    gerado_em: datetime
```

---

### Passo 2: Implementar a Lógica no Repositório ou Serviço
Abra o repositório relevante em `microservico/repositories/` (ou crie um novo se for uma nova entidade). Utilize sempre queries parametrizadas (`%s` para PostgreSQL / `?` para SQLite via `db_manager.placeholder`):

```python
# microservico/repositories/relatorio_repository.py
class RelatorioRepository:
    def __init__(self, db_manager):
        self.db = db_manager

    def consolidar_metricas(self, data_inicio, data_fim, cooperativa_codigo=None) -> dict:
        ph = self.db.placeholder
        query = f"""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN envelope_status = 'CANCELED' THEN 1 ELSE 0 END) as cancelados,
                SUM(CASE WHEN envelope_status = 'EXPIRED' THEN 1 ELSE 0 END) as expirados
            FROM envelopes
            WHERE created_at BETWEEN {ph} AND {ph}
        """
        params = [data_inicio, data_fim]
        if cooperativa_codigo:
            query += f" AND cooperativa_codigo = {ph}"
            params.append(cooperativa_codigo)

        with self.db.get_cursor() as cursor:
            cursor.execute(query, tuple(params))
            row = cursor.fetchone()
            return {
                "total": row[0] if row else 0,
                "cancelados": row[1] if row and row[1] else 0,
                "expirados": row[2] if row and row[2] else 0
            }
```

Atualize `microservico/api/dependencies.py` para injetar o novo repositório:
```python
def get_relatorio_repository(db=Depends(get_db)):
    return RelatorioRepository(db)
```

---

### Passo 3: Criar o Router do Endpoint
Crie o arquivo em `microservico/api/routers/relatorios.py` (ou inclua em um router existente):

```python
# microservico/api/routers/relatorios.py
from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime
from microservico.api.schemas import RelatorioAuditoriaRequest, RelatorioAuditoriaResponse
from microservico.api.dependencies import get_relatorio_repository
from microservico.repositories.relatorio_repository import RelatorioRepository

router = APIRouter(
    prefix="/api/v1/relatorios",
    tags=["Relatórios e Auditoria"]
)

@router.post(
    "/consolidado",
    response_model=RelatorioAuditoriaResponse,
    status_code=status.HTTP_200_OK,
    summary="Gerar Relatório Consolidado",
    description="Calcula as métricas de envelopes criados, cancelados e expirados dentro do período informado."
)
def gerar_relatorio_consolidado(
    payload: RelatorioAuditoriaRequest,
    repo: RelatorioRepository = Depends(get_relatorio_repository)
):
    try:
        metricas = repo.consolidar_metricas(
            data_inicio=payload.data_inicio,
            data_fim=payload.data_fim,
            cooperativa_codigo=payload.cooperativa_codigo
        )
        return RelatorioAuditoriaResponse(
            total_processados=metricas["total"],
            total_cancelados=metricas["cancelados"],
            total_expirados=metricas["expirados"],
            gerado_em=datetime.now()
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao processar relatório: {str(exc)}"
        )
```

---

### Passo 4: Registrar o Router no `main.py`
Abra `microservico/main.py` e inclua o router:

```python
# microservico/main.py
from microservico.api.routers import relatorios  # <-- Importar o router

# Adicionar junto aos outros routers:
app.include_router(relatorios.router)
```

---

### Passo 5: Escrever o Teste Unitário da Nova Rota
Adicione um teste em `microservico/tests/test_api.py`:

```python
def test_gerar_relatorio_consolidado(self):
    payload = {
        "data_inicio": "2026-01-01T00:00:00",
        "data_fim": "2026-12-31T23:59:59"
    }
    response = self.client.post("/api/v1/relatorios/consolidado", json=payload)
    self.assertEqual(response.status_code, 200)
    data = response.json()
    self.assertIn("total_processados", data)
    self.assertIn("gerado_em", data)
```

Execute o teste:
```bash
python -m unittest microservico/tests/test_api.py
```

---

### Passo 6: Visualizar e Validar no Swagger
Acesse [http://localhost:8000/docs](http://localhost:8000/docs). A nova rota aparecerá na categoria correspondente, com documentação interativa, campos obrigatórios, tipos de dados e botão "Try it out" para testes rápidos.
