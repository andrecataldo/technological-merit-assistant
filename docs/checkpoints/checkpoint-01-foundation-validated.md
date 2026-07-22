# Checkpoint 01 — Fundação Técnica Validada

## 1. Identificação

- Produto: Assistente de Avaliação de Mérito Tecnológico
- Iteração: I-001
- Data: 2026-07-22
- Responsável humano: André Cataldo
- Status: Validado

## 2. Objetivo do checkpoint

Registrar a validação da fundação técnica necessária para iniciar a ingestão
segura de documentos.

## 3. Estado consolidado

- Python 3.12.12 configurado por pyenv.
- Ambiente virtual local `.venv` operacional.
- VSCode definido como IDE principal.
- PostgreSQL 16 operacional em Docker.
- FastAPI operacional na porta 8000.
- Streamlit operacional na porta 8501.
- Alembic executando migrations na inicialização.
- Perfil inicial carregado corretamente.
- Criação e listagem de avaliações persistidas no PostgreSQL.
- Processamento externo desabilitado.
- Dados privados mantidos fora do Git.

## 4. Validações realizadas

- `pytest`: 3 testes aprovados.
- `ruff check .`: aprovado.
- `mypy src`: aprovado.
- `verify_i001_scope.sh`: aprovado.
- Container `db`: ativo e saudável.
- Container `api`: ativo.
- Container `ui`: ativo.
- Endpoint `/health`: operacional.
- Endpoint `/profiles`: operacional.
- Endpoints de criação e listagem de avaliações: operacionais.

## 5. Decisões vigentes

- O repositório de código pode permanecer público.
- Documentos reais e artefatos derivados permanecem exclusivamente locais.
- Nenhum PDF real será usado antes da conclusão dos testes de segurança do F01.
- O processamento externo permanece bloqueado.
- A responsabilidade pela avaliação final permanece humana.

## 6. Próximo incremento

F01 — Ingestão segura de documentos PDF.

O incremento deverá validar, armazenar, identificar e registrar documentos,
sem realizar OCR, RAG, embeddings, análise de mérito ou geração de respostas.

## 7. Condições de retomada

A implementação deve continuar sob o MCP+ 001 e interromper caso:

- seja necessário expandir o escopo;
- dados privados sejam incluídos no Git;
- documentos sejam enviados externamente;
- seja necessário alterar um Decision Lock;
- a rastreabilidade documental não possa ser preservada.
