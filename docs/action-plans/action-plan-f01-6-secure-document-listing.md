# Action Plan F01.6 — Listagem Segura de Documentos por Avaliação

## 1. Identificação

- **Projeto:** Assistente de Avaliação de Mérito Tecnológico
- **Feature:** F01.6 — Listagem Segura de Documentos por Avaliação
- **Feature pai:** F01 — Ingestão Segura de Documentos
- **Feature Intent:** `feature-intent-f01-6-secure-document-listing.md`
- **MCP+ aplicável:** MCP+ 001 v1.1
- **Branch:** `feature/f01-secure-document-ingestion`
- **Baseline de planejamento:** `c65fea5792f182726cae796ddaacc6efa1c44cf1`
- **Commit do Feature Intent aprovado:** `c65fea5792f182726cae796ddaacc6efa1c44cf1`
- **Data:** 2026-07-30
- **Responsável humano:** André Cataldo
- **Status:** Approved

### Dependências funcionais

- F01.1 — Modelo de Documento e Migration;
- F01.2 — Serviço Local de Armazenamento Seguro;
- F01.3 — Validação de PDF, Limite de Tamanho e SHA-256;
- F01.4 — Orquestração Segura do Upload e Persistência;
- F01.5 — Endpoint Seguro de Upload de Documentos.

---

## 2. Verificação de Prontidão

- Feature Intent F01.6 aprovado e commitado.
- F01.1 a F01.5 concluídas.
- Entidade `Document` disponível.
- Porta `DocumentPersistence` disponível.
- Adapter `SqlAlchemyDocumentPersistence` disponível.
- Schema público `DocumentUploadResponse` disponível com seis campos.
- Router documental e composição por request disponíveis.
- FastAPI e SQLAlchemy síncronos.
- PostgreSQL em `0002_add_documents (head)`.
- Baseline técnico: 214 testes aprovados.
- Ruff, mypy, I-001 e health aprovados.
- Processamento externo desabilitado.
- Nenhuma migration nova necessária.
- Nenhuma dependência nova necessária.
- Nenhuma alteração de entidade ou modelo necessária.
- Nenhum acesso ao storage necessário.
- Nenhum conflito com o MCP+ 001 v1.1.
- Nenhuma Decision Lock precisa ser alterada.
- Working tree limpa e branch sincronizada no início do planejamento.

## 2.1 Correção de Superfície após a Etapa 1

A verificação do baseline identificou que a extensão estrutural de
`DocumentPersistence` também afeta dois fakes existentes usados na regressão do
upload:

- `FakeUploadPersistence`, em `tests/test_document_upload_service.py`;
- `FailingCommitPersistence`, em
  `tests/test_document_upload_integration.py`.

Esses fakes deverão implementar `list_by_evaluation` exclusivamente para
continuarem estruturalmente compatíveis com a porta.

A operação não será chamada pelo fluxo de upload e não alterará o comportamento
da F01.4 ou da F01.5.

Nenhum arquivo de produção adicional foi incluído na superfície.

---

## 3.1 Objetivo

Implementar uma operação segura de leitura para listar documentos associados a
uma avaliação existente, sem abrir arquivos armazenados e sem expor metadados
internos.

O incremento entregará:

- `GET /evaluations/{evaluation_id}/documents`;
- caso de uso explícito de listagem;
- distinção entre avaliação inexistente e avaliação sem documentos;
- filtro obrigatório por `evaluation_id`;
- ordenação determinística por `created_at` e `id`;
- retorno apenas dos seis campos públicos;
- mensagens HTTP sanitizadas;
- testes unitários, de contrato e integrados;
- validação OpenAPI e operacional;
- preservação do endpoint POST existente.

O incremento não incluirá:

- Streamlit;
- upload, download ou exclusão;
- leitura, validação ou recálculo de arquivos;
- paginação, filtros ou busca;
- autenticação ou autorização;
- extração, OCR, embeddings, RAG ou LLM;
- processamento externo;
- migration ou alteração de modelo;
- refatorações não relacionadas.

---

## 3.2 Decisões Técnicas

- Criar `DocumentListingService`.
- Método público: `list_for_evaluation(evaluation_id)`.
- Dependência exclusiva de `DocumentPersistence`.
- Adicionar `list_by_evaluation(evaluation_id)` à porta.
- Retorno da porta: `Sequence[Document]`.
- Verificar a existência da avaliação antes da listagem.
- Avaliação existente sem documentos retorna coleção vazia.
- Adapter SQLAlchemy filtra por `evaluation_id`.
- Adapter SQLAlchemy ordena por `created_at ASC, id ASC`.
- Adapter converte `DocumentModel` para `Document`.
- Nenhum acesso a `DocumentStorage`, `LocalDocumentStorage`, inspector ou validator.
- Nenhum commit, rollback ou close no fluxo de leitura.
- Serviço criado por request com a sessão de `get_db_session`.
- Endpoint síncrono no router documental existente.
- Reutilizar `DocumentUploadResponse` como item público da resposta.
- GET retorna `list[DocumentUploadResponse]`.
- Preservar o POST existente sem mudança de comportamento.
- Não capturar `Exception` genericamente.
- Não retornar `str(exception)`.
- Mensagens públicas exatas:
  - `Evaluation not found.`;
  - `Unable to list documents.`.
- Nenhum commit de implementação antes da aprovação do H2.

### Concorrência

A distinção entre `404` e lista vazia usará:

1. `evaluation_exists(evaluation_id)`;
2. `list_by_evaluation(evaluation_id)`.

A iteração é monousuária e não possui exclusão concorrente de avaliações.
Locks ou isolamento adicional permanecem fora do escopo.

---

## 3.3 Superfície Prevista

### Produção — criar

- `src/merit_assistant/application/services/document_listing.py`.

### Produção — alterar

- `src/merit_assistant/application/ports/document_persistence.py`;
- `src/merit_assistant/application/services/__init__.py`;
- `src/merit_assistant/infrastructure/db/document_persistence.py`;
- `src/merit_assistant/api/dependencies.py`;
- `src/merit_assistant/api/routes/documents.py`.

### Testes — criar

- `tests/test_document_listing_service.py`;
- `tests/test_document_listing_api.py`;
- `tests/test_document_listing_api_integration.py`.

### Testes — alterar

- `tests/test_document_persistence_contract.py`;
- `tests/test_sqlalchemy_document_persistence.py`;
- `tests/test_document_upload_service.py`;
- `tests/test_document_upload_integration.py`.

### Documentação

- `docs/action-plans/action-plan-f01-6-secure-document-listing.md`;
- `docs/features/feature-intent-f01-6-secure-document-listing.md`
  somente no encerramento.

### Protegidos

Não alterar:

- `alembic.ini`;
- `alembic/versions/`;
- `src/merit_assistant/domain/entities.py`;
- `src/merit_assistant/infrastructure/db/models.py`;
- `src/merit_assistant/infrastructure/storage/`;
- `src/merit_assistant/infrastructure/pdf/`;
- `src/merit_assistant/application/services/document_upload.py`;
- `src/merit_assistant/application/services/document_validation.py`;
- `pyproject.toml`;
- `docker-compose.yml`;
- interface Streamlit;
- `data/private/`;
- documentos reais.

Mudança fora dessa superfície exige parada e nova aprovação.

---

## 3.4 Contratos de Aplicação

### Porta

Adicionar:

```python
from collections.abc import Sequence

def list_by_evaluation(
    self,
    evaluation_id: UUID,
) -> Sequence[Document]:
    ...
```

Regras:

- filtrar pela avaliação;
- retornar coleção vazia quando aplicável;
- retornar entidades `Document`;
- não retornar modelos SQLAlchemy;
- não controlar transação;
- traduzir `SQLAlchemyError` para `DocumentPersistenceError`;
- preservar a causa original.

### Caso de uso

Criar:

```python
class DocumentListingError(Exception):
    ...

class DocumentListingEvaluationNotFoundError(DocumentListingError):
    ...

class DocumentListingPersistenceError(DocumentListingError):
    ...

class DocumentListingService:
    def __init__(
        self,
        persistence: DocumentPersistence,
    ) -> None:
        ...

    def list_for_evaluation(
        self,
        evaluation_id: UUID,
    ) -> Sequence[Document]:
        ...
```

Fluxo obrigatório:

1. chamar `evaluation_exists` uma vez;
2. lançar `DocumentListingEvaluationNotFoundError` quando falso;
3. chamar `list_by_evaluation` uma vez quando verdadeiro;
4. retornar a coleção na ordem recebida;
5. traduzir `DocumentPersistenceError` para
   `DocumentListingPersistenceError`;
6. preservar a causa;
7. não executar commit, rollback ou close;
8. não capturar erros desconhecidos genericamente.

### Exportação

Adicionar ao `application/services/__init__.py`:

- `DocumentListingError`;
- `DocumentListingEvaluationNotFoundError`;
- `DocumentListingPersistenceError`;
- `DocumentListingService`.

Não remover exportações existentes.

---

## 3.5 Adapter SQLAlchemy

Consulta semanticamente equivalente a:

```python
statement = (
    select(DocumentModel)
    .where(DocumentModel.evaluation_id == evaluation_id)
    .order_by(
        DocumentModel.created_at.asc(),
        DocumentModel.id.asc(),
    )
)
```

Mapear:

- `id`;
- `evaluation_id`;
- `original_filename`;
- `storage_key`;
- `content_type`;
- `size_bytes`;
- `sha256`;
- `created_at`.

Regras:

- usar `session.scalars(statement)`;
- materializar o resultado;
- preservar a ordem;
- não fechar sessão;
- não executar flush, commit ou rollback;
- não abrir arquivo;
- traduzir `SQLAlchemyError`;
- usar mensagem interna constante e sanitizada.

---

## 3.6 Composição por Request

Adicionar:

```python
def get_document_listing_service(
    session: DatabaseSession,
) -> DocumentListingService:
    persistence = SqlAlchemyDocumentPersistence(session)
    return DocumentListingService(persistence=persistence)
```

Alias:

```python
DocumentListingServiceDependency = Annotated[
    DocumentListingService,
    Depends(get_document_listing_service),
]
```

A factory não poderá:

- criar sessão paralela;
- usar settings;
- criar storage;
- criar inspector;
- criar validator;
- executar commit ou close.

---

## 3.7 Contrato HTTP

Adicionar:

```text
GET /evaluations/{evaluation_id}/documents
```

Assinatura equivalente:

```python
@router.get(
    "/evaluations/{evaluation_id}/documents",
    response_model=list[DocumentUploadResponse],
    status_code=status.HTTP_200_OK,
)
def list_documents(
    evaluation_id: UUID,
    service: DocumentListingServiceDependency,
) -> list[DocumentUploadResponse]:
    ...
```

Fluxo:

1. receber UUID validado;
2. chamar o serviço uma vez;
3. converter cada entidade com `model_validate(..., from_attributes=True)`;
4. preservar a ordem;
5. retornar lista vazia quando aplicável;
6. não consultar persistence diretamente;
7. não acessar storage;
8. não executar query adicional.

### Erros

| Exceção                                  | HTTP | Detail                      |
| ---------------------------------------- | ---: | --------------------------- |
| `DocumentListingEvaluationNotFoundError` |  404 | `Evaluation not found.`     |
| `DocumentListingPersistenceError`        |  500 | `Unable to list documents.` |

Regras:

- encadear `HTTPException` com `from exc`;
- não capturar erros da infraestrutura no endpoint;
- não capturar `Exception`;
- UUID inválido usa o `422` padrão do FastAPI.

### OpenAPI

O path deverá conter `get` e `post`.

GET:

- resposta `200`;
- schema de array;
- itens com o schema público;
- sem request body;
- sem multipart.

POST:

- resposta `201`;
- multipart preservado;
- comportamento F01.5 preservado.

---

## 3.8 Estratégia de Testes

### Porta

Atualizar `tests/test_document_persistence_contract.py` para comprovar:

- operação nova presente;
- conjunto exato de operações;
- fake compatível;
- sequência retornada;
- nenhuma dependência SQLAlchemy;
- operações anteriores preservadas.

### Adapter

Atualizar `tests/test_sqlalchemy_document_persistence.py` para comprovar:

- filtro por avaliação;
- `ORDER BY created_at, id`;
- resultado vazio;
- mapeamento integral;
- ordem preservada;
- erro SQLAlchemy traduzido;
- causa preservada;
- nenhum close, commit ou rollback.

### Serviço

Criar `tests/test_document_listing_service.py` para cobrir:

- avaliação inexistente;
- avaliação sem documentos;
- um documento;
- vários documentos;
- ordem preservada;
- chamadas exatas à porta;
- falha na verificação;
- falha na listagem;
- tradução e encadeamento;
- ausência de storage;
- erros desconhecidos não ocultados.

### API

Criar `tests/test_document_listing_api.py` para cobrir:

- `200` com `[]`;
- `200` com documentos;
- ordem preservada;
- seis campos exatos;
- ausência de `storage_key`, SHA-256, path e conteúdo;
- `404` e mensagem exata;
- `500` e mensagem exata;
- detalhes internos ocultos;
- UUID inválido;
- serviço chamado uma vez;
- dependência por request;
- OpenAPI com GET e POST;
- GET sem body;
- POST preservado.

### Compatibilidade Estrutural com o Upload

Atualizar os fakes existentes sem alterar os casos de uso de upload:

- `FakeUploadPersistence` deverá implementar `list_by_evaluation`;
- a implementação deverá retornar uma coleção vazia;
- a operação não deverá ser chamada pelos testes do upload;
- `ConfigurableUploadPersistence` herdará a operação;
- `FailingCommitPersistence` deverá delegar `list_by_evaluation` ao adapter;
- nenhum teste existente de upload deverá mudar de resultado;
- `DocumentUploadService` não será alterado.

Executar integralmente:

- `tests/test_document_upload_service.py`;
- `tests/test_document_upload_integration.py`;
- `tests/test_document_upload_api.py`;
- `tests/test_document_upload_api_integration.py`.

### Integração

Criar `tests/test_document_listing_api_integration.py` usando:

- `TestClient`;
- FastAPI real;
- PostgreSQL real;
- sessão real;
- `SqlAlchemyDocumentPersistence`;
- `DocumentListingService`;
- dados sintéticos;
- nenhum arquivo PDF;
- nenhum diretório de storage.

Cenários:

- avaliação inexistente;
- avaliação existente sem documentos;
- isolamento entre duas avaliações;
- ordenação por timestamp e UUID;
- campos públicos exatos;
- ausência de arquivo físico;
- limpeza defensiva sem resíduos.

---

## Checkpoint Humano H1

Executar após produção e testes unitários, antes dos testes integrados.

### Pacote obrigatório

- branch e baseline;
- sincronização;
- estado Git;
- arquivos alterados;
- estatística;
- patch integral;
- SHA-256 do patch;
- testes específicos;
- suíte total no estágio H1;
- Ruff;
- mypy;
- I-001;
- `git diff --check`;
- superfície autorizada;
- ausência de PDFs e dados privados;
- warnings;
- confirmação de nenhum commit de implementação.

### Critérios

- porta mínima;
- query filtrada;
- ordenação explícita;
- mapeamento integral;
- serviço diferencia inexistência e vazio;
- serviço sem storage;
- resposta pública segura;
- mensagens sanitizadas;
- GET e POST coexistem;
- testes suficientes;
- superfície correta;
- nenhum commit de implementação.

### Registro

- **Status:** Pending
- **Aprovado por:** pendente
- **Data:** pendente
- **Pendências:** pendente
- **Evidências:** pendente

---

## 3.9 Etapas de Execução

### Etapa 1 — Confirmar baseline

**Descrição**

Confirmar branch, sincronização, artefatos e gates existentes.

**Arquivos afetados**

Nenhum.

**Verificação**

```bash
git branch --show-current
git status --short
git fetch origin
git rev-list --left-right --count   HEAD...origin/feature/f01-secure-document-ingestion
git log -5 --oneline --decorate
pytest
ruff check .
mypy src
./scripts/verify_i001_scope.sh
git diff --check
docker compose up -d
docker compose ps
alembic current
curl -fsS http://localhost:8000/health
```

**Resultado esperado**

- branch correta;
- working tree limpa;
- sincronização `0 0`;
- baseline `c65fea5`;
- 214 testes aprovados;
- gates aprovados;
- migration e health aprovados;

**Status:** Pending

---

### Etapa 2 — Estender a porta

**Descrição**

Adicionar `list_by_evaluation` e atualizar o contrato.

**Arquivos afetados**

- `src/merit_assistant/application/ports/document_persistence.py`;
- `tests/test_document_persistence_contract.py`;

**Verificação**

```bash
pytest tests/test_document_persistence_contract.py -q
ruff check   src/merit_assistant/application/ports/document_persistence.py   tests/test_document_persistence_contract.py
mypy src
git diff --check
```

**Resultado esperado**

- operação adicionada;
- fake compatível;
- nenhum import SQLAlchemy na porta;
- operações existentes preservadas;

**Status:** Pending

---

### Etapa 3 — Implementar consulta SQLAlchemy

**Descrição**

Implementar filtro, ordenação e mapeamento.

**Arquivos afetados**

- `src/merit_assistant/infrastructure/db/document_persistence.py`;
- `tests/test_sqlalchemy_document_persistence.py`;

**Verificação**

```bash
pytest tests/test_sqlalchemy_document_persistence.py -q
ruff check   src/merit_assistant/infrastructure/db/document_persistence.py   tests/test_sqlalchemy_document_persistence.py
mypy src
git diff --check
```

**Resultado esperado**

- filtro por avaliação;
- ordenação por `created_at` e `id`;
- mapeamento integral;
- erros traduzidos;
- nenhum controle de transação na leitura;

**Status:** Pending

---

### Etapa 4 — Criar caso de uso

**Descrição**

Criar serviço e erros específicos sem dependência de storage.

**Arquivos afetados**

- `src/merit_assistant/application/services/document_listing.py`;
- `src/merit_assistant/application/services/__init__.py`;
- `tests/test_document_listing_service.py`;

**Verificação**

```bash
pytest tests/test_document_listing_service.py -q
ruff check   src/merit_assistant/application/services/document_listing.py   src/merit_assistant/application/services/__init__.py   tests/test_document_listing_service.py
mypy src
git diff --check
```

**Resultado esperado**

- inexistência diferenciada de vazio;
- erros traduzidos e encadeados;
- ordem preservada;
- nenhum storage;
- nenhum commit, rollback ou close;

**Status:** Pending

---

### Etapa 5 — Criar composição por request

**Descrição**

Adicionar dependência FastAPI do serviço.

**Arquivos afetados**

- `src/merit_assistant/api/dependencies.py`;
- `tests/test_document_listing_api.py`;

**Verificação**

```bash
pytest tests/test_document_listing_api.py -q
ruff check   src/merit_assistant/api/dependencies.py   tests/test_document_listing_api.py
mypy src
git diff --check
```

**Resultado esperado**

- sessão do request reutilizada;
- serviço criado por request;
- nenhuma sessão global;
- nenhum storage;
- dependência sobrescrevível;

**Status:** Pending

---

### Etapa 6 — Criar endpoint GET

**Descrição**

Adicionar a listagem ao router documental existente.

**Arquivos afetados**

- `src/merit_assistant/api/routes/documents.py`;
- `tests/test_document_listing_api.py`;

**Verificação**

```bash
pytest tests/test_document_listing_api.py -q
ruff check   src/merit_assistant/api/routes/documents.py   tests/test_document_listing_api.py
mypy src
git diff --check
```

**Resultado esperado**

- GET registrado;
- POST preservado;
- `200`, `404` e `500` corretos;
- schema seguro;
- nenhuma leitura de storage;

**Status:** Pending

---

### Etapa 7 — Consolidar testes unitários

**Descrição**

Executar todos os testes unitários e de contrato da F01.6 antes do H1.

**Arquivos afetados**

- `tests/test_document_persistence_contract.py`;
- `tests/test_sqlalchemy_document_persistence.py`;
- `tests/test_document_listing_service.py`;
- `tests/test_document_listing_api.py`;
- `tests/test_document_upload_service.py`;
- `tests/test_document_upload_integration.py`;

**Verificação**

```bash
pytest   tests/test_document_persistence_contract.py   tests/test_sqlalchemy_document_persistence.py   tests/test_document_listing_service.py   tests/test_document_listing_api.py   -q
pytest   tests/test_document_upload_service.py   tests/test_document_upload_integration.py   tests/test_document_upload_api.py   tests/test_document_upload_api_integration.py   -q
pytest tests/test_health.py -q
ruff check src tests
mypy src
./scripts/verify_i001_scope.sh
git diff --check
```

**Resultado esperado**

- fluxos de listagem aprovados;
- regressão F01.5 aprovada;
- health preservado;
- gates locais aprovados;

**Status:** Pending

---

### Etapa 8 — Executar H1

**Descrição**

Preparar pacote de revisão e obter aprovação humana.

**Arquivos afetados**

Nenhum.

**Verificação**

```bash
git status --short
git diff --name-status
git diff --stat
git diff --check
```

**Resultado esperado**

- pacote H1 completo;
- patch e SHA-256 registrados;
- nenhuma expansão de escopo;
- nenhum documento real;
- nenhum commit de implementação;
- aprovação humana explícita;

**Status:** Pending

---

### Etapa 9 — Criar testes integrados

**Descrição**

Validar FastAPI, caso de uso, adapter e PostgreSQL reais.

**Arquivos afetados**

- `tests/test_document_listing_api_integration.py`;

**Verificação**

```bash
pytest tests/test_document_listing_api_integration.py -q
ruff check tests/test_document_listing_api_integration.py
mypy src
git diff --check
```

**Resultado esperado**

- inexistência e lista vazia aprovadas;
- isolamento aprovado;
- ordenação aprovada;
- campos públicos aprovados;
- nenhum arquivo criado ou lido;
- zero resíduos;

**Status:** Pending

---

### Etapa 10 — Reconstruir containers

**Descrição**

Validar a imagem executável e o OpenAPI.

**Arquivos afetados**

Nenhum.

**Verificação**

```bash
docker compose build --no-cache
docker compose up -d
docker compose ps
docker compose exec -T api alembic current
curl -fsS http://localhost:8000/health
```

**Resultado esperado**

- containers operacionais;
- migration `0002_add_documents (head)`;
- health aprovado;
- GET e POST presentes no OpenAPI;
- GET sem body e POST multipart preservado;

**Status:** Pending

---

### Etapa 11 — Executar Quality Gate

**Descrição**

Executar a validação técnica e de segurança completa.

**Arquivos afetados**

Nenhum.

**Verificação**

```bash
pytest -o addopts="-q --maxfail=1" -W default
ruff check .
mypy src
./scripts/verify_i001_scope.sh
git diff --check
git diff --name-status
git diff --stat
git ls-files '*.pdf'
git ls-files data/private
find data/private -type f ! -name '.gitkeep' -print
docker compose ps
alembic current
curl -fsS http://localhost:8000/health
```

**Resultado esperado**

- suíte completa aprovada;
- gates aprovados;
- superfície autorizada;
- nenhum PDF ou dado privado;
- nenhum resíduo;
- containers, migration e health aprovados;

**Status:** Pending

---

### Etapa 12 — Executar H2

**Descrição**

Preparar pacote final e obter autorização humana para commit.

**Arquivos afetados**

Nenhum.

**Verificação**

```bash
git status --short
git diff --name-status
git diff --stat
git diff --check
```

**Resultado esperado**

- patch integral revisado;
- SHA-256 registrado;
- testes e gates aprovados;
- OpenAPI aprovado;
- isolamento e ordenação comprovados;
- nenhum acesso ao storage;
- nenhum commit de implementação;
- aprovação humana explícita;

**Status:** Pending

---

### Etapa 13 — Commit da implementação

**Descrição**

Após H2, criar staging seletivo, commit e push.

**Arquivos afetados**

- `todos os arquivos de implementação previstos`;

**Verificação**

```bash
git add --   src/merit_assistant/application/ports/document_persistence.py   src/merit_assistant/application/services/__init__.py   src/merit_assistant/application/services/document_listing.py   src/merit_assistant/infrastructure/db/document_persistence.py   src/merit_assistant/api/dependencies.py   src/merit_assistant/api/routes/documents.py   tests/test_document_persistence_contract.py   tests/test_sqlalchemy_document_persistence.py   tests/test_document_listing_service.py   tests/test_document_listing_api.py   tests/test_document_listing_api_integration.py   tests/test_document_upload_service.py   tests/test_document_upload_integration.py
git commit -m "feat: add secure document listing endpoint"
git push origin feature/f01-secure-document-ingestion
```

**Resultado esperado**

- somente implementação no commit;
- nenhum documento de governança;
- branch sincronizada;

**Status:** Pending

---

### Etapa 14 — Encerramento documental

**Descrição**

Atualizar Feature Intent e Action Plan para `Done` em commit separado.

**Arquivos afetados**

- `docs/features/feature-intent-f01-6-secure-document-listing.md`;
- `docs/action-plans/action-plan-f01-6-secure-document-listing.md`;

**Verificação**

```bash
git add --   docs/features/feature-intent-f01-6-secure-document-listing.md   docs/action-plans/action-plan-f01-6-secure-document-listing.md
git commit -m "docs: close F01.6 secure document listing"
git push origin feature/f01-secure-document-ingestion
```

**Resultado esperado**

- itens IN concluídos;
- itens OUT preservados;
- commit de implementação registrado;
- H1 e H2 registrados;
- commit documental separado;
- working tree limpa e sincronização `0 0`;

**Status:** Pending

---

## Checkpoint Humano H2

Executar depois dos testes integrados, rebuild, OpenAPI, Quality Gate e
validação de resíduos; executar antes do staging e commit de implementação.

### Pacote obrigatório

- branch, baseline e sincronização;
- estado Git e superfície;
- patch integral e SHA-256;
- suíte completa e testes específicos;
- Ruff, mypy, I-001 e `git diff --check`;
- componentes protegidos;
- PDFs e área privada;
- resíduos PostgreSQL;
- containers, migration, health e OpenAPI;
- confirmação de nenhum commit de implementação.

### Critérios

- comportamento corresponde ao Feature Intent;
- `404` para avaliação inexistente;
- `[]` para avaliação existente sem documentos;
- isolamento entre avaliações;
- ordenação determinística;
- schema público seguro;
- nenhuma leitura de storage;
- mensagens sanitizadas;
- sessão por request;
- integração real aprovada;
- Quality Gate aprovado;
- nenhum commit de implementação.

### Registro

- **Status:** Pending
- **Aprovado por:** pendente
- **Data:** pendente
- **Pendências:** pendente
- **Evidências:** pendente

---

## 4. Matriz de Rastreabilidade

| Requisito                | Implementação                  | Evidência                  |
| ------------------------ | ------------------------------ | -------------------------- |
| GET por avaliação        | router documental              | API e OpenAPI              |
| 404 para inexistente     | serviço + router               | unitário, API e integração |
| 200 e lista vazia        | serviço + router               | unitário, API e integração |
| isolamento               | filtro SQLAlchemy              | adapter e integração       |
| ordenação                | `ORDER BY created_at, id`      | adapter e integração       |
| seis campos públicos     | schema reutilizado             | API e integração           |
| sem storage key/SHA/path | response model                 | testes negativos           |
| sem leitura de storage   | arquitetura                    | testes e diff              |
| PostgreSQL real          | adapter                        | integração                 |
| erros sanitizados        | serviço + router               | API                        |
| sem migration            | superfície protegida           | diff                       |
| sem dados reais          | fixtures sintéticas            | Git e testes               |
| processamento local      | ausência de integração externa | health e diff              |
| Quality Gates            | scripts existentes             | pacote H2                  |

---

## 5. Riscos e Mitigações

### Acesso cruzado

- filtro obrigatório por `evaluation_id`;
- teste da query;
- integração com duas avaliações.

### Ordenação instável

- `ORDER BY` explícito;
- UUID como desempate;
- teste com timestamps iguais.

### Vazamento de metadados

- schema explícito;
- conjunto exato de chaves;
- OpenAPI validado.

### Acoplamento ao storage

- serviço depende apenas da persistência;
- factory sem settings ou storage;
- integração sem arquivos.

### Regressão do upload

- preservar o POST;
- executar testes F01.5;
- validar GET e POST no OpenAPI.

### Erro interno exposto

- erros específicos;
- mensagens constantes;
- `str(exc)` proibido;
- causa interna preservada.

### Expansão prematura

- paginação, filtros, UI, download e exclusão permanecem OUT;
- superfície congelada;
- Stop Rule para mudança adicional.

---

## 6. Quality Gates

Obrigatórios:

1. suíte completa;
2. testes específicos F01.6;
3. regressão F01.5;
4. Ruff;
5. mypy;
6. I-001;
7. `git diff --check`;
8. OpenAPI;
9. PostgreSQL real;
10. containers;
11. migration;
12. health;
13. ausência de PDFs;
14. ausência de dados privados;
15. ausência de resíduos;
16. superfície autorizada;
17. H1;
18. H2.

Falha em qualquer gate impede o commit da implementação.

---

## 7. Critérios de Conclusão

A F01.6 estará concluída quando:

- Action Plan aprovado e commitado antes da implementação;
- porta, adapter, serviço, dependência e endpoint implementados;
- POST preservado;
- `404`, `[]`, isolamento e ordenação comprovados;
- schema seguro e ausência de storage comprovados;
- testes unitários, de contrato e integrados aprovados;
- Quality Gates aprovados;
- H1 e H2 aprovados;
- commit de implementação separado;
- Feature Intent e Action Plan em `Done`;
- commit documental separado;
- branch sincronizada;
- working tree limpa.

---

## 8. Aprovação

- [x] **Human Lead Engineer aprovou este Action Plan**
- **Data da aprovação:** 2026-07-30
- **Observações:** Action Plan corrigido aprovado. A superfície autorizada inclui os fakes de persistência dos testes de upload exclusivamente para compatibilidade estrutural com a porta atualizada.
