# Guidelines Técnicas v0.1

## Princípios

1. Evidência antes de narrativa.
2. Regras determinísticas antes de LLM.
3. Processamento local por padrão.
4. Provedores substituíveis.
5. Falhas e lacunas explícitas.

## Stack aprovada

Python 3.12, FastAPI, Streamlit, Pydantic, SQLAlchemy, Alembic, PostgreSQL, PyMuPDF, Pytest, Ruff, mypy e Docker Compose.

## Segurança

- nenhum documento real no Git;
- nenhum texto integral em logs;
- segredos fora do código;
- hashes para integridade;
- isolamento por avaliação;
- processamento externo bloqueado nesta iteração.

## Arquitetura

Monólito modular com separação entre domínio, aplicação, infraestrutura e interface.
