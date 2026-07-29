# Feature Intent F01.5 — Endpoint Seguro de Upload de Documentos

## 1. Identificação

- **Título da Feature:** F01.5 — Endpoint Seguro de Upload de Documentos
- **Feature pai:** F01 — Ingestão Segura de Documentos
- **Autor — Human Lead Engineer:** André Cataldo
- **Data:** 2026-07-29
- **Status:** Approved
- **Branch:** `feature/f01-secure-document-ingestion`
- **Baseline:** `38b22962dbb032620eea8772b0db35e7e0159640`
- **MCP+ aplicável:** MCP+ 001 v1.1
- **Dependências funcionais:**
  - F01.1 — Modelo de Documento e Migration;
  - F01.2 — Serviço Local de Armazenamento Seguro;
  - F01.3 — Validação de PDF, Limite de Tamanho e SHA-256;
  - F01.4 — Orquestração Segura do Upload e Persistência.

---

## 2. Contexto e Problema

A aplicação já possui um caso de uso capaz de:

- confirmar a existência da avaliação;
- validar o PDF;
- calcular tamanho e SHA-256;
- detectar duplicidade;
- armazenar o conteúdo em diretório privado;
- verificar os bytes consumidos pelo armazenamento;
- persistir os metadados;
- compensar arquivo e transação em caso de falha.

Ainda não existe uma porta HTTP que permita ao usuário ou à futura interface
Streamlit enviar um documento para esse caso de uso.

Sem um endpoint específico, uma integração futura poderia:

- duplicar regras já implementadas no `DocumentUploadService`;
- carregar uma segunda cópia integral do arquivo em memória;
- expor `storage_key`, caminho físico ou SHA-256;
- traduzir incorretamente erros da aplicação;
- administrar inadequadamente a sessão do PostgreSQL;
- fechar o arquivo antes da conclusão da operação;
- retornar detalhes internos de persistência ou compensação;
- introduzir processamento externo acidental.

---

## 3. Intenção — Outcome

Disponibilizar um endpoint HTTP capaz de receber um PDF por
`multipart/form-data`, adaptar o arquivo recebido para o
`DocumentUploadService` e retornar somente metadados públicos do documento
criado.

O endpoint deverá:

- receber o identificador da avaliação pela URL;
- receber um único arquivo no campo multipart `file`;
- utilizar `UploadFile.file` como fluxo binário;
- não executar `read()` integral na camada HTTP;
- construir ou receber o `DocumentUploadService` por injeção de dependência;
- utilizar a sessão PostgreSQL do request;
- retornar HTTP `201 Created`;
- traduzir erros conhecidos para códigos HTTP estáveis;
- preservar mensagens públicas sanitizadas;
- não expor detalhes internos de armazenamento;
- manter o processamento exclusivamente local.

---

## 4. Escopo

### 4.1 Dentro do escopo — IN

- [ ] Criar `POST /evaluations/{evaluation_id}/documents`.
- [ ] Receber `evaluation_id` como UUID no path.
- [ ] Receber um campo multipart obrigatório chamado `file`.
- [ ] Receber o arquivo por meio de `UploadFile`.
- [ ] Passar `UploadFile.file` diretamente ao `DocumentUploadService`.
- [ ] Passar `UploadFile.filename` como nome original.
- [ ] Passar `UploadFile.content_type` como tipo declarado.
- [ ] Rejeitar filename ausente antes da chamada do serviço.
- [ ] Criar schema público de resposta documental.
- [ ] Retornar HTTP `201 Created`.
- [ ] Retornar somente:
  - `id`;
  - `evaluation_id`;
  - `original_filename`;
  - `content_type`;
  - `size_bytes`;
  - `created_at`.
- [ ] Não retornar `storage_key`.
- [ ] Não retornar caminho físico.
- [ ] Não retornar SHA-256.
- [ ] Criar dependência de composição do `DocumentUploadService`.
- [ ] Utilizar a `Session` injetada pelo request.
- [ ] Criar `SqlAlchemyDocumentPersistence` com a sessão recebida.
- [ ] Criar ou reutilizar `DocumentValidationService`.
- [ ] Criar ou reutilizar `LocalDocumentStorage`.
- [ ] Criar ou reutilizar `PyMuPdfInspector`.
- [ ] Traduzir erros conhecidos para respostas HTTP.
- [ ] Preservar o fechamento da sessão em `get_db_session`.
- [ ] Deixar o fechamento do `UploadFile` para o ciclo de vida do FastAPI.
- [ ] Adicionar `python-multipart` como dependência de runtime.
- [ ] Criar testes unitários da camada HTTP.
- [ ] Criar teste integrado do endpoint.
- [ ] Usar somente PDFs sintéticos nos testes.
- [ ] Manter os Quality Gates existentes aprovados.

### 4.2 Fora do escopo — OUT

- [ ] Criar interface Streamlit.
- [ ] Criar listagem de documentos.
- [ ] Criar endpoint de download.
- [ ] Criar exclusão de documentos.
- [ ] Implementar autenticação ou autorização.
- [ ] Implementar rate limiting.
- [ ] Implementar antivírus.
- [ ] Implementar streaming de resposta.
- [ ] Extrair texto, páginas, imagens ou tabelas.
- [ ] Executar OCR.
- [ ] Criar embeddings.
- [ ] Implementar RAG ou LLM.
- [ ] Enviar conteúdo a serviço externo.
- [ ] Alterar `DocumentUploadService`.
- [ ] Alterar `DocumentValidationService`.
- [ ] Alterar `DocumentStorage`.
- [ ] Alterar `LocalDocumentStorage`.
- [ ] Alterar `SqlAlchemyDocumentPersistence`.
- [ ] Alterar entidades ou modelos existentes.
- [ ] Criar ou alterar migrations.
- [ ] Alterar a tabela `documents`.
- [ ] Refatorar os endpoints existentes.
- [ ] Converter a aplicação para SQLAlchemy assíncrono.
- [ ] Criar um container genérico de dependências.
- [ ] Criar tratamento global de exceções para toda a API.
- [ ] Criar limite de request em proxy ou infraestrutura externa.

---

## 5. Contrato HTTP

### 5.1 Request

```text
POST /evaluations/{evaluation_id}/documents
Content-Type: multipart/form-data
```

Parâmetros:

| Origem    | Nome            | Tipo | Obrigatório |
| --------- | --------------- | ---: | ----------: |
| Path      | `evaluation_id` | UUID |         Sim |
| Multipart | `file`          |  PDF |         Sim |

O endpoint deverá usar o nome do campo multipart exatamente como `file`.

Não deverá existir payload JSON adicional nesta iteração.

### 5.2 Response de sucesso

```text
HTTP/1.1 201 Created
Content-Type: application/json
```

Schema equivalente a:

```json
{
  "id": "uuid",
  "evaluation_id": "uuid",
  "original_filename": "documento.pdf",
  "content_type": "application/pdf",
  "size_bytes": 12345,
  "created_at": "2026-07-29T18:00:00Z"
}
```

Não deverão ser retornados:

- `storage_key`;
- caminho absoluto ou relativo;
- SHA-256;
- conteúdo;
- informações de compensação;
- detalhes de SQLAlchemy;
- detalhes do sistema de arquivos.

---

## 6. Composição das Dependências

A camada HTTP deverá depender do `DocumentUploadService`, não implementar suas
regras.

Deverá existir uma fábrica ou dependência equivalente a:

```python
def get_document_upload_service(
    session: DatabaseSession,
) -> DocumentUploadService:
    ...
```

A composição deverá utilizar:

- `DocumentValidationService`;
- `PyMuPdfInspector`;
- `LocalDocumentStorage`;
- `SqlAlchemyDocumentPersistence`;
- `Settings`;
- `Session` do request.

Regras:

- `DocumentUploadService` será criado no contexto do request;
- `SqlAlchemyDocumentPersistence` receberá a sessão do request;
- a sessão não será criada nem fechada pelo serviço;
- componentes sem estado associados ao request poderão ser reutilizados;
- não deverá existir sessão global;
- não deverá existir service global contendo uma sessão;
- dependências deverão poder ser sobrescritas nos testes;
- não deverá ser criado um container genérico de injeção de dependências.

---

## 7. Adaptação do UploadFile

O endpoint deverá:

1. receber `UploadFile`;
2. confirmar que `filename` está presente;
3. obter `file.file`;
4. chamar `DocumentUploadService.upload()` uma única vez;
5. não executar leitura antecipada do conteúdo;
6. não converter o conteúdo para `bytes`;
7. não criar arquivo temporário adicional;
8. não fechar o fluxo antes do retorno do serviço;
9. converter a entidade retornada para o schema público;
10. deixar o FastAPI administrar o encerramento do upload.

O endpoint deverá ser síncrono, pois:

- o serviço é síncrono;
- o armazenamento local é síncrono;
- SQLAlchemy está configurado de forma síncrona;
- endpoints síncronos são executados pelo FastAPI fora do event loop principal.

---

## 8. Tradução de Erros HTTP

### 8.1 Erros de request e validação

| Exceção ou condição            | HTTP | Mensagem pública                                |
| ------------------------------ | ---: | ----------------------------------------------- |
| UUID de path inválido          |  422 | Resposta padrão sanitizada do FastAPI           |
| Campo `file` ausente           |  422 | Resposta padrão sanitizada do FastAPI           |
| `filename` ausente             |  422 | `Nome de arquivo inválido.`                     |
| `InvalidOriginalFilenameError` |  422 | `Nome de arquivo inválido.`                     |
| `OriginalFilenameTooLongError` |  422 | `Nome de arquivo inválido.`                     |
| `EmptyDocumentError`           |  422 | `O documento está vazio.`                       |
| `InvalidPdfError`              |  422 | `O arquivo enviado não é um PDF válido.`        |
| `NonSeekableDocumentError`     |  422 | `Não foi possível processar o arquivo enviado.` |
| `UnsupportedContentTypeError`  |  415 | `Tipo de conteúdo não suportado.`               |
| `DocumentTooLargeError`        |  413 | `O documento excede o limite permitido.`        |

### 8.2 Erros de recurso e conflito

| Exceção                   | HTTP | Mensagem pública                      |
| ------------------------- | ---: | ------------------------------------- |
| `EvaluationNotFoundError` |  404 | `Avaliação não encontrada.`           |
| `DuplicateDocumentError`  |  409 | `Documento já associado à avaliação.` |

### 8.3 Erros internos

| Exceção                          | HTTP | Mensagem pública                                   |
| -------------------------------- | ---: | -------------------------------------------------- |
| `StoredContentMismatchError`     |  500 | `Não foi possível concluir o upload do documento.` |
| `DocumentUploadPersistenceError` |  500 | `Não foi possível concluir o upload do documento.` |
| `DocumentCompensationError`      |  500 | `Não foi possível concluir o upload do documento.` |
| `DocumentStorageError`           |  500 | `Não foi possível concluir o upload do documento.` |

Regras:

- não retornar `str(exception)` ao cliente;
- não retornar o encadeamento de exceções;
- não retornar SHA-256;
- não retornar `storage_key`;
- não retornar nomes de constraints;
- não retornar caminhos do sistema de arquivos;
- não retornar resultados internos de rollback ou exclusão;
- preservar as exceções originais somente no encadeamento interno.

---

## 9. Schema Público

Criar um schema equivalente a:

```python
class DocumentUploadResponse(BaseModel):
    id: UUID
    evaluation_id: UUID
    original_filename: str
    content_type: str
    size_bytes: int
    created_at: datetime
```

O schema não deverá possuir:

- `storage_key`;
- `sha256`;
- conteúdo;
- estado interno de persistência;
- estado interno de compensação.

A conversão deverá utilizar a entidade retornada pelo serviço, sem nova consulta
ao banco.

---

## 10. Dependência Multipart

A implementação deverá adicionar somente a dependência necessária ao parsing de
`multipart/form-data` pelo FastAPI:

```text
python-multipart
```

A faixa de versão será definida no Action Plan de acordo com o padrão do
`pyproject.toml`.

Nenhuma outra dependência nova está autorizada nesta feature sem nova aprovação
humana.

A imagem Docker deverá ser reconstruída após a alteração da dependência.

---

## 11. Segurança e Privacidade

A implementação deverá preservar:

- processamento exclusivamente local;
- conteúdo armazenado somente no diretório privado;
- ausência de documentos reais no Git;
- ausência de conteúdo documental nos logs;
- ausência do nome físico interno na resposta;
- ausência de `storage_key` na resposta;
- ausência de SHA-256 completo na resposta;
- mensagens de erro sanitizadas;
- nenhuma leitura adicional do documento pela camada HTTP;
- nenhuma cópia integral adicional em memória;
- nenhuma chamada de rede externa;
- `external_processing_enabled` permanecendo `false`;
- isolamento entre avaliações;
- validações e compensações já implementadas na F01.4.

O nome original deverá ser tratado como entrada não confiável e nunca utilizado
para construir o caminho físico.

---

## 12. Estratégia de Testes

### 12.1 Testes unitários do endpoint

Os testes deverão comprovar:

- rota e método corretos;
- status `201`;
- campo multipart `file`;
- propagação correta do `evaluation_id`;
- propagação correta do filename;
- propagação correta do content type;
- uso do fluxo binário do `UploadFile`;
- chamada única ao serviço;
- ausência de leitura integral na camada HTTP;
- conversão correta da entidade;
- ausência de `storage_key` na resposta;
- ausência de SHA-256 na resposta;
- tradução de cada erro conhecido;
- mensagens públicas sanitizadas;
- ausência de detalhes internos nas respostas.

### 12.2 Teste integrado

O teste integrado deverá usar:

- `TestClient`;
- PDF sintético;
- PostgreSQL real;
- diretório temporário fora do repositório;
- `PyMuPdfInspector`;
- `DocumentValidationService`;
- `LocalDocumentStorage`;
- `SqlAlchemyDocumentPersistence`;
- `DocumentUploadService`.

Deverá comprovar:

- criação HTTP com status `201`;
- registro criado no PostgreSQL;
- arquivo criado no armazenamento privado temporário;
- resposta correspondente à entidade persistida;
- ausência de `storage_key` e SHA-256;
- duplicidade retornando `409`;
- avaliação inexistente retornando `404`;
- PDF inválido retornando `422`;
- limpeza dos dados sintéticos;
- limpeza dos arquivos temporários;
- ausência de resíduos após o teste.

### 12.3 Quality Gates

Deverão permanecer aprovados:

- suíte completa do pytest;
- Ruff;
- mypy;
- verificador I-001;
- `git diff --check`;
- aplicação operacional;
- PostgreSQL saudável;
- migration em `0002_add_documents (head)`;
- endpoint `/health`;
- processamento externo desabilitado;
- ausência de arquivos privados versionados.

---

## 13. Critérios de Aceitação

1. O endpoint `POST /evaluations/{evaluation_id}/documents` existe.
2. O endpoint recebe um arquivo pelo campo multipart `file`.
3. O endpoint retorna `201` para upload válido.
4. O endpoint utiliza o `DocumentUploadService`.
5. O endpoint não duplica validação, armazenamento ou persistência.
6. O endpoint não lê o conteúdo integral antes do serviço.
7. O endpoint retorna somente metadados públicos.
8. A resposta não contém `storage_key`.
9. A resposta não contém SHA-256.
10. Avaliação inexistente retorna `404`.
11. Documento duplicado retorna `409`.
12. Documento acima do limite retorna `413`.
13. Content type não suportado retorna `415`.
14. PDF inválido retorna `422`.
15. Falhas internas retornam mensagem genérica com `500`.
16. Nenhuma resposta expõe detalhes internos.
17. O arquivo permanece restrito ao armazenamento privado.
18. A sessão é administrada pelo ciclo de vida do request.
19. Testes unitários e integrados são aprovados.
20. Quality Gates permanecem aprovados.
21. Nenhum documento real é versionado.
22. Nenhum processamento externo é executado.

---

## 14. Superfície Prevista

Arquivos que poderão ser criados ou alterados:

- `pyproject.toml`;
- `src/merit_assistant/api/main.py`;
- `src/merit_assistant/api/schemas.py`;
- `src/merit_assistant/api/dependencies.py`;
- `src/merit_assistant/api/routes/__init__.py`;
- `src/merit_assistant/api/routes/documents.py`;
- `tests/test_document_upload_api.py`;
- `tests/test_document_upload_api_integration.py`;
- este Feature Intent;
- futuro Action Plan da F01.5.

A necessidade de `APIRouter` e dos módulos `routes` será confirmada no Action
Plan. A implementação poderá permanecer em `main.py` somente quando a revisão
arquitetural concluir que isso mantém clareza e testabilidade.

Arquivos protegidos que não deverão ser alterados:

- migrations;
- `src/merit_assistant/domain/entities.py`;
- `src/merit_assistant/infrastructure/db/models.py`;
- `src/merit_assistant/application/ports/document_persistence.py`;
- `src/merit_assistant/application/ports/document_storage.py`;
- `src/merit_assistant/application/services/document_upload.py`;
- `src/merit_assistant/application/services/document_validation.py`;
- `src/merit_assistant/infrastructure/db/document_persistence.py`;
- `src/merit_assistant/infrastructure/storage/`;
- `src/merit_assistant/infrastructure/pdf/`;
- interface Streamlit;
- PDFs;
- arquivos privados.

---

## 15. Riscos e Mitigações

### R-01 — Cópia integral adicional em memória

**Mitigação:** passar `UploadFile.file` diretamente ao serviço e proibir
`await file.read()` ou `file.file.read()` na camada HTTP.

### R-02 — Exposição de armazenamento interno

**Mitigação:** usar schema público sem `storage_key`, caminho físico ou SHA-256.

### R-03 — Vazamento de detalhes por exceções

**Mitigação:** traduzir exceções conhecidas para mensagens constantes e nunca
retornar `str(exception)`.

### R-04 — Sessão incorreta ou global

**Mitigação:** criar o adapter com a sessão injetada pelo request e nunca
armazenar a sessão em singleton.

### R-05 — Regras duplicadas no endpoint

**Mitigação:** manter toda validação e orquestração no
`DocumentUploadService`.

### R-06 — Endpoint bloqueando o event loop

**Mitigação:** implementar o endpoint como função síncrona.

### R-07 — Filename ausente

**Mitigação:** validar explicitamente `UploadFile.filename` antes de chamar o
serviço.

### R-08 — Dependência multipart ausente

**Mitigação:** adicionar `python-multipart`, reconstruir a imagem e validar o
OpenAPI e o upload real.

### R-09 — Testes criando dados residuais

**Mitigação:** usar identificadores sintéticos e limpeza defensiva em `finally`
ou fixture equivalente.

### R-10 — Expansão prematura para listagem ou interface

**Mitigação:** limitar esta feature ao endpoint POST e ao schema da resposta.

---

## 16. Handoff para o Action Plan

O Action Plan deverá definir:

- organização final entre `main.py`, `dependencies.py` e `routes`;
- faixa exata de versão de `python-multipart`;
- assinatura das dependências FastAPI;
- schema definitivo da resposta;
- matriz completa de exceções e códigos HTTP;
- estratégia de sobrescrita de dependências nos testes;
- fixture integrada para PostgreSQL e storage temporário;
- checkpoints humanos;
- superfície final de arquivos;
- sequência de commit e encerramento.

Nenhum código de produção deverá ser implementado antes de:

1. revisão deste Feature Intent;
2. aprovação do Human Lead Engineer;
3. commit e push do Feature Intent aprovado;
4. criação e aprovação do Action Plan F01.5.

---

## Aprovação

- [x] **Human Lead Engineer aprovou este Feature Intent**
- **Data da aprovação:** 2026-07-29
