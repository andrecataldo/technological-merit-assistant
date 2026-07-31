# Assistente de Avaliação de Mérito Tecnológico

Aplicação assistiva para apoiar especialistas na análise documental e na
elaboração de avaliações técnicas de projetos de inovação, mantendo
rastreabilidade, confidencialidade e responsabilidade humana.

> **Estado atual:** Iteração I-001 — Fundação Técnica e Ingestão Documental
> Local.
>
> **F01.1 a F01.7 concluídas.** O backend cria e lista avaliações, recebe,
> valida, armazena e lista documentos. A interface Streamlit permite criar ou
> selecionar uma avaliação, enviar um PDF e consultar os documentos associados
> utilizando exclusivamente a FastAPI local.
>
> Nesta iteração não há LLM, RAG, embeddings, OCR, avaliação automática ou
> processamento externo.

## Princípios

- a aplicação apoia o especialista, mas não substitui sua decisão;
- a responsabilidade e a aprovação final permanecem humanas;
- código, documentação e testes sintéticos podem ser públicos;
- documentos reais e artefatos confidenciais permanecem locais ou privados;
- nenhum documento real é versionado no Git;
- o backend é a autoridade para validação, persistência e isolamento;
- processamento externo permanece desabilitado por padrão;
- erros públicos não expõem paths, SHA-256, storage keys, SQL ou conteúdo
  documental.

## Estado do incremento F01

| Incremento | Entrega | Estado |
| --- | --- | --- |
| F01.1 | Modelo `Document` e migration | Concluído |
| F01.2 | Armazenamento local seguro | Concluído |
| F01.3 | Validação de PDF, tamanho e SHA-256 | Concluído |
| F01.4 | Orquestração segura do upload e persistência | Concluído |
| F01.5 | Endpoint seguro de upload | Concluído |
| F01.6 | Endpoint seguro de listagem | Concluído |
| F01.7 | Interface Streamlit para upload e listagem | Concluído |

Último baseline validado da F01.7:

- implementação registrada em `75a8ddbd9f7a9dac68efac166935bac2a736d3f9`;
- 356 testes aprovados;
- Ruff aprovado;
- mypy aprovado em `src` e `ui`;
- verificação de escopo I-001 aprovada;
- PostgreSQL e migration `0002_add_documents (head)` operacionais;
- health da API e do Streamlit aprovados;
- integração e smoke operacional aprovados;
- nenhum PDF ou dado privado adicional rastreado;
- processamento externo desabilitado.

## Funcionalidades disponíveis

### Avaliações

- consulta do perfil de avaliação configurado;
- criação de avaliação;
- listagem de avaliações.

### Documentos

- modelo documental persistido no PostgreSQL;
- armazenamento privado em `data/private/`;
- validação de nome, tipo declarado, assinatura PDF e tamanho;
- cálculo de SHA-256;
- detecção de duplicidade por avaliação;
- compensação de arquivo e transação em falhas conhecidas;
- upload seguro de um PDF por requisição;
- listagem isolada por avaliação;
- ordenação determinística por `created_at` e `id`;
- retorno exclusivo de metadados públicos.

### Interface

A interface Streamlit:

- verifica o health da API;
- bloqueia a jornada quando o processamento externo está habilitado;
- consulta os perfis de avaliação;
- cria avaliações;
- lista avaliações existentes;
- seleciona uma avaliação por título e UUID completo;
- mantém a seleção durante reruns legítimos;
- aceita um PDF por submissão explícita;
- impede reenvio automático durante reruns;
- invalida o uploader após upload bem-sucedido;
- lista os documentos da avaliação selecionada;
- diferencia lista vazia de falha de carregamento;
- apresenta mensagens públicas sanitizadas;
- exibe somente os seis metadados documentais públicos;
- consome exclusivamente a FastAPI local;
- não acessa diretamente PostgreSQL ou `data/private`.

## Arquitetura

```text
Streamlit
   |
   v
FastAPI
   |
   v
Application Services
   |
   v
Ports
   |
   +--> PostgreSQL / SQLAlchemy
   +--> Armazenamento local privado
   +--> Inspeção local de PDF
```

Fronteiras principais:

- Streamlit consome somente a API HTTP;
- regras de negócio ficam nos serviços de aplicação;
- persistência e armazenamento são acessados por portas;
- documentos reais não passam pelo Git;
- nenhum componente da I-001 envia conteúdo para serviços externos.

## Contratos HTTP atuais

| Método | Endpoint | Finalidade |
| --- | --- | --- |
| `GET` | `/health` | Estado da aplicação e processamento externo |
| `GET` | `/profiles` | Perfil de avaliação configurado |
| `POST` | `/evaluations` | Criar avaliação |
| `GET` | `/evaluations` | Listar avaliações |
| `POST` | `/evaluations/{evaluation_id}/documents` | Enviar um PDF |
| `GET` | `/evaluations/{evaluation_id}/documents` | Listar documentos |

A resposta documental pública contém somente:

- `id`;
- `evaluation_id`;
- `original_filename`;
- `content_type`;
- `size_bytes`;
- `created_at`.

Não são retornados `storage_key`, caminho físico, SHA-256 ou conteúdo.

## Requisitos

- Ubuntu ou ambiente compatível;
- Python `>=3.12,<3.13`;
- Docker Engine;
- Docker Compose v2;
- Git.

## Inicialização com Docker Compose

```bash
cp .env.example .env
docker compose up --build
```

A API executa `alembic upgrade head` durante a inicialização.

Serviços locais:

- API: `http://localhost:8000`;
- documentação OpenAPI: `http://localhost:8000/docs`;
- interface Streamlit: `http://localhost:8501`;
- PostgreSQL: `localhost:5432`.

Verificação rápida:

```bash
docker compose ps
docker compose exec -T api alembic current
curl -fsS http://localhost:8000/health
```

Resposta esperada do health:

```json
{
  "status": "ok",
  "external_processing_enabled": false
}
```

## Desenvolvimento e Quality Gates

Crie e ative o ambiente virtual:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

Mantenha o PostgreSQL operacional para a suíte integrada:

```bash
docker compose up -d db
```

Execute os gates:

```bash
pytest
ruff check .
mypy src
mypy ui
./scripts/verify_i001_scope.sh
git diff --check
```

A verificação I-001 bloqueia, entre outros casos:

- documentos e bancos proibidos rastreados pelo Git;
- referências não autorizadas a LLM, RAG ou banco vetorial no código;
- processamento externo habilitado no ambiente local.

## Configuração

Copie `.env.example` para `.env` e revise os valores locais.

Configurações relevantes:

- `DATABASE_URL`;
- `PRIVATE_DATA_DIR`;
- `MAX_UPLOAD_SIZE_MB`;
- `EXTERNAL_PROCESSING_ENABLED=false`.

O arquivo `.env` nunca deve ser versionado.

## Dados privados

Nunca versionar:

- PDFs ou documentos reais;
- bancos locais;
- conteúdo extraído;
- embeddings;
- prompts ou logs sensíveis;
- respostas e pareceres reais;
- arquivos `.env`;
- dados exportados;
- artefatos derivados confidenciais.

Use `data/private/` exclusivamente no ambiente local. Somente o marcador
`.gitkeep` pode permanecer rastreado.

Os testes devem utilizar apenas identificadores e PDFs sintéticos.

## Governança

Leia os artefatos nesta ordem:

1. [`Checkpoint 00`](docs/checkpoints/checkpoint-00-definition-approved.md);
2. [`MCP+ 001`](docs/mcp/mcp-plus-001-foundation-ingestion.md);
3. [`Feature Intent da F01`](docs/features/feature-intent-f01-secure-document-ingestion.md);
4. [`Feature Intents`](docs/features/);
5. [`Action Plans`](docs/action-plans/).

O MCP+ 001 v1.1 governa a implementação da I-001.

Cada incremento segue o fluxo:

```text
Feature Intent
    -> aprovação humana
    -> commit documental
    -> Action Plan
    -> aprovação humana
    -> commit documental
    -> implementação
    -> checkpoints H1 e H2
    -> commit da implementação
    -> encerramento documental
```

Nenhum código de uma nova feature deve ser alterado antes da aprovação e do
commit de seus artefatos de governança.

## Situação após a F01.7

A F01 — Ingestão Segura de Documentos está concluída até a interface
operacional de upload e listagem.

O próximo incremento deverá ser definido por novo fluxo de governança:

~~~text
Feature Intent
    -> aprovação humana
    -> commit documental
    -> Action Plan
    -> aprovação humana
    -> commit documental
    -> implementação
~~~

Extração de texto, tabelas, OCR, embeddings, RAG, LLM e análise de mérito
continuam fora do escopo da I-001 até que sejam explicitamente planejados e
aprovados.
