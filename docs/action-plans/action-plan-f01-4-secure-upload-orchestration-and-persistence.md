# Action Plan F01.4 — Orquestração Segura do Upload e Persistência

## 1. Identificação

- **Projeto:** Assistente de Avaliação de Mérito Tecnológico
- **Feature:** F01.4 — Orquestração Segura do Upload e Persistência
- **Feature pai:** F01 — Ingestão Segura de Documentos
- **Feature Intent:** `feature-intent-f01-4-secure-upload-orchestration-and-persistence.md`
- **MCP+ aplicável:** MCP+ 001 v1.1
- **Dependências:**
  - F01.1 — Modelo de Documento e Migration;
  - F01.2 — Serviço Local de Armazenamento Seguro;
  - F01.3 — Validação de PDF, Limite de Tamanho e SHA-256.
- **Branch:** `feature/f01-secure-document-ingestion`
- **Data:** 2026-07-28
- **Responsável humano:** André Cataldo
- **Status:** Done

---

## 2. Verificação de Prontidão

- Feature Intent F01.4 aprovado.
- F01.1 concluído.
- F01.2 concluído.
- F01.3 concluído.
- Contratos existentes de domínio, armazenamento e validação disponíveis.
- Tabela `documents` disponível na migration `0002_add_documents`.
- Restrição `uq_documents_evaluation_sha256` disponível.
- Restrição `fk_documents_evaluation_id` disponível.
- Estratégia de compensação entre PostgreSQL e sistema de arquivos aprovada.
- Estratégia de verificação dos bytes consumidos pelo storage aprovada.
- Nenhuma migration nova necessária.
- Nenhuma dependência nova necessária.
- Nenhum endpoint necessário.
- Nenhuma interface necessária.
- Nenhum conflito identificado com o MCP+ 001 v1.1.
- Nenhuma Decision Lock precisa ser alterada.

---

## 3.1 Objetivo do Plano

Implementar o caso de uso responsável por coordenar a ingestão segura de um PDF,
desde a confirmação da avaliação até a persistência dos metadados, preservando a
consistência possível entre o PostgreSQL e o armazenamento local.

O incremento deverá criar:

- contrato `DocumentPersistence`;
- exceções específicas do port de persistência;
- implementação `SqlAlchemyDocumentPersistence`;
- serviço `DocumentUploadService`;
- exceções públicas da orquestração;
- leitor verificador que calcula tamanho e SHA-256 durante a leitura feita pelo
  armazenamento;
- validação do nome persistente com limite de 255 caracteres;
- verificação preventiva de duplicidade por avaliação e SHA-256;
- geração única de UUID;
- geração de `created_at` em UTC;
- criação da entidade `Document`;
- persistência transacional explícita;
- rollback e exclusão compensatória após falhas posteriores ao armazenamento;
- tradução de erros conhecidos do banco;
- testes unitários determinísticos;
- testes de persistência com PostgreSQL;
- teste integrado com PDF sintético e diretório temporário.

O incremento não incluirá:

- endpoint FastAPI;
- `UploadFile`;
- schema HTTP;
- interface Streamlit;
- download ou listagem;
- extração de texto ou imagens;
- OCR;
- páginas;
- embeddings;
- RAG ou LLM;
- antivírus;
- processamento externo;
- migration;
- alteração do modelo `DocumentModel`;
- alteração de `DocumentStorage`;
- alteração de `DocumentValidationService`;
- Unit of Work genérica;
- processamento assíncrono;
- recuperação posterior de órfãos.

---

## 3.2 Estratégia Geral

A implementação será dividida em mudanças pequenas e verificáveis:

1. confirmar o baseline;
2. criar o port de persistência e suas exceções;
3. implementar a persistência SQLAlchemy;
4. criar o leitor verificador e as exceções da orquestração;
5. implementar o fluxo nominal e as rejeições anteriores ao armazenamento;
6. implementar tradução de erros e compensação;
7. executar o Checkpoint Humano H1;
8. validar persistência e orquestração com PostgreSQL e armazenamento temporário;
9. executar o Quality Gate completo;
10. executar o Checkpoint Humano H2;
11. atualizar os artefatos e registrar a implementação.

### Decisões técnicas do plano

- `DocumentPersistence` será um `Protocol` da camada de aplicação.
- As exceções do port permanecerão junto ao contrato de persistência.
- A camada de aplicação não importará SQLAlchemy.
- `SqlAlchemyDocumentPersistence` receberá uma `Session` por injeção.
- A implementação de persistência não criará nem fechará a sessão.
- `evaluation_exists()` utilizará consulta de existência, sem materializar
  entidade completa.
- `exists_by_evaluation_and_sha256()` será limitada à avaliação recebida.
- `add()` mapeará `Document` para `DocumentModel` sem gerar novos valores.
- `commit()` será explícito.
- `rollback()` será explícito.
- A infraestrutura traduzirá violações conhecidas pelos nomes das constraints.
- A restrição `uq_documents_evaluation_sha256` será traduzida para
  `DuplicateDocumentPersistenceError`.
- A restrição `fk_documents_evaluation_id` será traduzida para
  `EvaluationReferencePersistenceError`.
- Outros erros conhecidos de SQLAlchemy serão traduzidos para
  `DocumentPersistenceError`.
- O port não executará rollback automaticamente em `commit()`.
- O serviço de upload será responsável por solicitar rollback.
- `DocumentUploadService` receberá validador, storage, persistência,
  `id_factory` e `clock` por injeção.
- O UUID será gerado uma única vez antes do armazenamento.
- `created_at` será gerado por `datetime.now(UTC)` na implementação padrão.
- O nome validado será rejeitado se possuir mais de 255 caracteres.
- A validação documental será executada uma única vez.
- Os metadados retornados pela validação não serão recalculados ou substituídos.
- Um segundo SHA-256 será calculado apenas sobre os bytes efetivamente consumidos
  pelo storage.
- O leitor verificador não manterá uma segunda cópia integral do documento.
- O leitor verificador deverá registrar:
  - quantidade de bytes lidos;
  - hash incremental;
  - confirmação de EOF observado.
- A aceitação após o armazenamento exigirá:
  - tamanho lido igual ao tamanho validado;
  - SHA-256 lido igual ao SHA-256 validado;
  - EOF observado.
- O fluxo original será restaurado diretamente pelo serviço após o storage.
- O fluxo não será fechado pelo serviço nem pelo leitor verificador.
- Depois que `store()` retornar uma `storage_key`, qualquer falha anterior ao
  commit confirmado exigirá compensação.
- Rollback e exclusão serão tentados independentemente.
- `delete()` retornando `False` será falha de compensação.
- A mensagem de `DocumentCompensationError` não incluirá nome, conteúdo,
  storage key, SHA-256 ou dados SQL.
- Nenhum commit de implementação será feito antes da aprovação do H2.

---

## 3.3 Etapas de Execução

### Etapa 1 — Confirmar o baseline

**Descrição**

Confirmar branch, working tree, artefatos aprovados e integridade técnica antes
da implementação.

**Arquivos afetados**

Nenhum.

**Resultado esperado**

- branch correta confirmada;
- working tree limpo e sincronizado;
- Feature Intent F01.4 presente e aprovado;
- F01.1, F01.2 e F01.3 confirmados como concluídos;
- banco na revisão `0002_add_documents`;
- suíte completa de testes aprovada;
- Ruff aprovado;
- mypy aprovado;
- verificador I-001 aprovado;
- `git diff --check` aprovado;
- serviços operacionais;
- endpoint `/health` aprovado;
- nenhum arquivo privado rastreado.

**Verificação**

```bash
git branch --show-current
git status
git status -sb
git log --oneline --decorate -7

test -f \
  docs/features/feature-intent-f01-4-secure-upload-orchestration-and-persistence.md

test -f \
  docs/features/feature-intent-f01-3-pdf-validation-size-and-sha256.md

test -f \
  docs/action-plans/action-plan-f01-3-pdf-validation-size-and-sha256.md

test -f \
  docs/mcp/mcp-plus-001-v1.1-foundation-ingestion.md

pytest
ruff check .
mypy src
./scripts/verify_i001_scope.sh
git diff --check

docker compose up -d
docker compose ps
alembic current

curl -fsS http://localhost:8000/health
echo
```

**Resultado**

- branch `feature/f01-secure-document-ingestion` confirmada;
- branch sincronizada com o remoto;
- working tree limpo;
- Feature Intent F01.4 aprovado;
- Action Plan F01.4 aprovado;
- MCP+ 001 v1.1 presente;
- F01.1, F01.2 e F01.3 concluídos;
- 124 testes aprovados;
- execução registrou 1 warning;
- Ruff aprovado;
- mypy aprovado em 24 arquivos;
- verificador de escopo I-001 aprovado;
- `git diff --check` aprovado;
- API, PostgreSQL e interface operacionais;
- banco em `0002_add_documents (head)`;
- endpoint `/health` aprovado;
- processamento externo desabilitado;
- nenhum arquivo privado rastreado.

**Status:** Concluída

---

### Etapa 2 — Criar o port de persistência e suas exceções

**Descrição**

Criar o contrato da camada de aplicação que isola o caso de uso dos detalhes de
SQLAlchemy e define os erros conhecidos da persistência documental.

**Arquivos previstos**

- `src/merit_assistant/application/ports/document_persistence.py`;
- `tests/test_document_persistence_contract.py`.

**Contrato previsto**

```python
class DocumentPersistence(Protocol):
    def evaluation_exists(self, evaluation_id: UUID) -> bool: ...

    def exists_by_evaluation_and_sha256(
        self,
        evaluation_id: UUID,
        sha256: str,
    ) -> bool: ...

    def add(self, document: Document) -> None: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...
```

**Exceções previstas**

```text
DocumentPersistenceError
├── DuplicateDocumentPersistenceError
└── EvaluationReferencePersistenceError
```

**Regras estruturais**

- o módulo não importará SQLAlchemy;
- o contrato será específico para a persistência de documentos;
- o port não receberá conteúdo binário;
- o port não receberá `storage`;
- o port não gerará UUID;
- o port não gerará data;
- o port não calculará hash;
- as mensagens não incluirão SHA-256 completo;
- as exceções não dependerão de FastAPI;
- os testes confirmarão compatibilidade estrutural com fakes.

**Verificação**

```bash
python -m compileall \
  src/merit_assistant/application/ports/document_persistence.py

pytest tests/test_document_persistence_contract.py -v

ruff check \
  src/merit_assistant/application/ports/document_persistence.py \
  tests/test_document_persistence_contract.py

mypy \
  src/merit_assistant/application/ports/document_persistence.py \
  tests/test_document_persistence_contract.py

git diff --check
```

**Resultado**

- contrato `DocumentPersistence` criado;
- operações aprovadas expostas pelo `Protocol`;
- `DocumentPersistenceError` criada;
- `DuplicateDocumentPersistenceError` criada;
- `EvaluationReferencePersistenceError` criada;
- port mantido independente de SQLAlchemy;
- port não recebe conteúdo binário ou storage;
- fake tipado confirmou compatibilidade estrutural;
- hierarquia de exceções validada;
- 4 testes específicos aprovados;
- Ruff aprovado;
- mypy aprovado em 2 arquivos;
- compilação aprovada;
- `git diff --check` aprovado.

**Status:** Concluída

---

### Etapa 3 — Implementar SqlAlchemyDocumentPersistence

**Descrição**

Criar a implementação concreta do port utilizando uma `Session` recebida por
injeção, sem criar ou fechar a sessão.

**Arquivos previstos**

- `src/merit_assistant/infrastructure/db/document_persistence.py`;
- `src/merit_assistant/infrastructure/db/__init__.py`;
- `tests/test_sqlalchemy_document_persistence.py`.

**Operações previstas**

```python
class SqlAlchemyDocumentPersistence:
    def __init__(self, session: Session) -> None:
        ...

    def evaluation_exists(self, evaluation_id: UUID) -> bool:
        ...

    def exists_by_evaluation_and_sha256(
        self,
        evaluation_id: UUID,
        sha256: str,
    ) -> bool:
        ...

    def add(self, document: Document) -> None:
        ...

    def commit(self) -> None:
        ...

    def rollback(self) -> None:
        ...
```

**Mapeamento previsto**

A implementação deverá persistir exatamente:

```text
id
evaluation_id
original_filename
storage_key
content_type
size_bytes
sha256
created_at
```

**Tradução de erros**

- `uq_documents_evaluation_sha256`:
  `DuplicateDocumentPersistenceError`;
- `fk_documents_evaluation_id`:
  `EvaluationReferencePersistenceError`;
- outras violações de integridade:
  `DocumentPersistenceError`;
- outros erros conhecidos de SQLAlchemy:
  `DocumentPersistenceError`.

A identificação de uma constraint PostgreSQL deverá utilizar o nome fornecido
pelo driver quando disponível. A implementação não deverá inferir duplicidade
pela mensagem textual completa do banco.

**Casos mínimos**

- avaliação existente retorna `True`;
- avaliação inexistente retorna `False`;
- documento existente na mesma avaliação e SHA-256 retorna `True`;
- mesmo SHA-256 em outra avaliação não é considerado duplicado;
- `add()` cria `DocumentModel` com todos os valores recebidos;
- `add()` não gera novo UUID;
- `add()` não altera a data;
- `add()` não altera a storage key;
- `commit()` chama a sessão uma única vez;
- `rollback()` chama a sessão uma única vez;
- a sessão não é fechada;
- erros conhecidos são traduzidos;
- erro traduzido preserva a causa por encadeamento.

**Verificação**

```bash
python -m compileall \
  src/merit_assistant/infrastructure/db/document_persistence.py

pytest tests/test_sqlalchemy_document_persistence.py -v

ruff check \
  src/merit_assistant/infrastructure/db/document_persistence.py \
  src/merit_assistant/infrastructure/db/__init__.py \
  tests/test_sqlalchemy_document_persistence.py

mypy \
  src \
  tests/test_sqlalchemy_document_persistence.py

git diff --check
```

**Resultado**

- adapter `SqlAlchemyDocumentPersistence` criado;
- sessão SQLAlchemy recebida por injeção;
- adapter não cria nem fecha a sessão;
- `evaluation_exists()` implementado;
- `exists_by_evaluation_and_sha256()` implementado;
- busca de duplicidade restrita à avaliação;
- `add()` mapeia todos os campos de `Document`;
- `commit()` implementado;
- `rollback()` implementado;
- constraint `uq_documents_evaluation_sha256` traduzida para `DuplicateDocumentPersistenceError`;
- constraint `fk_documents_evaluation_id` traduzida para `EvaluationReferencePersistenceError`;
- constraints desconhecidas traduzidas para `DocumentPersistenceError`;
- erros SQLAlchemy genéricos traduzidos para `DocumentPersistenceError`;
- causas originais preservadas por encadeamento de exceções;
- 10 testes específicos aprovados;
- Ruff aprovado;
- mypy aprovado em 27 arquivos;
- compilação aprovada;
- `git diff --check` aprovado.

**Status:** Concluída

---

### Etapa 4 — Criar o leitor verificador e as exceções da orquestração

**Descrição**

Criar os elementos internos necessários para observar os bytes efetivamente
consumidos pelo storage sem materializar uma segunda cópia integral.

**Arquivos previstos**

- `src/merit_assistant/application/services/document_upload.py`;
- `src/merit_assistant/application/services/__init__.py`;
- `tests/test_document_upload_service.py`.

**Exceções previstas**

```text
DocumentUploadError
├── EvaluationNotFoundError
├── DuplicateDocumentError
├── OriginalFilenameTooLongError
├── StoredContentMismatchError
├── DocumentUploadPersistenceError
└── DocumentCompensationError
```

**Leitor verificador**

O leitor deverá:

- receber um `BinaryIO`;
- delegar `read(size)` ao fluxo original;
- atualizar SHA-256 somente com bytes retornados;
- somar somente bytes retornados;
- registrar EOF quando `read()` retornar `b""`;
- não fechar o fluxo original;
- não chamar `seek()` durante a leitura;
- não acumular conteúdo;
- disponibilizar tamanho, SHA-256 e estado de EOF após a leitura.

**Casos mínimos**

- leitura integral produz tamanho correto;
- leitura integral produz SHA-256 correto;
- múltiplas leituras produzem o mesmo hash;
- leitura parcial não marca EOF;
- leitura até `b""` marca EOF;
- fluxo original permanece aberto;
- nenhuma segunda cópia integral é criada;
- erro do fluxo original é propagado;
- mensagens das exceções não expõem conteúdo documental.

**Verificação**

```bash
python -m compileall \
  src/merit_assistant/application/services/document_upload.py

pytest \
  tests/test_document_upload_service.py \
  -k 'reader or exception' \
  -v

ruff check \
  src/merit_assistant/application/services/document_upload.py \
  src/merit_assistant/application/services/__init__.py \
  tests/test_document_upload_service.py

mypy \
  src \
  tests/test_document_upload_service.py

git diff --check
```

**Resultado**

- módulo `document_upload.py` criado;
- hierarquia `DocumentUploadError` criada;
- `EvaluationNotFoundError` criada;
- `DuplicateDocumentError` criada;
- `OriginalFilenameTooLongError` criada;
- `StoredContentMismatchError` criada;
- `DocumentUploadPersistenceError` criada;
- `DocumentCompensationError` criada;
- leitor verificador interno criado;
- leitor delega `read(size)` ao fluxo original;
- somente bytes retornados são contabilizados;
- SHA-256 é atualizado somente com bytes retornados;
- EOF é registrado somente quando o fluxo retorna `b""`;
- leitor não executa `seek()` durante a leitura;
- leitor não fecha o fluxo original;
- leitor não mantém uma segunda cópia integral;
- erros do fluxo original são propagados;
- exceções públicas exportadas pelo pacote de serviços;
- leitor interno não foi exportado;
- mensagens não expõem conteúdo documental ou SHA-256 completo;
- 20 testes específicos aprovados;
- Ruff aprovado;
- mypy aprovado em 28 arquivos;
- compilação aprovada;
- `git diff --check` aprovado.

**Status:** Concluída

---

### Etapa 5 — Implementar o fluxo nominal e as rejeições anteriores ao armazenamento

**Descrição**

Implementar a parte do caso de uso que não exige compensação física.

**Ordem obrigatória**

1. confirmar existência da avaliação;
2. validar o documento;
3. validar comprimento do nome;
4. consultar duplicidade;
5. gerar UUID;
6. gerar data UTC;
7. confirmar fluxo na posição zero;
8. criar leitor verificador;
9. chamar storage;
10. comparar bytes consumidos;
11. restaurar fluxo;
12. criar entidade;
13. adicionar à persistência;
14. executar commit;
15. retornar entidade.

**Regras do fluxo nominal**

- avaliação inexistente será rejeitada antes da validação;
- nome maior que 255 caracteres será rejeitado após a validação e antes do
  armazenamento;
- duplicidade conhecida será rejeitada antes da geração de efeitos físicos;
- `id_factory` será chamado uma única vez;
- `clock` será chamado uma única vez;
- a data retornada deverá possuir timezone;
- o storage receberá o mesmo UUID da entidade;
- o storage receberá o fluxo verificador na posição inicial;
- o hash validado será mantido na entidade;
- a storage key será aceita somente a partir do retorno do storage;
- a entidade será adicionada antes do commit;
- o commit será executado uma única vez;
- o fluxo terminará aberto e na posição zero;
- nenhum rollback ou delete ocorrerá no sucesso.

**Rejeições anteriores ao armazenamento**

- `EvaluationNotFoundError`;
- erro propagado de `DocumentValidationService`;
- `OriginalFilenameTooLongError`;
- `DuplicateDocumentError`;
- data sem timezone será rejeitada antes do armazenamento.

A inclusão da validação de timezone não cria uma nova exceção pública. Uma
configuração inválida de `clock` deverá resultar em `ValueError` de programação.

**Casos mínimos**

- fluxo nominal retorna `Document`;
- valores da entidade correspondem às dependências;
- ordem das chamadas é comprovada;
- validador é chamado uma única vez;
- avaliação inexistente não chama validador;
- erro de validação não chama storage;
- nome longo não chama storage;
- duplicidade não chama storage;
- mesmo hash em avaliação diferente é permitido pelo port;
- UUID é consistente entre storage e entidade;
- data UTC é preservada;
- fluxo é entregue ao storage na posição zero;
- fluxo permanece aberto;
- fluxo termina na posição zero.

**Verificação**

```bash
pytest \
  tests/test_document_upload_service.py \
  -k 'success or evaluation or validation or filename or duplicate or timezone' \
  -v

ruff check \
  src/merit_assistant/application/services/document_upload.py \
  tests/test_document_upload_service.py

mypy \
  src \
  tests/test_document_upload_service.py

git diff --check
```

**Resultado**

- `DocumentUploadService` implementado;
- existência da avaliação verificada antes da validação;
- documento validado uma única vez;
- limite persistente de 255 caracteres aplicado ao nome validado;
- duplicidade consultada por avaliação e SHA-256;
- duplicidade conhecida rejeitada antes do armazenamento;
- mesmo SHA-256 permitido em avaliações diferentes;
- UUID gerado uma única vez;
- `clock` chamado uma única vez;
- data sem timezone rejeitada antes do armazenamento;
- data válida normalizada para UTC;
- posição inicial do fluxo confirmada antes do armazenamento;
- leitor verificador entregue ao storage;
- tamanho, SHA-256 e EOF comparados após o armazenamento;
- fluxo restaurado para a posição zero;
- entidade `Document` criada com os metadados validados;
- `storage_key` preservada a partir do retorno do storage;
- mesma entidade adicionada à persistência;
- `add()` executado antes de `commit()`;
- commit executado uma única vez no sucesso;
- nenhum rollback ou delete executado no sucesso;
- fluxo permanece aberto;
- fluxo termina na posição zero;
- serviço exportado pelo pacote de aplicação;
- 27 testes específicos aprovados;
- Ruff aprovado;
- mypy aprovado em 28 arquivos;
- compilação aprovada;
- `git diff --check` aprovado.

**Status:** Concluída

---

### Etapa 6 — Implementar tradução de erros e compensação

**Descrição**

Implementar o comportamento após a criação do arquivo e antes da confirmação
definitiva do commit.

**Condição de início da compensação**

A compensação será necessária somente quando:

- `DocumentStorage.store()` retornar uma `storage_key`;
- e qualquer etapa posterior falhar antes de `commit()` ser confirmado.

**Falhas que exigem compensação**

- EOF não observado pelo leitor verificador;
- tamanho armazenado divergente;
- SHA-256 armazenado divergente;
- falha ao criar a entidade;
- falha em `persistence.add()`;
- `DuplicateDocumentPersistenceError`;
- `EvaluationReferencePersistenceError`;
- outro `DocumentPersistenceError`;
- falha em `persistence.commit()`;
- falha ao restaurar o fluxo após o armazenamento.

**Procedimento de compensação**

1. tentar `persistence.rollback()`;
2. tentar `storage.delete(storage_key)`, mesmo se o rollback falhar;
3. tentar restaurar o fluxo, independentemente das outras ações;
4. se rollback e exclusão forem bem-sucedidos, propagar ou traduzir o erro
   original;
5. se rollback falhar, exclusão lançar erro ou exclusão retornar `False`,
   levantar `DocumentCompensationError`.

**Tradução prevista**

- `DuplicateDocumentPersistenceError`:
  `DuplicateDocumentError`;
- `EvaluationReferencePersistenceError`:
  `EvaluationNotFoundError`;
- outros `DocumentPersistenceError`:
  `DocumentUploadPersistenceError`;
- divergência de conteúdo:
  `StoredContentMismatchError`.

**Preservação da causa**

- as exceções traduzidas utilizarão `raise ... from exc`;
- `DocumentCompensationError` preservará a falha original por encadeamento;
- os resultados de rollback e delete serão mantidos de forma estruturada;
- a mensagem pública não conterá dados documentais.

**Casos mínimos**

- storage que não lê até EOF gera mismatch e compensação;
- tamanho divergente gera mismatch e compensação;
- hash divergente gera mismatch e compensação;
- falha no `add()` provoca rollback e delete;
- falha no commit provoca rollback e delete;
- duplicidade concorrente é traduzida e compensada;
- foreign key concorrente é traduzida e compensada;
- erro genérico de persistência é traduzido e compensado;
- rollback falha, mas delete ainda é tentado;
- delete falha, mas rollback foi tentado;
- delete retorna `False` e gera erro de compensação;
- ambas as ações falham e apenas um erro de compensação é retornado;
- arquivo não é excluído após commit confirmado;
- erro durante `store()` não chama `add()`;
- erro durante `store()` não chama delete pelo serviço;
- fluxo permanece aberto;
- fluxo é restaurado sempre que tecnicamente possível.

**Verificação**

```bash
pytest \
  tests/test_document_upload_service.py \
  -k 'mismatch or compensation or rollback or persistence or commit or storage' \
  -v

pytest tests/test_document_upload_service.py -v

ruff check \
  src/merit_assistant/application/services/document_upload.py \
  tests/test_document_upload_service.py

mypy \
  src \
  tests/test_document_upload_service.py

git diff --check
```

**Resultado**

- compensação iniciada somente após `store()` retornar uma `storage_key`;
- falhas anteriores ao armazenamento não executam compensação física;
- falha durante `store()` é propagada sem rollback ou delete pelo serviço;
- EOF não observado gera `StoredContentMismatchError`;
- divergência de tamanho gera `StoredContentMismatchError`;
- divergência de SHA-256 gera `StoredContentMismatchError`;
- falhas após armazenamento executam rollback;
- falhas após armazenamento executam exclusão do arquivo;
- rollback e exclusão são tentados independentemente;
- restauração do fluxo é tentada independentemente;
- `DuplicateDocumentPersistenceError` é traduzido para `DuplicateDocumentError`;
- `EvaluationReferencePersistenceError` é traduzido para `EvaluationNotFoundError`;
- outros erros do port são traduzidos para `DocumentUploadPersistenceError`;
- erros de consulta anteriores ao armazenamento são traduzidos sem compensação;
- falha de rollback gera `DocumentCompensationError`;
- exceção durante delete gera `DocumentCompensationError`;
- retorno `False` de delete gera `DocumentCompensationError`;
- falhas simultâneas de rollback e delete são preservadas estruturalmente;
- causa original é preservada por encadeamento;
- mensagens não expõem conteúdo documental;
- arquivo não é excluído após commit confirmado;
- fluxo permanece aberto;
- fluxo é restaurado sempre que tecnicamente possível;
- 24 testes selecionados de compensação aprovados;
- 42 testes completos do serviço aprovados;
- Ruff aprovado;
- mypy aprovado em 28 arquivos;
- compilação aprovada;
- `git diff --check` aprovado.

**Status:** Concluída

---

## 3.4 Checkpoint Humano Obrigatório H1

### H1 — Revisão da orquestração e compensação

**Momento**

Após a conclusão das Etapas 2 a 6 e antes da execução integrada com PostgreSQL e
armazenamento local real.

**Itens para revisão**

- [x] O port de persistência não depende de SQLAlchemy.
- [x] A implementação SQLAlchemy não depende do serviço de upload.
- [x] A sessão é recebida por injeção.
- [x] A sessão não é criada nem fechada pela persistência.
- [x] O mapeamento preserva todos os campos de `Document`.
- [x] A restrição de duplicidade é traduzida pelo nome aprovado.
- [x] A foreign key é traduzida pelo nome aprovado.
- [x] O serviço confirma a avaliação antes da validação.
- [x] O validador é chamado uma única vez.
- [x] O nome maior que 255 caracteres é rejeitado.
- [x] A duplicidade conhecida é rejeitada antes do storage.
- [x] O UUID é gerado uma única vez.
- [x] A data possui timezone UTC.
- [x] O leitor verificador não acumula conteúdo.
- [x] O leitor verificador exige EOF observado.
- [x] Tamanho e SHA-256 consumidos são comparados aos valores validados.
- [x] Divergência impede persistência.
- [x] Compensação ocorre após qualquer falha posterior ao storage.
- [x] Rollback e delete são tentados independentemente.
- [x] `delete()` retornando `False` é tratado como falha.
- [x] O erro original permanece encadeado.
- [x] Mensagens não expõem conteúdo, hash completo ou storage key.
- [x] O fluxo não é fechado.
- [x] O fluxo é restaurado sempre que possível.
- [x] Nenhum endpoint ou interface foi criado.
- [x] Nenhuma migration ou dependência foi adicionada.
- [x] `DocumentStorage` não foi alterado.
- [x] `DocumentValidationService` não foi alterado.
- [x] `DocumentModel` não foi alterado.
- [x] Testes unitários foram aprovados.
- [x] Ruff foi aprovado.
- [x] mypy foi aprovado.
- [x] `git diff --check` foi aprovado.

**Evidências**

- 57 testes unitários aprovados;
- Ruff aprovado;
- mypy aprovado em 30 arquivos;
- `git diff --check` aprovado;
- aplicação independente de SQLAlchemy;
- adapter SQLAlchemy independente do serviço de upload;
- sessão recebida por injeção;
- adapter não cria nem fecha a sessão;
- constraint `uq_documents_evaluation_sha256` confirmada;
- constraint `fk_documents_evaluation_id` confirmada;
- superfície da alteração aprovada;
- `DocumentStorage` inalterado;
- `DocumentValidationService` inalterado;
- `DocumentModel` inalterado;
- dependências e migrations inalteradas;
- nenhum endpoint ou interface criado.

**Status:** Approved
**Aprovado por:** Human Lead Engineer
**Data:** 2026-07-28

**Condição de saída**

A execução dos testes integrados com PostgreSQL e armazenamento temporário está
autorizada.

---

## 3.5 Etapas Executadas após o H1

### Etapa 7 — Validar persistência e orquestração integrada

**Descrição**

Validar os componentes concretos com PostgreSQL real, armazenamento temporário
e PDFs sintéticos.

**Pré-condições**

- H1 aprovado;
- banco na revisão `0002_add_documents`;
- serviços do Docker operacionais;
- diretório temporário fora do repositório;
- dados de teste isolados e removíveis.

**Testes de persistência com PostgreSQL**

- criar perfil de avaliação sintético;
- criar avaliação sintética;
- confirmar `evaluation_exists()`;
- confirmar `exists_by_evaluation_and_sha256()`;
- persistir documento com todos os campos;
- consultar registro criado;
- confirmar valores exatos;
- confirmar mesmo SHA-256 em avaliações diferentes;
- provocar duplicidade na mesma avaliação;
- confirmar `DuplicateDocumentPersistenceError`;
- provocar referência inválida;
- confirmar `EvaluationReferencePersistenceError`;
- executar rollback;
- confirmar que a sessão permanece aberta.

**Teste integrado nominal**

- gerar PDF sintético em memória;
- criar diretório temporário;
- usar `PyMuPdfInspector`;
- usar `DocumentValidationService`;
- usar `LocalDocumentStorage`;
- usar `SqlAlchemyDocumentPersistence`;
- executar `DocumentUploadService.upload()`;
- confirmar entidade retornada;
- confirmar registro no PostgreSQL;
- confirmar arquivo físico;
- confirmar storage key canônica;
- confirmar conteúdo físico idêntico ao PDF sintético;
- confirmar tamanho;
- confirmar SHA-256;
- confirmar fluxo aberto e na posição zero;
- remover dados sintéticos ao final.

**Teste integrado de compensação**

- armazenar PDF sintético em diretório temporário;
- provocar falha controlada de commit após o armazenamento;
- confirmar rollback;
- confirmar ausência de registro confirmado;
- confirmar remoção do arquivo;
- confirmar fluxo aberto e restaurado;
- confirmar ausência de arquivos temporários residuais.

**Isolamento**

- cada teste utilizará UUIDs próprios;
- nenhum PDF será gravado no repositório;
- nenhum dado real será utilizado;
- a limpeza será executada em `finally` ou fixture equivalente;
- os testes não dependerão da ordem de execução;
- os testes não alterarão migrations.

**Verificação**

```bash
docker compose up -d
docker compose ps
alembic current

pytest tests/test_sqlalchemy_document_persistence.py -v
pytest tests/test_document_upload_integration.py -v

ruff check \
  src/merit_assistant/application/ports/document_persistence.py \
  src/merit_assistant/application/services/document_upload.py \
  src/merit_assistant/infrastructure/db/document_persistence.py \
  tests/test_document_persistence_contract.py \
  tests/test_document_upload_service.py \
  tests/test_sqlalchemy_document_persistence.py \
  tests/test_document_upload_integration.py

mypy \
  src \
  tests/test_document_persistence_contract.py \
  tests/test_document_upload_service.py \
  tests/test_sqlalchemy_document_persistence.py \
  tests/test_document_upload_integration.py

git diff --check
```

**Arquivo adicional autorizado**

- `tests/test_document_upload_integration.py`.

Este arquivo é autorizado pelo Action Plan por tornar explícita a separação
entre testes unitários, testes do adapter SQLAlchemy e teste integrado completo.

**Resultado**

- PostgreSQL real utilizado na revisão `0002_add_documents`;
- serviços Docker operacionais;
- dados e PDFs utilizados exclusivamente sintéticos;
- armazenamento temporário criado fora do repositório;
- `evaluation_exists()` validado no PostgreSQL;
- `exists_by_evaluation_and_sha256()` validado no PostgreSQL;
- persistência completa de `DocumentModel` confirmada;
- valores persistidos comparados exatamente com a entidade;
- mesmo SHA-256 em avaliações diferentes permitido;
- duplicidade na mesma avaliação rejeitada por
  `uq_documents_evaluation_sha256`;
- referência inválida rejeitada por
  `fk_documents_evaluation_id`;
- erros das constraints traduzidos conforme o contrato;
- sessão permaneceu aberta após rollback;
- upload nominal validado com `PyMuPdfInspector`;
- `DocumentValidationService` utilizado sem alterações;
- `LocalDocumentStorage` utilizado sem alterações;
- storage key canônica confirmada;
- conteúdo físico idêntico ao PDF sintético confirmado;
- tamanho e SHA-256 confirmados;
- fluxo permaneceu aberto e restaurado na posição zero;
- falha controlada de commit executou rollback;
- falha controlada de commit removeu o arquivo armazenado;
- nenhum registro parcial permaneceu confirmado;
- nenhum arquivo temporário ou órfão permaneceu;
- dados sintéticos removidos ao final;
- perfis sintéticos residuais no PostgreSQL: zero;
- 3 testes integrados aprovados;
- 13 testes acumulados de adapter e integração aprovados;
- Ruff aprovado;
- mypy aprovado em 31 arquivos;
- `git diff --check` aprovado.

**Status:** Concluída

---

### Etapa 8 — Executar o Quality Gate completo

**Descrição**

Validar a suíte completa, análise estática, escopo, segurança e funcionamento
operacional da aplicação.

**Verificações**

```bash
pytest
ruff check .
mypy src
./scripts/verify_i001_scope.sh
git diff --check

docker compose up -d
docker compose ps
alembic current

curl -fsS http://localhost:8000/health
echo
```

**Verificação de dados privados**

```bash
PRIVATE_FILES=$(git ls-files | grep -Ei \
  '\.(pdf|db|sqlite|sqlite3|log|env|dump|backup|tmp)$' || true)

if [ -z "$PRIVATE_FILES" ]; then
  echo "Arquivos privados rastreados: nenhum"
else
  echo "ERRO: arquivos potencialmente privados encontrados:"
  printf '%s\n' "$PRIVATE_FILES"
  exit 1
fi
```

**Verificação de escopo**

```bash
git status --short --untracked-files=all

git status --short --untracked-files=all | grep -E \
  'alembic/versions/|infrastructure/db/models\.py|application/ports/document_storage\.py|application/services/document_validation\.py|infrastructure/storage/|infrastructure/pdf/|api/|streamlit|ui/|pyproject\.toml' \
  && echo "ATENÇÃO: arquivo protegido pelo escopo foi alterado" \
  || echo "Arquivos protegidos alterados: nenhum"
```

**Resultado esperado**

- suíte completa aprovada;
- Ruff aprovado;
- mypy aprovado;
- verificador I-001 aprovado;
- `git diff --check` aprovado;
- banco em `0002_add_documents`;
- serviços operacionais;
- endpoint `/health` aprovado;
- processamento externo desabilitado;
- nenhum PDF real ou arquivo privado rastreado;
- nenhuma alteração fora da superfície aprovada;
- nenhum arquivo órfão deixado pelos testes;
- nenhuma expansão de escopo identificada.

**Resultado**

- suíte completa aprovada com 184 testes;
- 1 warning registrado, sem falha no Quality Gate;
- Ruff aprovado;
- mypy aprovado em 27 arquivos de `src`;
- verificador de escopo I-001 aprovado;
- `git diff --check` aprovado;
- serviços Docker operacionais;
- PostgreSQL saudável;
- banco na revisão `0002_add_documents (head)`;
- endpoint `/health` aprovado;
- processamento externo confirmado como desabilitado;
- nenhum arquivo potencialmente privado rastreado;
- nenhum arquivo protegido alterado;
- nenhum PDF real encontrado;
- nenhum arquivo de banco, dump ou backup encontrado;
- cache `.mypy_cache` confirmado como ignorado e não rastreado;
- nenhum perfil sintético residual no PostgreSQL;
- integridade básica do PostgreSQL aprovada;
- nenhum arquivo órfão deixado pelos testes;
- nenhuma expansão de escopo identificada;
- superfície final correspondente ao Action Plan.

**Status:** Concluída

---

## 3.6 Checkpoint Humano Obrigatório H2

### H2 — Revisão final antes do commit

**Momento**

Após a conclusão da integração e do Quality Gate, antes do commit de
implementação.

**Itens para revisão**

- [x] Todos os critérios do Feature Intent foram atendidos.
- [x] O port de persistência permanece independente de SQLAlchemy.
- [x] A implementação SQLAlchemy recebe a sessão por injeção.
- [x] A sessão não é fechada.
- [x] O mapeamento para `DocumentModel` está completo.
- [x] Avaliação inexistente é rejeitada antes da validação.
- [x] Validação ocorre uma única vez.
- [x] Nome acima de 255 caracteres é rejeitado.
- [x] Duplicidade conhecida é rejeitada antes do armazenamento.
- [x] Restrição do banco continua sendo autoridade em concorrência.
- [x] Mesmo SHA-256 em avaliações diferentes é permitido.
- [x] UUID é único e consistente.
- [x] `created_at` possui timezone UTC.
- [x] Leitor verificador não mantém cópia integral.
- [x] EOF, tamanho e SHA-256 são verificados.
- [x] Divergência provoca compensação.
- [x] Erro de persistência provoca rollback e delete.
- [x] Rollback e delete são tentados independentemente.
- [x] Falha de compensação nunca retorna sucesso.
- [x] Erros são traduzidos conforme o contrato aprovado.
- [x] Causas são preservadas.
- [x] Mensagens não expõem dados documentais.
- [x] Fluxo permanece aberto e restaurado.
- [x] Teste integrado nominal foi aprovado.
- [x] Teste integrado de compensação foi aprovado.
- [x] PostgreSQL permaneceu íntegro.
- [x] Nenhum arquivo órfão permaneceu.
- [x] Nenhum PDF real foi versionado.
- [x] Nenhuma migration foi criada.
- [x] Nenhum modelo existente foi alterado.
- [x] Nenhum endpoint ou interface foi criado.
- [x] Nenhuma dependência foi adicionada.
- [x] `pytest` foi aprovado.
- [x] Ruff foi aprovado.
- [x] mypy foi aprovado.
- [x] Verificador I-001 foi aprovado.
- [x] `git diff --check` foi aprovado.
- [x] Aplicação permaneceu operacional.
- [x] Superfície da mudança corresponde ao plano.

**Evidências**

- revisão semântica integral do pacote H2 concluída;
- duas melhorias identificadas na revisão foram corrigidas;
- divergência isolada de SHA-256 testada com tamanho idêntico;
- limpeza defensiva dos dados sintéticos incorporada à fixture integrada;
- 184 testes aprovados;
- 1 warning sem impacto no Quality Gate;
- Ruff aprovado;
- mypy aprovado em 27 arquivos de `src`;
- verificador de escopo I-001 aprovado;
- `git diff --check` aprovado;
- testes integrados nominal e de compensação aprovados;
- PostgreSQL íntegro e sem dados sintéticos residuais;
- banco na revisão `0002_add_documents (head)`;
- API, PostgreSQL e interface operacionais;
- endpoint `/health` aprovado;
- processamento externo desabilitado;
- nenhum arquivo privado rastreado;
- nenhum arquivo órfão identificado;
- nenhuma migration, dependência, interface ou endpoint adicionado;
- superfície da alteração correspondente ao Action Plan;
- nenhum staging ou commit realizado antes da aprovação.

**Status:** Approved
**Aprovado por:** Human Lead Engineer
**Data:** 2026-07-28

**Condição de saída**

O commit e o push da implementação estão autorizados.

---

## 3.7 Etapa 9 — Atualizar artefatos e registrar a implementação

**Descrição**

Encerrar formalmente o F01.4 após o commit e o push da implementação.

**Sequência prevista**

1. registrar a aprovação do H2;
2. executar o Quality Gate final;
3. adicionar somente os arquivos aprovados ao staging;
4. revisar `git diff --cached`;
5. criar commit de implementação;
6. enviar a branch;
7. registrar o identificador do commit;
8. atualizar Feature Intent para `Done`;
9. atualizar Action Plan para `Done`;
10. registrar resultados reais dos testes;
11. criar commit documental de encerramento;
12. enviar a branch;
13. confirmar working tree limpo e branch sincronizada.

**Mensagem prevista para o commit de implementação**

```text
feat: add secure document upload orchestration
```

**Mensagem prevista para o commit documental**

```text
docs: close F01.4 secure upload orchestration
```

**Arquivos previstos da implementação**

- `src/merit_assistant/application/ports/document_persistence.py`;
- `src/merit_assistant/application/services/document_upload.py`;
- `src/merit_assistant/application/services/__init__.py`;
- `src/merit_assistant/infrastructure/db/document_persistence.py`;
- `src/merit_assistant/infrastructure/db/__init__.py`;
- `tests/test_document_persistence_contract.py`;
- `tests/test_document_upload_service.py`;
- `tests/test_sqlalchemy_document_persistence.py`;
- `tests/test_document_upload_integration.py`.

**Artefatos previstos**

- `docs/features/feature-intent-f01-4-secure-upload-orchestration-and-persistence.md`;
- `docs/action-plans/action-plan-f01-4-secure-upload-orchestration-and-persistence.md`.

**Arquivos protegidos que não deverão aparecer no commit**

- migrations;
- `src/merit_assistant/domain/entities.py`;
- `src/merit_assistant/infrastructure/db/models.py`;
- `src/merit_assistant/application/ports/document_storage.py`;
- `src/merit_assistant/infrastructure/storage/`;
- `src/merit_assistant/application/services/document_validation.py`;
- `src/merit_assistant/infrastructure/pdf/`;
- endpoints;
- interface;
- `pyproject.toml`;
- PDFs;
- arquivos privados.

**Resultado**

- aprovação do H2 registrada;
- Quality Gate final aprovado;
- staging seletivo revisado;
- arquivos protegidos mantidos fora do staging;
- commit de implementação criado com a mensagem aprovada;
- commit de implementação: `ddaf3791a42a0dcee5b697f9b656ac4e30dc8b51`;
- implementação enviada para `origin/feature/f01-secure-document-ingestion`;
- Feature Intent atualizado para `Done`;
- Action Plan atualizado para `Done`;
- 184 testes completos aprovados;
- 3 testes integrados aprovados;
- 1 warning registrado sem impacto no Quality Gate;
- Ruff aprovado;
- mypy aprovado;
- verificador I-001 aprovado;
- `git diff --check` aprovado;
- PostgreSQL em `0002_add_documents (head)`;
- endpoint `/health` aprovado;
- processamento externo desabilitado;
- nenhum dado sintético residual;
- nenhum arquivo privado versionado;
- nenhuma expansão de escopo;
- commit documental de encerramento preparado com a mensagem aprovada.

**Status:** Concluída

---

## 4. Estratégia de Testes

### 4.1 Testes unitários do port

Objetivo:

- confirmar a forma do contrato;
- confirmar compatibilidade com implementação fake;
- evitar dependência acidental de SQLAlchemy.

### 4.2 Testes unitários do leitor verificador

Objetivo:

- comprovar contagem incremental;
- comprovar hash incremental;
- comprovar detecção de EOF;
- comprovar ausência de cópia integral;
- comprovar preservação do fluxo.

### 4.3 Testes unitários do serviço

Objetivo:

- comprovar ordem das chamadas;
- comprovar ausência de efeitos antes do storage;
- comprovar geração determinística;
- comprovar criação da entidade;
- comprovar tradução de erros;
- comprovar compensação completa;
- comprovar ausência de sucesso parcial.

### 4.4 Testes de persistência

Objetivo:

- comprovar consultas reais;
- comprovar mapeamento real;
- comprovar constraints reais;
- comprovar tradução pelos nomes das constraints;
- comprovar rollback;
- comprovar que a sessão não é fechada.

### 4.5 Teste integrado

Objetivo:

- comprovar validação, armazenamento e persistência em conjunto;
- comprovar identidade dos bytes;
- comprovar consistência entre entidade, banco e arquivo;
- comprovar compensação após falha de commit;
- comprovar limpeza dos dados sintéticos.

---

## 5. Segurança e Privacidade

A implementação deverá manter:

- processamento somente local;
- nenhum envio de conteúdo a terceiros;
- nenhum conteúdo documental em logs;
- nenhuma storage key em mensagens públicas;
- nenhum SHA-256 completo em mensagens públicas;
- nenhum PDF real no Git;
- nenhum arquivo privado no repositório;
- armazenamento temporário dos testes fora da árvore versionada;
- permissões existentes do `LocalDocumentStorage`;
- ausência de endpoint de exposição;
- ausência de leitura posterior desnecessária do arquivo armazenado.

---

## 6. Restrições de Implementação

Durante a execução:

- não alterar o Feature Intent sem novo gate humano;
- não alterar Decision Locks;
- não alterar MCP+;
- não alterar migrations;
- não alterar modelos existentes;
- não alterar contratos F01.2 e F01.3;
- não adicionar dependências;
- não criar endpoint;
- não criar interface;
- não usar documentos reais;
- não usar rede;
- não usar LLM;
- não fazer commit de implementação antes do H2;
- interromper diante de conflito com artefato superior;
- interromper se a compensação não puder ser comprovada;
- registrar resultados reais, sem inventar contagens de testes.

---

## 7. Critérios de Conclusão do Action Plan

O plano será considerado concluído quando:

- todas as etapas estiverem marcadas como concluídas;
- H1 estiver aprovado;
- testes de integração estiverem aprovados;
- Quality Gate estiver aprovado;
- H2 estiver aprovado;
- implementação estiver commitada e enviada;
- Feature Intent estiver em `Done`;
- Action Plan estiver em `Done`;
- resultados reais estiverem registrados;
- working tree estiver limpo;
- branch estiver sincronizada com o remoto;
- nenhum dado privado estiver versionado.

---

## 8. Aprovação

- [x] **Human Lead Engineer aprovou este Action Plan**
- **Data da aprovação:** 2026-07-28
