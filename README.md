# Assistente de Avaliação de Mérito Tecnológico

Aplicação privada e assistiva para apoiar especialistas na análise documental e na elaboração de avaliações técnicas de projetos de inovação.

> Estado atual: **Iteração I-001 — Fundação Técnica e Ingestão Documental Local**.
>
> Nesta iteração não há LLM, RAG, embeddings, OCR, avaliação automática ou processamento externo.

## Princípios

- responsabilidade final humana;
- documentos e dados privados permanecem locais;
- rastreabilidade por documento e página;
- regras específicas organizadas em perfis versionados;
- nenhum documento real no Git;
- arquitetura híbrida aprovada, porém processamento externo bloqueado nesta iteração.

## Escopo deste scaffold

Este scaffold entrega a fundação reproduzível do projeto:

- Python 3.12 e `pyproject.toml`;
- FastAPI e Streamlit;
- PostgreSQL e Alembic;
- perfil inicial com metadados mínimos;
- endpoint de saúde;
- criação e listagem inicial de avaliações;
- estrutura modular para ingestão documental posterior;
- testes básicos e CI;
- política de dados privados e `.gitignore` restritivo.

## Requisitos

- Ubuntu ou ambiente compatível;
- Docker Engine;
- Docker Compose v2;
- Git;
- GitHub CLI (`gh`) apenas para criação do repositório remoto.

## Inicialização local

```bash
cp .env.example .env
docker compose up --build
```

Serviços:

- API: http://localhost:8000
- Documentação da API: http://localhost:8000/docs
- Interface: http://localhost:8501
- PostgreSQL: `localhost:5432`

## Testes locais sem Docker

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest
ruff check .
mypy src
```

## Criar o repositório privado

Depois de revisar os arquivos:

```bash
./scripts/create_private_repository.sh
```

O script exige autenticação prévia:

```bash
gh auth login
```

## Dados privados

Nunca versionar:

- PDFs reais;
- bancos locais;
- logs de execução;
- respostas ou pareceres reais;
- arquivos `.env`;
- dados exportados.

Use `data/private/` somente no ambiente local. O conteúdo do diretório é ignorado pelo Git.

## Documentos de governança

Leia nesta ordem:

1. `docs/checkpoints/checkpoint-00-definition-approved.md`
2. `docs/mcp/mcp-plus-001-foundation-ingestion.md`

O MCP+ 001 governa toda a implementação desta iteração.
