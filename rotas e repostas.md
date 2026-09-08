# Documentação da API de Assinatura Eletrônica (Open API v2)

Esta documentação descreve as operações de gerenciamento de envelopes de assinatura eletrônica e digital.

---

## 1. Criar Envelope

Cria uma nova instância de envelope de assinatura definindo signatários, provedor e regras de autenticação.

- **Método HTTP:** `POST`
- **Endpoint:** `{{baseUrl}}/assinatura-open-api/v2/envelope/create`
- **Headers:**
  - `Content-Type: application/json`

### Requisição (Payload)

#### Exemplo de Body
```json
{
  "coop": "0703",
  "tags": [
    "TESTE RPA"
  ],
  "title": "Teste RPA",
  "agency": "11",
  "account": "1111111111",
  "comment": "ALGUMA COISA",
  "signers": [
    {
      "cpf": "11111111111",
      "ddi": 55,
      "name": "Pedro Henrique Lopes",
      "email": "Pedro_HLOPES@sicredi.com.br",
      "phone": "42999843189",
      "title": [
        "teste signatário"
      ],
      "flowRole": "ASSINAR",
      "signatureType": "ELETRONIC",
      "secondAuthFactor": true,
      "authenticationMethods": [
        {
          "method": "WHATSAPP"
        }
      ]
    },
    {
      "cpf": "11158072937",
      "name": "Pedro Henrique Lopes",
      "email": "lopesp5151@gmail.com",
      "title": [
        "teste signatário"
      ],
      "ddi": 55,
      "phone": "42999843189",
      "flowRole": "ASSINAR",
      "signatureType": "DIGITAL"
    }
  ],
  "provider": "CERTISIGN",
  "notificationEmails": [
    "higor_custodio@sicredi.com.br"
  ],
  "allowSignatureOrder": true,
  "documentSignaturePattern": "PADES",
  "hasValueElectronicChannel": false
}


Campo,Tipo,Descrição
coop,String,"Código da cooperativa emissora (ex.: ""0703"")."
agency,String,Código da agência.
account,String,Conta de relacionamento vinculada.
title,String,Título identificador do envelope.
comment,String,Observação ou descrição do propósito do envelope.
tags,Array[String],Lista de identificadores/etiquetas para rastreio e indexação.
provider,String,"Provedor de assinatura homologado (ex.: ""CERTISIGN"")."
notificationEmails,Array[String],Lista de e-mails que receberão alertas sobre eventos do envelope.
allowSignatureOrder,Boolean,"Se true, impõe que as assinaturas sigam a ordem definida na lista."
documentSignaturePattern,String,"Padrão técnico de assinatura adotado (ex.: ""PADES"")."
hasValueElectronicChannel,Boolean,Sinalizador de canal eletrônico transacional/com valor financeiro.
signers,Array[Object],Lista de signatários participantes do fluxo.


Campo,Tipo,Descrição
cpf,String,Cadastro de Pessoa Física do signatário (apenas números).
name,String,Nome completo do signatário.
email,String,Endereço de e-mail do signatário.
ddi,Integer,Código de discagem direta internacional (ex.: 55).
phone,String,Número do telefone celular com DDD (apenas números).
title,Array[String],Qualificação/papel descritivo do signatário no documento.
flowRole,String,"Ação esperada no fluxo (ex.: ""ASSINAR"")."
signatureType,String,"Tipo da assinatura: ""ELETRONIC"" (eletrônica) ou ""DIGITAL"" (ICP-Brasil)."
secondAuthFactor,Boolean,Habilita autenticação em dois fatores (2FA).
authenticationMethods,Array[Object],"Canais de entrega do fator secundário (ex.: [{""method"": ""WHATSAPP""}])."

reposta 200

{
  "id": "6a9ab9fc7b5cfab6d0db164d",
  "ldapSender": null,
  "originSystem": "API_Python",
  "ldapCreator": "pedro_hlopes",
  "bffOrigin": false,
  "comment": "TESTE DE AUTOMAÇÃO",
  "allowSignatureOrder": true,
  "coop": "0703",
  "agency": "01",
  "account": "",
  "context": "cas;central_pr;sureg_planalto;sicredi_terceiro_planalto",
  "valid": false,
  "provider": "CERTISIGN",
  "sentProvider": null,
  "envelopeIdOfProvider": null,
  "validationMessages": null,
  "createdDateTime": "2026-09-04T09:30:51.57798551",
  "sendDateTime": null,
  "finishedDateTime": null,
  "signatureFinalizedDateTime": null,
  "status": "EM_PREENCHIMENTO",
  "hasValueElectronicChannel": false,
  "valueElectronicChannel": null,
  "title": "Teste RPA",
  "descriptionElectronicChannel": null,
  "associateElectronicChannelId": null,
  "dateTimeElectronicChannelSigned": null,
  "gedDocumentFolderId": null,
  "signers": [
    {
      "id": "11251288-2bd7-4367-8d3b-085f6cc34853",
      "signatarioIdDoProvedor": null,
      "signerStatus": "ENVIO_DE_LINK_PENDENTE",
      "cnpjs": [],
      "cpf": "08489951985",
      "name": "Debora Yumi Pelegrini",
      "phone": "42999400038",
      "ddi": 55,
      "phoneCountryCode": "BR",
      "email": "yumi.pelegrini@gmail.com",
      "title": [
        "teste signatário automação"
      ],
      "accounts": [],
      "flowRole": "ASSINAR",
      "signatureRequired": false,
      "allFilesSigned": false,
      "providerFileIdSigned": [],
      "signatureType": "DIGITAL",
      "secondAuthFactor": false,
      "authenticationMethods": [],
      "oneClickSignature": false,
      "formaAssinatura": "REMOTA",
      "metodoEnvioLink": "EMAIL",
      "assinaturaPresencial": null,
      "signatoriesEvidences": []
    }
  ],
  "tags": [
    "TESTE RPA"
  ],
  "notificationEmails": [
    "pedro_hlopes@sicredi.com.br"
  ],
  "logs": [],
  "restricted": [],
  "idTemplate": null,
  "idCategoria": null,
  "templateFiles": [],
  "documentSignaturePattern": "PADES"
}

Dicionário de Dados - Retorno


Campo,Tipo,Descrição
id,String,Identificador exclusivo do envelope criado.
originSystem,String,"Sistema emissor da requisição (ex.: ""API_Python"")."
ldapCreator,String,Usuário de rede/sistema responsável pela criação.
status,String,"Situação atual do ciclo de vida do envelope (ex.: ""EM_PREENCHIMENTO"")."
createdDateTime,String (ISO 8601),Data e hora exata da criação do envelope.
context,String,Hierarquia organizacional associada à criação.
signers[].id,UUID,Identificador exclusivo do signatário dentro deste envelope.
signers[].signerStatus,String,"Estado do signatário no fluxo (ex.: ""ENVIO_DE_LINK_PENDENTE"")."
signers[].formaAssinatura,String,"Modalidade de assinatura atribuída (ex.: ""REMOTA"")."
signers[].metodoEnvioLink,String,"Canal padrão configurado para envio do link (ex.: ""EMAIL"")."



2. Deletar Envelope
Cancela ou exclui um envelope existente na base a partir de seu identificador.

Método HTTP: DELETE

Endpoint: {{baseUrl}}/assinatura-open-api/v2/envelope/{{id_doc_criado}}

Parâmetros de URL (Path Parameters)

Parâmetro,Tipo,Obrigatório,Descrição
id_doc_criado,String,Sim,Identificador do envelope obtido no retorno da criação (ex.: 6a9ab9fc7b5cfab6d0db164d).


3. trocar assinatura

# Documentação Técnica: Atualizar Envelope (PUT)

Endpoint para atualizar dados cadastrais, signatários ou métodos de autenticação de um envelope existente.

- **Método HTTP:** `PUT`
- **Endpoint:** `{{baseUrl}}/assinatura-open-api/v2/envelope`
- **URL Base mTLS (Produção):** `https://mtls-api-coop.sicredi.com.br/assinatura-open-api/v2/envelope`
- **Headers:**
  - `Content-Type: application/json`

---

## Requisição (Payload)

### Exemplo de cURL
```bash
curl [https://mtls-api-coop.sicredi.com.br/assinatura-open-api/v2/envelope](https://mtls-api-coop.sicredi.com.br/assinatura-open-api/v2/envelope) \
  --request PUT \
  --header 'Content-Type: application/json' \
  --data '{
    "id": "6a9ab9fc7b5cfab6d0db164d",
    "tags": [
      "TESTE RPA"
    ],
    "comment": "ALTERAÇÃO DE SIGNATÁRIO / CANAL",
    "signers": [
      {
        "id": "11251288-2bd7-4367-8d3b-085f6cc34853",
        "phone": "42999843189",
        "ddi": 55,
        "email": "novo_email@sicredi.com.br",
        "secondAuthFactor": true,
        "authenticationMethods": [
          {
            "method": "WHATSAPP"
          }
        ]
      }
    ]
  }'