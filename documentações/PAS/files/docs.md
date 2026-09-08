# Documentação de API - Módulo de Arquivos e Envelopes

Este documento centraliza a documentação de 4 rotas relacionadas ao gerenciamento de arquivos e envelopes do Processo de Assinatura (PAS).

---

## 1. Baixar os arquivos do envelope (antes da assinatura)

Faz o download do arquivo de um envelope.

### Detalhes da Requisição
* **Método HTTP:** `GET`
* **Rota:** `/assinatura-open-api/files/envelope/{envelopeId}/files/{fileId}/download`

### Path Parameters
| Parâmetro | Tipo | Obrigatório |
| :--- | :--- | :--- |
| `envelopeId` | `string` | Sim |
| `fileId` | `string` | Sim |

### Headers
| Cabeçalho | Tipo | Obrigatório |
| :--- | :--- | :--- |
| `userLogged` | `string` | Não |
| `applicationId` | `string` | Não |
| `applicationSecret` | `string` | Não |
| `x-api-coop-user` | `string` | Sim |
| `x-api-coop-numero` | `string` | Sim |
| `x-api-coop-aplicacao` | `string` | Sim |
| `Authorization` | `string` | Sim |

### Responses
* **404 Not Found:** O registro finalizou em estado de erro. Logo, o arquivo não foi salvo.

---

## 2. Envio dos arquivos para Adesão Eletrônica

Cria a entidade com as informações do arquivo e envia o mesmo para ser salvo no s3.

### Detalhes da Requisição
* **Método HTTP:** `POST`
* **Rota:** `/assinatura-open-api/files/envelope/{envelopeId}/adesao/files`
* **Content-Type:** `multipart/form-data`

### Path Parameters
| Parâmetro | Tipo | Obrigatório |
| :--- | :--- | :--- |
| `envelopeId` | `string` | Sim |

### Headers
| Cabeçalho | Tipo | Obrigatório |
| :--- | :--- | :--- |
| `userLogged` | `string` | Não |
| `applicationId` | `string` | Não |
| `applicationSecret` | `string` | Não |
| `x-api-coop-user` | `string` | Sim |
| `x-api-coop-numero` | `string` | Sim |
| `x-api-coop-aplicacao` | `string` | Sim |
| `Authorization` | `string` | Sim |

### Body (multipart/form-data)
* `adesaoDTO`: objeto (required)
* `labels`: array string
* `files`: array string (required)

### Exemplo de Resposta (201 Criado com sucesso)
```json
[
  {
    "id": "string",
    "name": "string",
    "size": 1,
    "status": "UPLOAD_COMPLETED",
    "message": "string",
    "attachment": true,
    "envelopeId": "string",
    "createdDate": "2026-06-11T18:27:34.064Z",
    "documentType": "string",
    "idOfProvider": "string",
    "gedDocumentId": 1,
    "adesaoFileName": "string",
    "gedDocumentCode": "string",
    "signaturePlaces": [
      {
        "places": [
          {
            "dpi": 1,
            "page": 1,
            "metric": "MM",
            "topOffset": 1,
            "leftOffset": 1
          }
        ],
        "signerId": "string"
      }
    ],
    "localFileRemoved": true,
    "uploadSuccessful": true
  }
]
```

---

## 3. Envio dos arquivos para Assinatura Eletrônica/Digital

Cria a entidade com as informações do arquivo e envia o mesmo para ser salvo no s3.

### Detalhes da Requisição
* **Método HTTP:** `POST`
* **Rota:** `/assinatura-open-api/files/envelope/{envelopeId}/files`
* **Content-Type:** `multipart/form-data`

### Path Parameters
| Parâmetro | Tipo | Obrigatório |
| :--- | :--- | :--- |
| `envelopeId` | `string` | Sim |

### Body (multipart/form-data)
* `files`: array string (required)
* `documentTypes`: object
* `signaturePlaces`: object

### Exemplo de Resposta (201 Criado com sucesso)
```json
[
  {
    "id": "string",
    "name": "string",
    "size": 1,
    "status": "UPLOAD_COMPLETED",
    "message": "string",
    "attachment": true,
    "envelopeId": "string",
    "createdDate": "2026-06-11T18:27:34.064Z",
    "documentType": "string",
    "idOfProvider": "string",
    "gedDocumentId": 1,
    "adesaoFileName": "string",
    "gedDocumentCode": "string",
    "signaturePlaces": [
      {
        "places": [
          {
            "dpi": 1,
            "page": 1,
            "metric": "MM",
            "topOffset": 1,
            "leftOffset": 1
          }
        ],
        "signerId": "string"
      }
    ],
    "localFileRemoved": true,
    "uploadSuccessful": true
  }
]
```

---

## 4. Obter os arquivos do envelope (antes da assinatura)

### Detalhes da Requisição
* **Método HTTP:** `GET`
* **Rota:** `/assinatura-open-api/files/envelope/file/{envelopeId}/list`

### Path Parameters
| Parâmetro | Tipo | Obrigatório |
| :--- | :--- | :--- |
| `envelopeId` | `string` | Sim |

### Exemplo de Resposta (200 OK)
```json
[
  {
    "id": "string",
    "name": "string",
    "size": 1,
    "status": "UPLOAD_COMPLETED",
    "message": "string",
    "attachment": true,
    "envelopeId": "string",
    "createdDate": "2026-06-11T18:27:34.064Z",
    "documentType": "string",
    "idOfProvider": "string",
    "gedDocumentId": 1,
    "adesaoFileName": "string",
    "gedDocumentCode": "string",
    "signaturePlaces": [
      {
        "places": [
          {
            "dpi": 1,
            "page": 1,
            "metric": "MM",
            "topOffset": 1,
            "leftOffset": 1
          }
        ],
        "signerId": "string"
      }
    ],
    "localFileRemoved": true,
    "uploadSuccessful": true
  }
]
```