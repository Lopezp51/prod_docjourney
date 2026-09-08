# Módulo de Microsserviço Backend (DocJourney Microservice)

Módulo central de infraestrutura, repositórios de dados relacionais (PostgreSQL/SQLite), inicialização DDL idempotente, histórico de auditoria e mensageria/notificação de status (RabbitMQ e Webhooks HTTP).

---

## 🎯 1. Propósito do Módulo

O microsserviço atua como a camada de persistência e governança de dados da esteira de assinaturas:
- **Repositórios de Dados em Inglês:** Abstração completa via Repository Pattern para 8 entidades (`associates`, `processes`, `process_configurations`, `journey_requests`, `envelopes`, `documents`, `envelope_signers`, `maintenance_history`).
- **Garantia de Idempotência:** Impede duplicação de solicitações originárias do MongoDB/Fluid através do campo único `mongo_id`.
- **Governança do Ciclo de Vida:** Controle dos estados dos envelopes (`DRAFT`, `PENDING_SIGNATURE`, `COMPLETED`, `CANCELED`, `REPLACED_CANCELED`, `EXPIRED`, `INTERVENTION`).
- **Mensageria e Notificação Externa:** Publicação e consumo de eventos de assinatura via RabbitMQ (com fallback automático para fila em memória) e disparo de Webhooks HTTP resilientes com HTTPX/urllib.

---

## 💻 2. Diferenças de Execução: Windows vs Linux

Em ambiente produtivo, o **microsserviço executa tipicamente em servidores Linux** (Docker, Kubernetes ou systemd), enquanto a **automação RPA pode executar em máquinas Windows**.

| Aspecto | Ambiente Windows | Ambiente Linux (Produção) |
| :--- | :--- | :--- |
| **Ativação do Ambiente Virtual** | `.\.venv\Scripts\Activate.ps1` | `source .venv/bin/activate` |
| **Separadores de Diretório** | `\` (invertida) ou `/` | `/` (barra padrão POSIX) |
| **Codificação do Terminal (Stdout)** | Exige `sys.stdout.reconfigure(encoding="utf-8")` para caracteres especiais | UTF-8 nativo no sistema operacional |
| **Modo de Execução** | CLI interativa, Task Scheduler ou Agente RPA | Daemon em segundo plano, contêiner Docker ou serviço systemd |
| **Conexão com PostgreSQL / RabbitMQ** | Conecta via localhost ou IP corporativo com firewall local | Conecta via nomes de serviço DNS internos (ex.: `db.sicredi.local:5432`) |

---

## ⚙️ 3. Variáveis de Ambiente Necessárias

As configurações são lidas do arquivo `.env` na raiz do projeto ou das variáveis de ambiente do sistema operacional:

```env
# Banco de Dados PostgreSQL
DB_HOST=localhost
DB_PORT=5432
DB_NAME=docjourney_db
DB_USER=postgres
DB_PASSWORD=senha123

# Mensageria RabbitMQ
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest

# Webhook de Notificação Externa
NOTIFIER_WEBHOOK_URL=https://api-mock.sicredi.local/webhook/status
```

---

## 🐰 4. Mensageria RabbitMQ: Testes e Visualização da Fila

O sistema conta com um cliente RabbitMQ resiliente (`RabbitMQClient`) projetado para não interromper os fluxos caso o broker esteja temporariamente indisponível (ativa automaticamente a **Mock Queue em memória**).

### A. Execução da Bateria de Testes do RabbitMQ
Execute o script dedicado que publica eventos, monitora métricas e consome mensagens:

```powershell
# Windows
.\.venv\Scripts\python.exe microservico/tests/test_rabbitmq.py

# Linux
./.venv/bin/python microservico/tests/test_rabbitmq.py
```

### B. Como Subir e Rodar o RabbitMQ 24/7 em Segundo Plano (Sem Janela de Terminal Aberta)

> **Importante:** Você não precisa deixar nenhuma janela de terminal aberta. O RabbitMQ roda silenciosamente como Serviço do Windows ou Daemon do Linux.

1. **No Windows (Via Interface Gráfica ou PowerShell Admin):**
   - **Interface Gráfica:** Pressione `Win + R`, digite `services.msc` -> clique com o botão direito em **RabbitMQ** -> **Iniciar**.
   - **PowerShell (Admin):**
     ```powershell
     Start-Service -Name "RabbitMQ"
     Get-Service -Name "RabbitMQ"
     ```
   - O serviço já fica registrado como `Automatic`, iniciando sozinho com o Windows.

2. **No Linux (Produção):**
   ```bash
   sudo systemctl enable --now rabbitmq-server
   sudo rabbitmq-plugins enable rabbitmq_management
   sudo systemctl status rabbitmq-server
   ```

3. **Via Docker:**
   ```bash
   docker run -d --name rabbitmq --restart always -p 5672:5672 -p 15672:15672 rabbitmq:3-management
   ```

4. **Acesse o Painel Visual de Filas no Navegador:**
   - **URL:** [http://localhost:15672](http://localhost:15672)
   - **Usuário:** `guest`
   - **Senha:** `guest`
   - Clique na aba **"Queues"** (Filas) para acompanhar as mensagens em tempo real.

---

## 📦 5. Instalação e Execução de Testes

### Instalação de Dependências
```powershell
# Windows
.\.venv\Scripts\pip.exe install -r microservico/requirements.txt

# Linux
./.venv/bin/pip install -r microservico/requirements.txt
```

### Execução da Suíte de Testes Unitários
```powershell
.\.venv\Scripts\python.exe microservico/tests/run_tests.py
```

### Execução do Teste E2E com PostgreSQL Real
```powershell
.\.venv\Scripts\python.exe microservico/tests/test_postgres_e2e.py
```
