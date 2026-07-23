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
- **Status:** Done

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

```bash
git branch --show-current
git status
test -f docs/features/feature-intent-f01-1-document-model-and-migration.md
test -f docs/mcp/mcp-plus-001-v1.1-foundation-ingestion.md
```

---

### Etapa 2 — Criar a entidade de domínio Document

**Descrição**

Criar a entidade imutável `Document` com os metadados mínimos aprovados.

**Arquivos afetados**

- `src/merit_assistant/domain/entities.py`;
- `tests/test_document_model.py`.

**Resultado**

- entidade `Document` criada;
- tamanho não positivo rejeitado;
- SHA-256 com comprimento inválido rejeitado;
- caminho absoluto rejeitado;
- segmento `..` rejeitado.

**Status:** Concluída

**Evidência**

```bash
pytest tests/test_document_model.py -q
```

Resultado obtido:

```text
10 passed
```

---

### Etapa 3 — Criar o modelo SQLAlchemy DocumentModel

**Descrição**

Criar o modelo persistente `DocumentModel`, associado a `EvaluationModel`.

**Arquivos afetados**

- `src/merit_assistant/infrastructure/db/models.py`;
- `tests/test_document_model.py`.

**Resultado**

- tabela lógica `documents` representada no metadata SQLAlchemy;
- foreign key para `evaluations.id`;
- exclusão configurada com `ON DELETE CASCADE`;
- unicidade de `(evaluation_id, sha256)`;
- unicidade global de `storage_key`;
- check constraint para `size_bytes > 0`;
- check constraint para SHA-256 com 64 caracteres;
- índice para `evaluation_id`;
- nenhuma propriedade `relationship` adicionada.

**Verificação**

```bash
pytest tests/test_document_model.py -q

ruff check \
  src/merit_assistant/infrastructure/db/models.py \
  tests/test_document_model.py

mypy src/merit_assistant/infrastructure/db/models.py
```

**Status:** Concluída

---

### Etapa 4 — Criar a migration 0002_add_documents

**Descrição**

Criar a migration Alembic responsável pela tabela `documents`.

**Arquivo afetado**

- `alembic/versions/0002_add_documents.py`.

**Resultado**

- `upgrade()` cria a tabela `documents`;
- `upgrade()` cria a foreign key e as restrições previstas;
- `upgrade()` cria o índice para `evaluation_id`;
- `downgrade()` remove o índice;
- `downgrade()` remove exclusivamente a tabela `documents`;
- `0002_add_documents` sucede `0001_initial`.

**Verificação**

```bash
python -m compileall alembic/versions/0002_add_documents.py
ruff check alembic/versions/0002_add_documents.py
alembic heads
alembic history
```

Resultado esperado:

```text
0002_add_documents (head)
```

**Status:** Concluída

---

## 3.4 Checkpoints Humanos Obrigatórios

### H1 — Revisão do modelo e da migration

**Momento**

Após a criação da entidade `Document`, do modelo `DocumentModel`, dos testes
estruturais e da migration `0002_add_documents`, antes da execução da migration
no PostgreSQL.

**Itens revisados**

- [x] A entidade `Document` contém os campos aprovados.
- [x] `size_bytes` deve ser maior que zero.
- [x] `sha256` deve possuir 64 caracteres.
- [x] `storage_key` não aceita caminho absoluto ou segmento `..`.
- [x] `evaluation_id` referencia `evaluations.id`.
- [x] A foreign key utiliza `ON DELETE CASCADE`.
- [x] A duplicidade está limitada a `(evaluation_id, sha256)`.
- [x] `storage_key` possui unicidade global.
- [x] O modelo possui as check constraints previstas.
- [x] A migration possui upgrade e downgrade explícitos.
- [x] O downgrade remove somente o índice e a tabela `documents`.
- [x] Nenhum endpoint, interface ou serviço foi adicionado.
- [x] Nenhuma dependência nova foi adicionada.

**Status:** Approved
**Aprovado por:** André Cataldo
**Data:** 2026-07-22

**Condição de saída**

A execução da migration no PostgreSQL está autorizada.

---

## 3.5 Etapas Executadas após o H1

### Etapa 5 — Consolidar os testes automatizados

**Descrição**

Executar os testes da entidade de domínio e da estrutura do modelo SQLAlchemy.

**Resultado**

- criação válida de `Document` comprovada;
- tamanho não positivo rejeitado;
- SHA-256 com comprimento inválido rejeitado;
- caminhos absolutos e segmentos `..` rejeitados;
- campos e restrições do `DocumentModel` verificados;
- foreign key e `ON DELETE CASCADE` verificados;
- constraints de unicidade verificadas;
- check constraints e índice verificados.

**Verificação**

```bash
pytest tests/test_document_model.py -v
ruff check .
mypy src
```

**Status:** Concluída

---

### Etapa 6 — Validar upgrade e downgrade no PostgreSQL

**Descrição**

Executar a migration real no PostgreSQL e validar seu rollback.

**Resultado**

- upgrade de `0001_initial` para `0002_add_documents` aprovado;
- tabela `documents` criada com todas as colunas previstas;
- índice e constraints confirmados no PostgreSQL;
- tabela inicialmente vazia;
- downgrade para `0001_initial` aprovado;
- tabela `documents` removida pelo downgrade;
- tabelas `evaluations` e `evaluation_profiles` preservadas;
- novo upgrade para `0002_add_documents` aprovado;
- API e interface reiniciadas;
- health check aprovado.

**Estado final do banco**

```text
0002_add_documents (head)
```

**Status:** Concluída

---

### Etapa 7 — Executar o Quality Gate

**Descrição**

Validar testes, análise estática, escopo, segurança e funcionamento da aplicação.

**Verificações**

```bash
pytest
ruff check .
mypy src
./scripts/verify_i001_scope.sh
git diff --check
alembic current
docker compose ps
```

**Resultado**

- suíte de testes aprovada;
- Ruff aprovado;
- mypy aprovado;
- verificador I-001 aprovado;
- nenhuma inconsistência de whitespace;
- banco na revisão `0002_add_documents`;
- serviços operacionais;
- endpoint `/health` aprovado;
- nenhum documento real ou arquivo privado incluído no Git;
- nenhuma expansão de escopo identificada.

**Status:** Concluída

---

## 3.6 Checkpoint Humano Obrigatório H2

### H2 — Revisão final antes do commit

**Momento**

Após a conclusão dos testes, da migration real e do Quality Gate, antes do
registro definitivo da implementação.

**Itens revisados**

- [x] A entidade `Document` corresponde ao Feature Intent.
- [x] O modelo `DocumentModel` corresponde à entidade e à migration.
- [x] A migration possui upgrade e downgrade reversíveis.
- [x] A tabela real contém as colunas previstas.
- [x] A foreign key utiliza `ON DELETE CASCADE`.
- [x] A duplicidade está limitada a `(evaluation_id, sha256)`.
- [x] `storage_key` possui unicidade global.
- [x] As check constraints foram criadas no PostgreSQL.
- [x] O downgrade remove somente a tabela `documents`.
- [x] As tabelas anteriores foram preservadas.
- [x] O novo upgrade foi executado com sucesso.
- [x] Todos os testes foram aprovados.
- [x] Ruff foi aprovado.
- [x] mypy foi aprovado.
- [x] O verificador I-001 foi aprovado.
- [x] O endpoint de saúde permanece operacional.
- [x] Nenhum endpoint ou serviço fora do escopo foi criado.
- [x] Nenhuma dependência nova foi adicionada.
- [x] Nenhum documento real ou dado privado foi versionado.

---

## 3.7 Etapa 8 — Atualizar artefatos e registrar a implementação

**Descrição**

Encerrar formalmente o F01.1, atualizar seus artefatos de governança e
registrar a implementação na branch da feature.

**Artefatos atualizados**

- Feature Intent F01.1 alterado para `Done`;
- Action Plan F01.1 alterado para `Done`;
- critérios funcionais e técnicos marcados conforme as evidências;
- registro de conclusão incluído;
- implementação preparada para commit e push.

**Arquivos registrados**

- `src/merit_assistant/domain/entities.py`;
- `src/merit_assistant/infrastructure/db/models.py`;
- `alembic/versions/0002_add_documents.py`;
- `tests/test_document_model.py`;
- `docs/features/feature-intent-f01-1-document-model-and-migration.md`;
- `docs/action-plans/action-plan-f01-1-document-model-and-migration.md`.

**Resultado**

O F01.1 foi implementado, validado, revisado e preparado para integração.

**Status:** Concluída

---

## 4. Registro de Conclusão

- **Status final:** Done
- **Data da conclusão:** 2026-07-22
- **Checkpoint H1:** Approved
- **Checkpoint H2:** Approved
- **Migration final:** `0002_add_documents`
- **Quality Gate:** Approved
- **Desvios registrados:** nenhum
- **Expansão de escopo:** nenhuma

A implementação está autorizada para commit, push e posterior abertura de pull
request.
