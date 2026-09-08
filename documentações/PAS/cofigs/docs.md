# Documentação de API: Busca Parâmetros de Configuração

Esta API é responsável por buscar os parâmetros de configuração do PAS (Processo de Assinatura) por código de cooperativa. Caso ainda não existam parâmetros cadastrados para a cooperativa informada, o sistema cria e retorna automaticamente os parâmetros utilizando valores padrões.

## Detalhes da Requisição

* **Método HTTP:** `GET`
* **Rota:** `/assinatura-open-api/config/coop-parameters/{coop}`
* **URL Base (Exemplo):** `https://mtls-api-coop.sicredi.com.br`

---

## Parâmetros da Requisição

### Path Parameters (Parâmetros de Rota)

| Parâmetro | Tipo | Obrigatório | Descrição |
| :--- | :--- | :--- | :--- |
| `coop` | `string` | **Sim** | Código de identificação da cooperativa. |

### Headers (Cabeçalhos)

| Cabeçalho | Tipo | Obrigatório | Descrição |
| :--- | :--- | :--- | :--- |
| `x-api-coop-user` | `string` | **Sim** | Usuário da cooperativa realizando a requisição. |
| `x-api-coop-numero` | `string` | **Sim** | Número identificador da cooperativa. |
| `x-api-coop-aplicacao` | `string` | **Sim** | Identificador ou nome da aplicação que está consumindo a API. |
| `Authorization` | `string` | **Sim** | Token de autenticação (Bearer ou similar). |
| `userLogged` | `string` | Não | Identificação do usuário logado na sessão (opcional). |
| `applicationId` | `string` | Não | ID único da aplicação cliente (opcional). |
| `applicationSecret` | `string` | Não | Secret da aplicação cliente (opcional). |

---

## Exemplo de Chamada (cURL)

```bash
curl 'https://mtls-api-coop.sicredi.com.br/assinatura-open-api/config/coop-parameters/{coop}' \
  --header 'x-api-coop-user: ' \
  --header 'x-api-coop-numero: ' \
  --header 'x-api-coop-aplicacao: ' \
  --header 'Authorization: '
```

---

## Códigos de Retorno (Responses)

| Código | Descrição |
| :--- | :--- |
| **200 OK** | Retorna os parâmetros de configuração encontrados ou criados por padrão. |
| **400 Bad Request** | Existem métodos de autenticação que não estão disponíveis nos provedores de assinatura selecionados. |

---

## Exemplo de Resposta (Sucesso - 200 OK)

Abaixo está a estrutura completa do JSON retornado no corpo da resposta quando a requisição é bem-sucedida:

```json
{
  "coop": "string",
  "context": "string",
  "createdDateTime": "2026-06-11T18:27:34.064Z",
  "signatureProviders": [
    "string"
  ],
  "lastModificationDate": "2026-06-11T18:27:34.064Z",
  "linkExpirationInDays": 1,
  "signatureLinkMethods": [
    "EMAIL"
  ],
  "authenticationFactors": [
    {
      "id": "string",
      "webMask": {
        "stepMasks": [
          {
            "mask": "string",
            "stepOrder": 1,
            "comparatorValue": "string",
            "operatorMaskStepType": "EQUALS"
          }
        ],
        "clearValue": "string"
      },
      "typeValue": "EMAIL",
      "matchRegex": [
        "string"
      ],
      "methodName": "string",
      "description": "string",
      "displayName": "string",
      "valuedField": true
    }
  ],
  "associatedDataOverwriting": true,
  "secondAuthFactorRequired": true,
  "visibilityFrontLevelLink": "QR_CODE_AND_LINK",
  "userEnvelopeReadPermission": "COOP"
}
```