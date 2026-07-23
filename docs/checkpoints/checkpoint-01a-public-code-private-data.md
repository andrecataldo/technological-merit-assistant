# Checkpoint 01A — Código Público e Dados Privados

## 1. Identificação

- Produto: Assistente de Avaliação de Mérito Tecnológico
- Iteração: I-001
- Data: 2026-07-22
- Responsável humano: André Cataldo
- Status: Aprovado

## 2. Decisão registrada

O repositório do código-fonte poderá permanecer público.

A publicidade do código não autoriza a publicação, sincronização ou
compartilhamento de documentos reais ou de qualquer artefato derivado de
propostas avaliadas.

## 3. Conteúdo permitido no repositório

- código-fonte;
- documentação arquitetural;
- artefatos de governança sem conteúdo confidencial;
- configurações genéricas;
- regras baseadas em documentos públicos;
- testes e fixtures integralmente sintéticos.

## 4. Conteúdo proibido no repositório

- PDFs reais;
- textos extraídos;
- dados de proponentes ou equipes;
- avaliações e pareceres reais;
- bancos de dados e backups;
- logs com conteúdo sensível;
- embeddings e índices vetoriais;
- prompts contendo dados reais;
- arquivos de exportação;
- segredos e credenciais.

## 5. Consequência para a I-001

O MCP+ 001 foi versionado para v1.1.

A implementação poderá continuar desde que os controles de exclusão do Git
permaneçam ativos e sejam validados antes de cada checkpoint.

## 6. Stop Rule

A implementação deve ser interrompida caso qualquer dado real ou artefato
derivado seja incluído ou esteja prestes a ser incluído no repositório.
