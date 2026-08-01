# Feature Intent F01.7 — Interface Streamlit para Upload e Listagem Segura de Documentos

## 1. Identificação

- **Título da Feature:** F01.7 — Interface Streamlit para Upload e Listagem Segura de Documentos
- **Feature pai:** F01 — Ingestão Segura de Documentos
- **Autor — Human Lead Engineer:** André Cataldo
- **Data:** 2026-07-31
- **Status:** Done
- **Branch:** `feature/f01-secure-document-ingestion`
- **Baseline:** `7bf6c6a7c550986b467c5f837317d7af669858a6`
- **MCP+ aplicável:** MCP+ 001 v1.1
- **Dependências funcionais:**
  - F01.1 — Modelo de Documento e Migration;
  - F01.2 — Serviço Local de Armazenamento Seguro;
  - F01.3 — Validação de PDF, Limite de Tamanho e SHA-256;
  - F01.4 — Orquestração Segura do Upload e Persistência;
  - F01.5 — Endpoint Seguro de Upload de Documentos;
  - F01.6 — Listagem Segura de Documentos por Avaliação.

---

## 2. Contexto e Problema

A aplicação possui uma interface Streamlit inicial capaz de:

- verificar a disponibilidade da API;
- exibir o estado do processamento externo;
- consultar os perfis de avaliação;
- criar uma avaliação;
- listar as avaliações existentes.

A API já permite:

- enviar um PDF para uma avaliação por meio de
  `POST /evaluations/{evaluation_id}/documents`;
- listar os documentos de uma avaliação por meio de
  `GET /evaluations/{evaluation_id}/documents`;
- retornar somente os seis metadados documentais públicos;
- manter o conteúdo em armazenamento privado;
- preservar mensagens HTTP sanitizadas.

Ainda não existe na interface uma jornada operacional que permita ao
especialista:

- selecionar explicitamente uma avaliação;
- enviar um PDF para a avaliação selecionada;
- acompanhar o resultado do upload;
- consultar os documentos já associados;
- atualizar a listagem depois de um upload;
- distinguir estados vazios, falhas de validação e indisponibilidade da API.

Sem uma interface específica, o usuário precisa utilizar diretamente a API.

Uma implementação inadequada também poderia:

- acessar diretamente PostgreSQL ou `data/private`;
- duplicar regras de validação existentes no backend;
- gravar cópias temporárias do documento;
- disparar o mesmo upload novamente durante um rerun do Streamlit;
- exibir bodies HTTP, traces ou mensagens internas;
- expor `storage_key`, SHA-256 ou caminhos físicos;
- manter bytes documentais desnecessariamente em `session_state`;
- selecionar a avaliação errada quando títulos forem repetidos;
- ocultar falhas de comunicação com a API;
- criar acoplamento entre a interface e as camadas internas da aplicação.

---

## 3. Intenção — Outcome

Disponibilizar uma jornada Streamlit segura para selecionar uma avaliação,
enviar um PDF e consultar os documentos associados, utilizando exclusivamente
os contratos públicos da FastAPI.

A interface deverá:

- preservar a criação e a listagem de avaliações existentes;
- permitir a seleção explícita de uma avaliação;
- identificar avaliações por título e UUID;
- permitir o envio de um PDF por submissão;
- enviar o arquivo somente após ação explícita do usuário;
- chamar o endpoint de upload uma única vez por submissão;
- listar os documentos da avaliação selecionada;
- atualizar a listagem após upload concluído;
- apresentar estados vazios e mensagens de erro compreensíveis;
- mostrar somente metadados públicos;
- não acessar diretamente banco, storage ou serviços de domínio;
- não persistir cópias do arquivo na interface;
- não enviar dados a serviços externos;
- manter a decisão e a operação sob controle humano.

Vários documentos poderão ser associados à mesma avaliação por meio de
submissões sucessivas. Upload simultâneo em lote não será necessário nesta
iteração.

---

## 4. Escopo

### 4.1 Dentro do escopo — IN

- [x] Evoluir a interface Streamlit existente.
- [x] Preservar a verificação de health da API.
- [x] Preservar a exibição do estado de processamento externo.
- [x] Preservar a consulta dos perfis de avaliação.
- [x] Preservar a criação de avaliações.
- [x] Preservar a listagem de avaliações.
- [x] Tratar com segurança falhas nos fluxos já existentes da interface.
- [x] Permitir selecionar uma avaliação existente.
- [x] Identificar cada opção por título e UUID.
- [x] Manter a avaliação selecionada durante reruns legítimos da sessão.
- [x] Atualizar as opções depois da criação de uma avaliação.
- [x] Permitir selecionar um único PDF por submissão.
- [x] Restringir visualmente o seletor a arquivos PDF.
- [x] Manter a validação definitiva no backend.
- [x] Enviar o arquivo no campo multipart `file`.
- [x] Enviar o `evaluation_id` selecionado no path.
- [x] Utilizar o fluxo fornecido pelo `UploadedFile`.
- [x] Não criar arquivo temporário adicional.
- [x] Não executar upload antes da submissão explícita.
- [x] Bloquear nova submissão enquanto o upload estiver em andamento.
- [x] Impedir reenvio automático causado por rerun do Streamlit.
- [x] Limpar ou invalidar o arquivo selecionado após upload bem-sucedido.
- [x] Executar uma única chamada de upload por submissão.
- [x] Informar sucesso somente após resposta HTTP `201`.
- [x] Atualizar a lista documental após upload bem-sucedido.
- [x] Consultar documentos por meio do endpoint GET aprovado.
- [x] Exibir lista vazia de forma compreensível.
- [x] Exibir somente:
  - `id`;
  - `evaluation_id`;
  - `original_filename`;
  - `content_type`;
  - `size_bytes`;
  - `created_at`.
- [x] Não exibir `storage_key`.
- [x] Não exibir caminho físico absoluto ou relativo.
- [x] Não exibir SHA-256.
- [x] Não exibir conteúdo documental.
- [x] Não acessar diretamente PostgreSQL.
- [x] Não acessar diretamente `data/private`.
- [x] Não importar adapters, sessões ou serviços internos na interface.
- [x] Usar `API_BASE_URL` como fronteira de comunicação.
- [x] Utilizar timeouts finitos nas chamadas HTTP.
- [x] Tratar falhas de conexão e timeout.
- [x] Traduzir respostas conhecidas para mensagens estáveis na interface.
- [x] Não exibir `response.text` diretamente.
- [x] Não exibir traces ou detalhes internos.
- [x] Renderizar títulos, nomes de arquivos e mensagens como texto seguro.
- [x] Não usar `unsafe_allow_html=True` com dados controlados pelo usuário ou pela API.
- [x] Não registrar conteúdo documental em logs.
- [x] Não manter bytes documentais em estado persistente da aplicação.
- [x] Criar testes automatizados da comunicação HTTP da interface.
- [x] Criar testes automatizados dos principais estados da interface.
- [x] Validar o fluxo no Docker Compose.
- [x] Preservar todos os Quality Gates existentes.
- [x] Manter o processamento externo desabilitado.
- [x] Usar exclusivamente dados e PDFs sintéticos nos testes.

### 4.2 Fora do escopo — OUT

- [ ] Alterar os contratos dos endpoints documentais.
- [ ] Criar novos endpoints FastAPI.
- [ ] Alterar serviços de upload ou listagem.
- [ ] Alterar validações documentais do backend.
- [ ] Alterar entidades ou modelos SQLAlchemy.
- [ ] Criar ou alterar migrations.
- [ ] Alterar a tabela `documents`.
- [ ] Alterar o armazenamento privado.
- [ ] Criar upload simultâneo em lote.
- [ ] Criar endpoint batch.
- [ ] Fazer download de documentos.
- [ ] Excluir documentos.
- [ ] Visualizar o conteúdo do PDF.
- [ ] Editar ou substituir documentos.
- [ ] Classificar o tipo documental.
- [ ] Extrair texto, páginas, imagens ou tabelas.
- [ ] Executar OCR.
- [ ] Criar embeddings.
- [ ] Implementar RAG ou LLM.
- [ ] Executar análise de mérito.
- [ ] Enviar dados a serviços externos.
- [ ] Implementar autenticação ou autorização.
- [ ] Implementar rate limiting.
- [ ] Implementar antivírus.
- [ ] Criar paginação ou filtros documentais.
- [ ] Criar ordenação configurável pelo usuário.
- [ ] Realizar redesign visual amplo.
- [ ] Adotar outro framework de interface.
- [ ] Criar dependência direta entre Streamlit e PostgreSQL.
- [ ] Criar dependência direta entre Streamlit e o storage.
- [ ] Adicionar documentos reais ao repositório.
- [ ] Adicionar nova dependência de runtime sem aprovação.

---

## 5. Jornada do Usuário

### 5.1 Entrada

1. O usuário abre a interface Streamlit.
2. A interface verifica a disponibilidade da FastAPI.
3. A interface confirma que o processamento externo está desabilitado.
4. A interface consulta perfis e avaliações.

### 5.2 Criação ou seleção da avaliação

1. O usuário poderá criar uma avaliação pelo fluxo já existente.
2. A nova avaliação deverá ficar disponível para seleção.
3. O usuário selecionará uma avaliação de forma explícita.
4. A opção deverá permitir distinguir avaliações com títulos iguais por UUID.
5. Nenhum upload poderá ocorrer sem avaliação selecionada.

### 5.3 Upload

1. O usuário seleciona um PDF.
2. A interface apresenta o arquivo escolhido sem abrir seu conteúdo.
3. O usuário confirma o envio por um botão ou submissão explícita.
4. A interface envia um único multipart para a API.
5. Durante a operação, a interface apresenta estado de processamento e bloqueia nova submissão.
6. A interface informa sucesso somente após HTTP `201`.
7. A interface não repete automaticamente a chamada durante reruns.
8. Após sucesso, o arquivo selecionado é limpo ou invalidado.
9. Após sucesso, a listagem documental é atualizada.

### 5.4 Listagem

1. A interface chama o GET documental para a avaliação selecionada.
2. Uma avaliação sem documentos apresenta estado vazio.
3. Uma avaliação com documentos apresenta exclusivamente os seis campos
   públicos.
4. A ordem recebida da API é preservada.
5. A interface não consulta banco ou storage para complementar os dados.

---

## 6. Contratos HTTP Consumidos

### 6.1 Health

```text
GET /health
```

Finalidade:

- verificar disponibilidade da API;
- confirmar `external_processing_enabled`;
- impedir continuidade silenciosa quando a API estiver indisponível.

### 6.2 Perfis

```text
GET /profiles
```

Finalidade:

- preencher a seleção de perfil para criação de avaliação.

### 6.3 Avaliações

```text
POST /evaluations
GET /evaluations
```

Finalidade:

- preservar a criação existente;
- carregar as opções de avaliação;
- obter o UUID utilizado nos endpoints documentais.

### 6.4 Upload documental

```text
POST /evaluations/{evaluation_id}/documents
Content-Type: multipart/form-data
```

Regras da interface:

- campo multipart exatamente `file`;
- um arquivo por submissão;
- resposta de sucesso esperada: HTTP `201`;
- nenhuma duplicação das regras de validação do backend;
- nenhuma escrita local adicional.

### 6.5 Listagem documental

```text
GET /evaluations/{evaluation_id}/documents
```

Regras da interface:

- resposta de sucesso esperada: HTTP `200`;
- lista vazia é um resultado válido;
- ordem da API é preservada;
- somente o schema público é utilizado.

---

## 7. Estados da Interface

A interface deverá representar explicitamente:

- API disponível;
- API indisponível;
- carregamento de avaliações;
- nenhuma avaliação existente;
- avaliação selecionada;
- nenhum documento associado;
- carregamento da lista documental;
- documento pronto para submissão;
- upload em andamento;
- upload concluído;
- erro conhecido de validação;
- documento duplicado;
- avaliação inexistente;
- falha interna sanitizada;
- falha de conexão ou timeout.

A interface não deverá tratar falha de carregamento como lista vazia sem avisar o
usuário.

---

## 8. Contrato de Mensagens Seguras

A interface deverá apresentar mensagens públicas estáveis em português.

Exemplos de mensagens esperadas:

| Situação                 | Mensagem da interface                              |
| ------------------------ | -------------------------------------------------- |
| API indisponível         | `API indisponível. Verifique o ambiente local.`    |
| Nenhuma avaliação        | `Crie uma avaliação antes de enviar documentos.`   |
| Nenhum documento         | `Nenhum documento associado à avaliação.`          |
| Upload concluído         | `Documento enviado com sucesso.`                   |
| Avaliação inexistente    | `Avaliação não encontrada.`                        |
| Documento duplicado      | `Documento já associado à avaliação.`              |
| Arquivo muito grande     | `O documento excede o limite permitido.`           |
| Tipo não suportado       | `Tipo de conteúdo não suportado.`                  |
| PDF inválido             | `O arquivo enviado não é um PDF válido.`           |
| Falha de listagem        | `Não foi possível listar os documentos.`           |
| Falha genérica de upload | `Não foi possível concluir o upload do documento.` |

Regras:

- mensagens conhecidas somente poderão ser mapeadas por combinação previamente
  aprovada de status e detalhe público;
- mensagens ou detalhes não reconhecidos deverão gerar mensagem genérica;
- não apresentar `response.text`;
- não apresentar HTML retornado por proxy ou servidor;
- não apresentar SQL, constraints, paths ou stack traces;
- não apresentar conteúdo do arquivo;
- renderizar títulos, nomes de arquivos e mensagens como texto seguro;
- não interpolar dados controlados pelo usuário ou pela API em HTML inseguro;
- não confiar em mensagens arbitrárias recebidas da rede;
- detalhes técnicos poderão ser tratados internamente sem aparecer na tela.

---

## 9. Fronteiras Arquiteturais

A interface Streamlit deverá depender exclusivamente da API HTTP.

Fluxo permitido:

```text
Streamlit → FastAPI → Application Services → Ports → Infrastructure
```

Fluxos proibidos:

```text
Streamlit → SQLAlchemy
Streamlit → PostgreSQL
Streamlit → DocumentPersistence
Streamlit → DocumentStorage
Streamlit → LocalDocumentStorage
Streamlit → data/private
Streamlit → DocumentUploadService
Streamlit → DocumentListingService
```

A definição definitiva da organização dos módulos da interface, cliente HTTP,
funções de apresentação e estado de sessão será realizada no Action Plan.

Não deverá existir sessão SQLAlchemy ou caminho físico documental no processo da
interface.

---

## 10. Segurança e Privacidade

A implementação deverá preservar:

- processamento exclusivamente local;
- `external_processing_enabled` igual a `false`;
- conteúdo documental enviado somente à FastAPI local;
- ausência de envio a modelos ou serviços externos;
- armazenamento definitivo somente sob responsabilidade do backend;
- ausência de cópias temporárias criadas pela interface;
- ausência de conteúdo documental em logs;
- ausência de conteúdo documental em mensagens de erro;
- ausência de bytes persistidos em `session_state`;
- ausência de `storage_key`, SHA-256 ou path na tela;
- ausência de documentos reais no Git;
- validação autoritativa no backend;
- submissão humana explícita;
- uma chamada HTTP por ação de upload;
- seleção explícita da avaliação;
- isolamento entre avaliações provido pela API;
- mensagens sanitizadas;
- renderização segura, sem HTML inseguro para dados controlados;
- timeouts finitos;
- nenhuma chamada de rede fora da API configurada.

O filtro visual de arquivos PDF melhora a experiência, mas não substitui a
validação de assinatura, MIME type e tamanho realizada pelo backend.

---

## 11. Critérios de Aceitação

1. A interface inicia e confirma a disponibilidade da API.
2. O estado de processamento externo permanece visível e desabilitado.
3. O fluxo existente de criação de avaliação continua funcionando.
4. Avaliações existentes podem ser selecionadas.
5. Avaliações com títulos iguais podem ser distinguidas pelo UUID.
6. Nenhum upload ocorre sem avaliação e arquivo selecionados.
7. O upload ocorre somente após ação explícita.
8. Uma nova submissão fica bloqueada enquanto o upload estiver em andamento.
9. Cada submissão gera no máximo uma chamada de upload.
10. Reruns do Streamlit não reenviam automaticamente o documento.
11. Após sucesso, o arquivo selecionado é limpo ou invalidado.
12. Um PDF válido retorna confirmação de sucesso.
13. O documento criado aparece na listagem após o upload.
14. Vários documentos podem ser enviados por submissões sucessivas.
15. Documento duplicado apresenta mensagem segura.
16. PDF inválido apresenta mensagem segura.
17. Arquivo acima do limite apresenta mensagem segura.
18. Tipo não suportado apresenta mensagem segura.
19. Avaliação inexistente apresenta mensagem segura.
20. Avaliação sem documentos apresenta estado vazio.
21. A listagem contém somente documentos da avaliação selecionada.
22. A listagem preserva a ordem retornada pela API.
23. A tela utiliza somente os seis campos públicos aprovados.
24. A tela não apresenta `storage_key`, SHA-256, path ou conteúdo.
25. A interface não acessa banco, storage ou serviços internos.
26. A interface não grava arquivos temporários.
27. A interface não exibe `response.text`, traces ou detalhes internos.
28. A interface não usa HTML inseguro para títulos, nomes de arquivo ou
    mensagens controladas pelo usuário ou pela API.
29. Falha de conexão ou timeout é tratada sem crash não controlado.
30. A troca de avaliação atualiza a listagem correspondente.
31. Testes automatizados da interface são aprovados.
32. Testes de regressão do backend permanecem aprovados.
33. Ruff, mypy, I-001 e `git diff --check` permanecem aprovados.
34. O fluxo operacional funciona no Docker Compose.
35. Nenhum documento real ou artefato confidencial é versionado.

---

## 12. Estratégia de Testes

Os testes deverão cobrir, no mínimo:

Testes unitários e de componente deverão usar doubles ou mocks HTTP. Somente
a validação operacional no Docker Compose deverá utilizar a API real.

### Comunicação HTTP

- health aprovado;
- health indisponível;
- carregamento de perfis;
- carregamento de avaliações;
- criação de avaliação;
- upload multipart com campo `file`;
- propagação do UUID selecionado;
- chamada única de upload;
- listagem da avaliação selecionada;
- lista vazia;
- timeout;
- erro de conexão;
- resposta não JSON;
- status HTTP conhecido;
- status HTTP desconhecido;
- ausência de exibição do body bruto.

### Estados da interface

- nenhuma avaliação;
- seleção de avaliação;
- títulos duplicados;
- nenhum arquivo selecionado;
- upload explícito;
- upload concluído;
- documento duplicado;
- arquivo inválido;
- arquivo muito grande;
- avaliação inexistente;
- falha de listagem;
- listagem vazia;
- listagem com um documento;
- listagem com múltiplos documentos;
- troca de avaliação;
- atualização após upload;
- prevenção de upload duplicado em rerun;
- bloqueio de nova submissão durante upload;
- limpeza ou invalidação da seleção após sucesso;
- exibição exclusiva dos campos públicos;
- ausência de HTML inseguro para dados controlados.

### Segurança

- nenhum acesso direto ao banco;
- nenhum acesso ao storage;
- nenhum arquivo temporário criado;
- nenhum byte documental persistido em estado;
- nenhum campo interno exibido;
- nenhuma mensagem interna exibida;
- nenhum documento real utilizado;
- nenhuma chamada externa.

### Integração e operação

- Streamlit consumindo a FastAPI no Docker Compose;
- criação ou seleção de avaliação;
- upload de PDF sintético;
- persistência pelo backend;
- listagem do documento;
- health aprovado;
- processamento externo desabilitado;
- limpeza defensiva dos dados e arquivos sintéticos.

---

## 13. Riscos

### Upload duplicado por rerun

O Streamlit reexecuta o script após interações.

Mitigação: submissão explícita, bloqueio durante a operação, limpeza ou
invalidação da seleção após sucesso e teste que confirme uma única chamada
HTTP por ação.

### Vazamento de mensagens internas

A interface atual pode apresentar respostas HTTP de forma direta.

Mitigação: mapeamento de mensagens públicas, fallback genérico e testes
negativos para body bruto, traces, paths e detalhes internos.

### Seleção incorreta da avaliação

Títulos podem ser repetidos.

Mitigação: opções identificadas por título e UUID, mantendo o UUID como valor
real da seleção.

### Injeção na camada de apresentação

Títulos de avaliação e nomes de arquivo são dados controlados pelo usuário.

Mitigação: renderização como texto seguro, proibição de HTML inseguro e testes
negativos para conteúdo com marcação.

### Acoplamento ao backend interno

Uma implementação rápida poderia importar sessões, adapters ou serviços.

Mitigação: fronteira HTTP obrigatória e testes arquiteturais.

### Cópias documentais desnecessárias

A interface poderia usar bytes completos, arquivos temporários ou estado
persistente.

Mitigação: utilizar o fluxo do `UploadedFile`, não criar arquivos locais e não
persistir bytes em `session_state`.

### Confusão entre lista vazia e falha

Uma falha HTTP poderia ser apresentada como ausência de documentos.

Mitigação: estados distintos para sucesso vazio e erro de carregamento.

### API indisponível durante inicialização

O container Streamlit pode iniciar antes de a API estar pronta.

Mitigação: tratamento explícito de conexão, mensagem estável e possibilidade de
nova tentativa sem crash não controlado.

### Expansão prematura da interface

A feature pode crescer para preview, download, exclusão ou processamento.

Mitigação: manter essas capacidades explicitamente fora do escopo.

---

## 14. Dependências e Restrições

- Streamlit já configurado no projeto;
- `httpx` já configurado no projeto;
- `API_BASE_URL` já utilizado pela interface;
- FastAPI operacional;
- PostgreSQL operacional;
- endpoint de criação de avaliação existente;
- endpoint de listagem de avaliações existente;
- endpoint seguro de upload concluído;
- endpoint seguro de listagem concluído;
- migration `0002_add_documents (head)`;
- nenhum endpoint adicional necessário;
- nenhuma migration nova;
- nenhuma alteração de entidade ou modelo;
- nenhuma dependência externa;
- nenhum documento real em Git;
- MCP+ 001 v1.1 permanece aplicável;
- Decision Locks existentes permanecem válidos.

---

## 15. Condição para Início do Action Plan

O Action Plan somente poderá ser criado depois de:

- revisão deste Feature Intent;
- resolução de eventuais pendências;
- aprovação explícita do Human Lead Engineer;
- alteração do status para `Approved`;
- registro da data real de aprovação;
- commit documental específico;
- push do commit;
- sincronização da branch com o remoto.

Nenhum código de implementação da F01.7 poderá ser alterado antes da aprovação
e do commit deste Feature Intent e do Action Plan correspondente.

---

## 16. Aprovação

- [x] **Human Lead Engineer aprovou este Feature Intent**
- **Data da aprovação:** 2026-07-31
- **Observações:** Aprovado sem pendências bloqueantes.

---

## 17. Encerramento

- **Status final:** Done
- **Data do encerramento:** 2026-07-31
- **Checkpoint H1:** aprovado pelo Human Lead Engineer em 2026-07-31
- **Checkpoint H2:** aprovado pelo Human Lead Engineer em 2026-07-31
- **Commit da implementação:** `75a8ddbd9f7a9dac68efac166935bac2a736d3f9`
- **Commit documental:** registrado pelo commit de encerramento desta atualização.

### Evidências consolidadas

- 356 testes aprovados na suíte completa;
- testes específicos da interface e integração aprovados;
- Ruff aprovado;
- mypy aprovado em `src` e `ui`;
- verificação de escopo I-001 aprovada;
- `git diff --check` aprovado;
- PostgreSQL operacional;
- migration `0002_add_documents (head)`;
- health da FastAPI aprovado;
- health do Streamlit aprovado;
- integração Streamlit → FastAPI validada;
- criação, seleção, upload, listagem e duplicidade validados;
- smoke visual e operacional concluídos;
- somente os seis campos documentais públicos exibidos;
- nenhum documento real utilizado;
- nenhum PDF rastreado pelo Git;
- nenhum resíduo sintético no PostgreSQL ou storage privado;
- superfície de implementação limitada aos nove arquivos autorizados;
- arquivos protegidos preservados;
- processamento externo mantido desabilitado.

### Ocorrências tratadas durante a validação

O smoke visual identificou incompatibilidade de importação do entrypoint no
container Streamlit. O bootstrap da raiz do projeto foi corrigido em
`ui/app.py` e protegido por teste arquitetural.

O uso depreciado de `use_container_width` foi substituído por
`width="stretch"`.

Permanece somente o warning externo conhecido da integração
Starlette/TestClient com `httpx`. O warning não foi introduzido pela F01.7,
não causou falhas e está fora da superfície aprovada.

### Resultado

A intenção definida neste documento foi atendida sem expansão de escopo. A
interface depende exclusivamente da API HTTP local e não acessa diretamente
PostgreSQL, storage, serviços de aplicação ou infraestrutura.
