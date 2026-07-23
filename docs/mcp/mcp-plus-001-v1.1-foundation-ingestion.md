# MCP+ 001 — Fundação Técnica e Ingestão Documental Local

<!-- MCP+ v0.2 -->

## 1. Identificação

- **Projeto:** Assistente de Avaliação de Mérito Tecnológico
- **Produto:** Assistente de Avaliação de Mérito Tecnológico
- **Versão do MCP+:** v1.1
- **Data:** 2026-07-22
- **Iteração / Ciclo:** I-001 — Fundação Técnica e Ingestão Documental Local
- **Responsável humano:** André Cataldo

---

## 2. Objetivo do MCP+

Construir o primeiro incremento executável do produto, capaz de:

1. iniciar a aplicação localmente;
2. criar uma avaliação;
3. selecionar um perfil de avaliação;
4. receber múltiplos arquivos PDF;
5. validar e armazenar os arquivos localmente;
6. calcular hash e detectar duplicatas;
7. extrair texto página a página usando a camada textual nativa do PDF;
8. persistir metadados e páginas extraídas;
9. listar documentos e páginas;
10. pesquisar termos textuais no conteúdo extraído;
11. abrir o texto associado ao documento e à página de origem.

O problema específico desta iteração é validar a fundação documental, a rastreabilidade por página e a proteção local dos arquivos antes da introdução de RAG, LLMs, regras de mérito ou processamento externo.

Resultado concreto esperado: uma aplicação local reproduzível que execute o fluxo **criar avaliação → selecionar perfil → enviar PDFs → extrair páginas → visualizar → pesquisar**.

Este MCP+ governa todas as interações com IA durante a Iteração I-001.

---

## 3. Escopo Congelado — Scope Lock

### 3.1 Dentro do escopo — IN

- Manter o código-fonte e a documentação não sensível no repositório público
  `technological-merit-assistant`.
- Manter documentos reais, textos extraídos, bancos, logs sensíveis,
  avaliações e demais artefatos derivados exclusivamente no ambiente local.
- Adotar pacote principal `src/merit_assistant/`.
- Configurar Python 3.12 e gerenciamento de dependências via `pyproject.toml`.
- Criar monólito modular com separação mínima entre domínio, aplicação, infraestrutura e interface.
- Configurar FastAPI, Streamlit, Pydantic, SQLAlchemy, Alembic e PostgreSQL local.
- Criar `docker-compose.yml` para banco, API e interface.
- Criar configuração por variáveis de ambiente e `.env.example` sem segredos.
- Criar `.gitignore` bloqueando documentos e dados privados.
- Criar entidade `Evaluation` para representar um processo de análise.
- Criar entidade `EvaluationProfile` com metadados mínimos.
- Criar o perfil inicial `finep_mais_inovacao_tecnologias_digitais` apenas com identificador, nome, versão e status.
- Criar upload local de múltiplos PDFs.
- Validar extensão, MIME type, tamanho configurável e nome seguro do arquivo.
- Calcular SHA-256 e detectar arquivos duplicados dentro da avaliação.
- Armazenar documentos em diretório privado fora do Git.
- Extrair texto por página com PyMuPDF.
- Persistir documento, número da página, texto, método de extração e hash.
- Registrar falha ou baixa quantidade de texto sem acionar OCR.
- Listar avaliações, documentos e páginas.
- Visualizar o texto extraído de uma página.
- Implementar busca lexical simples por palavra ou expressão.
- Exibir documento, página e trecho correspondente nos resultados.
- Implementar logs estruturados sem conteúdo integral dos documentos.
- Criar testes unitários e de integração do caminho crítico.
- Criar documentação de instalação, execução e política de dados do incremento.

### 3.2 Fora do escopo — OUT

- OCR.
- Extração especializada de tabelas.
- Reconstrução de layout, colunas ou gráficos.
- Embeddings.
- Banco vetorial e pgvector em uso funcional.
- Busca semântica, reranking ou RAG.
- LLM local.
- LLM externo.
- SDK de qualquer provedor de IA.
- Data Egress Gateway.
- Sanitização para envio externo.
- Matriz de evidências.
- Regras determinísticas da seleção.
- Analisadores de inovação, risco, viabilidade ou mercado.
- Geração das quatro respostas.
- Contagem e compressão das respostas de mérito.
- Avaliação automática ou classificação alto/médio/baixo.
- OCR adicionado como correção oportunista.
- Autenticação, autorização e multiusuário.
- Armazenamento em nuvem.
- Integração com sistemas externos.
- Microsserviços, filas distribuídas ou Kubernetes.
- Pesquisa de estado da técnica.

Qualquer item fora do escopo não pode ser incluído, mesmo que a IA sugira.

---

## 4. Decisões Bloqueadas — Decision Locks

As decisões abaixo são imutáveis nesta iteração.

| ID         | Decisão                                                                                                      | Justificativa                                                                        | Data       |
| ---------- | ------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------ | ---------- |
| DL-001     | Nome do produto: Assistente de Avaliação de Mérito Tecnológico.                                              | Identidade genérica e reutilizável.                                                  | 2026-07-22 |
| DL-002     | Repositório e pacote central não usarão referência à Finep.                                                  | Evitar acoplamento institucional.                                                    | 2026-07-22 |
| DL-003     | Regras institucionais serão perfis versionados.                                                              | Separar núcleo e domínio específico.                                                 | 2026-07-22 |
| DL-004     | A aplicação será assistiva e não decisória.                                                                  | Responsabilidade final humana.                                                       | 2026-07-22 |
| DL-007     | Dados e documentos permanecem locais ou privados.                                                            | Confidencialidade.                                                                   | 2026-07-22 |
| DL-008     | Processamento externo fica desabilitado por padrão.                                                          | Controle de saída de dados.                                                          | 2026-07-22 |
| DL-010     | Documentos reais não entram no Git.                                                                          | Evitar vazamento.                                                                    | 2026-07-22 |
| DL-013     | O MVP será um monólito modular.                                                                              | Evitar complexidade prematura.                                                       | 2026-07-22 |
| I001-DL-01 | Nenhum LLM será integrado nesta iteração.                                                                    | Validar primeiro a fundação documental.                                              | 2026-07-22 |
| I001-DL-02 | A extração inicial usará apenas a camada textual nativa via PyMuPDF.                                         | Manter escopo controlado.                                                            | 2026-07-22 |
| I001-DL-03 | A busca inicial será lexical.                                                                                | Estabelecer baseline antes do RAG.                                                   | 2026-07-22 |
| I001-DL-04 | PostgreSQL será o banco local do incremento.                                                                 | Evitar migração de persistência no próximo ciclo.                                    | 2026-07-22 |
| I001-DL-05 | Streamlit será a interface inicial e FastAPI a camada de aplicação exposta.                                  | Permitir entrega rápida sem acoplar domínio à UI.                                    | 2026-07-22 |
| I001-DL-06 | O repositório de código poderá ser público, desde que nenhum dado real ou artefato derivado seja versionado. | Permitir transparência e reutilização do código sem comprometer a confidencialidade. | 2026-07-22 |

Para alterar uma decisão bloqueada é obrigatório criar novo checkpoint, nova versão do MCP+ e justificativa explícita.

---

## 5. Suposições Aceitas

| ID    | Suposição                                                            | Impacto                                     | Observações                                   |
| ----- | -------------------------------------------------------------------- | ------------------------------------------- | --------------------------------------------- |
| SA-01 | O ambiente principal é Ubuntu com Docker disponível.                 | Define instruções de instalação e execução. | Validar no início da implementação.           |
| SA-02 | O uso inicial é monousuário.                                         | Não haverá autenticação nesta iteração.     | Não confundir com produto final.              |
| SA-03 | Os PDFs principais do piloto possuem camada textual utilizável.      | Permite adiar OCR.                          | Caso não se confirme, aplicar Stop Rule.      |
| SA-04 | O armazenamento local possui espaço suficiente para o piloto.        | Dispensa object storage.                    | Tamanho máximo será configurável.             |
| SA-05 | Uma busca lexical é suficiente para validar rastreabilidade inicial. | RAG permanece fora do escopo.               | Qualidade semântica não será avaliada ainda.  |
| SA-06 | Os testes automatizados usarão apenas PDFs sintéticos ou públicos.   | Protege dados reais.                        | Documentos reais só em execução local manual. |
| SA-07 | O perfil inicial pode começar apenas com metadados.                  | Evita implementar regras antes da fundação. | Critérios entram em MCP+ posterior.           |

---

## 6. Perguntas Proibidas à IA

Durante esta iteração, a IA não deve:

- perguntar se deve incluir um LLM para melhorar a extração;
- sugerir RAG, embeddings, vector database ou reranking;
- sugerir envio dos PDFs para APIs externas;
- sugerir OCR como melhoria automática sem ativação de Stop Rule;
- reabrir o nome do produto, repositório ou pacote;
- substituir o monólito modular por microsserviços;
- introduzir autenticação ou multiusuário;
- implementar critérios de mérito;
- gerar respostas da avaliação;
- criar abstrações genéricas sem uso observável no incremento;
- alterar o perfil inicial para conter toda a regulamentação;
- tratar logs como mecanismo de armazenamento de conteúdo documental.

---

## 7. Critérios de Sucesso da Iteração

A iteração será considerada bem-sucedida quando todos os critérios abaixo forem observáveis:

1. `docker compose up` inicia PostgreSQL, API e interface sem configuração manual adicional além do `.env`.
2. A aplicação permite criar uma avaliação e selecionar o perfil inicial.
3. A aplicação aceita múltiplos PDFs válidos e rejeita arquivo com tipo não permitido.
4. Cada arquivo recebe hash SHA-256 e duplicatas são sinalizadas sem criar nova cópia lógica indevida.
5. O arquivo original é armazenado em diretório privado ignorado pelo Git.
6. O texto é extraído e persistido separadamente para cada página.
7. A numeração de página exibida ao usuário corresponde à página física do PDF, iniciando em 1.
8. O usuário consegue listar documentos e abrir o texto de uma página específica.
9. A busca lexical retorna documento, página e trecho para uma palavra existente.
10. A busca retorna resultado vazio explícito para termo inexistente, sem inventar correspondência.
11. Falhas ou páginas sem texto suficiente são registradas como estado de extração, sem OCR automático.
12. Logs não contêm texto integral de páginas, CPF, e-mail ou telefone.
13. Nenhum documento real, banco local, log ou diretório privado aparece como arquivo rastreado pelo Git.
14. Testes automatizados cobrem upload, hash, duplicata, extração por página, persistência e busca lexical.
15. O caminho crítico passa em ambiente limpo usando fixture PDF sintética ou pública.
16. O README contém instalação, execução, estrutura de dados, limitações e procedimento de exclusão local.
17. A aplicação não realiza chamadas de rede para provedores de IA.

---

## 8. Critérios de Parada — Stop Rules

A interação com IA e a implementação devem ser interrompidas se:

- surgir contradição entre PRD-Lite, Context Pack, Guidelines, Arquitetura, Checkpoint ou este MCP+;
- um requisito crítico de confidencialidade não puder ser atendido;
- for necessário enviar documentos para serviço externo;
- a extração nativa falhar em parte crítica dos documentos do piloto e OCR se tornar necessário;
- for necessário expandir o modelo para tabelas, imagens ou reconstrução de layout;
- a persistência precisar abandonar PostgreSQL;
- a separação FastAPI/Streamlit se mostrar tecnicamente inviável para o incremento;
- documentos ou dados privados forem adicionados ao Git;
- logs revelarem conteúdo sensível;
- o escopo precisar incluir RAG, LLM, regras de mérito ou geração de respostas;
- uma Decision Lock precisar ser revista;
- qualquer documento real, texto extraído, banco, log sensível, parecer,
  embedding ou artefato derivado for incluído ou estiver prestes a ser
  incluído no repositório público.

Nessas situações, criar novo checkpoint e nova versão do MCP+ antes de continuar.

---

## 9. Autoridade e Responsabilidades

### A IA pode

- propor estrutura de diretórios compatível com os artefatos aprovados;
- gerar código limitado ao escopo IN;
- gerar migrations, modelos, endpoints, páginas Streamlit e testes;
- apontar ambiguidades técnicas que bloqueiem implementação;
- sugerir correções de segurança dentro do escopo;
- executar tarefas explicitamente delegadas;
- interromper quando uma Stop Rule for atingida.

### A IA não pode

- tomar decisões finais;
- alterar escopo;
- invalidar Decision Locks;
- adicionar tecnologia fora da stack aprovada sem autorização;
- introduzir IA generativa no produto nesta iteração;
- processar ou reproduzir conteúdo confidencial em exemplos, testes ou logs;
- transformar suposições em requisitos permanentes.

### Responsabilidade humana

O responsável humano deve:

- assegurar a separação entre código público e dados confidenciais locais;
- aprovar a estrutura inicial antes da implementação extensa;
- validar o funcionamento local;
- decidir sobre qualquer Stop Rule;
- revisar segurança e conteúdo dos commits;
- encerrar conscientemente a iteração.

Decisão final é sempre humana.

---

## 10. Artefatos Vinculados

Este MCP+ se baseia nos seguintes artefatos:

- **PRD-Lite:** `docs/prd/prd-lite-v0.1.md`
- **Context Pack:** `docs/context/context-pack-v0.1.md`
- **Feature Intent:** não aplicável nesta iteração; a intenção está integralmente congelada neste MCP+.
- **Guidelines Técnicas:** `docs/guidelines/technical-guidelines-v0.1.md`
- **Arquitetura:** `docs/architecture/architecture-vision-v0.1.md`
- **Plano de Execução:** `docs/planning/execution-plan-v0.1.md`
- **Checkpoint:** `docs/checkpoints/checkpoint-00-definition-approved.md`

---

## 11. Definition of Ready

Status: **READY**.

Verificação:

- objetivo da iteração está claro;
- escopo IN e OUT está congelado;
- Decision Locks estão definidos;
- suposições estão explícitas;
- critérios de sucesso são observáveis;
- critérios de parada estão definidos;
- artefatos vinculados estão identificados;
- responsabilidade humana está explícita.

A implementação pode começar somente dentro deste contrato.

---

## 12. Validade do MCP+

Este MCP+ é válido:

- apenas para a Iteração I-001;
- até que todos os critérios de sucesso sejam atendidos;
- até que uma Stop Rule seja atingida;
- ou até ser explicitamente substituído por nova versão.

**Versão seguinte prevista:** MCP+ 002 — Estruturação de Entidades e Matriz de Evidências, sujeita ao checkpoint de encerramento da Iteração I-001.

- PRD-Lite: `docs/prd/prd-lite-v0.1.md`
- Context Pack: `docs/context/context-pack-v0.1.md`
- Guidelines Técnicas: `docs/guidelines/technical-guidelines-v0.1.md`
- Visão de Arquitetura: `docs/architecture/architecture-vision-v0.1.md`
- Plano de Execução: `docs/planning/execution-plan-v0.1.md`
- Checkpoint: `docs/checkpoints/checkpoint-00-definition-approved.md`

---

## 11. Validade do MCP+

Este MCP+ é válido somente para a Iteração I-001, até que um critério de parada seja atingido ou uma nova versão seja aprovada pelo responsável humano.
