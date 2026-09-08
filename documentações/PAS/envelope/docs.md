===============================================================================
DOCUMENTAÇÃO DE INTEGRAÇÃO - OPEN API ASSINATURA
===============================================================================

1. ESTRUTURA DE PASTAS DO PROJETO (REFERÊNCIA)
-------------------------------------------------------------------------------
Com base no seu ambiente de desenvolvimento, a organização dos arquivos de 
documentação segue este padrão:

DOCJOURNEY/
│
└── docs/
    ├── Certign/
    └── PAS/
        ├── Imagens/
        │   ├── Config/
        │   └── Envelope/
        │       ├── Baixar os arquivos assinados do envelope.md
        │       ├── Buscar envelope por id V2.md
        │       ├── Buscar envelope V2.md
        │       ├── Clonar envelope V2.md
        │       ├── Criar envelope V2.md
        │       ├── Deletar envelope V2.md
        │       └── Obter link de assinatura.md
        └── docs.md


2. CABEÇALHOS PADRÃO (HEADERS OBRIGATÓRIOS)
-------------------------------------------------------------------------------
A grande maioria das requisições descritas abaixo exige o envio dos seguintes 
parâmetros no Header:

* x-api-coop-user: Usuário operacional da cooperativa (String) — Obrigatório
* x-api-coop-numero: Número identificador da cooperativa (String) — Obrigatório
* x-api-coop-aplicacao: Identificador da aplicação originária (String) — Obrigatório
* Authorization: Token Bearer para autenticação do serviço (String) — Obrigatório


3. DETALHAMENTO DOS ENDPOINTS
-------------------------------------------------------------------------------

3.1. Criar Envelope V2
-------------------------------------------------------------------------------
Cria um novo envelope digital para assinaturas de documentos.

Rota: /assinatura-open-api/v2/envelope/create
Método: POST
Content-Type: application/json

Exemplo de Requisição (cURL):
curl 'https://mtls-api-coop.sicredi.com.br/assinatura-open-api/v2/envelope/create' \
--request POST \
--header 'x-api-coop-user: YOUR_USER' \
--header 'x-api-coop-numero: YOUR_COOP_NUMBER' \
--header 'x-api-coop-aplicacao: YOUR_APP_ID' \
--header 'Authorization: Bearer YOUR_TOKEN' \
--header 'Content-Type: application/json' \
--data '{
  "coop": "",
  "tags": [""],
  "title": "",
  "agency": "",
  "account": "",
  "comment": "",
  "signers": [
    {
      "id": "",
      "cpf": "",
      "ddi": 1,
      "cnpj": "",
      "name": "",
      "email": "",
      "phone": "",
      "title": [""],
      "account": {
        "account": "",
        "cooperative": ""
      },
      "flowRole": "ASSINAR",
      "signatureType": "ELETRONIC",
      "secondAuthFactor": true,
      "authenticationMethods": [
        {
          "id": "",
          "value": "",
          "method": ""
        }
      ]
    }
  ],
  "provider": "",
  "idTemplate": "",
  "restricted": [""],
  "notificationEmails": [""],
  "allowSignatureOrder": true,
  "valueElectronicChannel": 1,
  "documentSignaturePattern": "PADES",
  "hasValueElectronicChannel": true,
  "descriptionElectronicChannel": ""
}'

Resposta Esperada (201 Created):
{
  "id": "string",
  "coop": "string",
  "logs": [
    {
      "ref": "string",
      "tags": ["string"],
      "logType": "INFO",
      "exception": "string",
      "timestamp": "2026-06-11T18:27:34.064Z",
      "logDescription": "string"
    }
  ],
  "tags": ["string"],
  "title": "string",
  "valid": true,
  "agency": "string",
  "status": "EM_PREENCHIMENTO",
  "account": "string",
  "comment": "string",
  "context": "string",
  "signers": [
    {
      "id": "string",
      "cpf": "string",
      "ddi": 1,
      "name": "string",
      "cnpjs": ["string"],
      "email": "string",
      "phone": "string",
      "title": ["string"],
      "accounts": [
        {
          "account": "string",
          "cooperative": "string"
        }
      ],
      "flowRole": "ASSINAR",
      "signatureType": "ELETRONIC",
      "allFilesSigned": true,
      "phoneCountryCode": "string",
      "secondAuthFactor": true,
      "signatureRequired": true,
      "providerFileIdSigned": ["string"],
      "authenticationMethods": [
        {
          "id": "string",
          "value": "string",
          "method": "string"
        }
      ]
    }
  ],
  "provider": "string",
  "bffOrigin": true,
  "idTemplate": "string",
  "ldapSender": "string",
  "restricted": ["string"],
  "ldapCreator": "string",
  "originSystem": "string",
  "sendDateTime": "2026-06-11T18:27:34.064Z",
  "sentProvider": "string",
  "templateFiles": [
    {
      "fileName": "string",
      "ttdDocumentType": "string"
    }
  ],
  "createdDateTime": "2026-06-11T18:27:34.064Z",
  "finishedDateTime": "2026-06-11T18:27:34.064Z",
  "inPersonSignature": true,
  "oneClickSignature": true,
  "notificationEmails": ["string"],
  "validationMessages": ["string"],
  "allowSignatureOrder": true,
  "gedDocumentFolderId": 1,
  "envelopeIdOfProvider": "string",
  "valueElectronicChannel": 1,
  "documentSignaturePattern": "PADES",
  "hasValueElectronicChannel": true,
  "associateElectronicChannelId": "string",
  "descriptionElectronicChannel": "string",
  "dateTimeElectronicChannelSigned": "2026-06-11T18:27:34.064Z"
}


3.2. Clonar Envelope V2
-------------------------------------------------------------------------------
Clona a estrutura de um envelope existente gerando uma nova instância para 
preenchimento.

Rota: /assinatura-open-api/v2/envelope/{envelopeId}/clone
Método: POST
Content-Type: application/json

Parâmetros de URL (Path Parameters):
* envelopeId (String): Identificador único do envelope a ser clonado.

Exemplo de Requisição (cURL):
curl 'https://mtls-api-coop.sicredi.com.br/assinatura-open-api/v2/envelope/{envelopeId}/clone' \
--request POST \
--header 'x-api-coop-user: YOUR_USER' \
--header 'x-api-coop-numero: YOUR_COOP_NUMBER' \
--header 'x-api-coop-aplicacao: YOUR_APP_ID' \
--header 'Authorization: Bearer YOUR_TOKEN' \
--header 'Content-Type: application/json' \
--data '{
  "coop": "",
  "agency": ""
}'

Resposta Esperada (201 Created):
Retorna o novo objeto do envelope clonado no mesmo formato estrutural da 
criação (ver item 3.1).


3.3. Buscar Envelope por ID V2
-------------------------------------------------------------------------------
Recupera os detalhes completos de um determinado envelope.

Rota: /assinatura-open-api/v2/envelope/{id}
Método: GET

Parâmetros de URL (Path Parameters):
* id (String): Identificador único do envelope procurado.

Exemplo de Requisição (cURL):
curl 'https://mtls-api-coop.sicredi.com.br/assinatura-open-api/v2/envelope/{id}' \
--header 'x-api-coop-user: YOUR_USER' \
--header 'x-api-coop-numero: YOUR_COOP_NUMBER' \
--header 'x-api-coop-aplicacao: YOUR_APP_ID' \
--header 'Authorization: Bearer YOUR_TOKEN'

Resposta Esperada (200 OK):
Retorna o objeto JSON detalhado do envelope (idêntico à estrutura encontrada 
no retorno do item 3.1).


3.4. Buscar Envelope V2 (Filtros Avançados / Paginação)
-------------------------------------------------------------------------------
Pesquisa por múltiplos envelopes na base de dados utilizando paginação e 
filtros detalhados.

Rota: /assinatura-open-api/v2/envelope/search
Método: GET

Parâmetros de Consulta (Query Parameters):
* envelopeId (String) - Opcional
* status (Array[String]): Valores possíveis: EM_PREENCHIMENTO, 
  AGUARDANDO_ENVIO, AGUARDANDO_REENVIO, FALHA_NO_ENVIO, ASSINATURA_PENDENTE.
* account (String) - Opcional
* signerName (String) - Opcional
* sentProvider (String) - Opcional
* tag (String) - Opcional
* title (String) - Opcional
* cpfCnpj (String) - Opcional
* createdDateStart / createdDateEnd (String - Formato ISO 8601 ex: 2017-07-21)
* sendDateStart / sendDateEnd (String - Formato ISO 8601)
* sortField (String/Enum): id, firstSignerName, createdDateTime, status, 
  firstSignerAccount, ldapCreator, sentProvider.
* direction (String/Enum): ASC ou DESC.
* page (Integer - Padrão 32-bit): Número da página.
* size (Integer - Padrão 32-bit): Quantidade de registros por página.

Exemplo de Requisição (cURL):
curl 'https://mtls-api-coop.sicredi.com.br/assinatura-open-api/v2/envelope/search?envelopeId=&status=EM_PREENCHIMENTO&account=&signerName=&sentProvider=&tag=&title=&cpfCnpj=&createdDateStart=&createdDateEnd=&sendDateStart=&sendDateEnd=&sortField=id&direction=ASC&page=1&size=1' \
--header 'x-api-coop-user: YOUR_USER' \
--header 'x-api-coop-numero: YOUR_COOP_NUMBER' \
--header 'x-api-coop-aplicacao: YOUR_APP_ID' \
--header 'Authorization: Bearer YOUR_TOKEN'

Resposta Esperada (200 OK):
{
  "last": true,
  "size": 1,
  "sort": {
    "empty": true,
    "sorted": true,
    "unsorted": true
  },
  "empty": true,
  "first": true,
  "number": 1,
  "content": [
    {
      "coop": "string",
      "tags": ["string"],
      "owner": "string",
      "title": "string",
      "status": "EM_PREENCHIMENTO",
      "account": "string",
      "signers": ["string"],
      "provider": "string",
      "bffOrigin": true,
      "envelopeId": "string",
      "createdDate": "2026-06-11T18:27:34.064Z",
      "signerCount": 1,
      "sentProvider": "string",
      "hasAccessByRestriction": true
    }
  ],
  "pageable": {
    "sort": {
      "empty": true,
      "sorted": true,
      "unsorted": true
    },
    "paged": true,
    "offset": 1,
    "unpaged": true,
    "pageSize": 1,
    "pageNumber": 1
  },
  "totalPages": 1,
  "totalElements": 1,
  "numberOfElements": 1
}


3.5. Deletar Envelope V2
-------------------------------------------------------------------------------
Remove de forma lógica ou física um envelope especificado.

Rota: /assinatura-open-api/v2/envelope/{envelopeId}
Método: DELETE

Parâmetros de URL (Path Parameters):
* envelopeId (String): Código do envelope a ser removido.

Exemplo de Requisição (cURL):
curl 'https://mtls-api-coop.sicredi.com.br/assinatura-open-api/v2/envelope/{envelopeId}' \
--request DELETE \
--header 'x-api-coop-user: YOUR_USER' \
--header 'x-api-coop-numero: YOUR_COOP_NUMBER' \
--header 'x-api-coop-aplicacao: YOUR_APP_ID' \
--header 'Authorization: Bearer YOUR_TOKEN'

Resposta Esperada (204 No Content):
Sem corpo na resposta. Deleção executada com sucesso.


3.6. Obter Link de Assinatura
-------------------------------------------------------------------------------
Gera o endereço eletrônico (URL) externo para que um participante possa 
realizar a assinatura digital no documento.

Rota: /assinatura-open-api/envelope/{envelopeId}/signer/{signerId}/signature-link
Método: GET

Parâmetros de URL (Path Parameters):
* envelopeId (String): ID do envelope do fluxo.
* signerId (String): ID correspondente ao signatário específico.

Exemplo de Requisição (cURL):
curl 'https://mtls-api-coop.sicredi.com.br/assinatura-open-api/envelope/{envelopeId}/signer/{signerId}/signature-link' \
--header 'x-api-coop-user: YOUR_USER' \
--header 'x-api-coop-numero: YOUR_COOP_NUMBER' \
--header 'x-api-coop-aplicacao: YOUR_APP_ID' \
--header 'Authorization: Bearer YOUR_TOKEN'

Resposta Esperada (200 OK):
{
  "link": "string",
  "signerId": "string",
  "envelopeId": "string"
}


3.7. Baixar os Arquivos Assinados do Envelope
-------------------------------------------------------------------------------
Realiza o download consolidado dos documentos internos que já foram assinados 
pelas partes interessadas.

Rota: /assinatura-open-api/files/envelope/{envelopeId}/files/download-signed-files
Método: GET

Parâmetros de URL (Path Parameters):
* envelopeId (String): ID único do envelope associado aos arquivos.

Exemplo de Requisição (cURL):
curl 'https://mtls-api-coop.sicredi.com.br/assinatura-open-api/files/envelope/{envelopeId}/files/download-signed-files' \
--header 'x-api-coop-user: YOUR_USER' \
--header 'x-api-coop-numero: YOUR_COOP_NUMBER' \
--header 'x-api-coop-aplicacao: YOUR_APP_ID' \
--header 'Authorization: Bearer YOUR_TOKEN'

Resposta Esperada (200 OK):
Tipo de Retorno: String (Geralmente contendo o arquivo binário codificado em 
Base64 ou a URL/Stream direta para download).


4. TABELA GERAL DE CÓDIGOS DE RESPOSTA (STATUS HTTP)
-------------------------------------------------------------------------------

+--------+---------------+----------------------------------------------------+
| Código | Descrição     | Contexto de Aplicação                              |
+--------+---------------+----------------------------------------------------+
| 200    | OK            | Sucesso em consultas (GET), geração de links e     |
|        |               | downloads.                                         |
+--------+---------------+----------------------------------------------------+
| 201    | Created       | Sucesso na criação ou clonagem de novos Envelopes  |
|        |               | (POST).                                            |
+--------+---------------+----------------------------------------------------+
| 204    | No Content    | Deleção concluída com sucesso (DELETE).            |
+--------+---------------+----------------------------------------------------+
| 400    | Bad Request   | Filtros inválidos, range de datas superior a 90    |
|        |               | dias ou busca por nome de assinante com menos de 3 |
|        |               | caracteres.                                        |
+--------+---------------+----------------------------------------------------+
| 403    | Forbidden     | O usuário operacional informado não tem as         |
|        |               | permissões necessárias para ler, criar ou          |
|        |               | atualizar o envelope.                              |
+--------+---------------+----------------------------------------------------+
| 404    | Not Found     | O identificador do envelope (envelopeId) ou o tipo  |
|        |               | de documento associado não foi localizado.         |
+--------+---------------+----------------------------------------------------+