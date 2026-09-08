# Documentação de API: Buscar Tipos de Documento Relacionados (Apenas GED)

Esta rota realiza a pesquisa de tipos de documento específicos do PDS que estão relacionados apenas ao GED. A pesquisa ignora maiúsculas/minúsculas (case-insensitive) e acentuação no parâmetro de busca.

## Detalhes da Requisição

* **Método HTTP:** `GET`
* **Rota:** `/assinatura-open-api/pds-document-type/find/related-ged-only`
* **URL Base (Exemplo):** `https://mtls-api-coop.sicredi.com.br`

---

## Parâmetros da Requisição

### Query Parameters (Parâmetros de URL)

| Parâmetro | Tipo | Obrigatório | Padrão | Descrição |
| :--- | :--- | :--- | :--- | :--- |
| `name` | `string` | Não | `""` | Nome ou termo de busca para filtrar os tipos de documento. |

### Headers (Cabeçalhos)

| Cabeçalho | Tipo | Obrigatório | Descrição |
| :--- | :--- | :--- | :--- |
| `userLogged` | `string` | **Sim** | Identificação do usuário logado na sessão. |
| `x-api-coop-user` | `string` | **Sim** | Usuário da cooperativa realizando a requisição. |
| `x-api-coop-numero` | `string` | **Sim** | Número identificador da cooperativa. |
| `x-api-coop-aplicacao` | `string` | **Sim** | Identificador ou nome da aplicação que está consumindo a API. |
| `Authorization` | `string` | **Sim** | Token de autenticação (Bearer ou similar). |

---

## Exemplo de Chamada (cURL)

```bash
curl 'https://mtls-api-coop.sicredi.com.br/assinatura-open-api/pds-document-type/find/related-ged-only?name=' \
  --header 'x-api-coop-user: ' \
  --header 'x-api-coop-numero: ' \
  --header 'x-api-coop-aplicacao: ' \
  --header 'Authorization: '
```

---

## Códigos de Retorno (Responses)

| Código | Descrição |
| :--- | :--- |
| **200 OK** | Sucesso. Retorna uma lista de tipos de documento encontrados. |

---

## Exemplo de Resposta (Sucesso - 200 OK)

Abaixo está a estrutura da lista JSON retornada no corpo da resposta:

```json
[
  {
    "id": 1,
    "name": "string"
  }
]
```