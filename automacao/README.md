# Módulo de Automação RPA (DocJourney Automation)

Módulo orquestrador robótico responsável pela ingestão de tarefas do MongoDB (Fluid), pré-validação antecipada exaustiva, clusterização de envelopes por escopo documental, upload multipart e substituição seletiva via OpenAPI v2.

---

## 🎯 1. Propósito do Módulo

A automação RPA executa o trabalho operacional de envio e gestão dos documentos:
- **Pré-Validação Antecipada ('Tudo de uma Vez'):** Varre simultaneamente todos os signatários, CPFs, canais de comunicação e integridade dos anexos. Não interrompe no primeiro erro (*No-Fail-Fast*), gerando um parecer HTML padronizado com todas as pendências para o operador do Fluid.
- **Clusterização Documental por SHA256:** Agrupa participantes pela interseção exata dos documentos que lhes cabe assinar, garantindo que nenhum envelope tenha signatários com escopos documentais divergentes.
- **Integração OpenAPI v2:** Desacoplamento entre criação estrutural (`POST /v2/envelope/create`) e upload de binários multipart (`POST /files/envelope/:envelopeId/files`).
- **Substituição Seletiva e Versionamento:** Cancelamento gracioso de versões obsoletas e emissão de novos envelopes incrementais quando há alterações no processo.

---

## 🧠 2. Como a Automação Sabe se Cria ou Altera/Substitui um Documento

O ciclo decisório da automação segue rigorosamente a árvore lógica abaixo:

```mermaid
flowchart TD
    A[Recebe Tarefa MongoDB / Fluid] --> B{Jornada existe no banco? (mongo_id)}
    B -- Não --> C[Cria registro em journey_requests]
    B -- Sim --> D[Recupera jornada existente]
    C --> E[Executa Pré-Validação Antecipada]
    D --> E
    E -- Pendências Encontradas --> F[Dispara BulkValidationError & Gera Parecer HTML]
    E -- Dados Válidos --> G[Gera Clusters Documentais SHA256]
    G --> H{Existem envelopes ativos na jornada?}
    H -- Não (Primeira Criação) --> I[Cria Envelope Versão 1 no Banco]
    I --> J[POST /v2/envelope/create na OpenAPI]
    J --> K[POST /files/envelope/:id/files Upload Multipart]
    H -- Sim (Alteração de Documento ou Signatário) --> L[Substituição Seletiva: DELETE na OpenAPI v1]
    L --> M[Atualiza envelope antigo para REPLACED_CANCELED]
    M --> N[Calcula Versão = max_version + 1]
    N --> O[Cria Novo Envelope Versão N+1 no Banco]
    O --> P[POST /v2/envelope/create Versão Nova]
    P --> Q[POST /files/envelope/:id/files Upload Binários]
    Q --> R[Registra Histórico de Manutenção: DOC_VERSION_CHANGE ou SIGNER_CHANGE]
```

### Regras de Negócio Decisórias:
1. **Identificação da Jornada:** A automação consulta `journey_requests WHERE mongo_id = ?`. Se for uma tarefa reencaminhada do Fluid após correção de parecer, o registro existente é reutilizado.
2. **Cálculo do Hash de Escopo:** Para cada grupo de assinantes, calcula `document_scope_hash = SHA256(documentos_ordenados)`.
3. **Consulta de Envelopes Ativos:** Consulta `envelopes WHERE request_id = ? AND envelope_status NOT IN ('CANCELED', 'REPLACED_CANCELED', 'EXPIRED')`.
4. **Decisão de Criação vs Substituição:**
   - Se **nenhum envelope ativo existir**, é uma **Criação Inicial (Versão 1)**.
   - Se **já existirem envelopes ativos**, significa que o processo sofreu alterações (troca de arquivo PDF, inclusão de avalista/cônjuge ou retificação). A automação executa a **Substituição Seletiva**: cancela o envelope obsoleto na OpenAPI, marca-o como `REPLACED_CANCELED` no banco, cria a nova versão incremental (`versao = max_v + 1`) e registra auditoria em `maintenance_history`.

---

## 💻 3. Diferenças de Execução: Windows vs Linux

| Aspecto | Execução no Windows (Automação RPA) | Execução no Linux (Microsserviço / Worker) |
| :--- | :--- | :--- |
| **Ativação do Ambiente Virtual** | `.\.venv\Scripts\Activate.ps1` | `source .venv/bin/activate` |
| **Console Encoding** | `sys.stdout.reconfigure(encoding="utf-8")` é aplicado para compatibilidade com console Windows (CP1252/CP850) | UTF-8 nativo em terminais Linux |
| **Gerenciamento de Processos** | Agendador de Tarefas do Windows, PowerShell Scripts ou Orquestrador RPA | Systemd, Supervisor, Docker ou Celery Workers |
| **Caminhos de Arquivos** | Utiliza `os.path.join` e caminhos absolutos com barras normatizadas | Padrão POSIX (`/home/...`) |

---

## 🚀 4. Instruções de Execução e Testes

### Instalação de Dependências
```powershell
# Windows
.\.venv\Scripts\pip.exe install -r automacao/requirements.txt

# Linux
./.venv/bin/pip install -r automacao/requirements.txt
```

### Execução dos Testes Unitários da Automação
Valida o acúmulo de erros da pré-validação, a clusterização SHA256 e o workflow básico:
```powershell
.\.venv\Scripts\python.exe automacao/tests/run_tests.py
```

### Execução da Suíte Interativa dos 6 Cenários (PostgreSQL Real)
Simula em tempo real todos os cenários de criação, versionamento incremental, inclusão de cônjuge avalista, captura de erros e expiração de envelopes:
```powershell
# Execução padrão contra o banco PostgreSQL configurado no .env
.\.venv\Scripts\python.exe automacao/tests/test_interactive_scenarios.py

# Execução alternativa em modo isolado SQLite em memória (sem precisar de PostgreSQL)
.\.venv\Scripts\python.exe automacao/tests/test_interactive_scenarios.py --sqlite
```
