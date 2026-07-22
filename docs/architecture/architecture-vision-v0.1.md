# Visão de Arquitetura v0.1

## Estilo

Monólito modular para o MVP.

## Camadas

- Interface: Streamlit e FastAPI.
- Aplicação: casos de uso e orquestração.
- Domínio: entidades e regras independentes.
- Infraestrutura: banco, arquivos, extração e provedores futuros.

## Núcleo e perfis

O núcleo é genérico. Cada programa é representado por um perfil versionado com metadados, critérios, regras e prompts, adicionados progressivamente.

## Caminho documental futuro

Upload → validação → armazenamento privado → extração por página → persistência → busca lexical → visualização rastreável.

## Caminho externo

Está arquiteturalmente previsto para ciclos futuros, mas bloqueado no MCP+ 001.
