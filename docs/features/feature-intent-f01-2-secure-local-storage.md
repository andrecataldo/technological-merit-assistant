# Feature Intent F01.2 — Serviço Local de Armazenamento Seguro

## 1. Identificação

- **Título da Feature:** F01.2 — Serviço Local de Armazenamento Seguro
- **Feature pai:** F01 — Ingestão Segura de Documentos
- **Autor — Human Lead Engineer:** André Cataldo
- **Data:** 2026-07-23
- **Status:** Approved
- **MCP+ aplicável:** MCP+ 001 v1.1
- **Dependência:** F01.1 — Modelo de Documento e Migration

---

## 2. Contexto e Problema

A aplicação já possui uma representação persistente para documentos, incluindo
a chave relativa `storage_key`, mas ainda não possui um serviço responsável
pela gravação e recuperação segura dos arquivos no armazenamento local.

Gravar arquivos diretamente em endpoints ou serviços de aplicação aumentaria
o risco de:

- path traversal;
- sobrescrita acidental;
- gravação parcial;
- uso do nome original como caminho físico;
- arquivos fora do diretório privado;
- permissões inadequadas;
- acoplamento entre interface, aplicação e sistema de arquivos.

---

## 3. Intenção — Outcome

Criar um serviço local de armazenamento capaz de:

- armazenar um fluxo binário dentro do diretório privado configurado;
- gerar uma chave relativa segura e independente do nome original;
- impedir gravação fora da raiz privada;
- publicar o arquivo somente após a conclusão da escrita;
- impedir sobrescrita de arquivo existente;
- abrir arquivos armazenados em modo somente leitura;
- excluir arquivos para permitir compensação em caso de falha posterior;
- preservar confidencialidade e integridade operacional.

---

## 4. Escopo

### 4.1 Dentro do escopo — IN

- [ ] Criar o contrato `DocumentStorage`.
- [ ] Criar a implementação `LocalDocumentStorage`.
- [ ] Usar `Settings.private_data_dir` como raiz do armazenamento.
- [ ] Gerar `storage_key` usando somente UUIDs internos.
- [ ] Usar o formato:
      `evaluations/{evaluation_id}/documents/{document_id}.pdf`.
- [ ] Manter `storage_key` como caminho POSIX relativo.
- [ ] Criar diretórios privados quando necessário.
- [ ] Gravar conteúdo binário em blocos.
- [ ] Utilizar arquivo temporário no mesmo diretório do destino.
- [ ] Publicar o arquivo final de forma atômica.
- [ ] Impedir sobrescrita de arquivo existente.
- [ ] Remover arquivo temporário em caso de erro.
- [ ] Configurar diretórios com permissão `0700`.
- [ ] Configurar arquivos com permissão `0600`.
- [ ] Permitir abertura binária somente para leitura.
- [ ] Permitir exclusão idempotente de arquivo armazenado.
- [ ] Rejeitar caminhos absolutos.
- [ ] Rejeitar segmentos `..`.
- [ ] Rejeitar caminhos que escapem da raiz por symlink.
- [ ] Criar testes automatizados com dados sintéticos.

### 4.2 Fora do escopo — OUT

- [ ] Validar extensão PDF.
- [ ] Validar assinatura ou estrutura PDF.
- [ ] Validar MIME type.
- [ ] Aplicar limite máximo de tamanho.
- [ ] Calcular SHA-256.
- [ ] Detectar duplicidade.
- [ ] Persistir metadados no PostgreSQL.
- [ ] Criar ou atualizar registros `DocumentModel`.
- [ ] Criar endpoint de upload.
- [ ] Criar endpoint de download.
- [ ] Criar endpoint de listagem.
- [ ] Criar interface Streamlit.
- [ ] Extrair texto.
- [ ] Implementar OCR.
- [ ] Implementar criptografia própria de arquivos.
- [ ] Armazenar em nuvem.
- [ ] Integrar serviços externos.

---

## 5. Contrato Proposto

### DocumentStorage

O contrato deverá expor operações equivalentes a:

- `store(evaluation_id, document_id, source) -> storage_key`;
- `open_binary(storage_key)`;
- `delete(storage_key) -> bool`.

### Responsabilidades

`store` deverá:

- receber conteúdo binário já aceito pela camada chamadora;
- gerar internamente a chave de armazenamento;
- criar os diretórios necessários;
- escrever em blocos;
- impedir sobrescrita;
- retornar somente a chave relativa.

`open_binary` deverá:

- validar a chave recebida;
- garantir confinamento dentro da raiz privada;
- abrir o arquivo somente para leitura binária.

`delete` deverá:

- validar a chave recebida;
- remover somente o arquivo indicado;
- retornar `True` quando houver remoção;
- retornar `False` quando o arquivo já não existir;
- não remover diretórios superiores.

---

## 6. Regras de Segurança

- O nome original nunca será usado no caminho físico.
- Nenhum caminho absoluto será exposto ao chamador.
- Toda operação será confinada a `private_data_dir`.
- Uma chave inválida será rejeitada antes de acessar o sistema de arquivos.
- O serviço não poderá seguir symlink para fora da raiz privada.
- Arquivo existente não poderá ser substituído silenciosamente.
- Arquivo incompleto não poderá aparecer como arquivo final.
- Arquivos temporários deverão ser removidos após falha.
- Nenhum conteúdo documental deverá aparecer nos logs.
- Nenhuma chamada de rede será realizada.

---

## 7. Casos de Sucesso

- Um fluxo binário é gravado no diretório privado.
- O conteúdo lido é idêntico ao conteúdo recebido.
- A chave retornada é relativa e contém somente UUIDs internos.
- O arquivo final possui permissão `0600`.
- Os diretórios utilizados possuem permissão `0700`.
- Um arquivo armazenado pode ser aberto em modo binário de leitura.
- Um arquivo armazenado pode ser excluído.
- Excluir novamente o mesmo arquivo retorna resultado negativo sem falha.

---

## 8. Casos de Erro

- Caminho absoluto é rejeitado.
- Chave com segmento `..` é rejeitada.
- Chave que escape por symlink é rejeitada.
- Tentativa de gravar novamente no mesmo destino é rejeitada.
- Falha durante a escrita não deixa arquivo final parcial.
- Falha durante a escrita não deixa arquivo temporário abandonado.
- Tentativa de leitura fora da raiz é rejeitada.
- Tentativa de exclusão fora da raiz é rejeitada.

---

## 9. Critérios de Aceite

### 9.1 Funcionais

- [ ] O contrato `DocumentStorage` foi criado.
- [ ] `LocalDocumentStorage` implementa o contrato.
- [ ] A raiz vem de `Settings.private_data_dir`.
- [ ] A chave segue o formato aprovado.
- [ ] O arquivo é gravado dentro da raiz privada.
- [ ] O conteúdo armazenado permanece íntegro.
- [ ] O nome original não participa do caminho físico.
- [ ] A gravação final é atômica.
- [ ] Arquivo existente não é sobrescrito.
- [ ] Arquivos temporários são removidos após erro.
- [ ] Leitura binária funciona.
- [ ] Exclusão funciona de forma idempotente.
- [ ] Path traversal é rejeitado.
- [ ] Escape por symlink é rejeitado.
- [ ] Permissões de arquivo e diretório são restritivas.

### 9.2 Técnicos

- [ ] Testes usam apenas `tmp_path` e conteúdo sintético.
- [ ] Nenhum PDF real é necessário.
- [ ] Nenhuma dependência nova é adicionada.
- [ ] Nenhum endpoint é criado.
- [ ] Nenhum acesso ao PostgreSQL é realizado.
- [ ] `pytest` é aprovado.
- [ ] `ruff check .` é aprovado.
- [ ] `mypy src` é aprovado.
- [ ] `verify_i001_scope.sh` é aprovado.
- [ ] Nenhum arquivo privado é incluído no Git.

---

## 10. Superfície Prevista de Mudança

### Arquivos previstos

- `src/merit_assistant/application/ports/document_storage.py`;
- `src/merit_assistant/infrastructure/storage/__init__.py`;
- `src/merit_assistant/infrastructure/storage/local_document_storage.py`;
- `tests/test_local_document_storage.py`.

### Arquivos que não devem ser alterados

- modelos SQLAlchemy;
- migrations;
- endpoints FastAPI;
- interface Streamlit;
- perfil de avaliação;
- serviços de extração;
- regras institucionais.

---

## 11. Riscos

- path traversal;
- escape por symlink;
- condição de corrida durante publicação;
- sobrescrita acidental;
- arquivo parcial após falha;
- permissões excessivas;
- arquivo órfão caso uma operação posterior falhe;
- esgotamento de espaço em disco.

A persistência no banco e a compensação entre banco e sistema de arquivos serão
tratadas na orquestração do upload, não neste incremento.

---

## 12. Plano de Validação

Os testes deverão comprovar:

- geração correta da chave;
- escrita e leitura de conteúdo sintético;
- criação de diretórios;
- permissões `0700` e `0600`;
- rejeição de caminho absoluto;
- rejeição de `..`;
- rejeição de escape por symlink;
- rejeição de sobrescrita;
- limpeza após falha;
- exclusão existente;
- exclusão de arquivo ausente;
- ausência de escrita fora da raiz.

---

## 13. Handoff para IA

### Artefatos superiores

- MCP+ 001 v1.1;
- PRD-Lite v0.1;
- Feature Intent F01;
- Feature Intent F01.1 concluído;
- Context Pack v0.1;
- Guidelines Técnicas v0.1;
- Arquitetura v0.1.

### Regras de execução

- implementar somente armazenamento local;
- não validar PDF;
- não calcular SHA-256;
- não aplicar limite de tamanho;
- não acessar PostgreSQL;
- não criar endpoint ou interface;
- não adicionar dependências;
- não usar nome original no caminho;
- interromper em caso de conflito com artefato superior.

---

## Aprovação

- [x] **Human Lead Engineer aprovou esta Feature Intent**
- **Data da aprovação:** 2026-07-23
