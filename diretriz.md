# Prompt para Modelagem de Banco de Dados: Orquestrador de Assinaturas

**Objetivo:** Gerar um modelo Entidade-Relacionamento (Mermaid.js) e o script DDL (PostgreSQL) para um sistema de gestão de assinaturas eletrônicas via RPA.

---

**Copie e cole o texto abaixo na sua ferramenta de IA:**

Atue como um Engenheiro de Dados e Arquiteto de Software Especialista em PostgreSQL. Preciso modelar um banco de dados relacional para um **Orquestrador de Assinaturas Eletrônicas** que será consumido por robôs de automação (RPA).

### Contexto do Sistema:
Atualmente, o sistema recebe requisições de um processo genérico (chamado Fluid). O objetivo é unificar duas esteiras de assinaturas que hoje funcionam de forma separada e com configurações *hardcoded* (JSONs locais e NoSQL):
1. **Adesão:** Assinatura via aplicativo.
2. **Certisign:** Assinatura via WhatsApp ou E-mail.

### Regras de Negócio e Requisitos de Entidades:

* **Gestão de Associados (Visão Única do Cliente):** Precisamos de uma tabela central de `associados` (pessoas físicas ou jurídicas). O objetivo principal é manter um registro contínuo para que seja possível consultar, a qualquer momento, o histórico completo de todos os documentos que uma pessoa possui ou já assinou, independentemente de qual processo originou o documento.
* **Processos e Configurações:** Preciso de uma estrutura para cadastrar os 'Processos' (ex: Abertura de Conta). Cada processo deve armazenar parametrizações que hoje ficam em JSONs, como `id_template`, `nodos_envio`, `obrigatoriedade` e o mapeamento padrão de campos (DE-PARA de campos do sistema origem).
* **Jornada/Solicitação:** Uma tabela central que registra a chegada do pedido do orquestrador. Ela deve ser capaz de receber um *payload* dinâmico com os campos genéricos vindos do Fluid (sugestão: usar campo `JSONB` para não engessar os campos que variam por tipo de assinatura).
* **Gestão de Documentos:** Os documentos gerados precisam ter ciclo de vida e estar vinculados à solicitação e aos associados. Devem suportar:
  - Cancelamento (seja por tempo de vida útil expirado ou por requisição de outro processo).
  - Versionamento (atualizar a versão de um documento caso ele seja refeito).
* **Gestão de Assinaturas/Assinantes:** Um documento pode ter várias assinaturas exigidas e um associado pode assinar vários documentos. A modelagem deve permitir:
  - Inclusão de novos assinantes no meio do processo de um documento.
  - Troca de um assinante por outro.
  - Troca do método de validação da assinatura (ex: mudar de E-mail para WhatsApp ou App).

### Requisitos Técnicos da Saída:

1. Gere o **Modelo Conceitual** utilizando a sintaxe **Mermaid.js** (Diagrama Entidade-Relacionamento `erDiagram`).
2. Aplique boas práticas de nomenclatura para PostgreSQL (snake_case para tabelas e colunas, tabelas no plural).
3. Use `UUID` gerado nativamente como chave primária padrão para todas as tabelas.
4. Forneça o script **DDL PostgreSQL** completo, incluindo a criação de tabelas, chaves estrangeiras com regras claras de integridade (`ON DELETE CASCADE` ou `RESTRICT` onde fizer sentido), e campos de auditoria (`created_at`, `updated_at`, `status`).
5. Crie índices adequados para otimizar as buscas, focando principalmente na recuperação rápida de "todos os documentos de um associado", além de buscas por `id_processo`, `id_template` e status do documento.