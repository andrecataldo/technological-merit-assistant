# Feature Intent F02 — Extração Textual Nativa e Persistência Rastreável por Página

## 1. Identificação

- **Título da Feature:** F02 — Extração Textual Nativa e Persistência Rastreável por Página
- **Iteração:** I-001 — Fundação Técnica e Ingestão Documental Local
- **Autor — Human Lead Engineer:** André Cataldo
- **Data:** 2026-08-01
- **Status:** Approved
- **Branch:** `feature/f02-page-text-extraction`
- **Baseline:** `0152d5b80bfbe8389e22ba9b8f9ea7ad8386dc75`
- **MCP+ aplicável:** MCP+ 001 v1.1
- **Dependências funcionais:**
  - F01 — Ingestão Segura de Documentos;
  - armazenamento local privado;
  - validação documental;
  - persistência do documento;
  - isolamento por avaliação;
  - inspeção local de PDFs com PyMuPDF;
  - PostgreSQL e Alembic.

---

## 2. Contexto e Problema

A aplicação já permite:

- criar e listar avaliações;
- selecionar um perfil de avaliação;
- enviar um PDF por submissão explícita;
- validar extensão, MIME type, assinatura e tamanho;
- calcular SHA-256;
- detectar duplicidades dentro da avaliação;
- armazenar o arquivo em área privada;
- persistir os metadados documentais;
- listar os documentos associados a uma avaliação;
- operar a jornada por meio da FastAPI e da interface Streamlit.

Entretanto, o conteúdo textual dos documentos ainda não é extraído nem
persistido.

Como consequência, a aplicação ainda não consegue:

- representar individualmente as páginas de um documento;
- associar texto a uma página física específica;
- distinguir páginas com texto, vazias ou com pouca informação;
- preservar um hash determinístico do texto extraído;
- oferecer posteriormente visualização rastreável ou busca lexical;
- comprovar que uma informação veio de um documento e página específicos.

Uma implementação inadequada poderia:

- acessar o arquivo por caminho fornecido pelo usuário;
- contornar as fronteiras do armazenamento privado;
- extrair o PDF integral como um único bloco sem rastreabilidade;
- utilizar numeração de página iniciando em zero;
- duplicar registros durante reprocessamento;
- deixar registros parciais inconsistentes após falha;
- alterar ou sobrescrever o PDF original;
- registrar conteúdo documental integral nos logs;
- acionar OCR automaticamente;
- enviar conteúdo a bibliotecas, serviços ou APIs externas;
- introduzir prematuramente busca semântica, RAG ou LLM.

---

## 3. Intenção — Outcome

Permitir que um documento PDF já validado e armazenado seja processado
localmente, produzindo registros persistidos e rastreáveis para cada página
física do arquivo.

A feature deverá:

- processar um documento existente por vez;
- confirmar que o documento pertence à avaliação informada;
- resolver o arquivo exclusivamente por identificadores internos;
- utilizar somente a camada textual nativa do PDF;
- extrair o conteúdo página a página;
- numerar páginas fisicamente a partir de `1`;
- preservar a ordem original das páginas;
- persistir texto, estado, método e hash por página;
- identificar páginas vazias ou com texto insuficiente;
- representar falhas sem inventar ou substituir conteúdo;
- impedir registros lógicos duplicados;
- preservar o PDF original sem qualquer alteração;
- operar exclusivamente no ambiente local;
- manter processamento externo desabilitado;
- preparar a base para visualização e busca lexical posteriores.

O resultado esperado é um conjunto determinístico de registros de página
associados a um único documento e isolados dentro de sua avaliação.

---

## 4. Escopo

### 4.1 Dentro do escopo — IN

- [ ] Criar a representação persistente de uma página extraída.
- [ ] Criar migration Alembic para os registros de página.
- [ ] Associar cada página a um único documento.
- [ ] Preservar a associação indireta com a avaliação do documento.
- [ ] Impedir associação cruzada entre documentos e avaliações.
- [ ] Processar somente documentos previamente persistidos.
- [ ] Processar um documento por operação.
- [ ] Resolver o arquivo por `storage_key` interno.
- [ ] Rejeitar paths fornecidos externamente.
- [ ] Abrir o PDF exclusivamente no ambiente local.
- [ ] Utilizar PyMuPDF para leitura da camada textual nativa.
- [ ] Não utilizar OCR.
- [ ] Extrair cada página separadamente.
- [ ] Preservar a ordem física das páginas.
- [ ] Numerar páginas a partir de `1`.
- [ ] Manter números de página positivos e contíguos.
- [ ] Persistir o texto extraído de cada página.
- [ ] Persistir o método de extração.
- [ ] Persistir um estado observável de extração.
- [ ] Persistir a quantidade de caracteres extraídos.
- [ ] Persistir hash SHA-256 determinístico do texto da página.
- [ ] Representar página com texto utilizável.
- [ ] Representar página sem texto.
- [ ] Representar página com texto abaixo do limite mínimo.
- [ ] Representar falha de extração sem fabricar conteúdo.
- [ ] Registrar estado geral da extração do documento.
- [ ] Diferenciar conclusão integral de conclusão com avisos.
- [ ] Evitar registros parciais silenciosos.
- [ ] Preservar consistência entre documento e páginas.
- [ ] Definir comportamento idempotente para nova execução.
- [ ] Impedir duplicidade lógica por documento e número de página.
- [ ] Não alterar o arquivo PDF original.
- [ ] Não criar uma segunda cópia permanente do PDF.
- [ ] Não persistir bytes do documento na tabela de páginas.
- [ ] Não registrar texto integral nos logs.
- [ ] Não registrar CPF, e-mail ou telefone extraídos nos logs.
- [ ] Registrar somente metadados operacionais não sensíveis.
- [ ] Preservar o isolamento entre avaliações.
- [ ] Preservar o processamento externo desabilitado.
- [ ] Criar testes unitários do extrator.
- [ ] Criar testes do serviço de aplicação.
- [ ] Criar testes de persistência.
- [ ] Criar testes de integração com PostgreSQL.
- [ ] Utilizar somente PDFs sintéticos nos testes.
- [ ] Cobrir PDFs com uma página.
- [ ] Cobrir PDFs com múltiplas páginas.
- [ ] Cobrir página vazia.
- [ ] Cobrir página com pouco texto.
- [ ] Cobrir tentativa de extração de documento inexistente.
- [ ] Cobrir tentativa de associação cruzada.
- [ ] Cobrir reexecução sem duplicidade.
- [ ] Cobrir falha de leitura do arquivo.
- [ ] Preservar todos os Quality Gates existentes.

### 4.2 Fora do escopo — OUT

- [ ] OCR.
- [ ] Extração de texto de imagens.
- [ ] Extração especializada de tabelas.
- [ ] Reconstrução de layout.
- [ ] Reconstrução de colunas.
- [ ] Interpretação de gráficos.
- [ ] Extração de imagens.
- [ ] Classificação do tipo documental.
- [ ] Correção ortográfica do texto extraído.
- [ ] Resumo ou reescrita do conteúdo.
- [ ] Tradução do conteúdo.
- [ ] Identificação automática de entidades.
- [ ] Matriz de evidências.
- [ ] Regras determinísticas da seleção.
- [ ] Análise de mérito.
- [ ] Embeddings.
- [ ] Banco vetorial.
- [ ] Busca semântica.
- [ ] Reranking.
- [ ] RAG.
- [ ] LLM local.
- [ ] LLM externo.
- [ ] SDK de provedor de IA.
- [ ] Processamento externo.
- [ ] Data Egress Gateway.
- [ ] Busca lexical.
- [ ] Endpoint público para busca.
- [ ] Interface Streamlit para visualização de páginas.
- [ ] Interface Streamlit para reprocessamento.
- [ ] Download ou exclusão do documento.
- [ ] Edição ou substituição do PDF original.
- [ ] Processamento simultâneo em lote.
- [ ] Filas, workers ou processamento distribuído.
- [ ] Autenticação, autorização ou multiusuário.
- [ ] Armazenamento em nuvem.
- [ ] Uso de documentos reais em testes.
- [ ] Nova dependência de runtime sem aprovação.

---

## 5. Jornada Funcional

### 5.1 Entrada

A operação recebe internamente:

- `evaluation_id`;
- `document_id`.

A aplicação deverá confirmar:

1. que a avaliação existe;
2. que o documento existe;
3. que o documento pertence à avaliação;
4. que o documento possui referência interna válida de armazenamento;
5. que o arquivo privado está disponível;
6. que o processamento externo permanece desabilitado.

Nenhum caminho de arquivo poderá ser recebido do usuário ou de contrato
público.

### 5.2 Leitura local

1. A aplicação obtém a referência interna do documento.
2. A infraestrutura resolve o arquivo dentro da raiz privada aprovada.
3. O caminho resolvido deve permanecer contido na raiz privada.
4. O arquivo é aberto localmente e somente para leitura.
5. O PDF original não é modificado.
6. Nenhuma cópia permanente adicional é criada.

### 5.3 Extração

1. O documento é percorrido na ordem física original.
2. A primeira página recebe o número `1`.
3. Cada página é extraída separadamente.
4. O método registrado deve indicar extração textual nativa.
5. O texto extraído deve permanecer associado à página correspondente.
6. O sistema calcula a quantidade de caracteres.
7. O sistema calcula o SHA-256 do texto persistido.
8. Página sem texto recebe estado explícito.
9. Página com pouco texto recebe estado explícito.
10. Falha de uma página não pode gerar texto inventado.

### 5.4 Persistência

Para cada página, deverão ser persistidos ao menos:

- identificador interno;
- identificador do documento;
- número físico da página;
- texto extraído;
- método de extração;
- estado da extração;
- quantidade de caracteres;
- hash SHA-256 do texto;
- data de criação ou processamento.

O Action Plan definirá nomes, tipos, constraints e índices definitivos.

### 5.5 Resultado

A operação deverá retornar um resultado interno estável contendo:

- documento processado;
- quantidade total de páginas;
- quantidade de páginas com texto;
- quantidade de páginas vazias;
- quantidade de páginas com pouco texto;
- quantidade de páginas com falha;
- estado final do processamento.

Esta feature não exige endpoint público nem renderização na interface.

---

## 6. Regras Funcionais

### RF-01 — Documento previamente persistido

Somente documentos registrados pela ingestão segura poderão ser extraídos.

### RF-02 — Pertencimento à avaliação

O documento deverá pertencer à avaliação informada. A operação não poderá
acessar documento de outra avaliação.

### RF-03 — Numeração física

A numeração persistida deverá iniciar em `1`, acompanhar a ordem física do PDF
e permanecer contígua.

### RF-04 — Uma linha lógica por página

Um documento não poderá possuir mais de um registro ativo para o mesmo número
de página.

### RF-05 — Extração nativa

O único método autorizado é a extração da camada textual nativa por PyMuPDF.

### RF-06 — Ausência de texto

Ausência de texto deverá produzir estado explícito e texto vazio. Não deverá
acionar OCR nem gerar conteúdo substituto.

### RF-07 — Texto insuficiente

Texto abaixo do limite definido deverá ser preservado e marcado como
insuficiente. Ele não deverá ser descartado ou complementado artificialmente.

### RF-08 — Hash por página

O hash deverá ser calculado sobre a representação textual efetivamente
persistida, seguindo regra determinística definida no Action Plan.

### RF-09 — Idempotência

Repetir a operação para o mesmo documento não poderá criar registros lógicos
duplicados.

### RF-10 — PDF imutável

O documento original deverá permanecer inalterado.

### RF-11 — Falha explícita

Falhas deverão ser representadas por tipos internos estáveis e mensagens
sanitizadas, sem expor paths ou conteúdo.

### RF-12 — Sem processamento externo

Nenhum conteúdo, metadado extraído ou hash poderá ser enviado a serviço
externo.

---

## 7. Estados Esperados

O Action Plan deverá definir o conjunto definitivo de estados, preservando ao
menos os seguintes significados:

### Estado por página

- texto extraído e utilizável;
- página vazia;
- texto insuficiente;
- falha de extração.

### Estado por documento

- não processado;
- processamento iniciado;
- processamento concluído;
- processamento concluído com avisos;
- processamento falhou.

Não deverá existir estado que implique OCR automático ou processamento
externo.

---

## 8. Consistência e Idempotência

A implementação deverá garantir que:

- cada página pertence a um único documento;
- cada par documento + número de página é único;
- registros de outra avaliação não são alterados;
- reexecução não multiplica páginas;
- uma falha não deixa estado de sucesso incorreto;
- uma falha de persistência não produz conjunto silenciosamente incompleto;
- o estado final do documento é compatível com os estados de suas páginas;
- o PDF original permanece disponível e inalterado;
- rollback e compensação sejam definidos para falhas conhecidas.

A estratégia definitiva de substituição, atualização ou preservação de
resultados anteriores será definida no Action Plan.

---

## 9. Segurança e Privacidade

- O arquivo deverá ser resolvido somente dentro da raiz privada configurada.
- Nenhum path fornecido pelo usuário será aceito.
- Nenhum path físico será incluído em resposta pública.
- Nenhum `storage_key` será incluído em mensagem pública.
- Nenhum texto integral será registrado em logs.
- Nenhum fragmento textual será enviado a serviço externo.
- Nenhum PDF real será incluído em fixtures.
- Nenhum texto extraído real será versionado.
- O processamento deverá ocorrer com
  `EXTERNAL_PROCESSING_ENABLED=false`.
- O verificador I-001 continuará bloqueando artefatos proibidos.
- O conteúdo persistido será tratado como dado privado.

---

## 10. Arquitetura e Fronteiras

A feature deverá preservar o monólito modular:

```text
Application Service
    |
    +--> Document Persistence Port
    |
    +--> Document Storage Port
    |
    +--> Page Extraction Port
    |
    +--> Page Persistence Port
              |
              +--> PostgreSQL / SQLAlchemy

Page Extraction Adapter
    |
    +--> PyMuPDF local
```

Restrições:

- domínio e aplicação não importam SQLAlchemy;
- aplicação não resolve paths diretamente;
- aplicação não depende diretamente de PyMuPDF;
- infraestrutura implementa acesso ao PDF e ao PostgreSQL;
- a interface Streamlit não participa desta feature;
- nenhum endpoint existente pode acessar o banco de forma direta;
- nenhuma camada pode enviar conteúdo para serviço externo;
- o Action Plan deverá definir a superfície exata de arquivos.

---

## 11. Tratamento de Erros

Deverão existir erros internos estáveis para, no mínimo:

- avaliação inexistente;
- documento inexistente;
- documento não pertencente à avaliação;
- referência de armazenamento inválida;
- arquivo privado ausente;
- arquivo fora da raiz privada;
- falha ao abrir o PDF;
- falha ao ler uma página;
- falha de persistência;
- conflito de idempotência;
- estado de extração inconsistente.

Mensagens públicas ou operacionais não poderão revelar:

- path absoluto;
- path relativo interno;
- `storage_key`;
- SQL;
- stack trace;
- conteúdo textual;
- dados pessoais encontrados no documento.

---

## 12. Observabilidade

Logs poderão conter somente metadados operacionais necessários, como:

- identificadores internos;
- número da página;
- estado da operação;
- quantidade de caracteres;
- duração;
- tipo de erro sanitizado.

Logs não poderão conter:

- texto integral;
- trechos do documento;
- CPF;
- e-mail;
- telefone;
- path físico;
- `storage_key`;
- body bruto de exceção externa.

A observabilidade não poderá se tornar mecanismo de armazenamento do conteúdo.

---

## 13. Critérios de Aceitação

1. Um PDF sintético de uma página gera exatamente um registro de página.
2. Um PDF sintético de múltiplas páginas gera um registro por página.
3. A numeração começa em `1`.
4. A numeração acompanha a ordem física do PDF.
5. Cada página permanece associada ao documento correto.
6. Documento de outra avaliação não pode ser processado pelo contexto errado.
7. O texto é extraído somente pela camada textual nativa.
8. Página vazia recebe estado explícito.
9. Página com pouco texto preserva o texto e recebe estado explícito.
10. O método de extração é persistido.
11. A quantidade de caracteres é persistida.
12. O SHA-256 do texto persistido é determinístico.
13. Documento e número da página formam uma associação logicamente única.
14. Reexecutar a operação não cria páginas duplicadas.
15. O PDF original permanece inalterado.
16. Falha de extração não produz texto inventado.
17. Falha de persistência não deixa sucesso incorreto.
18. Nenhum texto integral aparece nos logs.
19. Nenhum path ou `storage_key` aparece em mensagem pública.
20. Nenhum conteúdo é enviado para serviços externos.
21. Somente PDFs e textos sintéticos são utilizados nos testes.
22. PostgreSQL e migration permanecem operacionais.
23. Todos os testes existentes continuam aprovados.
24. Novos testes unitários e integrados são aprovados.
25. Ruff é aprovado.
26. mypy em `src` e `ui` é aprovado.
27. verificação I-001 é aprovada.
28. `git diff --check` é aprovado.
29. CI/quality é aprovado.
30. Nenhum item fora do escopo é introduzido.

---

## 14. Estratégia de Testes Esperada

### Testes unitários

- extração de uma página;
- extração de múltiplas páginas;
- numeração iniciando em `1`;
- preservação da ordem;
- página vazia;
- página com pouco texto;
- cálculo de hash;
- falha de leitura;
- resultado agregado.

### Testes de serviço

- avaliação inexistente;
- documento inexistente;
- associação cruzada;
- documento válido;
- idempotência;
- falha do storage;
- falha do extrator;
- falha da persistência;
- resultado com avisos;
- resultado com falha.

### Testes de persistência

- criação de páginas;
- unicidade documento + página;
- ordenação determinística;
- isolamento entre documentos;
- isolamento entre avaliações;
- rollback;
- reexecução.

### Testes de integração

- PostgreSQL real;
- migration no `head`;
- storage privado temporário;
- PDF sintético;
- extração completa;
- persistência de todas as páginas;
- ausência de resíduos após limpeza;
- ausência de documentos rastreados no Git.

---

## 15. Dependências

- F01 concluída e integrada à `main`;
- tabela `documents`;
- persistência documental;
- armazenamento local privado;
- PyMuPDF já disponível;
- PostgreSQL;
- SQLAlchemy;
- Alembic;
- configuração local;
- CI com PostgreSQL;
- processamento externo desabilitado.

Nenhuma nova dependência de runtime está autorizada neste Feature Intent.

---

## 16. Riscos

### R-01 — PDFs sem camada textual

O PDF poderá conter páginas vazias para o extrator nativo. A feature deverá
registrar o estado e não acionar OCR.

### R-02 — Texto em ordem inadequada

PyMuPDF poderá retornar texto em ordem diferente da apresentação visual. A
feature persistirá a extração nativa sem reconstrução de layout.

### R-03 — Registros parciais

Uma falha entre páginas poderá deixar persistência incompleta. O Action Plan
deverá definir transação, estados e compensação.

### R-04 — Duplicidade no reprocessamento

Reexecuções poderão criar páginas duplicadas. A solução deverá combinar
constraint e comportamento idempotente.

### R-05 — Vazamento por logs

Exceções de bibliotecas poderão conter detalhes internos. O tratamento deverá
sanitizar mensagens antes do registro ou exposição.

### R-06 — Expansão oportunista

Resultados ruins poderão incentivar OCR, tabelas ou RAG. Esses itens continuam
fora do escopo e exigem novo processo de governança.

---

## 17. Stop Rules

A execução deverá parar e retornar à aprovação humana quando:

- OCR se tornar necessário;
- reconstrução de layout ou tabelas se tornar necessária;
- uma dependência nova de runtime for necessária;
- o PDF precisar ser enviado a serviço externo;
- o modelo precisar armazenar imagens ou bytes integrais;
- a persistência precisar abandonar PostgreSQL;
- documentos ou textos reais forem adicionados ao Git;
- conteúdo documental aparecer em logs;
- uma Decision Lock precisar ser alterada;
- busca lexical, RAG, LLM ou matriz de evidências se tornarem necessários;
- a superfície precisar ultrapassar o Action Plan aprovado;
- não for possível garantir idempotência ou consistência;
- houver contradição entre este Feature Intent e o MCP+ 001.

Nenhuma Stop Rule poderá ser contornada por implementação oportunista.

---

## 18. Checkpoints Humanos

### Aprovação do Feature Intent

Obrigatória antes de:

- alterar o status para `Approved`;
- criar o commit documental do Feature Intent;
- elaborar o Action Plan;
- alterar migrations, modelos ou código.

### Checkpoint H1

Deverá ocorrer após:

- modelo e migration;
- portas e contratos;
- extrator local;
- serviço principal;
- testes unitários e de persistência;
- antes da integração operacional completa.

### Checkpoint H2

Deverá ocorrer após:

- integração com PostgreSQL;
- migration validada;
- extração de PDF sintético;
- idempotência validada;
- limpeza de resíduos;
- suíte completa;
- Quality Gates;
- CI aprovado;
- antes do commit da implementação.

---

## 19. Definition of Ready

O Feature Intent estará pronto para aprovação quando:

- o outcome estiver claro;
- o escopo IN e OUT estiver explícito;
- OCR, RAG e LLM permanecerem bloqueados;
- os critérios de aceitação forem observáveis;
- a estratégia de idempotência puder ser detalhada no Action Plan;
- os riscos e Stop Rules estiverem registrados;
- a baseline e a branch estiverem corretas;
- não houver alteração de código;
- o Human Lead Engineer aprovar explicitamente.

Status atual: **Draft**.

---

## 20. Registro de Aprovação

- **Decisão:** Approved
- **Responsável:** André Cataldo — Human Lead Engineer
- **Data:** 2026-08-01
- **Observações:** Feature Intent aprovado para elaboração do Action Plan. A
  aprovação não autoriza alteração de migration, modelo, serviço, infraestrutura
  ou código de aplicação.

Nenhuma implementação está autorizada antes da aprovação e do commit
documental do Action Plan.
