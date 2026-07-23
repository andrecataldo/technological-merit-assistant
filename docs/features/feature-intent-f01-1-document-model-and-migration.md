# Feature Intent F01.1 — Modelo de Documento e Migration

## 1. Identificação

- **Título da Feature:** F01.1 — Modelo de Documento e Migration
- **Feature pai:** F01 — Ingestão Segura de Documentos
- **Autor — Human Lead Engineer:** André Cataldo
- **Data:** 2026-07-22
- **Status:** Done
- **MCP+ aplicável:** MCP+ 001 v1.1
- **Issue:** não definida

---

## 2. Contexto e Problema

A aplicação já possui avaliações e perfis persistidos, mas ainda não possui
uma representação de documento associada a uma avaliação.

Sem essa entidade, não é possível registrar arquivos com identidade própria,
integridade, isolamento entre avaliações e rastreabilidade necessária para os
próximos incrementos de upload e extração.

- **Quem sofre o problema:** usuário responsável pela avaliação e componentes
  posteriores de ingestão documental.
- **Quando acontece:** ao tentar associar um PDF a uma avaliação existente.
- **Impacto atual:** impossibilidade de persistir metadados documentais e
  implementar o upload seguro.

---

## 3. Intenção — Outcome

### Resultado esperado em linguagem de produto

O sistema deverá possuir uma representação persistente para cada documento
associado a uma avaliação, preservando identidade, origem, integridade e
metadados mínimos.

### Resultado esperado em linguagem técnica

Criar:

- entidade de domínio `Document`;
- modelo SQLAlchemy `DocumentModel`;
- tabela PostgreSQL `documents`;
- migration Alembic reversível;
- restrições de integridade e duplicidade;
- testes automatizados do modelo.

---

## 4. Escopo

### 4.1 Dentro do escopo — IN

- [x] Criar a entidade de domínio `Document`.
- [x] Criar o modelo SQLAlchemy `DocumentModel`.
- [x] Criar a tabela `documents`.
- [x] Associar cada documento a uma avaliação existente.
- [x] Usar UUID como identificador do documento.
- [x] Registrar o nome original do arquivo.
- [x] Registrar uma chave relativa de armazenamento.
- [x] Registrar o MIME type declarado.
- [x] Registrar o tamanho do arquivo em bytes.
- [x] Registrar o hash SHA-256.
- [x] Registrar a data de criação.
- [x] Impedir hash duplicado dentro da mesma avaliação.
- [x] Permitir o mesmo hash em avaliações diferentes.
- [x] Impedir tamanho igual ou inferior a zero.
- [x] Exigir SHA-256 com 64 caracteres.
- [x] Tornar a chave de armazenamento única.
- [x] Criar migration Alembic reversível.
- [x] Criar testes automatizados.

### 4.2 Fora do escopo — OUT

- [ ] Endpoint de upload.
- [ ] Interface Streamlit.
- [ ] Gravação física de arquivos.
- [ ] Leitura de arquivos.
- [ ] Validação de extensão.
- [ ] Validação da assinatura PDF.
- [ ] Detecção real de MIME type.
- [ ] Cálculo efetivo do SHA-256.
- [ ] Extração de texto.
- [ ] Entidade ou tabela de páginas.
- [ ] OCR.
- [ ] Logs de ingestão.
- [ ] Classificação documental.
- [ ] RAG, embeddings ou LLM.

---

## 5. Comportamento Esperado

### 5.1 Casos de sucesso

- Um documento pode ser associado a uma avaliação existente.
- Uma avaliação pode possuir vários documentos com hashes diferentes.
- O mesmo hash pode existir em avaliações diferentes.
- A migration cria a tabela e todas as restrições previstas.
- O downgrade remove exclusivamente a tabela `documents`.

### 5.2 Casos de erro ou exceção

- Documento associado a avaliação inexistente deve ser rejeitado.
- Hash duplicado dentro da mesma avaliação deve ser rejeitado.
- Tamanho igual ou inferior a zero deve ser rejeitado.
- SHA-256 com comprimento diferente de 64 caracteres deve ser rejeitado.
- Chave de armazenamento duplicada deve ser rejeitada.

### 5.3 Guardrails funcionais

- Nenhum conteúdo de PDF será armazenado nesta etapa.
- Nenhum caminho absoluto será persistido.
- `storage_key` representa somente uma chave relativa interna.
- Nenhum documento real será usado nos testes.
- Nenhuma nova dependência será adicionada.
- Nenhum endpoint será criado nesta etapa.

---

## 6. Modelo Proposto

### Entidade Document

| Campo               | Tipo                  | Regra                                 |
| ------------------- | --------------------- | ------------------------------------- |
| `id`                | UUID                  | chave primária                        |
| `evaluation_id`     | UUID                  | FK obrigatória para `evaluations.id`  |
| `original_filename` | string                | obrigatório, máximo 255               |
| `storage_key`       | string                | obrigatório, relativo e único         |
| `content_type`      | string                | obrigatório, máximo 100               |
| `size_bytes`        | inteiro               | obrigatório e maior que zero          |
| `sha256`            | string                | obrigatório, exatamente 64 caracteres |
| `created_at`        | datetime com timezone | obrigatório                           |

### Restrições

- chave primária em `id`;
- chave estrangeira de `evaluation_id` para `evaluations.id`;
- exclusão em cascata dos documentos quando a avaliação for removida;
- unicidade composta entre `evaluation_id` e `sha256`;
- unicidade global de `storage_key`;
- check constraint para `size_bytes > 0`;
- check constraint para comprimento de `sha256 = 64`;
- índice para `evaluation_id`.

---

## 7. Critérios de Aceite

### 7.1 Funcionais

- [x] A entidade de domínio `Document` foi criada.
- [x] O modelo SQLAlchemy corresponde ao modelo definido neste documento.
- [x] A tabela `documents` é criada pela migration.
- [x] `evaluation_id` referencia `evaluations.id`.
- [x] A exclusão de uma avaliação elimina seus documentos.
- [x] Existe unicidade para `(evaluation_id, sha256)`.
- [x] `storage_key` possui unicidade.
- [x] Existe restrição para `size_bytes > 0`.
- [x] Existe restrição para SHA-256 com 64 caracteres.
- [x] Upgrade e downgrade funcionam.
- [x] O downgrade remove somente a tabela criada nesta feature.

### 7.2 Técnicos

- [x] Testes automatizados criados ou atualizados.
- [x] Nenhuma regressão nos testes existentes.
- [x] `pytest` aprovado.
- [x] `ruff check .` aprovado.
- [x] `mypy src` aprovado.
- [x] `verify_i001_scope.sh` aprovado.
- [x] Nenhuma dependência nova.
- [x] Nenhum PDF ou dado real incluído no Git.

---

## 8. Restrições Técnicas

- **Arquitetura:** manter o monólito modular vigente.
- **Persistência:** PostgreSQL, SQLAlchemy 2 e Alembic.
- **Identificadores:** UUID.
- **Migration anterior:** `0001_initial`.
- **Segurança:** não armazenar conteúdo documental.
- **Privacidade:** usar somente dados sintéticos nos testes.
- **Compatibilidade:** não alterar contratos existentes de avaliação.
- **Autonomia:** não expandir para upload, extração ou interface.

---

## 9. Impacto e Superfície de Mudança

### Módulos afetados

- domínio;
- infraestrutura de persistência;
- migrations;
- testes.

### Arquivos previstos

- `src/merit_assistant/domain/entities.py`;
- `src/merit_assistant/infrastructure/db/models.py`;
- `alembic/versions/0002_add_documents.py`;
- `tests/test_document_model.py`.

### Arquivos que não devem ser alterados

- endpoints FastAPI;
- interface Streamlit;
- perfil de avaliação;
- configuração de processamento externo;
- serviços de extração;
- documentação normativa do programa.

### Riscos

- divergência entre entidade, modelo e migration;
- restrição de duplicidade implementada no escopo errado;
- armazenamento de caminho absoluto;
- inclusão antecipada de campos de páginas ou extração;
- downgrade removendo objetos fora da feature.

### Rollback

Executar:

`alembic downgrade 0001_initial`

O rollback deve remover exclusivamente a tabela `documents`.

---

## 10. Plano de Validação

### Testes automatizados

- validar os campos da entidade de domínio;
- validar colunas, índices e constraints do modelo;
- validar que os modelos anteriores permanecem disponíveis;
- executar toda a suíte de regressão.

### Teste da migration

1. Executar `alembic upgrade head`.
2. Confirmar a existência da tabela `documents`.
3. Confirmar colunas e constraints.
4. Executar `alembic downgrade 0001_initial`.
5. Confirmar a remoção da tabela `documents`.
6. Confirmar que `evaluations` e `evaluation_profiles` permanecem.
7. Executar novamente `alembic upgrade head`.

### Quality Gate

- `pytest`;
- `ruff check .`;
- `mypy src`;
- `./scripts/verify_i001_scope.sh`;
- `git status`;
- verificação de arquivos privados rastreados.

---

## 11. Handoff para IA

### Artefatos superiores

- MCP+ 001 v1.1;
- PRD-Lite v0.1;
- Feature Intent F01;
- Context Pack v0.1;
- Guidelines Técnicas v0.1;
- Arquitetura v0.1.

### Regras para execução

- implementar somente o modelo e a migration;
- não criar endpoints;
- não manipular arquivos físicos;
- não calcular hash;
- não extrair texto;
- não adicionar dependências;
- interromper em caso de conflito com artefato superior;
- preservar integralmente os Decision Locks.

---

## 12. Registro de Conclusão

- **Status final:** Done
- **Data da conclusão:** 2026-07-22
- **Migration criada:** `0002_add_documents`
- **Revisão anterior:** `0001_initial`
- **Responsável pela validação:** André Cataldo

### Evidências

- entidade de domínio `Document` criada;
- modelo SQLAlchemy `DocumentModel` criado;
- tabela PostgreSQL `documents` criada;
- foreign key para `evaluations.id` validada;
- `ON DELETE CASCADE` validado no PostgreSQL;
- unicidade de `(evaluation_id, sha256)` validada;
- unicidade global de `storage_key` validada;
- check de `size_bytes > 0` validado;
- check de SHA-256 com 64 caracteres validado;
- upgrade para `0002_add_documents` aprovado;
- downgrade para `0001_initial` aprovado;
- tabelas anteriores preservadas;
- novo upgrade para `0002_add_documents` aprovado;
- testes automatizados aprovados;
- Ruff aprovado;
- mypy aprovado;
- verificador de escopo I-001 aprovado;
- aplicação reiniciada e endpoint `/health` aprovado;
- nenhum documento real ou dado privado incluído no Git.

### Desvios

Nenhum desvio de escopo identificado.

### Itens deliberadamente não implementados

- upload de documentos;
- gravação física de arquivos;
- endpoints documentais;
- interface Streamlit para documentos;
- validação real de PDFs;
- cálculo efetivo de SHA-256;
- extração de texto;
- OCR;
- páginas, embeddings, RAG ou LLM.

## Aprovação

- [x] **Human Lead Engineer aprovou esta Feature Intent**
- **Data da aprovação:** 2026-07-22
