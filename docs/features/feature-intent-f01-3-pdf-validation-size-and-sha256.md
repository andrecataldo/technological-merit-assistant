# Feature Intent F01.3 — Validação de PDF, Limite de Tamanho e SHA-256

## 1. Identificação

- **Título da Feature:** F01.3 — Validação de PDF, Limite de Tamanho e SHA-256
- **Feature pai:** F01 — Ingestão Segura de Documentos
- **Autor — Human Lead Engineer:** André Cataldo
- **Data:** 2026-07-27
- **Status:** Approved
- **MCP+ aplicável:** MCP+ 001 v1.1
- **Dependências:**
  - F01.1 — Modelo de Documento e Migration;
  - F01.2 — Serviço Local de Armazenamento Seguro.

---

## 2. Contexto e Problema

A aplicação já possui:

- uma representação persistente para documentos;
- um serviço responsável pelo armazenamento local seguro.

Ainda não existe uma camada responsável por validar o conteúdo recebido antes
que ele seja armazenado e persistido.

Confiar somente no nome do arquivo, no MIME type declarado ou no tamanho
informado pelo cliente permitiria:

- envio de arquivos que não sejam PDFs;
- conteúdo malformado com extensão `.pdf`;
- arquivos vazios;
- arquivos maiores que o limite configurado;
- MIME type incompatível com o conteúdo;
- ausência de uma identificação criptográfica estável;
- consumo excessivo de memória ou disco;
- persistência de metadados incorretos.

---

## 3. Intenção — Outcome

Criar um serviço de validação documental capaz de:

- validar o nome original recebido como metadado;
- validar a extensão `.pdf`;
- validar o MIME type declarado;
- rejeitar arquivos vazios;
- aplicar o limite configurado de tamanho durante a leitura;
- calcular SHA-256 durante a mesma leitura;
- validar a assinatura inicial do PDF;
- validar estruturalmente o conteúdo com processamento local;
- retornar metadados confiáveis para a futura orquestração do upload;
- restaurar o fluxo de entrada para que possa ser armazenado posteriormente;
- não persistir nem armazenar definitivamente o documento.

---

## 4. Escopo

### 4.1 Dentro do escopo — IN

- [ ] Criar o contrato `PdfInspector`.
- [ ] Criar a implementação local `PyMuPdfInspector`.
- [ ] Criar o serviço `DocumentValidationService`.
- [ ] Criar o resultado imutável `ValidatedDocumentMetadata`.
- [ ] Receber `original_filename`, `declared_content_type` e `BinaryIO`.
- [ ] Validar que o nome original não esteja vazio.
- [ ] Rejeitar caracteres nulos no nome.
- [ ] Rejeitar componentes de diretório no nome original.
- [ ] Validar a extensão `.pdf` sem diferenciar maiúsculas de minúsculas.
- [ ] Validar o MIME type declarado como `application/pdf`.
- [ ] Rejeitar conteúdo vazio.
- [ ] Obter o limite a partir de `Settings.max_upload_size_mb`.
- [ ] Converter o limite configurado para bytes.
- [ ] Ler o fluxo em blocos de tamanho controlado.
- [ ] Interromper a leitura quando o limite for ultrapassado.
- [ ] Aceitar arquivo cujo tamanho seja exatamente igual ao limite.
- [ ] Calcular SHA-256 durante a leitura.
- [ ] Retornar SHA-256 hexadecimal em letras minúsculas.
- [ ] Validar a assinatura `%PDF-` no início do conteúdo.
- [ ] Validar a estrutura do PDF com PyMuPDF.
- [ ] Rejeitar PDF estruturalmente inválido.
- [ ] Rejeitar documento sem páginas.
- [ ] Restaurar o fluxo para a posição inicial após sucesso.
- [ ] Restaurar o fluxo após falha de validação.
- [ ] Rejeitar fluxo que não permita posicionamento.
- [ ] Utilizar somente processamento local.
- [ ] Criar testes exclusivamente com conteúdo sintético.

### 4.2 Fora do escopo — OUT

- [ ] Armazenar definitivamente o arquivo.
- [ ] Chamar `DocumentStorage.store()`.
- [ ] Criar ou atualizar `DocumentModel`.
- [ ] Persistir metadados no PostgreSQL.
- [ ] Verificar duplicidade no banco.
- [ ] Criar endpoint de upload.
- [ ] Criar endpoint de download.
- [ ] Criar endpoint de listagem.
- [ ] Criar interface Streamlit.
- [ ] Extrair texto.
- [ ] Extrair imagens.
- [ ] Executar OCR.
- [ ] Renderizar páginas.
- [ ] Criar registros de páginas.
- [ ] Gerar embeddings.
- [ ] Implementar RAG ou LLM.
- [ ] Enviar conteúdo para serviço externo.
- [ ] Implementar antivírus.
- [ ] Implementar Content Disarm and Reconstruction.
- [ ] Definir política completa para PDFs protegidos por senha.
- [ ] Confiar exclusivamente no MIME type declarado.
- [ ] Confiar exclusivamente na extensão do arquivo.

---

## 5. Contratos Propostos

### 5.1 ValidatedDocumentMetadata

Resultado imutável contendo:

- `original_filename: str`;
- `content_type: str`;
- `size_bytes: int`;
- `sha256: str`.

O resultado não deverá conter:

- caminho físico;
- `storage_key`;
- conteúdo binário;
- identificador de avaliação;
- identificador de documento;
- entidade ou modelo de banco.

### 5.2 PdfInspector

O contrato deverá expor uma operação equivalente a:

```python
class PdfInspector(Protocol):
    def validate(self, content: bytes) -> None: ...
```

A responsabilidade do inspector será exclusivamente confirmar que o conteúdo:

- pode ser aberto como PDF;
- possui estrutura reconhecida pelo parser local;
- contém pelo menos uma página.

O contrato recebe o conteúdo completo porque o PyMuPDF realiza a abertura de
streams a partir de uma área de memória, como `bytes`, `bytearray` ou
`BytesIO`.

A camada de serviço deverá ler a origem em blocos e interromper imediatamente
quando o limite for ultrapassado. Somente documentos dentro do limite serão
materializados integralmente para a validação estrutural.

A implementação deverá evitar manter cópias integrais simultâneas e
desnecessárias do mesmo documento.

### 5.3 DocumentValidationService

O serviço deverá expor uma operação equivalente a:

```python
def validate(
    self,
    original_filename: str,
    declared_content_type: str | None,
    source: BinaryIO,
) -> ValidatedDocumentMetadata:
    ...
```

O serviço deverá:

1. validar o nome original;
2. validar a extensão;
3. validar o MIME type declarado;
4. confirmar que o fluxo é posicionável;
5. ler o conteúdo em blocos;
6. rejeitar conteúdo vazio;
7. aplicar o limite durante a leitura;
8. calcular SHA-256;
9. validar a assinatura inicial;
10. delegar a validação estrutural ao `PdfInspector`;
11. restaurar o fluxo;
12. retornar os metadados validados.

---

## 6. Regras de Validação

### 6.1 Nome original

O nome deverá:

- ser uma string não vazia;
- não possuir somente espaços;
- não conter caractere nulo;
- não conter `/` ou `\`;
- não representar `.` ou `..`;
- terminar em `.pdf`, sem diferenciação entre maiúsculas e minúsculas.

O nome original será tratado somente como metadado e nunca como caminho físico.

### 6.2 MIME type

O MIME type aceito será:

```text
application/pdf
```

A comparação deverá:

- ignorar diferenças entre maiúsculas e minúsculas;
- ignorar espaços externos;
- desconsiderar parâmetros posteriores a `;`.

Exemplo aceito:

```text
application/pdf; charset=binary
```

Um MIME type ausente ou incompatível deverá ser rejeitado.

### 6.3 Tamanho

O limite será derivado de:

```text
Settings.max_upload_size_mb
```

A conversão deverá utilizar:

```text
max_size_bytes = max_upload_size_mb × 1024 × 1024
```

Regras:

- arquivo vazio é inválido;
- tamanho igual ao limite é aceito;
- tamanho superior ao limite é rejeitado;
- a validação não deverá depender apenas de `Content-Length`;
- a leitura deverá parar assim que o limite for ultrapassado.
- o conteúdo aceito poderá ser acumulado em memória para a inspeção estrutural;
- a materialização integral somente ocorrerá após a aplicação progressiva do
  limite;
- a implementação deverá evitar duplicações integrais desnecessárias do buffer.

### 6.4 SHA-256

O hash deverá:

- ser calculado durante a leitura;
- considerar exatamente os bytes recebidos;
- ser retornado como texto hexadecimal;
- possuir 64 caracteres;
- utilizar letras minúsculas;
- não depender do nome do arquivo ou de outros metadados.

### 6.5 Conteúdo PDF

O conteúdo deverá:

- começar com `%PDF-`;
- ser reconhecido pelo parser local;
- possuir pelo menos uma página;
- não exigir renderização para ser validado.

Um arquivo que apenas possua extensão `.pdf` ou MIME type correto não será
considerado válido sem a validação do conteúdo.

### 6.6 Fluxo de entrada

O fluxo deverá:

- oferecer leitura binária;
- permitir `tell()` e `seek()`;
- iniciar na posição zero;
- ser restaurado para a posição zero após sucesso;
- ser restaurado para a posição zero após erro de validação.

O serviço não deverá fechar o fluxo recebido.

---

## 7. Exceções Previstas

A implementação deverá possuir uma hierarquia equivalente a:

```text
DocumentValidationError
├── InvalidOriginalFilenameError
├── UnsupportedContentTypeError
├── EmptyDocumentError
├── DocumentTooLargeError
├── NonSeekableDocumentError
└── InvalidPdfError
```

As mensagens de erro:

- não deverão incluir conteúdo documental;
- não deverão incluir fragmentos binários;
- não deverão registrar o SHA-256 completo como dado de log;
- deverão permitir que a futura camada HTTP faça tradução adequada.

---

## 8. Casos de Sucesso

- PDF sintético válido é aceito.
- Extensão `.pdf` é aceita.
- Extensão `.PDF` é aceita.
- MIME type `application/pdf` é aceito.
- MIME type com parâmetro é normalizado e aceito.
- Arquivo exatamente no limite é aceito.
- Tamanho é calculado corretamente.
- SHA-256 corresponde exatamente ao conteúdo.
- SHA-256 é retornado em formato hexadecimal minúsculo.
- O PDF possui pelo menos uma página.
- O fluxo permanece aberto.
- O fluxo é restaurado à posição zero.
- Os metadados validados são retornados sem conteúdo binário.

---

## 9. Casos de Erro

- Nome vazio é rejeitado.
- Nome contendo somente espaços é rejeitado.
- Nome com `/` é rejeitado.
- Nome com `\` é rejeitado.
- Nome com caractere nulo é rejeitado.
- Nome sem extensão `.pdf` é rejeitado.
- MIME type ausente é rejeitado.
- MIME type incompatível é rejeitado.
- Conteúdo vazio é rejeitado.
- Conteúdo acima do limite é rejeitado.
- Leitura é interrompida após ultrapassar o limite.
- Conteúdo sem assinatura `%PDF-` é rejeitado.
- Conteúdo com assinatura, mas estruturalmente inválido, é rejeitado.
- PDF sem páginas é rejeitado.
- Fluxo não posicionável é rejeitado.
- Falha de leitura é propagada ou traduzida sem mascaramento indevido.
- O fluxo é restaurado após erro sempre que tecnicamente possível.

---

## 10. Critérios de Aceite

### 10.1 Funcionais

- [ ] `ValidatedDocumentMetadata` foi criado.
- [ ] `PdfInspector` foi criado.
- [ ] `PyMuPdfInspector` implementa o contrato.
- [ ] `DocumentValidationService` foi criado.
- [ ] Nome original é validado.
- [ ] Extensão `.pdf` é validada.
- [ ] MIME type é validado e normalizado.
- [ ] Arquivo vazio é rejeitado.
- [ ] Limite configurado é aplicado durante a leitura.
- [ ] Arquivo exatamente no limite é aceito.
- [ ] Arquivo acima do limite é rejeitado.
- [ ] SHA-256 é calculado durante a leitura.
- [ ] Assinatura `%PDF-` é validada.
- [ ] Estrutura PDF é validada localmente.
- [ ] PDF sem páginas é rejeitado.
- [ ] Metadados corretos são retornados.
- [ ] Fluxo permanece aberto.
- [ ] Fluxo é restaurado à posição zero.
- [ ] Nenhum arquivo é armazenado definitivamente.

### 10.2 Técnicos

- [ ] O limite vem de `Settings.max_upload_size_mb`.
- [ ] O processamento ocorre em blocos.
- [ ] A leitura para ao ultrapassar o limite.
- [ ] O inspector utiliza PyMuPDF já disponível no projeto.
- [ ] Nenhuma dependência nova é adicionada.
- [ ] Testes utilizam apenas conteúdo sintético.
- [ ] PDFs de teste são gerados em tempo de execução.
- [ ] Nenhum PDF real é incluído no repositório.
- [ ] Nenhum endpoint é criado ou alterado.
- [ ] Nenhuma migration é criada.
- [ ] Nenhum acesso ao PostgreSQL é realizado.
- [ ] Nenhum arquivo definitivo é criado em `data/private`.
- [ ] `pytest` é aprovado.
- [ ] `ruff check .` é aprovado.
- [ ] `mypy src` é aprovado.
- [ ] `verify_i001_scope.sh` é aprovado.
- [ ] Nenhum arquivo privado é incluído no Git.

---

## 11. Superfície Prevista de Mudança

### Arquivos previstos

- `src/merit_assistant/application/ports/pdf_inspector.py`;
- `src/merit_assistant/application/services/__init__.py`;
- `src/merit_assistant/application/services/document_validation.py`;
- `src/merit_assistant/infrastructure/pdf/__init__.py`;
- `src/merit_assistant/infrastructure/pdf/pymupdf_inspector.py`;
- `tests/test_document_validation.py`;
- `tests/test_pymupdf_inspector.py`.

### Arquivos que não devem ser alterados

- `src/merit_assistant/infrastructure/storage/`;
- modelos SQLAlchemy;
- migrations;
- endpoints FastAPI;
- interface Streamlit;
- perfis de avaliação;
- regras institucionais;
- `pyproject.toml`.

---

## 12. Riscos

- MIME type declarado incorretamente pelo cliente;
- arquivo malformado com assinatura válida;
- arquivo excessivamente grande;
- consumo de memória durante validação estrutural;
- comportamento inesperado do parser;
- fluxo não posicionável;
- arquivo protegido por senha;
- PDF válido, mas incompatível com uma futura extração;
- divergência entre tamanho recebido e informado externamente.

### Mitigações

- combinar extensão, MIME type, assinatura e parser;
- aplicar limite durante a leitura;
- interromper assim que o limite for excedido;
- ler a origem em blocos para aplicar o limite e calcular o SHA-256;
- interromper a leitura antes de acumular conteúdo acima do limite;
- realizar a validação estrutural em memória somente para documentos aceitos
  pelo limite configurado;
- evitar cópias integrais simultâneas do conteúdo;
- utilizar somente parser local;
- restaurar o fluxo após a validação;
- criar testes de fronteira e de conteúdo malformado;
- não confiar em metadados fornecidos pelo cliente como única evidência.

### Decisão sobre uso de memória

Para este incremento, a validação estrutural com PyMuPDF será realizada sobre o
conteúdo completo em memória.

A decisão é aceita porque:

- o tamanho é limitado antes da inspeção estrutural;
- a leitura é interrompida ao ultrapassar o limite;
- o processamento é exclusivamente local;
- nenhum conteúdo é enviado a serviços externos;
- a implementação evitará cópias integrais desnecessárias.

Caso o limite configurado ou o volume operacional tornem esse modelo
inadequado, será necessário um incremento específico para validação por arquivo
temporário privado ou outra estratégia de streaming.

---

## 13. Plano de Validação

Os testes deverão comprovar:

- criação dos metadados imutáveis;
- compatibilidade estrutural do inspector;
- geração de PDF sintético válido em memória;
- aceitação de PDF válido;
- rejeição de nome inválido;
- aceitação de `.pdf` e `.PDF`;
- rejeição de extensão incompatível;
- aceitação e normalização do MIME type;
- rejeição de MIME type ausente ou incompatível;
- rejeição de arquivo vazio;
- aceitação no limite exato;
- rejeição acima do limite;
- interrupção antecipada da leitura;
- tamanho calculado corretamente;
- SHA-256 correto;
- assinatura inicial válida;
- rejeição de assinatura ausente;
- rejeição de falso PDF;
- rejeição de PDF sem páginas;
- restauração do fluxo após sucesso;
- restauração do fluxo após falha;
- fluxo mantido aberto;
- ausência de armazenamento definitivo;
- ausência de chamadas de rede.

---

## 14. Handoff para IA

### Artefatos superiores

- MCP+ 001 v1.1;
- PRD-Lite v0.1;
- Feature Intent F01;
- Feature Intent F01.1 concluído;
- Feature Intent F01.2 concluído;
- Context Pack v0.1;
- Guidelines Técnicas v0.1;
- Arquitetura v0.1.

### Regras de execução

- implementar somente validação e caracterização do documento;
- não armazenar o arquivo definitivamente;
- não acessar `DocumentStorage`;
- não persistir no PostgreSQL;
- não criar endpoint ou interface;
- não extrair texto;
- não renderizar páginas;
- não executar OCR;
- não usar LLM;
- não adicionar dependências;
- não usar documentos reais nos testes;
- interromper em caso de conflito com artefato superior.

---

## Aprovação

- [x] **Human Lead Engineer aprovou esta Feature Intent**
- **Data da aprovação:** 2026-07-27
