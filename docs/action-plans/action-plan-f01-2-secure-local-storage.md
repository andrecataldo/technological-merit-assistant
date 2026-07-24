# Action Plan F01.2 — Serviço Local de Armazenamento Seguro

## 1. Identificação

- **Projeto:** Assistente de Avaliação de Mérito Tecnológico
- **Feature:** F01.2 — Serviço Local de Armazenamento Seguro
- **Feature pai:** F01 — Ingestão Segura de Documentos
- **Feature Intent:** `feature-intent-f01-2-secure-local-storage.md`
- **MCP+ aplicável:** MCP+ 001 v1.1
- **Dependência:** F01.1 — Modelo de Documento e Migration
- **Branch:** `feature/f01-secure-document-ingestion`
- **Data:** 2026-07-23
- **Responsável humano:** André Cataldo
- **Status:** Done

---

## 2. Verificação de Prontidão

- Feature Intent F01.2 aprovado.
- F01.1 concluído.
- Escopo IN e OUT definidos.
- Contrato mínimo definido.
- Regras de segurança definidas.
- Critérios funcionais e técnicos definidos.
- Nenhuma dependência nova necessária.
- Nenhuma alteração de banco necessária.
- Nenhum conflito identificado com o MCP+ 001 v1.1.
- Nenhuma Decision Lock precisa ser alterada.

---

## 3.1 Objetivo do Plano

Implementar um serviço local de armazenamento responsável por gravar, abrir e
excluir arquivos documentais dentro do diretório privado configurado.

O incremento deverá criar:

- contrato `DocumentStorage`;
- exceções específicas de armazenamento;
- implementação `LocalDocumentStorage`;
- geração segura de `storage_key`;
- confinamento das operações à raiz privada;
- escrita binária em blocos;
- publicação atômica sem sobrescrita;
- permissões restritivas;
- leitura binária;
- exclusão idempotente;
- testes automatizados de segurança.

O incremento não incluirá:

- validação de PDF;
- limite máximo de tamanho;
- cálculo de SHA-256;
- persistência no PostgreSQL;
- endpoints;
- interface Streamlit;
- extração de texto.

---

## 3.2 Estratégia Geral

A implementação será dividida em mudanças pequenas e verificáveis:

1. confirmar o baseline;
2. criar o contrato de armazenamento;
3. implementar geração de chave e confinamento de caminhos;
4. implementar gravação atômica;
5. implementar leitura e exclusão;
6. consolidar os testes de segurança;
7. executar o Quality Gate;
8. atualizar os artefatos e registrar a implementação.

### Decisões técnicas do plano

- `LocalDocumentStorage` receberá a raiz por injeção explícita.
- A criação para uso real deverá usar `Settings.private_data_dir`.
- Os testes utilizarão `tmp_path`.
- O conteúdo de entrada será representado por `BinaryIO`.
- O conteúdo será lido em blocos, sem carregamento integral obrigatório.
- A chave será gerada internamente com `PurePosixPath`.
- A chave terá o formato:

```text
evaluations/{evaluation_id}/documents/{document_id}.pdf
```

- A escrita será feita em arquivo temporário no diretório final.
- O arquivo temporário será submetido a `flush()` e `fsync()`.
- A publicação usará operação atômica que não substitua destino existente.
- `os.replace()` não será usado, porque permitiria sobrescrita.
- Diretórios receberão permissão `0700`.
- Arquivos receberão permissão `0600`.
- Nenhum nome original será recebido ou usado pelo serviço.
- Nenhuma propriedade de PDF será validada nesta feature.

---

## 3.3 Etapas de Execução

### Etapa 1 — Confirmar o baseline

**Descrição**

Confirmar branch, working tree, artefatos de governança e integridade da base.

**Arquivos afetados**

Nenhum.

**Resultado esperado**

Execução iniciada em uma branch limpa e com todos os controles atuais
aprovados.

**Verificação**

```bash
git branch --show-current
git status

test -f docs/features/feature-intent-f01-2-secure-local-storage.md
test -f docs/action-plans/action-plan-f01-1-document-model-and-migration.md
test -f docs/mcp/mcp-plus-001-v1.1-foundation-ingestion.md

pytest
ruff check .
mypy src
./scripts/verify_i001_scope.sh
```

**Resultado**

- branch correta confirmada;
- working tree limpo;
- artefatos de governança presentes;
- suíte de testes aprovada;
- Ruff aprovado;
- mypy aprovado;
- verificador I-001 aprovado;
- PostgreSQL operacional;
- banco mantido em `0002_add_documents`;
- API operacional;
- endpoint `/health` aprovado.

**Status:** Concluída

---

### Etapa 2 — Criar o contrato DocumentStorage

**Descrição**

Criar o port de aplicação que define as operações disponíveis para
armazenamento documental.

**Arquivo previsto**

- `src/merit_assistant/application/ports/document_storage.py`.

**Contrato previsto**

```python
class DocumentStorage(Protocol):
    def store(
        self,
        evaluation_id: UUID,
        document_id: UUID,
        source: BinaryIO,
    ) -> str: ...

    def open_binary(self, storage_key: str) -> BinaryIO: ...

    def delete(self, storage_key: str) -> bool: ...
```

**Exceções previstas**

- `DocumentStorageError`;
- `UnsafeStoragePathError`;
- `DocumentAlreadyExistsError`.

Erros de arquivo ausente durante leitura poderão permanecer como
`FileNotFoundError`.

**Resultado esperado**

A camada de aplicação possui um contrato sem dependência de sistema de arquivos,
FastAPI, SQLAlchemy ou Streamlit.

**Verificação**

```bash
python -m compileall \
  src/merit_assistant/application/ports/document_storage.py

ruff check \
  src/merit_assistant/application/ports/document_storage.py

mypy \
  src/merit_assistant/application/ports/document_storage.py
```

**Resultado**

- contrato `DocumentStorage` criado;
- operações `store`, `open_binary` e `delete` definidas;
- exceção-base `DocumentStorageError` criada;
- exceção `UnsafeStoragePathError` criada;
- exceção `DocumentAlreadyExistsError` criada;
- contrato sem dependência de infraestrutura concreta;
- compilação, Ruff e mypy aprovados.

**Status:** Concluída

---

### Etapa 3 — Implementar chave segura e confinamento de caminhos

**Descrição**

Criar a estrutura de infraestrutura e implementar as regras que transformam uma
chave relativa em caminho local seguro.

**Arquivos previstos**

- `src/merit_assistant/infrastructure/storage/__init__.py`;
- `src/merit_assistant/infrastructure/storage/local_document_storage.py`;
- `tests/test_local_document_storage.py`.

**Comportamentos previstos**

- receber uma raiz privada explícita;
- oferecer criação baseada em `Settings.private_data_dir`;
- resolver a raiz para uma localização canônica;
- gerar a chave somente a partir de UUIDs;
- manter a chave em formato POSIX relativo;
- rejeitar chave vazia;
- rejeitar caminho absoluto;
- rejeitar segmento `..`;
- garantir que o destino permaneça dentro da raiz;
- rejeitar componentes que sejam symlinks;
- criar diretórios progressivamente;
- aplicar permissão `0700` aos diretórios.

**Resultado esperado**

Nenhuma operação de leitura, escrita ou exclusão consegue alcançar um caminho
fora da raiz privada.

**Verificação**

```bash
pytest tests/test_local_document_storage.py \
  -k "key or path or traversal or symlink" -v

ruff check \
  src/merit_assistant/infrastructure/storage \
  tests/test_local_document_storage.py

mypy src/merit_assistant/infrastructure/storage
```

**Resultado**

- `LocalDocumentStorage` criado;
- raiz privada recebida por injeção explícita;
- construção por `Settings.private_data_dir` implementada;
- `storage_key` gerada exclusivamente com UUIDs internos;
- chave mantida em formato POSIX relativo;
- estrutura canônica da chave validada;
- caminhos absolutos rejeitados;
- segmentos `..` rejeitados;
- estruturas não canônicas rejeitadas;
- identificadores UUID inválidos rejeitados;
- raiz configurada como symlink rejeitada;
- componentes de caminho com symlink rejeitados;
- confinamento à raiz privada validado;
- diretórios criados com permissão `0700`;
- 19 testes específicos aprovados;
- Ruff e mypy aprovados.

**Status:** Concluída

---

### Etapa 4 — Implementar gravação binária atômica

**Descrição**

Implementar `store()` com escrita em blocos, arquivo temporário e publicação
atômica sem sobrescrita.

**Fluxo previsto**

1. gerar `storage_key`;
2. validar e preparar o diretório de destino;
3. rejeitar destino já existente;
4. criar arquivo temporário no mesmo diretório;
5. aplicar permissão `0600`;
6. ler `source` em blocos;
7. gravar cada bloco;
8. executar `flush()`;
9. executar `os.fsync()`;
10. publicar o arquivo sem substituir destino existente;
11. remover o nome temporário;
12. retornar somente a chave relativa.

**Regras de erro**

- destino existente gera `DocumentAlreadyExistsError`;
- falha de leitura ou escrita não cria arquivo final;
- arquivo temporário é removido no bloco de compensação;
- erro original é propagado após a limpeza;
- nenhum conteúdo documental é incluído em mensagens ou logs.

**Resultado esperado**

O arquivo final somente se torna visível após a conclusão da escrita e nunca é
silenciosamente sobrescrito.

**Verificação**

```bash
pytest tests/test_local_document_storage.py \
  -k "store or atomic or overwrite or partial or cleanup or chunk" -v
```

**Resultado**

- `store()` implementado;
- conteúdo binário gravado em blocos;
- arquivo temporário criado no diretório final;
- arquivo temporário configurado com permissão `0600`;
- `flush()` e `fsync()` executados antes da publicação;
- publicação realizada sem substituir destino existente;
- sobrescrita rejeitada por `DocumentAlreadyExistsError`;
- conteúdo original preservado após tentativa duplicada;
- falhas durante a leitura não deixam arquivo final parcial;
- arquivos temporários removidos após falha;
- 23 testes específicos aprovados;
- Ruff e mypy aprovados.

**Status:** Concluída

---

### Etapa 5 — Implementar leitura e exclusão

**Descrição**

Implementar `open_binary()` e `delete()` reutilizando as mesmas regras de
confinamento.

**Comportamento de open_binary**

- validar a chave;
- rejeitar path traversal e symlink;
- abrir exclusivamente com modo `rb`;
- retornar um objeto binário fechável;
- propagar `FileNotFoundError` quando ausente.

**Comportamento de delete**

- validar a chave;
- rejeitar path traversal e symlink;
- remover somente o arquivo indicado;
- retornar `True` quando houver remoção;
- retornar `False` quando o arquivo não existir;
- não remover diretórios superiores.

**Resultado esperado**

Arquivos podem ser lidos e excluídos sem expor caminhos absolutos ou permitir
acesso fora da raiz.

**Verificação**

```bash
pytest tests/test_local_document_storage.py \
  -k "open or read or delete" -v
```

**Resultado**

- `open_binary()` implementado;
- arquivos abertos exclusivamente em modo binário de leitura;
- descritor protegido com `O_NOFOLLOW`;
- leitura de arquivo inexistente propaga `FileNotFoundError`;
- `delete()` implementado;
- exclusão de arquivo existente retorna `True`;
- exclusão repetida retorna `False`;
- diretórios superiores são preservados;
- caminhos absolutos e segmentos `..` são rejeitados;
- symlink documental é rejeitado na leitura;
- symlink documental é rejeitado na exclusão;
- alvo externo de symlink permanece preservado;
- 12 testes específicos de leitura e exclusão aprovados;
- 35 testes totais do armazenamento aprovados;
- Ruff e mypy aprovados.

**Status:** Concluída

---

### Etapa 6 — Consolidar os testes de segurança

**Descrição**

Completar a suíte específica do armazenamento usando somente `tmp_path`,
`BytesIO`, UUIDs e conteúdo sintético.

**Casos mínimos**

- geração exata da chave;
- chave relativa;
- chave contendo somente identificadores internos;
- armazenamento dentro da raiz;
- escrita e leitura do mesmo conteúdo;
- leitura em blocos;
- criação dos diretórios;
- diretórios com permissão `0700`;
- arquivo com permissão `0600`;
- rejeição de caminho absoluto;
- rejeição de segmento `..`;
- rejeição de symlink externo;
- rejeição de sobrescrita;
- preservação do arquivo original após tentativa duplicada;
- falha durante a leitura da origem;
- ausência de arquivo final após falha;
- limpeza de arquivo temporário após falha;
- leitura de arquivo existente;
- leitura de arquivo ausente;
- exclusão de arquivo existente;
- segunda exclusão retornando `False`;
- ausência de arquivo criado fora da raiz;
- construção a partir de `Settings.private_data_dir`.

**Arquivos afetados**

- `tests/test_local_document_storage.py`;
- arquivos da implementação, quando correções forem necessárias.

**Resultado esperado**

As regras funcionais e de segurança possuem cobertura automatizada sem uso de
PDF real.

**Verificação**

```bash
pytest tests/test_local_document_storage.py -v

ruff check \
  src/merit_assistant/application/ports/document_storage.py \
  src/merit_assistant/infrastructure/storage \
  tests/test_local_document_storage.py

mypy src
git diff --check
```

**Resultado**

- suíte de segurança consolidada com conteúdo exclusivamente sintético;
- contrato `DocumentStorage` validado por tipagem estrutural;
- `LocalDocumentStorage` confirmado como implementação compatível com o contrato;
- geração canônica de `storage_key` validada;
- confinamento à raiz privada validado;
- tentativa de escrita por symlink externo rejeitada;
- nenhum arquivo criado fora da raiz privada;
- gravação em blocos validada;
- publicação sem sobrescrita validada;
- arquivo original preservado após tentativa duplicada;
- falhas não deixam arquivo final parcial;
- arquivos temporários são removidos após falha;
- permissões `0700` e `0600` validadas;
- leitura binária somente leitura validada;
- exclusão idempotente validada;
- path traversal, caminhos não canônicos e UUIDs inválidos rejeitados;
- symlinks na raiz, nos diretórios e no arquivo rejeitados;
- 37 testes específicos aprovados;
- Ruff aprovado;
- mypy aprovado em código e testes;
- `git diff --check` aprovado.

**Status:** Concluída

---

## 3.4 Checkpoint Humano Obrigatório H1

### H1 — Revisão de segurança do armazenamento

**Momento**

Após as Etapas 2 a 6 e antes do Quality Gate completo.

**Itens para revisão**

- [x] O contrato não depende de infraestrutura concreta.
- [x] A implementação usa a raiz configurada.
- [x] A chave contém apenas UUIDs internos.
- [x] O nome original não participa do caminho.
- [x] Caminhos absolutos são rejeitados.
- [x] Segmentos `..` são rejeitados.
- [x] Symlinks capazes de escapar da raiz são rejeitados.
- [x] A gravação ocorre em blocos.
- [x] O arquivo temporário fica no mesmo diretório do destino.
- [x] A publicação final é atômica.
- [x] Arquivo existente não é sobrescrito.
- [x] Falhas não deixam arquivo final parcial.
- [x] Falhas removem arquivos temporários.
- [x] Arquivos usam permissão `0600`.
- [x] Diretórios usam permissão `0700`.
- [x] Leitura usa somente modo binário.
- [x] Exclusão é idempotente.
- [x] Nenhum conteúdo aparece em logs.
- [x] Nenhum endpoint, banco ou validação de PDF foi introduzido.
- [x] Nenhuma dependência nova foi adicionada.

**Evidências**

```bash
git diff -- \
  src/merit_assistant/application/ports/document_storage.py \
  src/merit_assistant/infrastructure/storage \
  tests/test_local_document_storage.py

pytest tests/test_local_document_storage.py -v
```

**Status:** Approved
**Aprovado por:** André Cataldo
**Data:** 2026-07-23

**Risco residual aceito**

Permanece o risco residual de condição de corrida entre validação e operação
baseada em caminho no sistema de arquivos. O risco é considerado aceitável para
este incremento porque:

- a execução ocorre em ambiente Ubuntu local;
- a raiz privada possui permissão `0700`;
- não há processamento externo;
- symlinks são rejeitados;
- a publicação não substitui arquivos existentes;
- os testes comprovaram ausência de escrita fora da raiz.

**Condição de saída**

A implementação está autorizada a seguir para o Quality Gate completo.

---

## 3.5 Etapa 7 — Executar o Quality Gate

**Descrição**

Validar regressão, tipagem, estilo, escopo e segurança do repositório.

**Verificação**

```bash
pytest
ruff check .
mypy src
./scripts/verify_i001_scope.sh
git diff --check
git status --short
```

Confirmar ausência de arquivos privados rastreados:

```bash
git ls-files | grep -Ei \
  '\.(pdf|db|sqlite|sqlite3|log|env|dump|backup|tmp)$'
```

Confirmar a superfície da mudança:

```bash
git diff --name-only
```

**Arquivos de implementação esperados**

```text
src/merit_assistant/application/ports/document_storage.py
src/merit_assistant/infrastructure/storage/__init__.py
src/merit_assistant/infrastructure/storage/local_document_storage.py
tests/test_local_document_storage.py
```

**Arquivos de governança esperados**

```text
docs/features/feature-intent-f01-2-secure-local-storage.md
docs/action-plans/action-plan-f01-2-secure-local-storage.md
```

**Resultado**

- suíte completa aprovada com 57 testes;
- warning preexistente e não bloqueante identificado;
- Ruff aprovado;
- mypy aprovado;
- verificador de escopo I-001 aprovado;
- `git diff --check` aprovado;
- banco mantido em `0002_add_documents`;
- PostgreSQL saudável;
- API e UI operacionais;
- endpoint `/health` aprovado;
- processamento externo mantido desativado;
- superfície da mudança compatível com o plano;
- nenhum documento real ou arquivo privado rastreado pelo Git;
- nenhuma expansão de escopo identificada.

**Status:** Concluída

---

## 3.6 Checkpoint Humano Obrigatório H2

### H2 — Revisão final antes do commit

**Momento**

Após o Quality Gate e antes do encerramento formal.

**Itens para revisão**

- [x] Todos os 57 testes foram aprovados.
- [x] Os 37 testes específicos de armazenamento foram aprovados.
- [x] Ruff foi aprovado.
- [x] mypy foi aprovado.
- [x] O verificador I-001 foi aprovado.
- [x] `git diff --check` foi aprovado.
- [x] PostgreSQL permanece saudável.
- [x] Alembic permanece em `0002_add_documents`.
- [x] API e UI permanecem operacionais.
- [x] O endpoint `/health` foi aprovado.
- [x] O contrato permanece independente da infraestrutura.
- [x] A gravação é confinada à raiz privada.
- [x] A publicação não sobrescreve arquivos existentes.
- [x] Falhas não deixam arquivo parcial ou temporário.
- [x] Path traversal e symlinks inseguros são rejeitados.
- [x] Nenhum endpoint, banco ou interface foi alterado.
- [x] Nenhuma dependência foi adicionada.
- [x] Nenhum documento real ou arquivo privado foi versionado.
- [x] Nenhuma expansão de escopo foi identificada.
- [x] O Feature Intent F01.2 permanece integralmente atendido.

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
**Data:** 2026-07-23

**Condição de saída**

A implementação está autorizada para encerramento, commit e push.

---

## 3.7 Etapa 8 — Encerrar e registrar a implementação

**Descrição**

Atualizar os artefatos de governança e registrar a implementação.

**Ações previstas**

- alterar o Feature Intent F01.2 para `Done`;
- marcar critérios comprovados;
- adicionar registro de conclusão;
- alterar este Action Plan para `Done`;
- marcar as etapas como concluídas;
- registrar H1 e H2;
- executar validação final;
- realizar commit;
- enviar a branch ao remoto.

**Commit sugerido**

```bash
git add \
  src/merit_assistant/application/ports/document_storage.py \
  src/merit_assistant/infrastructure/storage/__init__.py \
  src/merit_assistant/infrastructure/storage/local_document_storage.py \
  tests/test_local_document_storage.py \
  docs/features/feature-intent-f01-2-secure-local-storage.md \
  docs/action-plans/action-plan-f01-2-secure-local-storage.md

git commit -m "feat: add secure local document storage"

git push origin feature/f01-secure-document-ingestion
```

**Resultado**

- Feature Intent F01.2 atualizado para `Done`;
- Action Plan F01.2 atualizado para `Done`;
- critérios de aceite marcados conforme as evidências;
- checkpoints H1 e H2 registrados;
- Quality Gate aprovado;
- implementação preparada para commit e push;
- nenhum desvio ou expansão de escopo identificado.

**Status:** Concluída

---

## 4. Riscos e Mitigações

### R-01 — Path traversal

**Mitigação**

Validar a chave como caminho POSIX relativo e rejeitar `..` antes de qualquer
acesso ao sistema de arquivos.

### R-02 — Escape por symlink

**Mitigação**

Inspecionar componentes existentes, rejeitar symlinks e confirmar confinamento
na raiz canônica.

### R-03 — Condição de corrida

**Mitigação**

Publicar o arquivo por operação atômica que falhe caso o destino já exista.

### R-04 — Sobrescrita acidental

**Mitigação**

Não usar `os.replace()` e tratar destino existente como conflito explícito.

### R-05 — Arquivo parcial

**Mitigação**

Gravar em arquivo temporário, sincronizar e publicar somente após sucesso.

### R-06 — Arquivo temporário abandonado

**Mitigação**

Remover o temporário em bloco `finally` ou compensação equivalente.

### R-07 — Permissões excessivas

**Mitigação**

Aplicar explicitamente `0700` em diretórios e `0600` em arquivos.

### R-08 — Carregamento integral em memória

**Mitigação**

Consumir `BinaryIO` em blocos de tamanho controlado.

### R-09 — Portabilidade da publicação atômica

**Mitigação**

A implementação inicial é destinada ao ambiente Ubuntu definido na iteração.
Qualquer necessidade de suporte a outro sistema operacional exigirá nova
decisão explícita.

### R-10 — Arquivo órfão após falha de persistência futura

**Mitigação**

Disponibilizar `delete()` idempotente. A coordenação entre arquivo e banco será
implementada no fluxo de upload, não nesta feature.

---

## 5. Critério de Conclusão

O F01.2 estará concluído quando:

- `DocumentStorage` existir;
- `LocalDocumentStorage` implementar o contrato;
- a raiz vier de `Settings.private_data_dir`;
- a chave seguir o formato aprovado;
- nenhuma operação escapar da raiz;
- path traversal for rejeitado;
- symlink externo for rejeitado;
- escrita ocorrer em blocos;
- publicação for atômica;
- sobrescrita for impedida;
- falhas não deixarem arquivo parcial;
- temporários forem removidos após erro;
- arquivos possuírem permissão `0600`;
- diretórios possuírem permissão `0700`;
- leitura binária funcionar;
- exclusão idempotente funcionar;
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

- for necessário validar conteúdo PDF;
- for necessário calcular SHA-256;
- for necessário aplicar limite de tamanho;
- for necessário acessar PostgreSQL;
- for necessário criar endpoint ou interface;
- uma nova dependência for necessária;
- o confinamento contra symlink não puder ser garantido;
- a publicação sem sobrescrita não puder ser implementada;
- o ambiente precisar deixar de ser Ubuntu;
- uma Decision Lock precisar ser alterada;
- um documento real for necessário para os testes;
- o escopo F01.2 não puder ser preservado.

---

## 7. Registro de Conclusão

- **Status final:** Done
- **Data da conclusão:** 2026-07-23
- **Checkpoint H1:** Approved
- **Checkpoint H2:** Approved
- **Quality Gate:** Approved
- **Testes específicos:** 37 aprovados
- **Suíte completa:** 57 aprovados
- **Desvios registrados:** nenhum
- **Expansão de escopo:** nenhuma

O F01.2 foi implementado, validado e autorizado para registro definitivo.

---

## 8. Aprovação

- [x] **Human Lead Engineer aprovou este Action Plan**
- **Data da aprovação:** 2026-07-23
