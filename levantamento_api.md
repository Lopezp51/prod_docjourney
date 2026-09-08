# Levantamento de Integrações e Dados: PAS e Certisign

Este documento mapeia todas as rotas disponíveis nas APIs do PAS e da Certisign, além de detalhar os parâmetros e dados necessários para a automação de assinatura de documentos. Este material visa auxiliar na construção da estrutura do banco de dados e no planejamento das rotinas de manutenção.

---

## 1. Mapeamento de Dados Necessários (Baseados no Payload do Processo)

Para cada signatário e processo, extrairemos as seguintes informações (com base no campo `10410` e mapeamentos do JSON recebido `visao geral.md`):

### Dados da Pessoa / Signatário
* **CPF:** `10411`
* **Nome:** `10412`
* **E-mail:** `10415`
* **Telefone:** `10416` (Importante caso a notificação seja via WhatsApp)

### Dados do Processo de Assinatura
* **Ordem de Assinatura:** `10417` (Varia de 1 a 10. Na Certisign, e possivelmente no PAS, permite definir que o próximo só assina quando o anterior finalizar).
* **Papel / Tipo de Assinante:** `8665` ou `11248` (Ex: "Procurador Segurado", "Segurado", "Representante da Empresa", "Cônjuge Avalista").
* **Documentos a Assinar:** `10751` ou `11249` (Lista contendo o ID e/ou nome dos documentos. Ex: `["765 - CCB", "613 - Seguro Prestamista"]`).
* **Tipo de Assinatura:** `10418` ("Eletrônica" ou "Certificado Digital").
* **Canal de Comunicação/Envio:** `10414` ("E-mail", "WhatsApp Enterprise", "Presencial - Foto"). *Nota: Assinaturas presenciais não seguem pela automação.*

### Dados Estruturais Adicionais (Do JSON geral)
* **Informações do Processo:** `num_processo`, `nome_processo`, `status`
* **Informações do Fluid:** `fluid_infos` (processo_id, arvore, nodo, email_resp, emp_origem)
* **Anexos (`infos_envio.anexos`):** Será necessário correlacionar os documentos listados com os arquivos recebidos (`nome`, `hash`, `tipo_doc_id`, `extensao`), para saber quais arquivos devem ser enviados ao PAS/Certisign.

---

## 2. Rotas Disponíveis - PAS (Processo de Assinatura)

As requisições ao PAS geralmente exigem os headers de autenticação corporativa: `x-api-coop-user`, `x-api-coop-numero`, `x-api-coop-aplicacao`, `Authorization`.

### Configurações e Tipos
* **`GET` `/assinatura-open-api/pds-document-type/find/related-ged-only`**
  * **Uso:** Buscar tipos de documentos relacionados ao GED.
  * **Parâmetros:** `name` (Query param opcional para filtrar pelo nome do tipo).
* **`GET` `/assinatura-open-api/config/coop-parameters/{coop}`**
  * **Uso:** Buscar parâmetros de configuração do PAS para uma cooperativa específica.
  * **Parâmetros:** `coop` (Path param obrigatório com o código da cooperativa).

### Gestão de Envelopes
* **`POST` `/assinatura-open-api/v2/envelope/create`**
  * **Uso:** Criar um novo envelope digital informando os signatários, ordem e tipos de assinatura.
  * **Parâmetros Principais (Body):** `coop`, `title`, `signers` (lista de signatários com nome, cpf, email, telefone, flowRole, tipo de assinatura, métodos de autenticação), `provider`, `notificationEmails`, `documentSignaturePattern`.
* **`POST` `/assinatura-open-api/v2/envelope/{envelopeId}/clone`**
  * **Uso:** Clonar a estrutura de um envelope existente.
  * **Parâmetros:** `envelopeId` (Path param), e Body contendo `coop` e `agency`.
* **`GET` `/assinatura-open-api/v2/envelope/{id}`**
  * **Uso:** Recuperar os detalhes completos de um envelope específico.
  * **Parâmetros:** `id` (Path param obrigatório com o ID do envelope).
* **`GET` `/assinatura-open-api/v2/envelope/search`**
  * **Uso:** Pesquisar envelopes com paginação e múltiplos filtros.
  * **Parâmetros de Busca (Query):** `status` (ex: ASSINATURA_PENDENTE), `cpfCnpj`, `signerName`, `createdDateStart`, `createdDateEnd`, `page`, `size`, `sortField`.
* **`DELETE` `/assinatura-open-api/v2/envelope/{envelopeId}`**
  * **Uso:** Deletar um envelope.
  * **Parâmetros:** `envelopeId` (Path param).

### Assinaturas e Arquivos
* **`GET` `/assinatura-open-api/envelope/{envelopeId}/signer/{signerId}/signature-link`**
  * **Uso:** Gerar e obter a URL do link de assinatura para enviar externamente ao signatário.
  * **Parâmetros:** `envelopeId` e `signerId` (Path params).
* **`GET` `/assinatura-open-api/files/envelope/{envelopeId}/files/download-signed-files`**
  * **Uso:** Baixar de forma consolidada todos os arquivos já assinados de um envelope.
  * **Parâmetros:** `envelopeId` (Path param).
* **`GET` `/assinatura-open-api/files/envelope/{envelopeId}/files/{fileId}/download`**
  * **Uso:** Baixar um arquivo do envelope antes da assinatura.
  * **Parâmetros:** `envelopeId` e `fileId` (Path params).
* **`POST` `/assinatura-open-api/files/envelope/{envelopeId}/adesao/files`**
  * **Uso:** Enviar arquivos para a modalidade "Adesão Eletrônica" no envelope gerado.
  * **Parâmetros:** `envelopeId` (Path param), Body (Multipart/form-data) contendo `files` (os arquivos físicos) e `adesaoDTO`.
* **`POST` `/assinatura-open-api/files/envelope/{envelopeId}/files`**
  * **Uso:** Enviar os arquivos PDFs para a modalidade padrão de "Assinatura Eletrônica/Digital".
  * **Parâmetros:** `envelopeId` (Path param), Body (Multipart/form-data) contendo `files`, `documentTypes`, `signaturePlaces`.
* **`GET` `/assinatura-open-api/files/envelope/file/{envelopeId}/list`**
  * **Uso:** Obter a lista de todos os arquivos vinculados a um envelope.
  * **Parâmetros:** `envelopeId` (Path param).

---

## 3. Rotas Disponíveis - Certisign V2

A API Certisign utiliza `token` ou `code` no cabeçalho e trabalha orientada a Documentos e Dossiês.

### Gestão de Documentos (Assinatura)
* **`POST` `/document/upload`**
  * **Uso:** Fazer upload dos bytes do arquivo temporariamente (Retorna um `uploadId`).
  * **Parâmetros Principais (Body):** `fileName` (nome do arquivo) e `bytes` (array numérico dos bytes do arquivo).
* **`POST` `/document/create`**
  * **Uso:** Submeter o documento (usando o `uploadId` gerado) configurando todo o fluxo de signatários (`signers`, `electronicSigners`, ordem, posições de assinatura, notificações).
  * **Parâmetros Principais (Body):** `typeId` (usar 1), objeto `document` (contendo o `uploadId`), `folderId` (Id do dossiê do associado), listas `signers` e `electronicSigners`, e `callback`.
* **`GET` `/document/listByStatus`**
  * **Uso:** Listar documentos filtrados por status em uma conta/dossiê.
  * **Parâmetros de Busca (Query):** `status` (ex: pendente), `dossierId`, `identifier` (CPF/CNPJ, por exemplo), `offset`, `max`.
* **`GET` `/document/package`**
  * **Uso:** Fazer download do Pacote final (arquivo ZIP contendo PDF assinado, manifesto e arquivo `.p7s`).
  * **Parâmetros (Query):** `key` (Chave do documento) e `includeOriginal` (booleano).
* **`DELETE` `/document/delete`**
  * **Uso:** Remover um documento do portal.
  * **Parâmetros (Query):** `id` (Id numérico do documento).
* **`POST` `/document/versionAdd`**
  * **Uso:** Adicionar uma nova versão a um documento existente.
  * **Parâmetros (Body):** `id` (do documento pai), objeto `upload` (info do novo arquivo com uploadId).
* **`POST` `/document/createBatch`**
  * **Uso:** Criar vários documentos em lote simultaneamente.
  * **Parâmetros (Body):** `documents` (Lista de objetos do tipo DocumentCreate).
* **`POST` `/document/reject`**
  * **Uso:** Sinalizar a rejeição do documento via API.
  * **Parâmetros (Body):** `documentId`, `reason` (motivo descritivo), `rejected` (booleano).
* **`GET` `/document/flowActions`**
  * **Uso:** Retornar em que estágio o fluxo do documento está parado (quem ainda precisa assinar).
  * **Parâmetros (Query):** `id` (Id numérico do documento).

### Outros Serviços Certisign
* **`POST` `/dossier/create`**
  * **Uso:** Criar um dossiê (pasta agrupador) de documentos. 
  * **Parâmetros (Body):** `name` (Nome do dossiê).
  * **Detalhe de Aplicação (Para Pendências):** O dossiê é muito útil para agrupar todos os documentos de um mesmo associado ou de uma mesma operação. Assim, é possível usar o endpoint `/document/listByStatus` passando o `dossierId` para buscar facilmente se existem assinaturas pendentes para aquele grupo de documentos.
* **`POST` `/signatureVerifier/fileEvaluation` e `/verifySignature`**
  * **Uso:** Submeter e verificar/validar assinaturas já embutidas em um documento PDF.
  * **Parâmetros (Body):** `signatureFileName` (UploadId do arquivo na nuvem) e flag `generateReport`.
* **`POST` `/personalDocument/identification`**
  * **Uso:** Enviar upload de imagens (frente e verso de CNH/RG) para extração de identificação.
  * **Parâmetros (Body):** `documentFrontId`, `documentBackId` (Ambos oriundos do /document/upload) e `typeOfDocument`.

---

## 4. Como Consultar Pendências por Associado (Dúvida do Gestor)

Para atender a necessidade de "puxar as pendências do associado" no momento em que ele for assinar um documento (mostrando tudo o que ele tem pendente), a abordagem recomendada é:

**Se usar o PAS:**
Utilize a rota **`GET` `/assinatura-open-api/v2/envelope/search`**.
* **Como fazer:** Você pode passar os parâmetros de busca `cpfCnpj` do associado e `status=ASSINATURA_PENDENTE` (ou `AGUARDANDO_ENVIO` conforme o momento).
* **Resultado:** A API retornará todos os envelopes que aquele associado precisa assinar e que ainda estão pendentes.

**Se usar a Certisign:**
A Certisign trabalha muito bem com Dossiês para esse tipo de organização.
1. Na geração dos documentos, você agrupa tudo do associado num Dossiê (**`POST` `/dossier/create`**).
2. Para consultar, utilize a rota **`GET` `/document/listByStatus`**.
* **Como fazer:** Informe o `dossierId` (referente ao associado ou operação) e o parâmetro `status` indicando documentos pendentes.
* **Resultado:** O sistema listará os documentos contidos naquele Dossiê que aguardam finalização, podendo apresentar essa lista de pendências para o associado no momento em que ele estiver na agência ou for assinar.

---

## 4. Estrutura Sugerida para o Banco de Dados

Para suportar essas APIs e garantir que o Robô saiba monitorar os pendentes e armazenar corretamente o andamento, será necessário o mínimo destas tabelas/entidades:

1. **Pessoa / Signatário (`signatarios`)**
   * Deve ser checado antes da criação; caso não exista, realiza o insert.
   * Campos: `id`, `cpf_cnpj`, `nome`, `email`, `telefone`, `data_cadastro`
2. **Processo Origem (`processos`)**
   * Guarda o controle da tarefa do Fluid.
   * Campos: `id`, `num_processo`, `nome_processo`, `processo_fluid_id`, `data_recebimento`, `status_automacao`
3. **Envelope / Dossiê de Assinatura (`envelopes`)**
   * Agrupa todo um fluxo para uma ou mais pessoas.
   * Campos: `id`, `processo_id`, `plataforma` (Enum: PAS ou CERTISIGN), `id_plataforma_externo` (Guarda o envelopeId ou documentId), `status` (Ex: Em Preenchimento, Aguardando Assinaturas, Finalizado), `data_criacao`
4. **Documentos do Envelope (`documentos`)**
   * Quais arquivos estão em cada envelope.
   * Campos: `id`, `envelope_id`, `hash_origem` (Fluig), `nome_arquivo`, `id_tipo_doc`, `id_externo_arquivo` (Para Certisign é o UploadId, para o PAS é o id retornado no envio), `assinado` (Booleano)
5. **Acompanhamento de Signatários do Envelope (`envelope_signatarios`)**
   * Liga as pessoas aos envelopes para controle individual (importante se cada um assinar em um momento ou canal distinto).
   * Campos: `id`, `envelope_id`, `signatario_id`, `papel_assinatura`, `ordem_assinatura`, `tipo_assinatura` (Eletrônica/Digital), `canal_comunicacao` (Whats/Email), `link_assinatura_gerado`, `status_assinatura`
