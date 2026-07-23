# Action Plan F01.1 — Modelo de Documento e Migration

## 1. Identificação

- **Projeto:** Assistente de Avaliação de Mérito Tecnológico
- **Feature:** F01.1 — Modelo de Documento e Migration
- **Feature pai:** F01 — Ingestão Segura de Documentos
- **Feature Intent:** `feature-intent-f01-1-document-model-and-migration.md`
- **MCP+ aplicável:** MCP+ 001 v1.1
- **Branch:** `feature/f01-secure-document-ingestion`
- **Data:** 2026-07-22
- **Responsável humano:** André Cataldo
- **Status:** Approved

---

## 2. Verificação de Prontidão

- Feature Intent F01.1 aprovado.
- Escopo IN e OUT definidos.
- Critérios de aceite definidos.
- Migration anterior identificada como `0001_initial`.
- Nenhuma dependência nova necessária.
- Nenhum conflito identificado com o MCP+ 001 v1.1.
- Nenhuma Decision Lock precisa ser alterada.

---

## 3.1 Objetivo do Plano

Implementar a representação persistente de documentos associados a avaliações.

O incremento deverá criar:

- entidade de domínio `Document`;
- modelo SQLAlchemy `DocumentModel`;
- tabela PostgreSQL `documents`;
- migration Alembic reversível;
- restrições de integridade e duplicidade;
- testes automatizados do modelo.

O incremento não incluirá upload, acesso a arquivos, extração de texto,
endpoints ou interface.

---

## 3.2 Estratégia Geral

A implementação será dividida em mudanças pequenas e verificáveis:

1. validar o estado inicial;
2. criar a entidade de domínio;
3. criar o modelo SQLAlchemy;
4. criar a migration;
5. criar os testes;
6. validar upgrade e downgrade;
7. executar o quality gate;
8. atualizar os artefatos e registrar a implementação.

A entidade, o modelo SQLAlchemy e a migration deverão representar o mesmo
contrato de dados.

Não serão criados:

- endpoints;
- schemas de API;
- relacionamentos ORM desnecessários;
- serviços de armazenamento;
- manipulação física de arquivos;
- campos de página ou extração;
- novas dependências.

---

## 3.3 Etapas de Execução

### Etapa 1 — Confirmar o baseline

**Descrição**

Confirmar branch, working tree e artefatos de governança.

**Arquivos afetados**

Nenhum.

**Resultado esperado**

Execução iniciada em uma branch limpa e atualizada.

**Verificação**

- [x] **Human Lead Engineer aprovou este Action Plan**
- **Data da aprovação:** 2026-07-22
