# Action Plan F01.7 — Interface Streamlit para Upload e Listagem Segura de Documentos

## 1. Identificação

- **Projeto:** Assistente de Avaliação de Mérito Tecnológico
- **Feature:** F01.7 — Interface Streamlit para Upload e Listagem Segura de Documentos
- **Feature pai:** F01 — Ingestão Segura de Documentos
- **Feature Intent:** `feature-intent-f01-7-streamlit-document-interface.md`
- **MCP+ aplicável:** MCP+ 001 v1.1
- **Branch:** `feature/f01-secure-document-ingestion`
- **Baseline de planejamento:** `c36c4e3bbc46c7f56fee4fbc2874d36c1dd46112`
- **Commit do Feature Intent aprovado:**
  `c36c4e3bbc46c7f56fee4fbc2874d36c1dd46112`
- **Commit da implementação:** pendente
- **Data:** 2026-07-31
- **Responsável humano:** André Cataldo
- **Status:** Approved

### Dependências funcionais

- F01.1 — Modelo de Documento e Migration;
- F01.2 — Serviço Local de Armazenamento Seguro;
- F01.3 — Validação de PDF, Limite de Tamanho e SHA-256;
- F01.4 — Orquestração Segura do Upload e Persistência;
- F01.5 — Endpoint Seguro de Upload de Documentos;
- F01.6 — Listagem Segura de Documentos por Avaliação.

---

## 2. Verificação de Prontidão

- Feature Intent F01.7 aprovado e commitado.
- F01.1 a F01.6 concluídas.
- Endpoints de health, perfis, avaliações, upload e listagem disponíveis.
- Schema documental público com seis campos disponível.
- Interface inicial existente em `ui/app.py`.
- `API_BASE_URL` já utilizado pela interface.
- Serviço Streamlit disponível no Docker Compose.
- Streamlit, `httpx` e Pydantic já são dependências do projeto.
- Último baseline técnico registrado: 240 testes aprovados.
- PostgreSQL em `0002_add_documents (head)`.
- Processamento externo desabilitado.
- Nenhuma migration, alteração de backend ou dependência nova necessária.
- Nenhuma Decision Lock precisa ser alterada.
- Nenhum conflito com o MCP+ 001 v1.1 identificado.

### 2.1 Estado atual da interface

A interface atual:

- verifica health;
- consulta perfis;
- cria avaliações;
- lista avaliações.

Ela ainda não:

- isola a comunicação HTTP;
- valida respostas com modelos estritos;
- restringe `API_BASE_URL` a destinos locais;
- seleciona uma avaliação de forma operacional;
- envia documentos;
- lista documentos por avaliação;
- controla reruns após upload;
- sanitiza todas as falhas;
- possui testes específicos de interface.

### 2.2 Compatibilidade do AppTest

O projeto aceita Streamlit `>=1.39,<2`.

O plano não elevará a versão mínima e não dependerá de interação programática
com `st.file_uploader` no AppTest.

A estratégia será:

- AppTest para estados e widgets suportados;
- funções testáveis para o workflow de upload;
- cliente testado com FastAPI real por `TestClient`;
- upload completo validado no Docker Compose com PDF sintético.

---

## 3. Objetivo

Entregar uma jornada Streamlit segura para:

1. confirmar a disponibilidade da aplicação;
2. criar ou selecionar uma avaliação;
3. distinguir títulos repetidos pelo UUID;
4. selecionar um único PDF;
5. enviar o PDF por ação humana explícita;
6. impedir reenvio causado por rerun;
7. invalidar o uploader após sucesso;
8. listar documentos da avaliação selecionada;
9. preservar a ordem da API;
10. exibir somente seis metadados públicos;
11. apresentar mensagens estáveis em português;
12. manter banco, storage e serviços internos fora da interface.

Continuam fora do escopo:

- mudança de endpoint ou schema;
- acesso direto a PostgreSQL ou `data/private`;
- preview, download, exclusão ou edição;
- upload em lote;
- classificação, extração, OCR, embeddings, RAG ou LLM;
- autenticação, autorização ou redesign amplo;
- cache de conteúdo documental;
- processamento externo;
- novas dependências.

---

## 4. Decisões Técnicas

### 4.1 Organização

Criar:

- `ui/__init__.py`;
- `ui/api_client.py`;
- `ui/presentation.py`.

Alterar:

- `ui/app.py`.

Responsabilidades:

- `ui/api_client.py`: fronteira HTTP, modelos e erros;
- `ui/presentation.py`: renderização, estado e workflows;
- `ui/app.py`: entrypoint fino;
- nenhum arquivo de UI importa camadas internas do backend.

### 4.2 Cliente HTTP

Criar `MeritAssistantApiClient` com:

- cliente HTTP injetável;
- `httpx.Client` próprio no fluxo padrão;
- context manager;
- timeouts finitos;
- redirects desabilitados;
- ausência de cliente global;
- ausência de cache;
- fechamento somente do cliente próprio.

Operações:

```python
health() -> HealthView
list_profiles() -> list[ProfileView]
create_evaluation(title, profile_id) -> EvaluationView
list_evaluations() -> list[EvaluationView]
upload_document(evaluation_id, filename, content_type, source) -> DocumentView
list_documents(evaluation_id) -> list[DocumentView]
```

### 4.3 Política de URL

Permitir somente:

- esquema `http`;
- hosts `localhost`, `127.0.0.1`, `::1` ou `api`;
- porta `8000`;
- path vazio ou `/`;
- ausência de credenciais, query e fragment.

Rejeitar qualquer outro destino com:

```text
Configuração local da API inválida.
```

O cliente não seguirá redirects.

### 4.4 Modelos da fronteira

Criar modelos Pydantic próprios:

- `HealthView`;
- `ProfileView`;
- `EvaluationView`;
- `DocumentView`.

Todos usarão:

```python
ConfigDict(extra="forbid")
```

Rejeitar:

- JSON inválido;
- shape inesperado;
- campos extras;
- campos ausentes;
- tipos inválidos;
- status de sucesso diferente do contrato.

### 4.5 Exceções públicas

Criar:

```python
ApiClientError
ApiConfigurationError
ApiUnavailableError
ApiProtocolError
ApiOperationError
```

Regras:

- mensagem pública constante;
- nenhuma mensagem usa `response.text`;
- nenhuma mensagem usa `str(exc)`;
- body bruto nunca é armazenado;
- causas técnicas poderão ser encadeadas;
- detalhes internos nunca serão exibidos.

### 4.6 Timeouts

Usar configuração equivalente a:

```python
httpx.Timeout(
    connect=5.0,
    read=30.0,
    write=60.0,
    pool=5.0,
)
```

### 4.7 Status esperados

| Operação | Status |
| --- | ---: |
| health | `200` |
| perfis | `200` |
| criar avaliação | `201` |
| listar avaliações | `200` |
| upload | `201` |
| listar documentos | `200` |

### 4.8 Mensagens seguras

Mapear somente combinações aprovadas de:

- operação;
- status HTTP;
- `detail` JSON exato.

Mensagens conhecidas de upload:

- `Avaliação não encontrada.`;
- `Documento já associado à avaliação.`;
- `O documento excede o limite permitido.`;
- `Tipo de conteúdo não suportado.`;
- `Nome de arquivo inválido.`;
- `O documento está vazio.`;
- `O arquivo enviado não é um PDF válido.`;
- `Não foi possível processar o arquivo enviado.`.

Listagem:

- `404` com `Evaluation not found.` vira `Avaliação não encontrada.`;
- `500` com `Unable to list documents.` vira mensagem genérica de listagem.

Fallbacks:

- `Não foi possível carregar os perfis.`;
- `Não foi possível carregar as avaliações.`;
- `Não foi possível criar a avaliação.`;
- `Não foi possível concluir o upload do documento.`;
- `Não foi possível listar os documentos.`;
- `A API retornou uma resposta inválida.`;
- `API indisponível. Verifique o ambiente local.`;
- `Não foi possível concluir a operação.`.

### 4.9 Estado da sessão

Permitir somente:

- `selected_evaluation_id`;
- `upload_in_progress`;
- `upload_widget_generation`;
- `flash_success`.

Proibir:

- bytes do PDF;
- `UploadedFile`;
- conteúdo documental;
- body HTTP;
- path;
- SHA-256;
- `storage_key`.

### 4.10 Seleção da avaliação

- valor real: UUID;
- label: `título — UUID completo`;
- títulos normalizados para exibição segura;
- ordem da API preservada;
- seleção mantida enquanto o UUID existir;
- nova avaliação selecionada após criação;
- seleção inexistente removida.

### 4.11 Upload

- usar `st.form`;
- usar `st.file_uploader`;
- `type=["pdf"]`;
- `accept_multiple_files=False`;
- não usar `getvalue()`;
- passar o próprio file-like ao cliente;
- campo multipart exatamente `file`;
- submissão humana explícita;
- verificar `upload_in_progress`;
- uma chamada por evento;
- restaurar flag em `finally`;
- em sucesso, incrementar `upload_widget_generation`;
- em sucesso, registrar somente mensagem flash;
- em sucesso, executar rerun;
- em erro, não repetir automaticamente.

O uploader será invalidado por mudança de `key`.

A implementação não atribuirá valor ao uploader por `session_state`.

### 4.12 Listagem

- consumir somente o GET aprovado;
- não ordenar novamente;
- não consultar storage;
- exibir exatamente:
  - `id`;
  - `evaluation_id`;
  - `original_filename`;
  - `content_type`;
  - `size_bytes`;
  - `created_at`;
- usar `st.dataframe`;
- ocultar índice;
- tratar `[]` como sucesso vazio;
- diferenciar erro de lista vazia.

### 4.13 Renderização segura

- não usar `unsafe_allow_html=True`;
- não usar HTML para títulos ou nomes;
- não usar `st.markdown` com dados controlados;
- remover caracteres de controle de labels;
- preservar Unicode legível;
- não interpolar body de rede.

### 4.14 Processamento externo

Quando `external_processing_enabled` for `true`:

- exibir `Processamento externo habilitado; operação bloqueada.`;
- interromper a jornada;
- não consultar perfis, avaliações ou documentos;
- não executar upload.

---

## 5. Superfície Prevista

### Produção — criar

- `ui/__init__.py`;
- `ui/api_client.py`;
- `ui/presentation.py`.

### Produção — alterar

- `ui/app.py`.

### Testes — criar

- `tests/test_streamlit_api_client.py`;
- `tests/test_streamlit_presentation.py`;
- `tests/test_streamlit_app.py`;
- `tests/test_streamlit_api_integration.py`;
- `tests/test_streamlit_architecture.py`.

### Documentação — encerramento

- `docs/action-plans/action-plan-f01-7-streamlit-document-interface.md`;
- `docs/features/feature-intent-f01-7-streamlit-document-interface.md`;
- `README.md`.

### Protegidos

Não alterar:

- `src/merit_assistant/`;
- `alembic.ini`;
- `alembic/versions/`;
- `pyproject.toml`;
- `docker-compose.yml`;
- `Dockerfile`;
- `.env.example`;
- `config/`;
- `scripts/`;
- testes existentes do backend;
- `data/private/`;
- `logs/`;
- documentos reais.

Mudança fora dessa superfície exige parada e nova aprovação.

---

## 6. Estratégia de Testes

### 6.1 Cliente HTTP

`tests/test_streamlit_api_client.py` cobrirá:

- URLs locais válidas;
- destinos externos rejeitados;
- credenciais, query e fragment rejeitados;
- redirects não seguidos;
- timeouts;
- lifecycle do cliente;
- health, perfis, avaliações e documentos;
- upload multipart `file`;
- stream sem cópia intermediária;
- lista vazia;
- campos extras e ausentes;
- JSON inválido;
- status inesperado;
- timeout e conexão;
- mensagens conhecidas e fallback;
- body HTML e detalhes internos ocultos.

Usar `httpx.MockTransport` quando aplicável.

### 6.2 Apresentação

`tests/test_streamlit_presentation.py` cobrirá:

- texto seguro;
- caracteres de controle;
- label com UUID completo;
- títulos duplicados;
- seleção válida e inválida;
- tabela com seis campos;
- ordem preservada;
- mensagem flash;
- geração do uploader;
- estado sem bytes;
- chamada única de upload;
- flag restaurado em sucesso e erro;
- stream, filename e content type encaminhados.

### 6.3 Aplicação Streamlit

`tests/test_streamlit_app.py` usará AppTest para:

- health aprovado;
- API indisponível;
- processamento externo habilitado;
- ausência de perfil;
- ausência de avaliação;
- criação e seleção;
- títulos duplicados;
- lista vazia;
- lista com documentos;
- falhas sanitizadas;
- ausência de body bruto;
- ausência de exception renderizada;
- ausência de chamada documental sem seleção.

A interação programática com o uploader não será requisito.

### 6.4 Integração real

`tests/test_streamlit_api_integration.py` usará:

- FastAPI real;
- `TestClient`;
- PostgreSQL real;
- storage real controlado;
- cliente da UI com transporte injetado;
- PDF e IDs sintéticos;
- limpeza defensiva.

Cenários:

1. health e perfis;
2. criar e listar avaliação;
3. listar documentos e obter `[]`;
4. enviar PDF sintético;
5. listar documento;
6. confirmar seis campos;
7. confirmar isolamento;
8. confirmar duplicidade;
9. confirmar mensagem segura;
10. limpar banco e arquivo;
11. confirmar zero resíduos.

### 6.5 Arquitetura

`tests/test_streamlit_architecture.py` comprovará:

- nenhum import SQLAlchemy;
- nenhum import de infraestrutura;
- nenhum import de application services;
- nenhum import de models do backend;
- nenhuma referência a `data/private`;
- ausência de `unsafe_allow_html=True`;
- ausência de `response.text`;
- ausência de escrita local;
- ausência de URL externa;
- superfície exata.

### 6.6 Regressão

Executar:

- health;
- avaliações;
- upload;
- listagem;
- storage;
- persistência;
- integrações anteriores;
- suíte completa.

---

## Checkpoint Humano H1

Executar após cliente, apresentação e testes unitários/de componente, antes da
integração real e do smoke operacional.

### Pacote obrigatório

- branch e baseline;
- sincronização e estado Git;
- arquivos alterados;
- patch e SHA-256;
- testes específicos;
- suíte total no estágio H1;
- Ruff;
- mypy em `src` e `ui`;
- I-001;
- `git diff --check`;
- teste arquitetural;
- superfície autorizada;
- ausência de PDFs e dados privados;
- warnings;
- confirmação de nenhum commit de implementação.

### Critérios

- cliente isolado;
- URL local restrita;
- redirects desabilitados;
- timeouts finitos;
- modelos estritos;
- mensagens sanitizadas;
- seleção por UUID;
- uma chamada por submissão;
- nenhum byte em estado;
- seis campos públicos;
- nenhum acesso interno;
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

## 7. Etapas de Execução

### Etapa 1 — Confirmar baseline

**Arquivos afetados:** nenhum.

```bash
git branch --show-current
git rev-parse HEAD
git status --short
git fetch origin
git rev-list   --left-right   --count   HEAD...origin/feature/f01-secure-document-ingestion
pytest -o addopts="-q --maxfail=1" -W default
ruff check .
mypy src
./scripts/verify_i001_scope.sh
git diff --check
docker compose up -d
docker compose ps
docker compose exec -T api alembic current
curl -fsS http://localhost:8000/health
curl -fsS http://localhost:8501/_stcore/health
```

**Resultado esperado:**

- baseline `c36c4e3`;
- working tree limpa;
- sincronização `0 0`;
- gates, migration e health aprovados;
- UI operacional;
- processamento externo desabilitado.

**Status:** Pending

---

### Etapa 2 — Criar pacote e cliente base

**Arquivos afetados:**

- `ui/__init__.py`;
- `ui/api_client.py`;
- `tests/test_streamlit_api_client.py`;
- `tests/test_streamlit_architecture.py`.

**Verificação:**

```bash
pytest   tests/test_streamlit_api_client.py   tests/test_streamlit_architecture.py   -q
ruff check ui tests/test_streamlit_api_client.py
mypy ui
git diff --check
```

**Resultado esperado:**

- URLs locais aceitas;
- URLs externas rejeitadas;
- redirects bloqueados;
- modelos e lifecycle testados;
- arquitetura preservada.

**Status:** Pending

---

### Etapa 3 — Implementar operações HTTP

**Arquivos afetados:**

- `ui/api_client.py`;
- `tests/test_streamlit_api_client.py`.

**Verificação:**

```bash
pytest tests/test_streamlit_api_client.py -q
ruff check ui/api_client.py tests/test_streamlit_api_client.py
mypy ui
git diff --check
```

**Resultado esperado:**

- seis operações implementadas;
- status e JSON validados;
- multipart correto;
- mensagens sanitizadas;
- nenhum body bruto.

**Status:** Pending

---

### Etapa 4 — Criar apresentação e estado

**Arquivos afetados:**

- `ui/presentation.py`;
- `tests/test_streamlit_presentation.py`;
- `tests/test_streamlit_architecture.py`.

**Verificação:**

```bash
pytest   tests/test_streamlit_presentation.py   tests/test_streamlit_architecture.py   -q
ruff check ui tests/test_streamlit_presentation.py
mypy ui
git diff --check
```

**Resultado esperado:**

- labels seguros;
- seleção estável;
- tabela segura;
- nenhum byte no estado;
- nenhum HTML inseguro.

**Status:** Pending

---

### Etapa 5 — Refatorar fluxos existentes

**Arquivos afetados:**

- `ui/app.py`;
- `ui/presentation.py`;
- `tests/test_streamlit_app.py`;
- `tests/test_streamlit_architecture.py`.

**Verificação:**

```bash
pytest \
  tests/test_streamlit_app.py \
  tests/test_streamlit_architecture.py \
  tests/test_health.py \
  -q
ruff check ui tests/test_streamlit_app.py
mypy src
mypy ui
git diff --check
```

**Resultado esperado:**

- health, perfis, criação e listagem preservados;
- external true bloqueado;
- `response.text` removido;
- nenhum traceback público.

**Status:** Pending

---

### Etapa 6 — Implementar seleção da avaliação

**Arquivos afetados:**

- `ui/presentation.py`;
- `tests/test_streamlit_presentation.py`;
- `tests/test_streamlit_app.py`.

**Verificação:**

```bash
pytest   tests/test_streamlit_presentation.py   tests/test_streamlit_app.py   -q
ruff check ui tests/test_streamlit_*.py
mypy ui
git diff --check
```

**Resultado esperado:**

- títulos duplicados distinguíveis;
- UUID completo;
- seleção mantida;
- nova avaliação selecionada;
- seleção inválida descartada.

**Status:** Pending

---

### Etapa 7 — Implementar upload

**Arquivos afetados:**

- `ui/presentation.py`;
- `tests/test_streamlit_presentation.py`;
- `tests/test_streamlit_app.py`;
- `tests/test_streamlit_architecture.py`.

**Verificação:**

```bash
pytest \
  tests/test_streamlit_presentation.py \
  tests/test_streamlit_app.py \
  tests/test_streamlit_architecture.py \
  -q
ruff check ui tests/test_streamlit_*.py
mypy ui
git diff --check
```

**Resultado esperado:**

- submissão explícita;
- chamada única;
- flag restaurado;
- stream encaminhado;
- uploader invalidado no sucesso;
- erro sem reenvio;
- nenhum byte em estado.

**Status:** Pending

---

### Etapa 8 — Implementar listagem

**Arquivos afetados:**

- `ui/presentation.py`;
- `tests/test_streamlit_presentation.py`;
- `tests/test_streamlit_app.py`.

**Verificação:**

```bash
pytest   tests/test_streamlit_presentation.py   tests/test_streamlit_app.py   -q
ruff check ui tests/test_streamlit_*.py
mypy ui
git diff --check
```

**Resultado esperado:**

- lista vazia diferenciada de erro;
- seis campos exatos;
- ordem preservada;
- nenhum campo interno.

**Status:** Pending

---

### Etapa 9 — Consolidar testes antes do H1

```bash
pytest \
  tests/test_streamlit_api_client.py \
  tests/test_streamlit_presentation.py \
  tests/test_streamlit_app.py \
  tests/test_streamlit_architecture.py \
  -q
pytest \
  tests/test_document_upload_api.py \
  tests/test_document_listing_api.py \
  tests/test_health.py \
  -q
pytest -o addopts="-q --maxfail=1" -W default
ruff check .
mypy src
mypy ui
./scripts/verify_i001_scope.sh
git diff --check
```

**Resultado esperado:**

- interface, cliente e arquitetura aprovados;
- backend preservado;
- suíte e gates aprovados.

**Status:** Pending

---

### Etapa 10 — Executar H1

**Resultado esperado:**

- patch H1 completo;
- SHA-256 registrado;
- nenhuma expansão de escopo;
- nenhum documento real;
- nenhum commit de implementação;
- aprovação humana explícita.

**Status:** Pending

---

### Etapa 11 — Criar integração real

**Arquivo afetado:**

- `tests/test_streamlit_api_integration.py`.

```bash
pytest tests/test_streamlit_api_integration.py -q
ruff check tests/test_streamlit_api_integration.py
mypy src
mypy ui
git diff --check
```

**Resultado esperado:**

- jornada HTTP real aprovada;
- upload e listagem aprovados;
- duplicidade e isolamento aprovados;
- zero resíduos.

**Status:** Pending

---

### Etapa 12 — Reconstruir e validar Docker Compose

```bash
docker compose build --no-cache
docker compose up -d
docker compose ps
docker compose exec -T api alembic current
curl -fsS http://localhost:8000/health
curl -fsS http://localhost:8501/_stcore/health
```

Smoke humano com PDF sintético:

1. abrir a interface;
2. confirmar external false;
3. criar ou selecionar avaliação sintética;
4. enviar PDF sintético uma vez;
5. confirmar mensagem e invalidação do uploader;
6. confirmar documento na lista;
7. trocar de avaliação e confirmar isolamento;
8. provocar duplicidade e confirmar mensagem;
9. limpar banco e arquivo;
10. confirmar zero resíduos.

**Status:** Pending

---

### Etapa 13 — Executar Quality Gate

```bash
pytest -o addopts="-q --maxfail=1" -W default
ruff check .
mypy src
mypy ui
./scripts/verify_i001_scope.sh
git diff --check
git diff --name-status
git diff --stat
git ls-files '*.pdf'
git ls-files data/private
find data/private -type f ! -name '.gitkeep' -print
grep -RIn   --exclude-dir='__pycache__'   'unsafe_allow_html=True\|response\.text'   ui || true
docker compose ps
docker compose exec -T api alembic current
curl -fsS http://localhost:8000/health
curl -fsS http://localhost:8501/_stcore/health
```

**Resultado esperado:**

- suíte e gates aprovados;
- superfície autorizada;
- nenhum PDF, dado privado ou resíduo;
- nenhum HTML inseguro ou body bruto;
- containers, migration e health aprovados.

**Status:** Pending

---

### Etapa 14 — Executar H2

**Resultado esperado:**

- patch final e SHA-256;
- testes, Docker e smoke aprovados;
- nenhuma expansão de escopo;
- nenhum commit de implementação;
- aprovação humana explícita.

**Status:** Pending

---

### Etapa 15 — Commit da implementação

```bash
git add -- \
  ui/__init__.py \
  ui/api_client.py \
  ui/presentation.py \
  ui/app.py \
  tests/test_streamlit_api_client.py \
  tests/test_streamlit_presentation.py \
  tests/test_streamlit_app.py \
  tests/test_streamlit_api_integration.py \
  tests/test_streamlit_architecture.py

git commit -m   ":sparkles: feat: add streamlit document interface"

git push   origin   feature/f01-secure-document-ingestion
```

**Resultado esperado:**

- exatamente nove arquivos;
- somente implementação e testes;
- nenhum documento de governança;
- branch sincronizada.

**Status:** Pending

---

### Etapa 16 — Encerramento documental

```bash
git add -- \
  docs/features/feature-intent-f01-7-streamlit-document-interface.md \
  docs/action-plans/action-plan-f01-7-streamlit-document-interface.md \
  README.md

git commit -m   ":books: docs: close F01.7 streamlit interface"

git push   origin   feature/f01-secure-document-ingestion
```

**Resultado esperado:**

- Feature Intent e Action Plan em `Done`;
- README atualizado;
- commit de implementação registrado;
- H1 e H2 registrados;
- commit documental separado;
- working tree limpa;
- sincronização `0 0`.

**Status:** Pending

---

## Checkpoint Humano H2

Executar após integração, Docker, smoke, Quality Gate e validação de resíduos.

### Pacote obrigatório

- branch, baseline e sincronização;
- estado Git e superfície;
- patch final e SHA-256;
- suíte completa e testes específicos;
- Ruff;
- mypy em `src` e `ui`;
- I-001;
- teste arquitetural;
- arquivos protegidos;
- PDFs e área privada;
- resíduos de PostgreSQL e storage;
- containers, migration e health;
- evidência do smoke;
- confirmação de nenhum commit de implementação.

### Critérios

- comportamento conforme o Feature Intent;
- URL local restrita;
- redirects bloqueados;
- processamento externo bloqueado;
- criação e seleção comprovadas;
- upload explícito;
- uma chamada por submissão;
- uploader invalidado;
- lista atualizada;
- seis campos públicos;
- mensagens sanitizadas;
- nenhum acesso interno;
- integração e Quality Gate aprovados;
- nenhum commit de implementação.

### Registro

- **Status:** Pending
- **Aprovado por:** pendente
- **Data:** pendente
- **Pendências:** pendente
- **Evidências:** pendente

---

## 8. Matriz de Rastreabilidade

| Requisito | Implementação | Evidência |
| --- | --- | --- |
| health | cliente + apresentação | cliente, AppTest e Docker |
| external false | apresentação | AppTest e Docker |
| perfis | cliente | cliente e integração |
| criar avaliação | cliente + apresentação | AppTest e integração |
| seleção por UUID | apresentação | unitário e AppTest |
| títulos duplicados | label seguro | unitário e AppTest |
| upload explícito | form | componente e smoke |
| chamada única | flag | unitário e smoke |
| invalidação | geração da key | unitário e smoke |
| multipart `file` | cliente | cliente e integração |
| lista vazia | cliente + apresentação | AppTest e integração |
| isolamento | API existente | integração e smoke |
| ordem | apresentação | unitário e integração |
| seis campos | modelo + tabela | cliente e integração |
| sem campos internos | modelo estrito | testes negativos |
| erros seguros | mapeamento | cliente e AppTest |
| sem body bruto | cliente + arquitetura | AST e testes |
| sem HTML inseguro | apresentação | AST e testes |
| sem bytes no estado | apresentação | unitário |
| URL local | cliente | política |
| sem redirect | cliente | cliente |
| sem banco/storage | arquitetura | AST |
| sem dados reais | fixtures | Git e testes |
| Docker Compose | ambiente | smoke |
| Quality Gates | scripts | H2 |

---

## 9. Riscos e Mitigações

### Upload duplicado

- form e ação explícita;
- flag `upload_in_progress`;
- chamada única;
- invalidação após sucesso;
- sem retry automático.

### Saída externa

- allowlist de host e porta;
- redirects desabilitados;
- credenciais, query e fragment rejeitados.

### Vazamento de mensagem

- nenhum `response.text`;
- `detail` somente quando conhecido;
- fallback constante;
- testes com HTML, SQL e path.

### Dados maliciosos na apresentação

- texto seguro;
- remoção de controles;
- ausência de HTML inseguro.

### Bytes em sessão

- nenhum `UploadedFile` no estado;
- nenhum `getvalue`;
- estado limitado a UUID, flags, contador e mensagem.

### Incompatibilidade do AppTest

- upload testado como workflow;
- cliente testado com FastAPI real;
- widget validado no smoke;
- nenhuma mudança de dependência.

### Regressão

- preservar fluxos existentes;
- executar regressão completa;
- smoke no Docker Compose.

### Expansão prematura

- superfície congelada;
- Stop Rule para arquivo ou função adicional.

---

## 10. Quality Gates

Obrigatórios:

1. suíte completa;
2. cliente Streamlit;
3. apresentação;
4. AppTest;
5. integração real;
6. arquitetura;
7. regressão de health, avaliações, upload e listagem;
8. Ruff;
9. mypy em `src`;
10. mypy em `ui`;
11. I-001;
12. `git diff --check`;
13. política de URL;
14. redirects bloqueados;
15. ausência de `response.text`;
16. ausência de `unsafe_allow_html=True`;
17. ausência de imports proibidos;
18. ausência de PDFs;
19. ausência de dados privados;
20. ausência de resíduos;
21. PostgreSQL e storage reais;
22. containers;
23. migration;
24. health da API e Streamlit;
25. smoke operacional;
26. superfície autorizada;
27. H1;
28. H2.

Falha em qualquer gate impede o commit da implementação.

---

## 11. Stop Rules

Parar quando houver necessidade de:

- alterar endpoint, schema, migration, model ou storage;
- alterar `pyproject.toml` ou elevar Streamlit;
- alterar Docker Compose;
- adicionar dependência;
- acessar banco ou `data/private` pela UI;
- armazenar bytes em estado;
- usar HTML inseguro;
- aceitar URL externa ou seguir redirect;
- criar arquivo fora da superfície;
- usar documento real;
- habilitar processamento externo;
- expandir para preview, download ou exclusão.

Após a parada:

1. registrar a causa;
2. preservar working tree;
3. não criar commit de implementação;
4. revisar os artefatos;
5. obter nova aprovação humana.

---

## 12. Critérios de Conclusão

A F01.7 estará concluída quando:

- Action Plan aprovado e commitado antes da implementação;
- cliente HTTP e política local implementados;
- modelos estritos e mensagens seguras;
- health e bloqueio externo comprovados;
- criação e seleção comprovadas;
- upload explícito e chamada única;
- uploader invalidado após sucesso;
- listagem atualizada;
- lista vazia diferenciada de erro;
- seis campos públicos;
- ordem preservada;
- ausência de banco, storage, bytes e HTML inseguro;
- testes unitários, de componente e integrados aprovados;
- smoke Docker aprovado;
- Quality Gates, H1 e H2 aprovados;
- commit de implementação separado;
- Feature Intent e Action Plan em `Done`;
- README atualizado;
- commit documental separado;
- branch sincronizada e working tree limpa.

---

## 13. Aprovação

- [x] **Human Lead Engineer aprovou este Action Plan**
- **Data da aprovação:** 2026-07-31
- **Observações:** Aprovado sem pendências bloqueantes.
