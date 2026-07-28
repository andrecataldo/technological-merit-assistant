# Feature Intent F01.4 — Orquestração Segura do Upload e Persistência

## 1. Identificação

- **Título da Feature:** F01.4 — Orquestração Segura do Upload e Persistência
- **Feature pai:** F01 — Ingestão Segura de Documentos
- **Autor — Human Lead Engineer:** André Cataldo
- **Data:** 2026-07-28
- **Status:** Approved
- **MCP+ aplicável:** MCP+ 001 v1.1
- **Dependências:**
  - F01.1 — Modelo de Documento e Migration;
  - F01.2 — Serviço Local de Armazenamento Seguro;
  - F01.3 — Validação de PDF, Limite de Tamanho e SHA-256.

---

## 2. Contexto e Problema

A aplicação já possui componentes independentes para:

- representar um documento no domínio;
- persistir documentos na tabela `documents`;
- validar o conteúdo recebido;
- calcular tamanho e SHA-256;
- armazenar o arquivo em diretório privado;
- excluir um arquivo armazenado.

Ainda não existe um caso de uso responsável por coordenar essas capacidades em
uma operação única de ingestão documental.

Sem essa coordenação, uma implementação futura poderia:

- armazenar um arquivo sem criar o registro correspondente;
- criar um registro sem que o arquivo exista;
- aceitar documento duplicado na mesma avaliação;
- deixar arquivo órfão após falha do PostgreSQL;
- persistir metadados diferentes dos bytes armazenados;
- usar identificadores diferentes entre banco e armazenamento;
- tentar persistir documento para uma avaliação inexistente;
- expor detalhes de SQLAlchemy à camada de aplicação;
- fechar ou deixar o fluxo de entrada em posição inesperada.

---

## 3. Intenção — Outcome

Criar um caso de uso de aplicação capaz de:

- confirmar que a avaliação de destino existe;
- validar o PDF usando `DocumentValidationService`;
- verificar duplicidade pelo SHA-256 dentro da avaliação;
- gerar o identificador do documento antes do armazenamento;
- armazenar o arquivo com `DocumentStorage`;
- verificar que os bytes efetivamente consumidos pelo armazenamento possuem o
  mesmo tamanho e SHA-256 produzidos pela validação;
- criar a entidade de domínio `Document`;
- persistir seus metadados no PostgreSQL;
- confirmar a transação;
- compensar o armazenamento caso a persistência falhe;
- restaurar o fluxo para a posição inicial;
- retornar a entidade `Document` criada;
- preservar separação entre aplicação, armazenamento e SQLAlchemy.

---

## 4. Escopo

### 4.1 Dentro do escopo — IN

- [ ] Criar o contrato `DocumentPersistence`.
- [ ] Criar a implementação `SqlAlchemyDocumentPersistence`.
- [ ] Criar o serviço `DocumentUploadService`.
- [ ] Receber:
  - `evaluation_id`;
  - `original_filename`;
  - `declared_content_type`;
  - `BinaryIO`.
- [ ] Confirmar a existência da avaliação antes do armazenamento.
- [ ] Executar `DocumentValidationService.validate()`.
- [ ] Utilizar exclusivamente os metadados retornados pela validação.
- [ ] Rejeitar nome validado com mais de 255 caracteres.
- [ ] Verificar duplicidade por `(evaluation_id, sha256)`.
- [ ] Rejeitar documento duplicado antes do armazenamento quando detectável.
- [ ] Gerar `document_id` na camada de aplicação.
- [ ] Gerar `created_at` em UTC.
- [ ] Usar o mesmo `document_id` no domínio, armazenamento e banco.
- [ ] Armazenar por meio do contrato `DocumentStorage`.
- [ ] Utilizar um leitor verificador durante o armazenamento.
- [ ] Calcular tamanho e SHA-256 dos bytes efetivamente lidos pelo storage.
- [ ] Comparar os valores efetivamente armazenados com os metadados validados.
- [ ] Rejeitar e compensar qualquer divergência de conteúdo.
- [ ] Receber do armazenamento a `storage_key` canônica.
- [ ] Criar a entidade imutável `Document`.
- [ ] Persistir os metadados por meio de `DocumentPersistence`.
- [ ] Confirmar explicitamente a transação.
- [ ] Executar rollback em caso de falha de persistência.
- [ ] Excluir o arquivo armazenado quando a persistência não for confirmada.
- [ ] Tratar corrida de duplicidade detectada pelo banco.
- [ ] Restaurar o fluxo para a posição zero após o armazenamento.
- [ ] Manter o fluxo recebido aberto.
- [ ] Retornar a entidade `Document` após sucesso.
- [ ] Criar testes unitários com fakes.
- [ ] Criar testes de integração com PostgreSQL e armazenamento temporário.
- [ ] Usar apenas PDFs sintéticos nos testes.

### 4.2 Fora do escopo — OUT

- [ ] Criar endpoint FastAPI de upload.
- [ ] Receber `UploadFile` diretamente.
- [ ] Criar schema HTTP.
- [ ] Traduzir exceções para códigos HTTP.
- [ ] Criar interface Streamlit.
- [ ] Criar endpoint de download.
- [ ] Criar listagem de documentos.
- [ ] Criar exclusão de documento pelo usuário.
- [ ] Extrair texto.
- [ ] Extrair imagens.
- [ ] Renderizar páginas.
- [ ] Executar OCR.
- [ ] Criar registros de páginas.
- [ ] Criar embeddings.
- [ ] Implementar RAG ou LLM.
- [ ] Implementar antivírus.
- [ ] Enviar conteúdo a serviço externo.
- [ ] Alterar a tabela `documents`.
- [ ] Criar migration.
- [ ] Alterar `DocumentStorage`.
- [ ] Alterar `DocumentValidationService`.
- [ ] Implementar deduplicação global entre avaliações.
- [ ] Persistir o conteúdo binário no PostgreSQL.
- [ ] Implementar filas ou processamento assíncrono.
- [ ] Implementar recuperação automática posterior de órfãos.
- [ ] Criar uma Unit of Work genérica para toda a aplicação.
- [ ] Manter uma segunda cópia integral do documento em memória.
- [ ] Reabrir o arquivo armazenado apenas para recalcular o hash.

---

## 5. Invariantes Existentes

A implementação deverá preservar:

- `Document.id` como UUID;
- `Document.evaluation_id` como UUID;
- `size_bytes` maior que zero;
- SHA-256 com 64 caracteres;
- `storage_key` relativa;
- ausência de segmento `..` na `storage_key`;
- foreign key de `documents.evaluation_id` para `evaluations.id`;
- `ON DELETE CASCADE`;
- unicidade de `(evaluation_id, sha256)`;
- unicidade global de `storage_key`;
- `original_filename` limitado a 255 caracteres no modelo persistente;
- `content_type` limitado a 100 caracteres;
- conteúdo armazenado somente no diretório privado;
- nenhum documento real no Git;
- processamento exclusivamente local nesta iteração.

---

## 6. Contratos Propostos

### 6.1 DocumentPersistence

A camada de aplicação não deverá importar `Session`, `select`, `IntegrityError`
ou `DocumentModel`.

O contrato deverá ser equivalente a:

```python
class DocumentPersistence(Protocol):
    def evaluation_exists(self, evaluation_id: UUID) -> bool: ...

    def exists_by_evaluation_and_sha256(
        self,
        evaluation_id: UUID,
        sha256: str,
    ) -> bool: ...

    def add(self, document: Document) -> None: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...
```

Responsabilidades:

- consultar a existência da avaliação;
- consultar duplicidade conhecida;
- mapear `Document` para `DocumentModel`;
- adicionar o modelo à transação;
- confirmar a transação;
- desfazer a transação;
- traduzir erros conhecidos do banco para exceções do port.

O port deverá definir uma hierarquia equivalente a:

```text
DocumentPersistenceError
├── DuplicateDocumentPersistenceError
└── EvaluationReferencePersistenceError
```

A infraestrutura não deverá importar exceções definidas no serviço de upload.
O serviço traduzirá erros do port para as exceções públicas da orquestração.

O contrato será específico para este caso de uso. Não deverá se transformar em
uma abstração genérica prematura para toda a aplicação.

### 6.2 SqlAlchemyDocumentPersistence

A implementação concreta deverá:

- receber uma `Session` por injeção;
- não criar nem fechar a sessão;
- consultar `EvaluationModel`;
- consultar `DocumentModel`;
- persistir todos os campos da entidade `Document`;
- não gerar outro UUID;
- não recalcular SHA-256;
- não alterar `storage_key`;
- não ler o conteúdo documental;
- traduzir a violação de `(evaluation_id, sha256)` para
  `DuplicateDocumentPersistenceError`;
- traduzir a violação da foreign key da avaliação para
  `EvaluationReferencePersistenceError`;
- traduzir outras falhas para `DocumentPersistenceError`;
- permitir rollback explícito pelo serviço.

### 6.3 DocumentUploadService

O serviço deverá expor uma operação equivalente a:

```python
def upload(
    self,
    evaluation_id: UUID,
    original_filename: str,
    declared_content_type: str | None,
    source: BinaryIO,
) -> Document:
    ...
```

Dependências previstas:

```python
class DocumentUploadService:
    def __init__(
        self,
        validator: DocumentValidationService,
        storage: DocumentStorage,
        persistence: DocumentPersistence,
        id_factory: Callable[[], UUID] = uuid4,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        ...
```

`id_factory` e `clock` deverão ser substituíveis nos testes.

---

## 7. Fluxo Nominal

A operação deverá seguir esta ordem:

1. confirmar que a avaliação existe;
2. validar o documento recebido;
3. obter `original_filename`, `content_type`, `size_bytes` e `sha256`;
4. validar o limite persistente do nome original;
5. consultar duplicidade na mesma avaliação;
6. gerar `document_id`;
7. gerar `created_at` em UTC;
8. confirmar que o fluxo está na posição zero;
9. envolver o fluxo em um leitor verificador;
10. armazenar o arquivo com:
    - `evaluation_id`;
    - `document_id`;
    - leitor verificador;
11. receber a `storage_key`;
12. comparar o tamanho e o SHA-256 dos bytes consumidos pelo storage com os
    metadados validados;
13. restaurar o fluxo para a posição zero;
14. criar a entidade `Document`;
15. adicionar a entidade à persistência;
16. confirmar a transação;
17. retornar a entidade criada.

A validação deverá ocorrer uma única vez.

O SHA-256 validado não será substituído. Um segundo cálculo será realizado
somente durante a leitura executada pelo armazenamento, para comprovar que os
bytes armazenados correspondem aos bytes anteriormente validados.

Essa verificação não deverá criar outra cópia integral do conteúdo nem exigir
uma segunda leitura do arquivo armazenado.

---

## 8. Regras de Existência e Duplicidade

### 8.1 Avaliação inexistente

Quando `evaluation_id` não identificar uma avaliação existente:

- a operação será rejeitada;
- o validador não será chamado;
- o armazenamento não será chamado;
- nenhum registro será criado;
- nenhuma transação será confirmada.

### 8.2 Duplicidade conhecida

Um documento será considerado duplicado quando existir, na mesma avaliação, um
registro com o mesmo SHA-256.

Quando a duplicidade for detectada antes do armazenamento:

- nenhum arquivo será criado;
- nenhuma entidade será persistida;
- nenhuma transação será confirmada.

O mesmo SHA-256 poderá existir em avaliações diferentes.

### 8.3 Corrida de concorrência

A consulta prévia não substitui a restrição do PostgreSQL.

Caso duas operações concorrentes ultrapassem a verificação inicial:

- a restrição `uq_documents_evaluation_sha256` continuará sendo a autoridade;
- a falha deverá ser traduzida para `DuplicateDocumentError`;
- a transação deverá ser desfeita;
- o arquivo criado pela operação rejeitada deverá ser excluído.

---

## 9. Consistência e Compensação

O sistema de arquivos e o PostgreSQL não participam de uma única transação
atômica. Portanto, a operação usará compensação explícita.

### 9.1 Ordem de efeitos

A ordem aprovada será:

1. validação;
2. verificação de duplicidade;
3. armazenamento;
4. persistência;
5. commit.

### 9.2 Verificação dos bytes armazenados

O serviço deverá fornecer ao storage um leitor que:

- delegue a leitura ao fluxo original;
- conte os bytes efetivamente consumidos;
- calcule SHA-256 durante essas leituras;
- não feche o fluxo original;
- não mantenha uma segunda cópia integral do conteúdo.

Após `DocumentStorage.store()` retornar, o serviço deverá comparar:

- quantidade de bytes efetivamente lidos;
- SHA-256 dos bytes efetivamente lidos;
- `size_bytes` e `sha256` retornados pelo F01.3.

Qualquer divergência deverá:

1. impedir a criação da entidade;
2. impedir o commit;
3. iniciar a compensação;
4. gerar `StoredContentMismatchError`.

### 9.3 Falha antes do armazenamento

Quando a falha ocorrer antes de `DocumentStorage.store()`:

- nenhum arquivo precisará ser removido;
- nenhum registro deverá permanecer pendente;
- nenhuma compensação física será necessária.

### 9.4 Falha durante o armazenamento

Quando `DocumentStorage.store()` falhar:

- nenhum registro deverá ser adicionado;
- nenhuma transação deverá ser confirmada;
- o erro de armazenamento será propagado;
- a limpeza interna continuará sendo responsabilidade do storage.

### 9.5 Falha após o armazenamento e antes do commit

Quando qualquer falha ocorrer após a criação do arquivo:

1. executar rollback;
2. excluir o arquivo usando a `storage_key`;
3. restaurar o fluxo;
4. propagar o erro original, quando a compensação for concluída.

### 9.6 Falha de compensação

O rollback e a exclusão deverão ser tentados independentemente. A falha de
uma ação não deverá impedir a tentativa da outra.

Será considerada falha de compensação quando:

- `rollback()` lançar exceção;
- `delete()` lançar exceção;
- `delete()` retornar `False` para um arquivo que acabou de ser armazenado.

Se qualquer ação de compensação falhar:

- a operação nunca deverá ser reportada como sucesso;
- deverá ser levantado `DocumentCompensationError`;
- a falha original deverá permanecer encadeada;
- os resultados das duas tentativas deverão ser preservados para diagnóstico;
- nenhuma informação documental deverá aparecer na mensagem;
- a situação deverá ser tratada como possível inconsistência operacional.

### 9.7 Commit confirmado

Após `commit()` bem-sucedido:

- o arquivo não deverá ser removido;
- a entidade criada será retornada;
- nenhuma nova operação de banco será necessária;
- o serviço não deverá fechar a sessão.

---

## 10. Fluxo de Entrada

O fluxo recebido:

- deverá ser binário;
- deverá ser posicionável, conforme F01.3;
- será restaurado pelo validador após a validação;
- será consumido pelo armazenamento;
- deverá ser restaurado novamente antes do commit;
- deverá permanecer aberto;
- deverá ficar na posição zero após sucesso;
- deverá ficar na posição zero após falha sempre que tecnicamente possível.

O serviço não deverá manter uma segunda cópia integral do documento.

---

## 11. Entidade Criada

A entidade retornada deverá conter:

```text
id
evaluation_id
original_filename
storage_key
content_type
size_bytes
sha256
created_at
```

Regras:

- `id` será gerado uma única vez;
- `evaluation_id` será exatamente o recebido;
- metadados virão do resultado da validação;
- `storage_key` virá do armazenamento;
- `created_at` deverá possuir timezone UTC;
- a mesma entidade será usada como base para a persistência;
- nenhuma instância de `DocumentModel` será retornada pela aplicação.

---

## 12. Exceções Previstas

As exceções específicas da orquestração deverão seguir uma hierarquia
equivalente a:

```text
DocumentUploadError
├── EvaluationNotFoundError
├── DuplicateDocumentError
├── OriginalFilenameTooLongError
├── StoredContentMismatchError
├── DocumentUploadPersistenceError
└── DocumentCompensationError
```

Erros já existentes poderão ser propagados:

```text
DocumentValidationError
DocumentStorageError
DocumentPersistenceError
```

Regras:

- validação inválida não será convertida em erro de persistência;
- erro de armazenamento não será convertido em erro de validação;
- `DuplicateDocumentPersistenceError` será traduzido para
  `DuplicateDocumentError`;
- `EvaluationReferencePersistenceError` será traduzido para
  `EvaluationNotFoundError`;
- outros erros do port serão traduzidos para
  `DocumentUploadPersistenceError`;
- divergência entre conteúdo validado e armazenado gerará
  `StoredContentMismatchError`;
- mensagens não conterão bytes, fragmentos do PDF ou SHA-256 completo;
- nenhuma exceção dependerá de FastAPI.

---

## 13. Casos de Sucesso

- avaliação existente recebe PDF sintético válido;
- validador é chamado uma única vez;
- metadados validados são utilizados sem alteração;
- fluxo é entregue ao storage na posição zero;
- um único UUID é usado em toda a operação;
- `storage_key` retornada pelo storage é persistida;
- tamanho e SHA-256 efetivamente lidos pelo storage correspondem aos valores
  validados;
- entidade é adicionada antes do commit;
- commit é chamado uma única vez;
- entidade `Document` correta é retornada;
- fluxo permanece aberto e na posição zero;
- mesmo SHA-256 é permitido em avaliações diferentes;
- nenhuma compensação é executada após sucesso.

---

## 14. Casos de Erro

- avaliação inexistente é rejeitada antes da validação;
- nome com mais de 255 caracteres é rejeitado antes do armazenamento;
- erro de validação impede armazenamento e persistência;
- duplicidade conhecida impede armazenamento;
- erro de armazenamento impede persistência;
- divergência entre conteúdo validado e armazenado provoca compensação;
- leitura parcial pelo storage provoca compensação;
- falha ao adicionar o documento provoca rollback e exclusão;
- falha no commit provoca rollback e exclusão;
- corrida de duplicidade provoca rollback e exclusão;
- falha de foreign key após verificação provoca rollback e exclusão;
- arquivo armazenado é removido quando o banco não confirma a operação;
- falha na exclusão gera `DocumentCompensationError`;
- falha no rollback gera `DocumentCompensationError`;
- fluxo é restaurado após falha;
- fluxo nunca é fechado pelo serviço;
- nenhuma operação retorna sucesso parcial.

---

## 15. Critérios de Aceite

### 15.1 Funcionais

- [ ] `DocumentPersistence` foi criado.
- [ ] `SqlAlchemyDocumentPersistence` implementa o contrato.
- [ ] `DocumentUploadService` foi criado.
- [ ] Avaliação inexistente é rejeitada.
- [ ] `DocumentValidationService` é utilizado.
- [ ] Nome com mais de 255 caracteres é rejeitado.
- [ ] Duplicidade na mesma avaliação é rejeitada.
- [ ] Mesmo SHA-256 em avaliações diferentes é permitido.
- [ ] UUID é gerado antes do armazenamento.
- [ ] `created_at` é gerado em UTC.
- [ ] Arquivo é armazenado com o UUID aprovado.
- [ ] Bytes consumidos pelo storage são verificados.
- [ ] Tamanho armazenado corresponde ao tamanho validado.
- [ ] SHA-256 armazenado corresponde ao SHA-256 validado.
- [ ] Entidade `Document` é criada com os campos corretos.
- [ ] Entidade é persistida no PostgreSQL.
- [ ] Transação é confirmada explicitamente.
- [ ] Entidade de domínio é retornada.
- [ ] Fluxo permanece aberto.
- [ ] Fluxo termina na posição zero.

### 15.2 Consistência

- [ ] Erro de validação não cria arquivo.
- [ ] Duplicidade conhecida não cria arquivo.
- [ ] Erro de armazenamento não cria registro.
- [ ] Divergência de conteúdo não cria registro.
- [ ] Divergência de conteúdo remove o arquivo criado.
- [ ] Erro de persistência executa rollback.
- [ ] Erro de persistência remove o arquivo armazenado.
- [ ] Corrida de duplicidade remove o arquivo rejeitado.
- [ ] Falha de compensação gera erro específico.
- [ ] Nenhum sucesso parcial é retornado.

### 15.3 Técnicos

- [ ] Aplicação não importa SQLAlchemy.
- [ ] Persistência não lê conteúdo binário.
- [ ] Storage não acessa banco.
- [ ] Validador não acessa banco ou storage.
- [ ] Nenhuma migration é criada.
- [ ] `DocumentModel` não é alterado.
- [ ] `DocumentStorage` não é alterado.
- [ ] `DocumentValidationService` não é alterado.
- [ ] Nenhuma dependência nova é adicionada.
- [ ] Nenhum endpoint é criado ou alterado.
- [ ] Nenhuma interface é criada ou alterada.
- [ ] Testes unitários usam fakes determinísticos.
- [ ] Testes de integração usam PostgreSQL.
- [ ] Armazenamento de integração usa diretório temporário.
- [ ] PDFs são gerados sinteticamente.
- [ ] Nenhum PDF real é incluído no Git.
- [ ] `pytest` é aprovado.
- [ ] `ruff check .` é aprovado.
- [ ] `mypy src` é aprovado.
- [ ] `verify_i001_scope.sh` é aprovado.
- [ ] `git diff --check` é aprovado.

---

## 16. Superfície Prevista de Mudança

### Arquivos novos previstos

- `src/merit_assistant/application/ports/document_persistence.py`;
- `src/merit_assistant/application/services/document_upload.py`;
- `src/merit_assistant/infrastructure/db/document_persistence.py`;
- `tests/test_document_upload_service.py`;
- `tests/test_sqlalchemy_document_persistence.py`.

### Arquivos existentes que poderão ser alterados

- `src/merit_assistant/application/services/__init__.py`;
- `src/merit_assistant/infrastructure/db/__init__.py`.

### Arquivos que não devem ser alterados

- `src/merit_assistant/domain/entities.py`;
- `src/merit_assistant/infrastructure/db/models.py`;
- `src/merit_assistant/application/ports/document_storage.py`;
- `src/merit_assistant/infrastructure/storage/`;
- `src/merit_assistant/application/services/document_validation.py`;
- `src/merit_assistant/infrastructure/pdf/`;
- migrations Alembic;
- endpoints FastAPI;
- interface Streamlit;
- `pyproject.toml`.

---

## 17. Riscos e Mitigações

### R-01 — Arquivo órfão após falha do banco

**Mitigação**

Executar rollback e exclusão compensatória sempre que o arquivo tiver sido
criado, mas o commit não tiver sido confirmado.

### R-02 — Registro sem arquivo

**Mitigação**

Executar armazenamento antes da adição e do commit no PostgreSQL.

### R-03 — Corrida de duplicidade

**Mitigação**

Combinar consulta preventiva com a restrição única do PostgreSQL e compensar o
arquivo da operação rejeitada.

### R-04 — Avaliação removida durante o upload

**Mitigação**

Conservar a foreign key como autoridade final. Em caso de falha, executar
rollback e compensação física.

### R-05 — UUID inconsistente

**Mitigação**

Gerar o identificador uma única vez na aplicação e fornecê-lo ao storage, ao
domínio e à persistência.

### R-06 — Metadados divergentes

**Mitigação**

Persistir somente os valores retornados pelo `DocumentValidationService`.

### R-07 — Compensação incompleta

**Mitigação**

Gerar erro específico, preservar o encadeamento da falha original e nunca
retornar sucesso.

### R-08 — Sessão fechada indevidamente

**Mitigação**

A implementação receberá a sessão por injeção e não será responsável por
fechá-la.

### R-09 — Fluxo deixado no final

**Mitigação**

Restaurar o fluxo imediatamente após o armazenamento e antes do commit.

### R-10 — Nome maior que a coluna

**Mitigação**

Rejeitar o nome validado com mais de 255 caracteres antes da criação do arquivo.

---

## 18. Plano de Validação

Os testes unitários deverão comprovar:

- ordem das chamadas;
- avaliação inexistente;
- erro de validação;
- duplicidade conhecida;
- geração determinística de UUID;
- geração determinística de data;
- uso dos metadados validados;
- uso da `storage_key` retornada;
- verificação dos bytes efetivamente consumidos pelo storage;
- detecção de tamanho divergente;
- detecção de SHA-256 divergente;
- detecção de leitura parcial;
- criação correta da entidade;
- commit após armazenamento;
- rollback em falha;
- exclusão compensatória;
- erro específico de compensação;
- restauração e não fechamento do fluxo;
- ausência de chamadas indevidas.

Os testes de persistência deverão comprovar:

- consulta de avaliação existente e inexistente;
- consulta por avaliação e SHA-256;
- mapeamento completo para `DocumentModel`;
- persistência real dos campos;
- duplicidade na mesma avaliação;
- aceitação do mesmo SHA-256 em avaliações diferentes;
- tradução de violações conhecidas;
- rollback sem fechamento da sessão.

O teste integrado deverá comprovar:

- PDF sintético validado;
- armazenamento em diretório temporário;
- registro criado no PostgreSQL;
- arquivo físico existente;
- conteúdo armazenado idêntico ao recebido;
- entidade retornada correspondente ao banco;
- limpeza controlada ao final do teste;
- compensação quando o commit falhar;
- compensação quando os bytes armazenados divergirem dos bytes validados;
- tentativa independente de rollback e exclusão;
- `delete()` retornando `False` tratado como falha de compensação.

---

## 19. Handoff para IA

### Artefatos superiores

- MCP+ 001 v1.1;
- PRD-Lite v0.1;
- Feature Intent F01;
- Feature Intent F01.1 concluído;
- Feature Intent F01.2 concluído;
- Feature Intent F01.3 concluído;
- Context Pack v0.1;
- Guidelines Técnicas v0.1;
- Arquitetura v0.1.

### Regras de execução

- implementar somente o caso de uso de upload e sua persistência;
- preservar os contratos F01.2 e F01.3;
- não alterar modelo ou migration;
- não criar endpoint;
- não criar interface;
- não extrair conteúdo;
- não executar OCR;
- não usar LLM;
- não adicionar dependência;
- não usar documento real;
- não enviar dados para serviço externo;
- interromper em caso de conflito com artefato superior;
- interromper se a compensação não puder ser testada.

---

## Aprovação

- [x] **Human Lead Engineer aprovou esta Feature Intent**
- **Data da aprovação:** 2026-07-28
