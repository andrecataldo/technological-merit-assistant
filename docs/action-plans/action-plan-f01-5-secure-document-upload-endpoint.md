# Action Plan F01.5 — Endpoint Seguro de Upload de Documentos

## 1. Identificação

- **Projeto:** Assistente de Avaliação de Mérito Tecnológico
- **Feature:** F01.5 — Endpoint Seguro de Upload de Documentos
- **Feature pai:** F01 — Ingestão Segura de Documentos
- **Feature Intent:** `feature-intent-f01-5-secure-document-upload-endpoint.md`
- **MCP+ aplicável:** MCP+ 001 v1.1
- **Dependências funcionais:**
  - F01.1 — Modelo de Documento e Migration;
  - F01.2 — Serviço Local de Armazenamento Seguro;
  - F01.3 — Validação de PDF, Limite de Tamanho e SHA-256;
  - F01.4 — Orquestração Segura do Upload e Persistência.
- **Branch:** `feature/f01-secure-document-ingestion`
- **Baseline de planejamento:** `96d3cf5`
- **Data:** 2026-07-29
- **Responsável humano:** André Cataldo
- **Status:** Done

---

## 2. Verificação de Prontidão

- Feature Intent F01.5 aprovado.
- Feature Intent registrado no commit `96d3cf5`.
- F01.1 concluído.
- F01.2 concluído.
- F01.3 concluído.
- F01.4 concluído.
- `DocumentUploadService` disponível e validado.
- `DocumentValidationService` disponível e validado.
- `LocalDocumentStorage` disponível e validado.
- `SqlAlchemyDocumentPersistence` disponível e validado.
- FastAPI configurado de forma síncrona.
- SQLAlchemy configurado de forma síncrona.
- Sessão PostgreSQL disponível por `get_db_session`.
- PostgreSQL na revisão `0002_add_documents (head)`.
- Nenhuma migration nova necessária.
- Nenhuma alteração de entidade ou modelo necessária.
- Uma dependência de runtime nova autorizada: `python-multipart`.
- Nenhuma interface Streamlit necessária.
- Nenhum endpoint de listagem, download ou exclusão necessário.
- Nenhum processamento externo autorizado.
- Nenhum conflito identificado com o MCP+ 001 v1.1.
- Nenhuma Decision Lock precisa ser alterada.
- Working tree limpa e branch sincronizada no início do planejamento.

---

## 3.1 Objetivo do Plano

Implementar uma porta HTTP segura para o caso de uso já existente de upload
documental.

O incremento deverá disponibilizar:

- endpoint `POST /evaluations/{evaluation_id}/documents`;
- recebimento de um único arquivo no campo multipart `file`;
- adaptação direta de `UploadFile.file` para `DocumentUploadService.upload()`;
- composição das dependências por request;
- schema público sem `storage_key`, caminho físico ou SHA-256;
- tradução explícita de exceções conhecidas;
- respostas HTTP sanitizadas;
- testes unitários da camada HTTP;
- teste integrado com PostgreSQL real e armazenamento temporário;
- validação operacional do endpoint;
- preservação dos Quality Gates existentes.

O incremento não incluirá:

- interface Streamlit;
- listagem de documentos;
- download;
- exclusão;
- autenticação;
- autorização;
- rate limiting;
- antivírus;
- extração de texto;
- OCR;
- páginas;
- embeddings;
- RAG;
- LLM;
- processamento assíncrono;
- processamento externo;
- migration;
- alteração de entidades ou modelos;
- alteração de contratos ou serviços da F01.1–F01.4;
- tratamento global de exceções da API;
- refatoração geral dos endpoints existentes.

---

## 3.2 Estratégia Geral

A implementação será dividida em mudanças pequenas e verificáveis:

1. confirmar o baseline técnico e documental;
2. adicionar a dependência multipart autorizada;
3. criar o schema público da resposta;
4. criar a composição do `DocumentUploadService`;
5. criar o router e o endpoint síncrono;
6. implementar a tradução explícita de erros HTTP;
7. criar e aprovar os testes unitários da camada HTTP;
8. executar o Checkpoint Humano H1;
9. criar os testes integrados com PostgreSQL e storage temporário;
10. reconstruir e validar a aplicação em containers;
11. executar o Quality Gate completo;
12. executar o Checkpoint Humano H2;
13. criar e enviar o commit de implementação;
14. atualizar e encerrar os artefatos documentais.

### Decisões técnicas do plano

- O endpoint será implementado em um `APIRouter` dedicado.
- O router ficará em `src/merit_assistant/api/routes/documents.py`.
- O arquivo `src/merit_assistant/api/main.py` apenas incluirá o router.
- A composição do caso de uso ficará em
  `src/merit_assistant/api/dependencies.py`.
- A composição não criará container genérico de dependências.
- A composição receberá a `Session` pelo `Depends(get_db_session)`.
- `SqlAlchemyDocumentPersistence` receberá a sessão do request.
- A sessão não será criada nem fechada pelo adapter ou pelo serviço.
- Não existirá sessão global.
- Não existirá `DocumentUploadService` global contendo uma sessão.
- `DocumentUploadService` será criado por request.
- A dependência `get_document_upload_service` será sobrescrevível nos testes.
- O endpoint será síncrono.
- O endpoint receberá `UploadFile` por `File(...)`.
- O nome do campo multipart será exatamente `file`.
- O endpoint passará `file.file` diretamente ao serviço.
- O endpoint não executará `file.read()`.
- O endpoint não executará `await file.read()`.
- O endpoint não converterá o conteúdo para `bytes`.
- O endpoint não criará outro arquivo temporário.
- O endpoint não fechará o fluxo antes da conclusão do serviço.
- O FastAPI continuará responsável pelo ciclo de vida do `UploadFile`.
- O endpoint chamará `DocumentUploadService.upload()` uma única vez.
- A entidade retornada pelo serviço será convertida diretamente para o schema.
- Não haverá nova consulta ao banco depois do upload.
- Erros conhecidos serão traduzidos localmente pelo router.
- Não será capturado `Exception` de forma genérica.
- Mensagens públicas serão constantes e sanitizadas.
- `str(exception)` nunca será enviado ao cliente.
- O schema não incluirá `storage_key`.
- O schema não incluirá SHA-256.
- O schema não incluirá caminho físico.
- O schema não incluirá conteúdo.
- O endpoint não adicionará logs com filename, conteúdo, hash ou storage key.
- A dependência multipart será `python-multipart>=0.0.32,<0.1`.
- Nenhuma outra dependência será adicionada.
- Nenhuma migration será criada ou modificada.
- Nenhum serviço das etapas anteriores será alterado.
- Nenhum commit de implementação será feito antes da aprovação do H2.

---

## 3.3 Superfície Final Prevista

### Arquivos de produção criados

- `src/merit_assistant/api/dependencies.py`;
- `src/merit_assistant/api/routes/__init__.py`;
- `src/merit_assistant/api/routes/documents.py`.

### Arquivos de produção alterados

- `pyproject.toml`;
- `src/merit_assistant/api/main.py`;
- `src/merit_assistant/api/schemas.py`.

### Arquivos de teste criados

- `tests/test_document_upload_api.py`;
- `tests/test_document_upload_api_integration.py`.

### Arquivos documentais

- `docs/features/feature-intent-f01-5-secure-document-upload-endpoint.md`;
- `docs/action-plans/action-plan-f01-5-secure-document-upload-endpoint.md`.

### Arquivos protegidos

Não deverão ser alterados:

- `alembic.ini`;
- `migrations/`;
- `src/merit_assistant/domain/entities.py`;
- `src/merit_assistant/infrastructure/db/models.py`;
- `src/merit_assistant/infrastructure/db/session.py`;
- `src/merit_assistant/application/ports/document_persistence.py`;
- `src/merit_assistant/application/ports/document_storage.py`;
- `src/merit_assistant/application/ports/pdf_inspector.py`;
- `src/merit_assistant/application/services/document_upload.py`;
- `src/merit_assistant/application/services/document_validation.py`;
- `src/merit_assistant/infrastructure/db/document_persistence.py`;
- `src/merit_assistant/infrastructure/storage/`;
- `src/merit_assistant/infrastructure/pdf/`;
- interface Streamlit;
- PDFs reais;
- arquivos em `data/private`.

Qualquer necessidade de alteração fora dessa superfície exige interrupção da
implementação e nova aprovação humana.

---

## 3.4 Contratos da Implementação

### 3.4.1 Dependência multipart

Adicionar em `pyproject.toml`:

```toml
"python-multipart>=0.0.32,<0.1",
```

Regras:

- manter ordenação coerente com as dependências existentes;
- não adicionar pacote chamado `multipart`;
- atualizar o ambiente virtual;
- reconstruir a imagem Docker;
- confirmar a importação da aplicação;
- confirmar a geração do OpenAPI;
- registrar a versão efetivamente instalada.

Verificações previstas:

```bash
python -m pip install -e '.[dev]'
python -m pip show python-multipart
python -c "import multipart; print(multipart.__version__)"
```

### 3.4.2 Schema público

Adicionar em `src/merit_assistant/api/schemas.py`:

```python
class DocumentUploadResponse(BaseModel):
    id: UUID
    evaluation_id: UUID
    original_filename: str
    content_type: str
    size_bytes: int
    created_at: datetime
```

Regras:

- não incluir `storage_key`;
- não incluir `sha256`;
- não incluir caminho físico;
- não incluir conteúdo;
- não incluir informações de compensação;
- não incluir informações de persistência;
- converter a entidade com `model_validate(..., from_attributes=True)` ou
  configuração equivalente;
- preservar o padrão atual de schemas simples do projeto.

### 3.4.3 Composição das dependências

Criar `src/merit_assistant/api/dependencies.py`.

Assinatura prevista:

```python
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

DatabaseSession = Annotated[Session, Depends(get_db_session)]


def get_document_upload_service(
    session: DatabaseSession,
) -> DocumentUploadService:
    settings = get_settings()
    inspector = PyMuPdfInspector()
    validator = DocumentValidationService.from_settings(inspector, settings)
    storage = LocalDocumentStorage.from_settings(settings)
    persistence = SqlAlchemyDocumentPersistence(session)

    return DocumentUploadService(
        validator=validator,
        storage=storage,
        persistence=persistence,
    )


DocumentUploadServiceDependency = Annotated[
    DocumentUploadService,
    Depends(get_document_upload_service),
]
```

A assinatura poderá ser ajustada durante a implementação para atender Ruff e
mypy, sem modificar as decisões arquiteturais.

Regras:

- `get_db_session` continuará sendo o dono da sessão;
- a fábrica não executará commit;
- a fábrica não executará rollback;
- a fábrica não fechará a sessão;
- a fábrica não armazenará sessão ou serviço em cache;
- `get_settings()` poderá manter o cache já existente;
- `LocalDocumentStorage.from_settings()` utilizará o diretório privado
  configurado;
- o serviço será criado somente após a resolução da sessão;
- a dependência será substituível em testes com
  `app.dependency_overrides`.

### 3.4.4 Router documental

Criar `src/merit_assistant/api/routes/documents.py`.

Estrutura prevista:

```python
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, HTTPException, UploadFile, status

router = APIRouter(tags=["documents"])


@router.post(
    "/evaluations/{evaluation_id}/documents",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_document(
    evaluation_id: UUID,
    file: Annotated[UploadFile, File(...)],
    service: DocumentUploadServiceDependency,
) -> DocumentUploadResponse:
    ...
```

A ordem dos parâmetros poderá ser ajustada para atender a sintaxe Python e o
modelo de dependências do FastAPI.

Regras:

- `evaluation_id` será validado pelo FastAPI como UUID;
- campo multipart ausente será validado pelo FastAPI;
- `file.filename` ausente ou vazio será rejeitado antes do serviço;
- `file.content_type` será encaminhado sem normalização local;
- `file.file` será encaminhado diretamente;
- o endpoint não executará lógica de validação documental;
- o endpoint não executará lógica de armazenamento;
- o endpoint não executará lógica de persistência;
- o endpoint não executará compensação;
- o endpoint não fará consulta adicional ao banco;
- o endpoint não fechará `file.file`;
- o endpoint retornará `DocumentUploadResponse`;
- o endpoint não retornará a entidade `Document` diretamente.

### 3.4.5 Inclusão do router

Alterar `src/merit_assistant/api/main.py` apenas para importar e incluir o router:

```python
from merit_assistant.api.routes.documents import router as documents_router

app.include_router(documents_router)
```

Regras:

- preservar os endpoints existentes;
- preservar `DatabaseSession` existente em `main.py`;
- não mover os endpoints existentes nesta iteração;
- não criar prefixo global;
- não alterar o contrato de `/health`, `/profiles` ou `/evaluations`;
- não alterar a versão da API;
- não adicionar middleware;
- não adicionar handler global.

---

## 3.5 Matriz de Tradução HTTP

### Erros de validação e request

| Origem                         | HTTP | Detail público                                  |
| ------------------------------ | ---: | ----------------------------------------------- |
| UUID inválido no path          |  422 | Resposta padrão do FastAPI                      |
| Campo `file` ausente           |  422 | Resposta padrão do FastAPI                      |
| `filename` ausente ou vazio    |  422 | `Nome de arquivo inválido.`                     |
| `InvalidOriginalFilenameError` |  422 | `Nome de arquivo inválido.`                     |
| `OriginalFilenameTooLongError` |  422 | `Nome de arquivo inválido.`                     |
| `EmptyDocumentError`           |  422 | `O documento está vazio.`                       |
| `InvalidPdfError`              |  422 | `O arquivo enviado não é um PDF válido.`        |
| `NonSeekableDocumentError`     |  422 | `Não foi possível processar o arquivo enviado.` |
| `UnsupportedContentTypeError`  |  415 | `Tipo de conteúdo não suportado.`               |
| `DocumentTooLargeError`        |  413 | `O documento excede o limite permitido.`        |

### Erros de recurso e conflito

| Origem                    | HTTP | Detail público                        |
| ------------------------- | ---: | ------------------------------------- |
| `EvaluationNotFoundError` |  404 | `Avaliação não encontrada.`           |
| `DuplicateDocumentError`  |  409 | `Documento já associado à avaliação.` |

### Erros internos conhecidos

| Origem                           | HTTP | Detail público                                     |
| -------------------------------- | ---: | -------------------------------------------------- |
| `StoredContentMismatchError`     |  500 | `Não foi possível concluir o upload do documento.` |
| `DocumentUploadPersistenceError` |  500 | `Não foi possível concluir o upload do documento.` |
| `DocumentCompensationError`      |  500 | `Não foi possível concluir o upload do documento.` |
| `DocumentStorageError`           |  500 | `Não foi possível concluir o upload do documento.` |

### Implementação prevista

As exceções poderão ser agrupadas por status e mensagem:

```python
except (InvalidOriginalFilenameError, OriginalFilenameTooLongError) as exc:
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail="Nome de arquivo inválido.",
    ) from exc
```

Regras:

- preservar `raise ... from exc`;
- não usar `detail=str(exc)`;
- não retornar `repr(exc)`;
- não retornar `exc.__cause__`;
- não retornar atributos de `DocumentCompensationError`;
- não retornar nomes de constraints;
- não retornar paths;
- não retornar hashes;
- não registrar conteúdo;
- não capturar exceções desconhecidas;
- não transformar falhas desconhecidas em sucesso.

A constante FastAPI disponível para `422` será confirmada no ambiente instalado.
Caso `HTTP_422_UNPROCESSABLE_CONTENT` esteja disponível, ela será preferida.
Caso contrário, usar a constante oficial equivalente disponível, sem literal
mágico disperso.

---

## 3.6 Estratégia de Testes Unitários

Criar `tests/test_document_upload_api.py`.

### Abordagem

Os testes serão divididos em duas camadas:

1. testes diretos da função do endpoint;
2. testes HTTP com `TestClient` e override da dependência do serviço.

Essa divisão permitirá comprovar simultaneamente:

- identidade do fluxo `UploadFile.file`;
- ausência de leitura feita pelo endpoint;
- contrato multipart real;
- status e schema HTTP;
- tradução das exceções.

### Fake de serviço

Criar fake ou stub mínimo que:

- implemente `upload(...)`;
- registre quantidade de chamadas;
- registre `evaluation_id`;
- registre `original_filename`;
- registre `declared_content_type`;
- registre a identidade de `source`;
- retorne uma entidade `Document` sintética;
- possa ser configurado para lançar uma exceção específica;
- não leia o stream.

### Casos diretos da função

Comprovar:

- `file.file` é passado por identidade;
- `evaluation_id` é propagado sem transformação;
- filename é propagado;
- content type é propagado;
- o serviço é chamado uma única vez;
- filename ausente é rejeitado antes do serviço;
- o endpoint não chama `read()`;
- o endpoint não chama `close()`;
- a resposta é construída com os campos públicos;
- não há segunda consulta ao banco.

### Casos HTTP nominais

Comprovar:

- método `POST`;
- path correto;
- campo multipart `file`;
- status `201`;
- response content type JSON;
- resposta contém exatamente:
  - `id`;
  - `evaluation_id`;
  - `original_filename`;
  - `content_type`;
  - `size_bytes`;
  - `created_at`;
- resposta não contém `storage_key`;
- resposta não contém `sha256`;
- resposta não contém conteúdo;
- campo ausente retorna `422`;
- UUID inválido retorna `422`.

### Casos HTTP de erros

Criar teste parametrizado para:

- `InvalidOriginalFilenameError` → `422`;
- `OriginalFilenameTooLongError` → `422`;
- `EmptyDocumentError` → `422`;
- `InvalidPdfError` → `422`;
- `NonSeekableDocumentError` → `422`;
- `UnsupportedContentTypeError` → `415`;
- `DocumentTooLargeError` → `413`;
- `EvaluationNotFoundError` → `404`;
- `DuplicateDocumentError` → `409`;
- `StoredContentMismatchError` → `500`;
- `DocumentUploadPersistenceError` → `500`;
- `DocumentCompensationError` → `500`;
- `DocumentStorageError` → `500`.

Cada caso deverá confirmar:

- status exato;
- detail público exato;
- ausência da mensagem interna;
- ausência de hash;
- ausência de storage key;
- ausência de path;
- ausência de constraint;
- ausência de atributos de compensação.

### Isolamento dos testes

- usar `app.dependency_overrides[get_document_upload_service]`;
- restaurar `app.dependency_overrides` em `finally` ou fixture;
- não acessar PostgreSQL nos testes unitários;
- não escrever em `data/private`;
- não depender de ordem de execução;
- usar apenas dados sintéticos.

---

## 3.7 Checkpoint Humano H1

### Momento

Executar depois de:

- dependência multipart instalada;
- schema criado;
- composição criada;
- router criado;
- endpoint criado;
- tradução de erros implementada;
- testes unitários aprovados;
- Ruff aprovado no escopo alterado;
- mypy aprovado no escopo alterado;
- `git diff --check` aprovado;
- antes dos testes integrados;
- antes de qualquer commit de implementação.

### Pacote de revisão H1

O pacote deverá incluir:

- branch e commit-base;
- `git status --short`;
- `git diff --stat`;
- lista de arquivos alterados;
- diff completo da implementação parcial;
- versão instalada de `python-multipart`;
- resultado dos testes unitários;
- resultado do Ruff;
- resultado do mypy;
- resultado de `git diff --check`;
- confirmação de ausência de documentos privados;
- confirmação de ausência de alterações protegidas.

### Critérios de aprovação H1

- superfície compatível com o plano;
- nenhuma migration alterada;
- nenhum serviço da F01.1–F01.4 alterado;
- nenhuma sessão global;
- nenhum service global com sessão;
- dependência sobrescrevível;
- endpoint síncrono;
- uso direto de `UploadFile.file`;
- ausência de leitura no endpoint;
- schema público seguro;
- matriz de erros completa;
- mensagens sanitizadas;
- testes unitários suficientes;
- nenhuma dependência além de `python-multipart`;
- nenhum documento real presente;
- nenhum commit de implementação realizado.

### Registro

- **Status:** Approved
- **Aprovado por:** André Cataldo
- **Data:** 2026-07-29
- **Pendências:** Um warning externo e não bloqueante do FastAPI/Starlette TestClient sobre futura migração para httpx2.
- **Evidências:** 25 testes unitários F01.5 e 209 testes totais aprovados; Ruff, mypy e git diff --check aprovados; superfície protegida preservada; HTTP 422 atualizado para HTTP_422_UNPROCESSABLE_CONTENT.

---

## 3.8 Estratégia de Testes Integrados

Criar `tests/test_document_upload_api_integration.py`.

### Infraestrutura real

Utilizar:

- `TestClient`;
- aplicação FastAPI real;
- PostgreSQL configurado pelo projeto;
- sessão real;
- migration `0002_add_documents (head)`;
- `PyMuPdfInspector`;
- `DocumentValidationService`;
- `LocalDocumentStorage`;
- `SqlAlchemyDocumentPersistence`;
- `DocumentUploadService`;
- diretório temporário fora do repositório;
- PDFs sintéticos gerados no teste.

### Override integrado

Sobrescrever `get_document_upload_service` por uma dependência que:

- receba a sessão pelo `get_db_session`;
- use settings de teste ou composição explícita;
- use `LocalDocumentStorage` apontando para `tmp_path`;
- use `PyMuPdfInspector`;
- use `DocumentValidationService`;
- use `SqlAlchemyDocumentPersistence`;
- retorne `DocumentUploadService`;
- não crie nem feche sessão paralela.

### Dados sintéticos

Antes de cada cenário:

- gerar identificadores exclusivos;
- criar perfil sintético compatível ou reutilizar perfil controlado;
- criar avaliação sintética;
- gerar PDF mínimo válido com PyMuPDF;
- nunca usar documentos reais;
- nunca gravar o PDF no repositório;
- usar bytes apenas dentro da fixture/teste;
- usar diretório temporário do pytest.

### Cenário nominal

Comprovar:

- `POST` retorna `201`;
- resposta contém metadados públicos;
- `evaluation_id` corresponde ao path;
- `original_filename` corresponde ao multipart;
- `content_type` é `application/pdf`;
- `size_bytes` corresponde ao arquivo;
- `created_at` é serializado;
- documento foi persistido;
- arquivo foi criado no storage temporário;
- nome físico usa UUID;
- storage key segue o padrão aprovado;
- resposta não contém storage key;
- resposta não contém SHA-256;
- resposta não contém path;
- registro persistido possui SHA-256;
- registro persistido possui storage key;
- arquivo armazenado possui os bytes esperados.

### Cenário de duplicidade

- primeiro upload retorna `201`;
- segundo upload idêntico na mesma avaliação retorna `409`;
- somente um registro permanece no PostgreSQL;
- somente um arquivo permanece no storage temporário;
- resposta não expõe SHA-256 ou detalhes da constraint.

### Cenário de avaliação inexistente

- usar UUID inexistente;
- upload retorna `404`;
- nenhum documento é persistido;
- nenhum arquivo é criado.

### Cenário de PDF inválido

- enviar conteúdo sintético inválido com filename `.pdf`;
- usar content type `application/pdf`;
- upload retorna `422`;
- nenhum documento é persistido;
- nenhum arquivo é criado;
- resposta não expõe conteúdo recebido.

### Cenário de content type inválido

- enviar PDF sintético válido;
- declarar content type diferente de `application/pdf`;
- upload retorna `415`;
- nenhum documento é persistido;
- nenhum arquivo é criado.

### Cenário de limite

O limite será testado unitariamente por meio de exceção configurada no fake.
Um teste integrado com payload acima de 50 MB não será obrigatório nesta
iteração, para evitar custo e lentidão desnecessários. A integração do código
`413` será coberta pelo endpoint real com override de serviço que lança
`DocumentTooLargeError`.

### Limpeza defensiva

A fixture integrada deverá:

- conhecer previamente todos os identificadores sintéticos;
- executar rollback antes da limpeza;
- excluir documentos sintéticos;
- excluir avaliações sintéticas;
- excluir perfis sintéticos criados pelo teste;
- executar commit da limpeza quando aplicável;
- remover o diretório temporário;
- tolerar falhas parciais de setup;
- verificar ausência de resíduos;
- fechar recursos abertos;
- restaurar `app.dependency_overrides`.

A limpeza deverá permanecer segura mesmo quando:

- o setup falhar depois de um commit;
- o teste falhar antes do primeiro request;
- o upload falhar após criar arquivo;
- a tradução HTTP falhar;
- a asserção final falhar.

---

## 3.9 Etapas de Execução

### Etapa 1 — Confirmar baseline

**Descrição**

Confirmar branch, sincronização, artefatos aprovados e integridade técnica.

**Arquivos afetados**

Nenhum.

**Verificação**

```bash
git branch --show-current
git status --short
git fetch origin
git rev-list \
  --left-right \
  --count \
  HEAD...origin/feature/f01-secure-document-ingestion
git log -5 --oneline --decorate

test -f \
  docs/features/feature-intent-f01-5-secure-document-upload-endpoint.md

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
```

**Resultado esperado**

- branch correta;
- working tree limpa;
- sincronização `0 0`;
- Feature Intent aprovado;
- commit-base `96d3cf5`;
- testes aprovados;
- Ruff aprovado;
- mypy aprovado;
- I-001 aprovado;
- diff check aprovado;
- containers operacionais;
- banco em `0002_add_documents (head)`;
- health aprovado;
- processamento externo desabilitado;
- nenhum arquivo privado rastreado.

**Status:** Done

---

### Etapa 2 — Adicionar `python-multipart`

**Descrição**

Adicionar a dependência necessária ao parsing multipart e atualizar o ambiente.

**Arquivos afetados**

- `pyproject.toml`.

**Alteração prevista**

```toml
"python-multipart>=0.0.32,<0.1",
```

**Verificação**

```bash
python -m pip install -e '.[dev]'
python -m pip show python-multipart
python -c "import multipart; print(multipart.__version__)"
ruff check pyproject.toml
git diff --check
```

**Resultado esperado**

- dependência instalada;
- versão compatível confirmada;
- nenhuma outra dependência adicionada;
- aplicação importável;
- diff check aprovado.

**Status:** Done

---

### Etapa 3 — Criar schema público

**Descrição**

Criar `DocumentUploadResponse` com somente metadados públicos.

**Arquivos afetados**

- `src/merit_assistant/api/schemas.py`;
- `tests/test_document_upload_api.py`.

**Verificação**

```bash
pytest tests/test_document_upload_api.py -q
ruff check src/merit_assistant/api/schemas.py tests/test_document_upload_api.py
mypy src
git diff --check
```

**Resultado esperado**

- schema criado;
- campos permitidos presentes;
- campos internos ausentes;
- conversão por atributos aprovada;
- testes aprovados.

**Status:** Done

---

### Etapa 4 — Criar composição do serviço

**Descrição**

Criar dependência FastAPI que componha o caso de uso com a sessão do request.

**Arquivos afetados**

- `src/merit_assistant/api/dependencies.py`;
- `tests/test_document_upload_api.py`.

**Verificação**

```bash
pytest tests/test_document_upload_api.py -q
ruff check \
  src/merit_assistant/api/dependencies.py \
  tests/test_document_upload_api.py
mypy src
git diff --check
```

**Resultado esperado**

- sessão recebida por dependência;
- adapter criado com a sessão;
- serviço criado por request;
- nenhuma sessão global;
- dependência sobrescrevível;
- nenhum commit ou close executado pela fábrica.

**Status:** Done

---

### Etapa 5 — Criar router e endpoint

**Descrição**

Implementar o endpoint síncrono e incluir o router na aplicação.

**Arquivos afetados**

- `src/merit_assistant/api/routes/__init__.py`;
- `src/merit_assistant/api/routes/documents.py`;
- `src/merit_assistant/api/main.py`;
- `tests/test_document_upload_api.py`.

**Verificação**

```bash
pytest tests/test_document_upload_api.py -q
ruff check \
  src/merit_assistant/api \
  tests/test_document_upload_api.py
mypy src
git diff --check
```

**Resultado esperado**

- endpoint registrado;
- campo multipart obrigatório;
- status `201`;
- uso direto de `UploadFile.file`;
- chamada única ao serviço;
- resposta segura;
- endpoints existentes preservados.

**Status:** Done

---

### Etapa 6 — Implementar tradução HTTP

**Descrição**

Traduzir todas as exceções conhecidas conforme a matriz aprovada.

**Arquivos afetados**

- `src/merit_assistant/api/routes/documents.py`;
- `tests/test_document_upload_api.py`.

**Verificação**

```bash
pytest tests/test_document_upload_api.py -q
ruff check \
  src/merit_assistant/api/routes/documents.py \
  tests/test_document_upload_api.py
mypy src
git diff --check
```

**Resultado esperado**

- códigos HTTP corretos;
- mensagens públicas constantes;
- nenhuma mensagem interna exposta;
- nenhuma captura genérica;
- encadeamento interno preservado;
- testes parametrizados aprovados.

**Status:** Done

---

### Etapa 7 — Consolidar testes unitários

**Descrição**

Concluir a cobertura unitária do endpoint e da composição.

**Arquivos afetados**

- `tests/test_document_upload_api.py`.

**Verificação**

```bash
pytest tests/test_document_upload_api.py -q
pytest tests/test_health.py -q
ruff check src tests
mypy src
git diff --check
```

**Resultado esperado**

- fluxo nominal aprovado;
- identidade do stream comprovada;
- ausência de leitura local comprovada;
- matriz de erros aprovada;
- schema seguro comprovado;
- health preservado.

**Status:** Done

---

### Etapa 8 — Executar H1

**Descrição**

Preparar pacote de revisão e obter aprovação humana antes dos testes integrados.

**Arquivos afetados**

Nenhum arquivo novo além da implementação em revisão.

**Resultado esperado**

- pacote H1 completo;
- nenhuma alteração fora do escopo;
- nenhuma alteração protegida;
- aprovação humana registrada;
- nenhuma implementação commitada.

**Status:** Done

---

### Etapa 9 — Criar testes integrados

**Descrição**

Validar o endpoint real com PostgreSQL e armazenamento temporário.

**Arquivos afetados**

- `tests/test_document_upload_api_integration.py`.

**Verificação**

```bash
pytest tests/test_document_upload_api_integration.py -q
ruff check tests/test_document_upload_api_integration.py
mypy src
git diff --check
```

**Resultado esperado**

- nominal `201`;
- duplicidade `409`;
- avaliação inexistente `404`;
- PDF inválido `422`;
- content type inválido `415`;
- persistência real comprovada;
- storage real comprovado;
- resposta segura comprovada;
- limpeza defensiva aprovada;
- zero resíduos.

**Status:** Done

---

### Etapa 10 — Reconstruir e validar containers

**Descrição**

Atualizar a imagem com `python-multipart` e validar a aplicação operacional.

**Arquivos afetados**

Nenhum arquivo adicional.

**Verificação**

```bash
docker compose build --no-cache
docker compose up -d
docker compose ps

alembic current

curl -fsS http://localhost:8000/health

python - <<'PY'
from merit_assistant.api.main import app

schema = app.openapi()
path = "/evaluations/{evaluation_id}/documents"

assert path in schema["paths"]
assert "post" in schema["paths"][path]
print("OpenAPI F01.5: OK")
PY
```

**Resultado esperado**

- build aprovado;
- containers operacionais;
- banco na revisão correta;
- health aprovado;
- processamento externo desabilitado;
- rota presente no OpenAPI.

**Status:** Done

---

### Etapa 11 — Quality Gate completo

**Descrição**

Executar todos os controles técnicos e de escopo.

**Verificação**

```bash
pytest
ruff check .
mypy src
./scripts/verify_i001_scope.sh
git diff --check

git status --short
git diff --stat
git diff --name-status

git ls-files data/private
git ls-files '*.pdf'
```

Validar também:

```bash
docker compose ps
alembic current
curl -fsS http://localhost:8000/health
```

**Resultado esperado**

- suíte completa aprovada;
- Ruff aprovado;
- mypy aprovado;
- I-001 aprovado;
- diff check aprovado;
- aplicação operacional;
- banco em `0002_add_documents (head)`;
- health aprovado;
- processamento externo desabilitado;
- nenhum PDF real rastreado;
- nenhum arquivo privado rastreado;
- nenhuma alteração fora do escopo;
- zero dados sintéticos residuais;
- zero arquivos órfãos.

**Status:** Done

---

### Etapa 12 — Executar H2

**Descrição**

Realizar revisão semântica final antes do commit de implementação.

**Pacote H2**

Incluir:

- branch e baseline;
- status completo;
- lista de arquivos alterados;
- diff integral;
- hash SHA-256 do patch;
- versão de `python-multipart`;
- resultado da suíte completa;
- resultado dos testes integrados;
- resultado do Ruff;
- resultado do mypy;
- resultado do I-001;
- resultado de `git diff --check`;
- estado dos containers;
- revisão do banco;
- resposta do health;
- OpenAPI validado;
- confirmação de ausência de arquivos privados;
- confirmação de ausência de PDFs reais;
- confirmação de zero resíduos;
- confirmação de nenhuma expansão de escopo.

**Critérios de aprovação**

- comportamento corresponde ao Feature Intent;
- endpoint não lê o arquivo;
- endpoint não fecha o arquivo;
- serviço chamado uma única vez;
- schema não expõe campos internos;
- matriz HTTP completa;
- mensagens sanitizadas;
- sessão administrada pelo request;
- dependência sobrescrevível;
- testes suficientes;
- integração real aprovada;
- superfície de arquivos correta;
- Quality Gate aprovado;
- nenhum commit de implementação realizado.

**Registro**

- **Status:** Done
- **Aprovado por:** pendente
- **Data:** pendente
- **Pendências:** pendente
- **Evidências:** pendente

---

### Etapa 13 — Commit e push da implementação

**Pré-condição**

H2 aprovado pelo Human Lead Engineer.

**Staging seletivo previsto**

Somente:

- `pyproject.toml`;
- `src/merit_assistant/api/main.py`;
- `src/merit_assistant/api/schemas.py`;
- `src/merit_assistant/api/dependencies.py`;
- `src/merit_assistant/api/routes/__init__.py`;
- `src/merit_assistant/api/routes/documents.py`;
- `tests/test_document_upload_api.py`;
- `tests/test_document_upload_api_integration.py`.

**Mensagem prevista**

```text
feat: add secure document upload endpoint
```

**Verificação**

```bash
git diff --cached --name-status
git diff --cached --check
git status --short

git commit -m "feat: add secure document upload endpoint"
git push origin feature/f01-secure-document-ingestion
```

**Resultado esperado**

- exatamente os arquivos autorizados em staging;
- nenhum artefato documental misturado ao commit;
- nenhum arquivo protegido alterado;
- commit criado;
- push concluído;
- branch remota atualizada.

**Status:** Done

---

### Etapa 14 — Encerramento documental

**Descrição**

Registrar resultados reais, commits e conclusão da F01.5.

**Arquivos afetados**

- Feature Intent F01.5;
- Action Plan F01.5.

**Atualizações previstas**

- registrar commit de implementação;
- atualizar Feature Intent para `Done`;
- marcar itens IN concluídos;
- manter itens OUT não executados;
- atualizar Action Plan para `Done`;
- registrar resultados reais dos testes;
- registrar versão efetiva de `python-multipart`;
- registrar estado do banco;
- registrar health;
- registrar H1;
- registrar H2;
- registrar ausência de resíduos;
- registrar ausência de expansão de escopo.

**Mensagem prevista**

```text
docs: close F01.5 secure document upload endpoint
```

**Verificação**

```bash
git add -- \
  docs/features/feature-intent-f01-5-secure-document-upload-endpoint.md \
  docs/action-plans/action-plan-f01-5-secure-document-upload-endpoint.md

git diff --cached --name-status
git diff --cached --check

git commit -m "docs: close F01.5 secure document upload endpoint"
git push origin feature/f01-secure-document-ingestion

git fetch origin
git status --short
git rev-list \
  --left-right \
  --count \
  HEAD...origin/feature/f01-secure-document-ingestion
git log -3 --oneline --decorate
```

**Resultado esperado**

- commit documental criado;
- push concluído;
- working tree limpa;
- sincronização `0 0`;
- F01.5 registrada como `Done`.

**Status:** Done

---

## 4. Quality Gates Obrigatórios

### QG-01 — Testes

```bash
pytest
```

Critério:

- todos os testes aprovados;
- warnings avaliados;
- nenhum teste pulado sem justificativa aprovada.

### QG-02 — Ruff

```bash
ruff check .
```

Critério:

- zero erros.

### QG-03 — mypy

```bash
mypy src
```

Critério:

- zero erros.

### QG-04 — Escopo I-001

```bash
./scripts/verify_i001_scope.sh
```

Critério:

- aprovado.

### QG-05 — Integridade Git

```bash
git diff --check
git status --short
```

Critério:

- zero erros de whitespace;
- somente arquivos autorizados modificados.

### QG-06 — Segurança documental

```bash
git ls-files data/private
git ls-files '*.pdf'
```

Critério:

- nenhum arquivo privado;
- nenhum PDF real.

### QG-07 — Banco

```bash
alembic current
```

Critério:

- `0002_add_documents (head)`.

### QG-08 — Aplicação

```bash
docker compose ps
curl -fsS http://localhost:8000/health
```

Critério:

- serviços operacionais;
- health `ok`;
- processamento externo desabilitado.

### QG-09 — OpenAPI

Critério:

- path documental presente;
- método POST presente;
- request multipart presente;
- response `201` presente;
- schema público sem campos internos.

### QG-10 — Resíduos

Critério:

- zero registros sintéticos residuais;
- zero arquivos sintéticos residuais;
- zero arquivos órfãos;
- overrides de dependência restaurados.

---

## 5. Riscos de Execução

### R-01 — Leitura duplicada na camada HTTP

**Controle**

- teste direto da identidade do stream;
- fake que não lê o conteúdo;
- revisão semântica do endpoint;
- proibição de `file.read()`.

### R-02 — Exposição de metadados internos

**Controle**

- schema explícito;
- teste de conjunto exato de chaves;
- teste negativo para `storage_key`, `sha256` e path.

### R-03 — Vazamento por exceções

**Controle**

- mensagens constantes;
- teste parametrizado de todas as exceções;
- proibição de `str(exc)` no detail;
- revisão de respostas `500`.

### R-04 — Sessão global

**Controle**

- sessão recebida por `Depends`;
- adapter criado por request;
- revisão da composição;
- teste de override da dependência.

### R-05 — Dependência multipart incorreta

**Controle**

- instalar somente `python-multipart`;
- não instalar `multipart`;
- registrar versão;
- importar aplicação;
- validar OpenAPI;
- reconstruir imagem.

### R-06 — Falha de cleanup integrado

**Controle**

- identificadores conhecidos antes do setup;
- limpeza em fixture defensiva;
- rollback inicial;
- cleanup após commits parciais;
- verificação final de resíduos.

### R-07 — Captura genérica mascarando defeitos

**Controle**

- não capturar `Exception`;
- mapear somente exceções conhecidas;
- manter falhas desconhecidas visíveis durante os testes.

### R-08 — Expansão para listagem ou UI

**Controle**

- limitar a rota ao POST;
- proibir Streamlit;
- proibir GET, DELETE e download;
- revisar a superfície no H1 e H2.

### R-09 — Alteração indevida dos serviços existentes

**Controle**

- tratar arquivos da F01.1–F01.4 como protegidos;
- revisar `git diff --name-status`;
- interromper a implementação caso surja necessidade de alteração.

### R-10 — Divergência entre ambiente local e container

**Controle**

- reinstalar ambiente;
- rebuild sem cache;
- validar versão instalada;
- executar teste operacional no container.

---

## 6. Critérios de Conclusão

A F01.5 poderá ser considerada concluída somente quando:

1. Feature Intent estiver aprovado;
2. Action Plan estiver aprovado;
3. `python-multipart` estiver declarado e instalado;
4. endpoint POST estiver disponível;
5. contrato multipart estiver correto;
6. endpoint usar `UploadFile.file`;
7. endpoint não fizer leitura integral;
8. endpoint não fechar o stream;
9. `DocumentUploadService` for chamado uma vez;
10. schema público estiver correto;
11. `storage_key` não for exposta;
12. SHA-256 não for exposto;
13. path físico não for exposto;
14. matriz HTTP estiver implementada;
15. mensagens estiverem sanitizadas;
16. sessão for administrada pelo request;
17. testes unitários estiverem aprovados;
18. testes integrados estiverem aprovados;
19. Quality Gates estiverem aprovados;
20. H1 estiver aprovado;
21. H2 estiver aprovado;
22. commit de implementação estiver criado e enviado;
23. artefatos estiverem atualizados para `Done`;
24. commit documental estiver criado e enviado;
25. working tree estiver limpa;
26. branch estiver sincronizada;
27. nenhum documento real estiver versionado;
28. nenhum resíduo sintético permanecer;
29. nenhuma expansão de escopo tiver ocorrido.

---

## 7. Mensagens de Commit Previstas

### Aprovação do Action Plan

```text
docs: approve F01.5 secure document upload endpoint action plan
```

### Implementação

```text
feat: add secure document upload endpoint
```

### Encerramento

```text
docs: close F01.5 secure document upload endpoint
```

---


## 7.1 Registro de Encerramento

- **Status final:** Done
- **Data de conclusão:** 2026-07-29
- **Commit de implementação:** `b9fddd28c9ca9af15676acc7364a2f675e9e1b58`
- **Commit documental:** este commit de encerramento
- **Dependência instalada:** `python-multipart 0.0.32`
- **Testes unitários F01.5:** 25 aprovados
- **Testes integrados F01.5:** 5 aprovados
- **Suíte completa:** 214 testes aprovados
- **Quality Gates:** pytest, Ruff, mypy, I-001 e `git diff --check` aprovados
- **Warning avaliado:** 1 warning externo e não bloqueante do FastAPI/Starlette TestClient
- **Containers:** API, UI e PostgreSQL operacionais
- **Banco:** `0002_add_documents (head)`
- **Health:** `{"status":"ok","external_processing_enabled":false}`
- **OpenAPI:** endpoint POST, multipart e seis campos públicos aprovados
- **H1:** Approved
- **H2:** Approved
- **Resíduos PostgreSQL:** zero
- **Arquivos sintéticos residuais:** zero
- **PDFs reais rastreados:** zero
- **Arquivos privados rastreados:** somente `data/private/.gitkeep`
- **Componentes protegidos alterados:** nenhum
- **Expansão de escopo:** nenhuma
- **Branch após implementação:** sincronizada com o remoto

---

## 8. Aprovação

- [x] **Human Lead Engineer aprovou este Action Plan**
- **Data da aprovação:** 2026-07-29
- **Observações:** Aprovado sem pendências bloqueantes.
