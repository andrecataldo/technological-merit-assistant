# Action Plan F01.3 — Validação de PDF, Limite de Tamanho e SHA-256

## 1. Identificação

- **Projeto:** Assistente de Avaliação de Mérito Tecnológico
- **Feature:** F01.3 — Validação de PDF, Limite de Tamanho e SHA-256
- **Feature pai:** F01 — Ingestão Segura de Documentos
- **Feature Intent:** `feature-intent-f01-3-pdf-validation-size-and-sha256.md`
- **MCP+ aplicável:** MCP+ 001 v1.1
- **Dependências:**
  - F01.1 — Modelo de Documento e Migration;
  - F01.2 — Serviço Local de Armazenamento Seguro.
- **Branch:** `feature/f01-secure-document-ingestion`
- **Data:** 2026-07-27
- **Responsável humano:** André Cataldo
- **Status:** Approved

---

## 2. Verificação de Prontidão

- Feature Intent F01.3 aprovado.
- F01.1 concluído.
- F01.2 concluído.
- Escopo IN e OUT definidos.
- Contratos mínimos definidos.
- Regras de nome, MIME type, tamanho, SHA-256 e PDF definidas.
- Estratégia de uso de memória aprovada.
- PyMuPDF já disponível no projeto.
- Nenhuma dependência nova necessária.
- Nenhuma alteração de banco necessária.
- Nenhum endpoint necessário.
- Nenhum conflito identificado com o MCP+ 001 v1.1.
- Nenhuma Decision Lock precisa ser alterada.

---

## 3.1 Objetivo do Plano

Implementar a validação e a caracterização local de documentos PDF antes do
armazenamento definitivo e da persistência dos metadados.

O incremento deverá criar:

- resultado imutável `ValidatedDocumentMetadata`;
- hierarquia de exceções de validação;
- contrato `PdfInspector`;
- implementação `PyMuPdfInspector`;
- serviço `DocumentValidationService`;
- validação do nome original;
- validação e normalização do MIME type;
- leitura binária em blocos;
- aplicação progressiva do limite de tamanho;
- cálculo de SHA-256 durante a leitura;
- validação da assinatura `%PDF-`;
- validação estrutural local com PyMuPDF;
- restauração do fluxo de entrada;
- testes automatizados com PDFs sintéticos.

O incremento não incluirá:

- armazenamento definitivo;
- chamada ao `DocumentStorage`;
- persistência no PostgreSQL;
- verificação de duplicidade;
- endpoints;
- interface Streamlit;
- extração de texto ou imagens;
- OCR;
- renderização;
- antivírus;
- RAG ou LLM.

---

## 3.2 Estratégia Geral

A implementação será dividida em mudanças pequenas e verificáveis:

1. confirmar o baseline;
2. criar contratos, resultado e exceções;
3. implementar a inspeção estrutural com PyMuPDF;
4. implementar validação de nome, MIME type e fluxo;
5. implementar leitura, limite, SHA-256 e assinatura;
6. integrar a inspeção estrutural e consolidar os testes;
7. executar o Quality Gate;
8. atualizar os artefatos e registrar a implementação.

### Decisões técnicas do plano

- `PdfInspector` será um `Protocol` da camada de aplicação.
- `PyMuPdfInspector` será uma implementação de infraestrutura.
- `DocumentValidationService` receberá o inspector por injeção.
- O limite será recebido em bytes no construtor do serviço.
- Uma factory baseada em `Settings` converterá megabytes para bytes.
- O limite será calculado por:

```text
max_size_bytes = max_upload_size_mb × 1024 × 1024
```

- O fluxo deverá ser posicionável por `seek()` e `tell()`.
- A validação sempre partirá da posição zero.
- O fluxo não será fechado pelo serviço.
- O fluxo será restaurado para a posição zero após sucesso ou falha.
- A origem será lida em blocos.
- Cada leitura será limitada ao espaço restante mais um byte.
- A leitura será interrompida assim que o limite for ultrapassado.
- O SHA-256 será atualizado durante a mesma leitura.
- O conteúdo aceito será acumulado para inspeção estrutural em memória.
- Somente uma conversão final para `bytes` será realizada quando necessária.
- Nenhum conteúdo documental será incluído em logs ou mensagens de erro.
- O nome original será tratado somente como metadado.
- O MIME type retornado será normalizado para `application/pdf`.
- O nome retornado será o nome validado sem espaços externos.
- Nenhuma política específica para PDF protegido por senha será criada.
- O resultado do parser local governará os casos não cobertos explicitamente.

---

## 3.3 Etapas de Execução

### Etapa 1 — Confirmar o baseline

**Descrição**

Confirmar branch, working tree, artefatos de governança e integridade técnica da
base antes da implementação.

**Arquivos afetados**

Nenhum.

**Resultado**

- branch correta confirmada;
- working tree limpo e sincronizado;
- Feature Intent e Action Plan F01.3 presentes e aprovados;
- F01.2 confirmado como concluído;
- suíte de testes aprovada;
- Ruff aprovado;
- mypy aprovado;
- verificador I-001 aprovado;
- `git diff --check` aprovado;
- PyMuPDF disponível;
- PostgreSQL saudável;
- banco mantido em `0002_add_documents`;
- API e interface operacionais;
- endpoint `/health` aprovado.

**Verificação**

```bash
git branch --show-current
git status
git log --oneline --decorate -5

test -f \
  docs/features/feature-intent-f01-3-pdf-validation-size-and-sha256.md

test -f \
  docs/action-plans/action-plan-f01-2-secure-local-storage.md

test -f \
  docs/mcp/mcp-plus-001-v1.1-foundation-ingestion.md

pytest
ruff check .
mypy src
./scripts/verify_i001_scope.sh
git diff --check
```

**Status:** Concluída

---

### Etapa 2 — Criar contratos, resultado e exceções

**Descrição**

Criar os elementos da camada de aplicação que definem o resultado da validação,
o contrato de inspeção estrutural e os erros esperados.

**Arquivos previstos**

- `src/merit_assistant/application/ports/pdf_inspector.py`;
- `src/merit_assistant/application/services/__init__.py`;
- `src/merit_assistant/application/services/document_validation.py`;
- `tests/test_document_validation.py`.

**Contrato previsto**

```python
class PdfInspector(Protocol):
    def validate(self, content: bytes) -> None: ...
```

**Resultado previsto**

- contrato `PdfInspector` criado sem dependência de PyMuPDF;
- resultado imutável `ValidatedDocumentMetadata` criado;
- resultado limitado aos quatro campos aprovados;
- invariantes de tamanho e SHA-256 implementadas;
- hierarquia de exceções de validação criada;
- pacote de serviços configurado;
- 18 testes específicos aprovados;
- compilação aprovada;
- Ruff aprovado;
- mypy aprovado em 23 arquivos;
- `git diff --check` aprovado.

```python
@dataclass(frozen=True, slots=True)
class ValidatedDocumentMetadata:
    original_filename: str
    content_type: str
    size_bytes: int
    sha256: str
```

**Exceções previstas**

```text
DocumentValidationError
├── InvalidOriginalFilenameError
├── UnsupportedContentTypeError
├── EmptyDocumentError
├── DocumentTooLargeError
├── NonSeekableDocumentError
└── InvalidPdfError
```

**Regras estruturais**

- o resultado será imutável;
- `size_bytes` deverá ser maior que zero;
- `sha256` deverá possuir 64 caracteres hexadecimais minúsculos;
- o resultado não conterá caminho, chave física, conteúdo ou identificadores;
- o contrato não dependerá de PyMuPDF;
- nenhuma exceção incluirá bytes do documento.

**Verificação**

```bash
python -m compileall \
  src/merit_assistant/application/ports/pdf_inspector.py \
  src/merit_assistant/application/services/document_validation.py

ruff check \
  src/merit_assistant/application/ports/pdf_inspector.py \
  src/merit_assistant/application/services \
  tests/test_document_validation.py

mypy \
  src/merit_assistant/application/ports/pdf_inspector.py \
  src/merit_assistant/application/services/document_validation.py
```

**Status:** Concluída

---

### Etapa 3 — Implementar PyMuPdfInspector

**Descrição**

Criar a implementação local do contrato `PdfInspector` usando PyMuPDF.

**Arquivos previstos**

- `src/merit_assistant/infrastructure/pdf/__init__.py`;
- `src/merit_assistant/infrastructure/pdf/pymupdf_inspector.py`;
- `tests/test_pymupdf_inspector.py`.

**Comportamento previsto**

- receber o conteúdo completo como `bytes`;
- abrir o conteúdo explicitamente como PDF;
- utilizar somente processamento local;
- encerrar corretamente o documento aberto;
- rejeitar conteúdo que o parser não reconheça;
- rejeitar documento com zero páginas;
- traduzir erros esperados do parser para `InvalidPdfError`;
- não renderizar páginas;
- não extrair texto;
- não extrair imagens;
- não registrar conteúdo ou hash em logs.

**Operação prevista**

```python
class PyMuPdfInspector:
    def validate(self, content: bytes) -> None:
        ...
```

**PDF sintético de teste**

Os testes gerarão PDFs em memória durante a execução, utilizando o próprio
PyMuPDF. Nenhum arquivo `.pdf` será gravado no repositório.

**Casos mínimos**

- PDF sintético com uma página é aceito;
- conteúdo arbitrário é rejeitado;
- conteúdo que imita assinatura sem estrutura válida é rejeitado;
- documento sem páginas é rejeitado;
- implementação satisfaz o contrato `PdfInspector`.

**Verificação**

```bash
pytest tests/test_pymupdf_inspector.py -v

ruff check \
  src/merit_assistant/infrastructure/pdf \
  tests/test_pymupdf_inspector.py

mypy \
  src \
  tests/test_pymupdf_inspector.py
```

**Resultado**

- pacote de infraestrutura PDF criado;
- `PyMuPdfInspector` implementado;
- contrato `PdfInspector` atendido;
- validação estrutural realizada localmente com PyMuPDF;
- PDF sintético válido aceito;
- conteúdo arbitrário rejeitado;
- falsa assinatura PDF rejeitada;
- conteúdo reconhecido como não PDF rejeitado;
- PDF sem páginas rejeitado;
- nenhum documento real incluído;
- nenhuma gravação em disco realizada pelos testes;
- 6 testes específicos aprovados;
- 24 testes acumulados aprovados;
- Ruff aprovado;
- mypy aprovado;
- `git diff --check` aprovado.

**Status:** Concluída

---

### Etapa 4 — Implementar validação de nome, MIME type e fluxo

**Descrição**

Implementar as validações anteriores à leitura integral do conteúdo.

**Arquivo principal**

- `src/merit_assistant/application/services/document_validation.py`.

**Validação do nome**

O serviço deverá:

- rejeitar nome vazio;
- rejeitar nome contendo somente espaços;
- rejeitar caractere nulo;
- rejeitar `/`;
- rejeitar `\`;
- rejeitar `.` e `..`;
- rejeitar extensão diferente de `.pdf`;
- aceitar `.pdf` e `.PDF`;
- remover somente espaços externos;
- preservar o restante do nome como metadado.

**Validação do MIME type**

O serviço deverá:

- rejeitar valor ausente;
- remover espaços externos;
- desconsiderar parâmetros após `;`;
- normalizar para letras minúsculas;
- aceitar somente `application/pdf`;
- retornar `application/pdf` no resultado.

**Validação do fluxo**

O serviço deverá:

- confirmar disponibilidade de `seek()` e `tell()`;
- posicionar o fluxo no início;
- confirmar a posição zero;
- rejeitar fluxo não posicionável;
- não fechar o fluxo recebido;
- restaurar a posição zero em bloco de finalização.

**Casos mínimos**

- nome válido aceito;
- `.PDF` aceito;
- nome inválido rejeitado;
- caminhos disfarçados como nome rejeitados;
- MIME type normal aceito;
- MIME type com parâmetro aceito;
- MIME type ausente ou incompatível rejeitado;
- fluxo inicialmente fora da posição zero é reposicionado;
- fluxo não posicionável é rejeitado;
- fluxo permanece aberto.

**Verificação**

```bash
pytest tests/test_document_validation.py \
  -k "filename or content_type or mime or seekable or position" -v
```

**Resultado**

- `DocumentValidationService` criado com injeção de `PdfInspector`;
- limite positivo validado no construtor;
- nome original tratado somente como metadado;
- espaços externos removidos do nome;
- extensões `.pdf` e `.PDF` aceitas;
- nomes vazios, caminhos e caracteres nulos rejeitados;
- MIME type `application/pdf` validado;
- diferenças de caixa, espaços e parâmetros MIME normalizados;
- MIME type ausente ou incompatível rejeitado;
- fluxo posicionável validado;
- fluxo inicialmente deslocado reposicionado para zero;
- fluxo não posicionável rejeitado com erro específico;
- fluxo recebido mantido aberto;
- 41 testes específicos aprovados;
- 47 testes acumulados aprovados;
- compilação aprovada;
- Ruff aprovado;
- mypy aprovado em 26 arquivos;
- `git diff --check` aprovado.

**Status:** Concluída

---

### Etapa 5 — Implementar leitura, limite, SHA-256 e assinatura

**Descrição**

Implementar a leitura controlada do fluxo e a caracterização do conteúdo.

**Fluxo previsto**

1. calcular o limite em bytes;
2. criar acumulador de conteúdo;
3. criar calculador SHA-256;
4. calcular o espaço restante;
5. solicitar no máximo o espaço restante mais um byte;
6. interromper ao encontrar fim do fluxo;
7. rejeitar quando o total ultrapassar o limite;
8. atualizar tamanho, hash e acumulador;
9. rejeitar conteúdo vazio;
10. validar o prefixo `%PDF-`;
11. materializar o conteúdo aceito como `bytes`;
12. restaurar o fluxo para a posição zero.

**Leitura de fronteira**

A quantidade solicitada em cada leitura deverá ser equivalente a:

```text
min(CHUNK_SIZE, remaining_bytes + 1)
```

Isso garante que:

- o arquivo exatamente no limite seja aceito;
- um arquivo acima do limite seja detectado com apenas um byte adicional;
- o serviço não leia um bloco inteiro desnecessário após atingir o limite.

**SHA-256**

O hash deverá:

- ser calculado durante a leitura;
- considerar exatamente os bytes recebidos;
- ser retornado por `hexdigest()`;
- possuir 64 caracteres;
- usar letras minúsculas.

**Assinatura**

O conteúdo deverá começar exatamente com:

```text
%PDF-
```

Extensão e MIME type corretos não substituirão essa verificação.

**Casos mínimos**

- conteúdo vazio rejeitado;
- tamanho calculado corretamente;
- SHA-256 correto;
- leitura em blocos comprovada;
- arquivo abaixo do limite aceito;
- arquivo exatamente no limite aceito;
- arquivo um byte acima do limite rejeitado;
- leitura interrompida após o primeiro byte excedente;
- ausência da assinatura rejeitada;
- fluxo restaurado após sucesso;
- fluxo restaurado após erro;
- falha da origem propagada sem exposição de conteúdo.

**Verificação**

```bash
pytest tests/test_document_validation.py \
  -k "empty or size or limit or chunk or sha256 or signature or reset" -v
```

**Resultado**

- método público `validate()` implementado;
- origem lida em blocos de tamanho controlado;
- limite aplicado progressivamente durante a leitura;
- cada leitura limitada ao espaço restante mais um byte;
- arquivo exatamente no limite aceito;
- arquivo acima do limite rejeitado após o primeiro byte excedente;
- arquivo vazio rejeitado;
- SHA-256 calculado durante a mesma leitura;
- tamanho calculado a partir dos bytes efetivamente recebidos;
- assinatura `%PDF-` validada;
- conteúdo aceito materializado para inspeção estrutural;
- fluxo restaurado para a posição zero após sucesso;
- fluxo restaurado após erros de validação;
- fluxo recebido mantido aberto;
- falhas de leitura propagadas sem exposição de conteúdo;
- testes de fronteira, leitura e hash aprovados.

**Status:** Concluída

---

### Etapa 6 — Integrar inspeção estrutural e consolidar os testes

**Descrição**

Integrar o `PdfInspector` ao fluxo de validação e consolidar toda a cobertura do
Feature Intent.

**Ordem final da validação**

1. nome original;
2. MIME type;
3. capacidade de posicionamento;
4. leitura e limite;
5. conteúdo vazio;
6. assinatura inicial;
7. inspeção estrutural;
8. criação dos metadados;
9. restauração do fluxo.

**Regras de integração**

- o inspector será chamado somente após as validações preliminares;
- conteúdo acima do limite não chegará ao inspector;
- conteúdo sem assinatura não chegará ao inspector;
- o serviço não conhecerá PyMuPDF diretamente;
- o fluxo permanecerá aberto;
- nenhuma gravação definitiva será realizada;
- nenhuma chamada de rede será realizada.

**Casos de consolidação**

- PDF sintético válido retorna metadados corretos;
- inspector é chamado uma única vez;
- inspector recebe exatamente os bytes validados;
- inspector não é chamado para nome inválido;
- inspector não é chamado para MIME type inválido;
- inspector não é chamado para arquivo vazio;
- inspector não é chamado para arquivo acima do limite;
- inspector não é chamado para assinatura inválida;
- falha estrutural é traduzida para `InvalidPdfError`;
- fluxo é restaurado após falha estrutural;
- metadados não contêm conteúdo, caminho ou `storage_key`;
- nenhum arquivo é criado em `data/private`.

**Verificação**

```bash
pytest \
  tests/test_document_validation.py \
  tests/test_pymupdf_inspector.py \
  -v

ruff check \
  src/merit_assistant/application/ports/pdf_inspector.py \
  src/merit_assistant/application/services \
  src/merit_assistant/infrastructure/pdf \
  tests/test_document_validation.py \
  tests/test_pymupdf_inspector.py

mypy \
  src \
  tests/test_document_validation.py \
  tests/test_pymupdf_inspector.py

git diff --check
```

**Resultado**

- `PdfInspector` integrado ao `DocumentValidationService`;
- inspector recebido por injeção de dependência;
- factory `from_settings()` criada;
- `Settings.max_upload_size_mb` convertido corretamente para bytes;
- inspector chamado somente após validações preliminares;
- inspector chamado uma única vez com os bytes exatos recebidos;
- inspector não chamado para nome inválido;
- inspector não chamado para MIME type incompatível;
- inspector não chamado para documento vazio;
- inspector não chamado para documento acima do limite;
- inspector não chamado para assinatura inválida;
- falha estrutural traduzida por `InvalidPdfError`;
- fluxo restaurado após falha estrutural;
- integração real com `PyMuPdfInspector` aprovada;
- PDF sintético válido aceito pelo serviço completo;
- nenhum arquivo definitivo criado;
- nenhuma chamada de rede realizada;
- 67 testes acumulados aprovados;
- Ruff aprovado;
- mypy aprovado em 26 arquivos;
- `git diff --check` aprovado.

**Status:** Concluída

---

## 3.4 Checkpoint Humano Obrigatório H1

### H1 — Revisão da validação documental

**Momento**

Após as Etapas 2 a 6 e antes do Quality Gate completo.

**Itens para revisão**

- [x] `ValidatedDocumentMetadata` é imutável.
- [x] O resultado contém somente os quatro campos aprovados.
- [x] O contrato `PdfInspector` não depende de PyMuPDF.
- [x] `PyMuPdfInspector` satisfaz o contrato.
- [x] O serviço depende somente do contrato.
- [x] O nome original é tratado apenas como metadado.
- [x] Componentes de diretório são rejeitados.
- [x] A extensão `.pdf` é validada.
- [x] O MIME type é normalizado e validado.
- [x] O limite vem de `Settings.max_upload_size_mb`.
- [x] A conversão de megabytes para bytes está correta.
- [x] A leitura ocorre em blocos.
- [x] Cada leitura respeita o espaço restante mais um byte.
- [x] Arquivo exatamente no limite é aceito.
- [x] Arquivo acima do limite é rejeitado.
- [x] O SHA-256 é calculado durante a leitura.
- [x] A assinatura `%PDF-` é validada.
- [x] A estrutura é validada localmente com PyMuPDF.
- [x] PDF sem páginas é rejeitado.
- [x] O fluxo é restaurado para a posição zero.
- [x] O fluxo não é fechado.
- [x] Nenhum conteúdo documental aparece em logs ou erros.
- [x] Nenhum arquivo é armazenado definitivamente.
- [x] Nenhum endpoint, banco ou interface foi alterado.
- [x] Nenhuma dependência nova foi adicionada.
- [x] Somente conteúdo sintético foi utilizado nos testes.

**Evidências**

```bash
git diff -- \
  src/merit_assistant/application/ports/pdf_inspector.py \
  src/merit_assistant/application/services \
  src/merit_assistant/infrastructure/pdf

pytest \
  tests/test_document_validation.py \
  tests/test_pymupdf_inspector.py \
  -v
```

**Status:** Approved
**Aprovado por:** André Cataldo
**Data:** 2026-07-27

**Condição de saída**

A implementação estará autorizada a seguir para o Quality Gate completo.

---

## 3.5 Etapa 7 — Executar o Quality Gate

**Descrição**

Validar regressão, tipagem, estilo, escopo, operação e ausência de arquivos
privados.

**Verificação**

```bash
pytest
ruff check .
mypy src
./scripts/verify_i001_scope.sh
git diff --check
```

**Estado operacional**

```bash
alembic current
docker compose ps

curl -fsS http://localhost:8000/health
echo
```

**Ausência de arquivos privados**

```bash
git ls-files | grep -Ei \
  '\.(pdf|db|sqlite|sqlite3|log|env|dump|backup|tmp)$'
```

**Superfície da mudança**

```bash
git status --short
git diff --stat
git diff --name-only
```

**Arquivos de implementação esperados**

```text
src/merit_assistant/application/ports/pdf_inspector.py
src/merit_assistant/application/services/__init__.py
src/merit_assistant/application/services/document_validation.py
src/merit_assistant/infrastructure/pdf/__init__.py
src/merit_assistant/infrastructure/pdf/pymupdf_inspector.py
tests/test_document_validation.py
tests/test_pymupdf_inspector.py
```

**Arquivos de governança esperados**

```text
docs/features/feature-intent-f01-3-pdf-validation-size-and-sha256.md
docs/action-plans/action-plan-f01-3-pdf-validation-size-and-sha256.md
```

**Resultado**

- suíte completa de testes aprovada;
- Ruff aprovado;
- mypy aprovado;
- verificador de escopo I-001 aprovado;
- `git diff --check` aprovado;
- PostgreSQL operacional;
- banco mantido em `0002_add_documents`;
- API e interface operacionais;
- endpoint `/health` aprovado;
- processamento externo mantido desabilitado;
- nenhum PDF real ou arquivo privado rastreado;
- superfície da mudança correspondente ao Action Plan.

**Status:** Concluída

---

## 3.6 Checkpoint Humano Obrigatório H2

### H2 — Revisão final antes do commit

**Momento**

Após o Quality Gate e antes do encerramento formal.

**Itens para revisão**

- [x] Todos os testes foram aprovados.
- [x] Ruff foi aprovado.
- [x] mypy foi aprovado.
- [x] O verificador I-001 foi aprovado.
- [x] `git diff --check` foi aprovado.
- [x] Banco e aplicação permanecem operacionais.
- [x] Nenhum PDF real foi incluído no Git.
- [x] Nenhum arquivo temporário foi rastreado.
- [x] A superfície da mudança corresponde ao plano.
- [x] O armazenamento F01.2 não foi alterado.
- [x] Nenhum modelo ou migration foi alterado.
- [x] Nenhum endpoint foi alterado.
- [x] Nenhuma interface foi alterada.
- [x] Nenhuma chamada de rede foi introduzida.
- [x] Nenhuma expansão de escopo foi identificada.
- [x] O Feature Intent F01.3 permanece integralmente atendido.

**Evidências**

```bash
git status
git diff --stat
git diff

pytest
ruff check .
mypy src
./scripts/verify_i001_scope.sh
```

**Status:** Approved
**Aprovado por:** André Cataldo
**Data:** 2026-07-27

**Condição de saída**

A implementação estará autorizada para encerramento, commit e push.

---

## 3.7 Etapa 8 — Encerrar e registrar a implementação

**Descrição**

Atualizar os artefatos de governança e registrar definitivamente a
implementação.

**Ações previstas**

- alterar o Feature Intent F01.3 para `Done`;
- marcar os critérios comprovados;
- adicionar o registro de conclusão;
- alterar este Action Plan para `Done`;
- registrar os resultados das etapas;
- registrar H1 e H2;
- executar a validação final;
- realizar commit;
- enviar a branch ao remoto.

**Commit sugerido**

```bash
git add \
  docs/features/feature-intent-f01-3-pdf-validation-size-and-sha256.md \
  docs/action-plans/action-plan-f01-3-pdf-validation-size-and-sha256.md \
  src/merit_assistant/application/ports/pdf_inspector.py \
  src/merit_assistant/application/services/__init__.py \
  src/merit_assistant/application/services/document_validation.py \
  src/merit_assistant/infrastructure/pdf/__init__.py \
  src/merit_assistant/infrastructure/pdf/pymupdf_inspector.py \
  tests/test_document_validation.py \
  tests/test_pymupdf_inspector.py

git commit -m "feat: add PDF validation and SHA-256 inspection"

git push origin feature/f01-secure-document-ingestion
```

**Resultado**

- implementação registrada no commit `b0203fc`;
- commit enviado à branch remota;
- Feature Intent atualizado para `Done`;
- Action Plan atualizado para `Done`;
- evidências técnicas e humanas registradas;
- F01.3 concluído sem expansão de escopo.

**Status:** Concluída

---

## 4. Riscos e Mitigações

### R-01 — Arquivo acima do limite

**Mitigação**

Ler no máximo o espaço restante mais um byte e interromper imediatamente após
detectar o excesso.

### R-02 — Consumo excessivo de memória

**Mitigação**

Aplicar o limite progressivamente antes da inspeção estrutural e evitar cópias
integrais desnecessárias do conteúdo.

### R-03 — Confiança indevida em metadados do cliente

**Mitigação**

Combinar validação de nome, extensão, MIME type, assinatura e parser local.

### R-04 — PDF com assinatura, mas estrutura inválida

**Mitigação**

Delegar a validação estrutural ao `PyMuPdfInspector`.

### R-05 — Fluxo não posicionável

**Mitigação**

Validar `seek()` e `tell()` antes da leitura e rejeitar com erro específico.

### R-06 — Fluxo deixado em posição incorreta

**Mitigação**

Restaurar a posição zero em bloco de finalização, sem fechar o fluxo.

### R-07 — Exposição de conteúdo em erro ou log

**Mitigação**

Usar mensagens genéricas sem fragmentos binários, conteúdo ou hash completo.

### R-08 — Comportamento inesperado do parser

**Mitigação**

Traduzir erros esperados do PyMuPDF para `InvalidPdfError` e preservar erros
inesperados para diagnóstico controlado.

### R-09 — PDF protegido por senha

**Mitigação**

Não criar política específica neste incremento. O comportamento será governado
pelo parser e deverá ser registrado como risco residual.

### R-10 — Divergência entre validação e armazenamento futuro

**Mitigação**

Restaurar o fluxo para a posição zero e retornar metadados calculados
exclusivamente sobre os bytes recebidos.

---

## 5. Critério de Conclusão

O F01.3 estará concluído quando:

- `ValidatedDocumentMetadata` existir;
- `PdfInspector` existir;
- `PyMuPdfInspector` implementar o contrato;
- `DocumentValidationService` existir;
- nome e extensão forem validados;
- MIME type for normalizado e validado;
- arquivo vazio for rejeitado;
- limite configurado for aplicado durante a leitura;
- arquivo exatamente no limite for aceito;
- arquivo acima do limite for rejeitado;
- SHA-256 for calculado durante a leitura;
- assinatura `%PDF-` for validada;
- estrutura PDF for validada localmente;
- documento sem páginas for rejeitado;
- fluxo permanecer aberto;
- fluxo for restaurado para a posição zero;
- nenhum arquivo definitivo for armazenado;
- testes específicos forem aprovados;
- suíte completa for aprovada;
- Ruff, mypy e verificador I-001 forem aprovados;
- nenhum PDF real ou dado privado estiver no Git;
- H1 e H2 forem aprovados;
- Feature Intent e Action Plan estiverem em `Done`;
- commit e push tiverem sido realizados.

---

## 6. Stop Conditions

Interromper imediatamente se:

- for necessário armazenar o documento definitivamente;
- for necessário chamar `DocumentStorage`;
- for necessário acessar PostgreSQL;
- for necessário criar ou alterar endpoint;
- for necessário alterar a interface;
- for necessário modificar modelos ou migrations;
- for necessário adicionar dependência;
- for necessário usar documento real nos testes;
- for necessário enviar conteúdo para serviço externo;
- for necessário extrair texto, imagem ou executar OCR;
- o limite não puder ser aplicado durante a leitura;
- o fluxo não puder ser restaurado;
- o comportamento do PyMuPDF exigir mudança no Feature Intent;
- uma Decision Lock precisar ser alterada;
- o escopo F01.3 não puder ser preservado.

---

## 7. Aprovação

- [x] **Human Lead Engineer aprovou este Action Plan**
- **Data da aprovação:** 2026-07-27

## Registro de Conclusão

- **Data de conclusão:** 2026-07-27
- **Commit de implementação:**`b0203fc`
- **Resultado:** validação local de PDF, limite progressivo de tamanho,
  SHA-256, inspeção estrutural e restauração do fluxo implementados.
- **Testes específicos:** 67 aprovados.
- **Quality Gate:** pytest, Ruff, mypy, verificador I-001 e
  `git diff --check` aprovados.
- **Dados privados:** nenhum PDF real ou dado privado incluído no Git.
