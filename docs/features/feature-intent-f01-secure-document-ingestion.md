# Feature Intent F01 — Ingestão Segura de Documentos

## Propósito

Permitir que o usuário associe documentos PDF a uma avaliação, mantendo
confidencialidade, integridade, rastreabilidade e isolamento entre avaliações.

## Valor

Estabelecer a base documental sobre a qual serão construídas posteriormente
a extração por página, a matriz de evidências e a avaliação técnica.

## Dentro do escopo

- selecionar uma avaliação existente;
- enviar um arquivo PDF;
- limitar o tamanho conforme configuração;
- validar extensão, MIME type e assinatura PDF;
- calcular hash SHA-256;
- detectar duplicidade dentro da avaliação;
- gerar identificador interno independente do nome original;
- armazenar localmente em `data/private`;
- registrar metadados no PostgreSQL;
- listar documentos associados à avaliação;
- preservar o nome original somente como metadado;
- impedir vazamento de conteúdo nos logs.

## Fora do escopo

- extração de texto;
- OCR;
- extração de tabelas;
- embeddings;
- RAG;
- LLM;
- classificação automática;
- geração das quatro respostas;
- envio de dados para serviços externos;
- edição ou alteração do documento original.

## Critérios de aceitação

1. Arquivos não PDF são rejeitados.
2. Arquivos acima do limite configurado são rejeitados.
3. PDFs inválidos ou malformados são rejeitados.
4. O conteúdo é armazenado fora do Git.
5. O nome físico usa identificador interno seguro.
6. O SHA-256 é registrado.
7. Duplicidades são detectadas.
8. O documento pertence a uma única avaliação.
9. A listagem não expõe o caminho físico interno.
10. Nenhum conteúdo documental aparece nos logs.
11. Testes unitários e de integração são aprovados.
12. Ruff, mypy e verificador I-001 permanecem aprovados.

## Dependências

- avaliação persistida;
- PostgreSQL;
- diretório privado configurado;
- FastAPI;
- Streamlit;
- SQLAlchemy e Alembic.

## Riscos principais

- path traversal por nome de arquivo;
- arquivo falso com extensão PDF;
- consumo excessivo de memória;
- gravação parcial em caso de erro;
- colisão ou duplicidade;
- acesso cruzado entre avaliações;
- inclusão acidental do documento no Git.
