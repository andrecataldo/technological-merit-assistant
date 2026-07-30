# Feature Intent F01.6 — Listagem Segura de Documentos por Avaliação

## 1. Identificação

- **Título da Feature:** F01.6 — Listagem Segura de Documentos por Avaliação
- **Feature pai:** F01 — Ingestão Segura de Documentos
- **Autor — Human Lead Engineer:** André Cataldo
- **Data:** 2026-07-30
- **Status:** Approved
- **Branch:** `feature/f01-secure-document-ingestion`
- **Baseline:** `408fdfab61ac817c9d91ac7cb421d1adfdb3a9a1`
- **MCP+ aplicável:** MCP+ 001 v1.1
- **Dependências funcionais:**
  - F01.1 — Modelo de Documento e Migration;
  - F01.2 — Serviço Local de Armazenamento Seguro;
  - F01.3 — Validação de PDF, Limite de Tamanho e SHA-256;
  - F01.4 — Orquestração Segura do Upload e Persistência;
  - F01.5 — Endpoint Seguro de Upload de Documentos.

---

## 2. Contexto e Problema

A aplicação já permite associar um PDF válido a uma avaliação por meio de um
endpoint seguro de upload.

Os metadados do documento são persistidos no PostgreSQL, enquanto o conteúdo
permanece em armazenamento local privado e fora do Git.

Ainda não existe uma operação pública para consultar os documentos associados
a uma avaliação.

Sem uma listagem específica, uma integração futura poderia:

- consultar diretamente modelos ou tabelas da infraestrutura;
- expor `storage_key`, caminho físico ou SHA-256;
- acessar desnecessariamente os arquivos armazenados;
- retornar documentos pertencentes a outra avaliação;
- produzir uma ordenação não determinística;
- tratar incorretamente uma avaliação inexistente;
- duplicar regras entre FastAPI e Streamlit.

---

## 3. Intenção — Outcome

Disponibilizar uma operação segura que liste os documentos pertencentes a uma
avaliação e retorne exclusivamente metadados públicos.

A listagem deverá:

- receber o identificador da avaliação;
- confirmar que a avaliação existe;
- consultar somente os documentos da avaliação informada;
- usar uma ordem determinística;
- retornar uma coleção vazia para avaliação existente sem documentos;
- não abrir nem ler os arquivos armazenados;
- não expor identificadores ou caminhos internos de armazenamento;
- não expor SHA-256;
- manter o processamento exclusivamente local.

---

## 4. Escopo

### 4.1 Dentro do escopo — IN

- [ ] Criar `GET /evaluations/{evaluation_id}/documents`.
- [ ] Receber `evaluation_id` como UUID no path.
- [ ] Confirmar a existência da avaliação.
- [ ] Retornar HTTP `404 Not Found` para avaliação inexistente.
- [ ] Retornar HTTP `200 OK` para avaliação existente.
- [ ] Retornar lista vazia quando a avaliação não possuir documentos.
- [ ] Listar somente documentos cujo `evaluation_id` corresponda ao path.
- [ ] Definir ordenação determinística por `created_at` e `id`.
- [ ] Retornar, para cada documento, somente:
  - `id`;
  - `evaluation_id`;
  - `original_filename`;
  - `content_type`;
  - `size_bytes`;
  - `created_at`.
- [ ] Não retornar `storage_key`.
- [ ] Não retornar caminho físico absoluto ou relativo.
- [ ] Não retornar SHA-256.
- [ ] Não retornar conteúdo documental.
- [ ] Não acessar o arquivo no storage durante a listagem.
- [ ] Criar ou reutilizar schema público documental.
- [ ] Criar caso de uso explícito para listagem.
- [ ] Estender a porta de persistência somente com as operações necessárias.
- [ ] Implementar a consulta no adapter SQLAlchemy.
- [ ] Utilizar a sessão PostgreSQL administrada pelo request.
- [ ] Traduzir falhas conhecidas para respostas HTTP estáveis.
- [ ] Manter mensagens públicas sanitizadas.
- [ ] Criar testes unitários do caso de uso e da camada HTTP.
- [ ] Criar testes de contrato do adapter de persistência.
- [ ] Criar testes integrados com PostgreSQL real.
- [ ] Confirmar isolamento entre avaliações.
- [ ] Confirmar ausência de leitura do storage.
- [ ] Manter os Quality Gates existentes aprovados.
- [ ] Manter o processamento externo desabilitado.
- [ ] Usar somente dados e identificadores sintéticos nos testes.

### 4.2 Fora do escopo — OUT

- [ ] Criar interface Streamlit.
- [ ] Fazer upload de documentos.
- [ ] Fazer download de documentos.
- [ ] Excluir documentos.
- [ ] Exibir ou retornar conteúdo documental.
- [ ] Validar novamente o PDF durante a listagem.
- [ ] Recalcular tamanho ou SHA-256.
- [ ] Verificar novamente o arquivo no storage.
- [ ] Criar paginação nesta iteração.
- [ ] Criar busca textual ou filtros.
- [ ] Criar ordenação configurável pelo cliente.
- [ ] Implementar autenticação ou autorização.
- [ ] Implementar rate limiting.
- [ ] Implementar antivírus.
- [ ] Extrair texto, páginas, imagens ou tabelas.
- [ ] Executar OCR.
- [ ] Criar embeddings.
- [ ] Implementar RAG ou LLM.
- [ ] Enviar dados para serviços externos.
- [ ] Alterar o documento original.
- [ ] Alterar `LocalDocumentStorage`.
- [ ] Criar ou alterar migrations.
- [ ] Alterar a tabela `documents`.
- [ ] Converter a aplicação para SQLAlchemy assíncrono.
- [ ] Refatorar funcionalidades não relacionadas.

---

## 5. Contrato HTTP

### 5.1 Request

```text
GET /evaluations/{evaluation_id}/documents
```

Parâmetros:

| Origem | Nome            | Tipo | Obrigatório |
| ------ | --------------- | ---: | ----------: |
| Path   | `evaluation_id` | UUID |         Sim |

Não haverá body, multipart ou acesso ao arquivo armazenado.

### 5.2 Response de sucesso com documentos

```text
HTTP/1.1 200 OK
Content-Type: application/json
```

Exemplo:

```json
[
  {
    "id": "uuid",
    "evaluation_id": "uuid",
    "original_filename": "documento.pdf",
    "content_type": "application/pdf",
    "size_bytes": 12345,
    "created_at": "2026-07-30T18:00:00Z"
  }
]
```

### 5.3 Response de sucesso sem documentos

Para uma avaliação existente sem documentos:

```text
HTTP/1.1 200 OK
Content-Type: application/json
```

```json
[]
```

### 5.4 Campos proibidos

A resposta não deverá conter:

- `storage_key`;
- caminho absoluto ou relativo;
- SHA-256;
- conteúdo do documento;
- detalhes de PostgreSQL ou SQLAlchemy;
- informações do sistema de arquivos.

---

## 6. Ordenação

A resposta deverá possuir ordenação determinística:

1. `created_at` crescente;
2. `id` crescente como critério de desempate.

A ordenação deverá ser aplicada pela consulta de persistência, evitando
dependência da ordem natural do PostgreSQL.

---

## 7. Fronteiras Arquiteturais

A camada HTTP deverá depender de um caso de uso explícito de listagem.

O caso de uso poderá depender de uma porta de persistência com operações
equivalentes a:

```python
def evaluation_exists(self, evaluation_id: UUID) -> bool:
    ...

def list_by_evaluation(
    self,
    evaluation_id: UUID,
) -> Sequence[Document]:
    ...
```

A definição definitiva de nomes, tipos e composição será estabelecida no
Action Plan.

A operação não deverá depender de:

- `DocumentStorage`;
- `LocalDocumentStorage`;
- `PdfInspector`;
- `DocumentValidationService`;
- abertura ou leitura de arquivos;
- serviços externos.

---

## 8. Contrato de Erros

| Situação                      | HTTP | Mensagem pública            |
| ----------------------------- | ---: | --------------------------- |
| UUID inválido no path         |  422 | resposta padrão sanitizada  |
| Avaliação inexistente         |  404 | `Evaluation not found.`     |
| Falha interna de persistência |  500 | `Unable to list documents.` |

As mensagens internas de SQLAlchemy, PostgreSQL, paths, constraints ou
configuração não poderão ser retornadas.

Não deverá existir captura genérica de `Exception` apenas para ocultar erros
desconhecidos.

---

## 9. Critérios de Aceitação

1. Avaliação inexistente retorna `404`.
2. Avaliação existente sem documentos retorna `200` e `[]`.
3. Avaliação com documentos retorna somente seus próprios documentos.
4. Documentos de outra avaliação não aparecem na resposta.
5. A ordenação é determinística por `created_at` e `id`.
6. A resposta contém somente os seis campos públicos aprovados.
7. A resposta não contém `storage_key`, path ou SHA-256.
8. A operação não abre nem lê arquivos do storage.
9. A consulta utiliza PostgreSQL por meio da porta e do adapter aprovados.
10. Testes unitários, de contrato e integrados são aprovados.
11. Ruff, mypy, I-001 e `git diff --check` permanecem aprovados.
12. Nenhum documento real é utilizado ou versionado.
13. O health permanece aprovado.
14. O processamento externo permanece desabilitado.

---

## 10. Estratégia de Testes

Os testes deverão cobrir, no mínimo:

- avaliação inexistente;
- avaliação existente sem documentos;
- avaliação com um documento;
- avaliação com múltiplos documentos;
- isolamento entre duas avaliações;
- ordenação determinística;
- schema público seguro;
- ausência de acesso ao storage;
- falha de persistência com mensagem sanitizada;
- PostgreSQL real em teste integrado;
- limpeza defensiva dos dados sintéticos.

---

## 11. Riscos

### Vazamento de metadados internos

Mitigação: schema público explícito e testes negativos para campos proibidos.

### Acesso cruzado entre avaliações

Mitigação: consulta obrigatoriamente filtrada por `evaluation_id` e teste
integrado com duas avaliações.

### Ordenação instável

Mitigação: `ORDER BY created_at, id` explícito no adapter.

### Acoplamento ao storage

Mitigação: caso de uso de listagem dependerá somente da persistência.

### Expansão prematura

Mitigação: paginação, filtros, UI, download e exclusão permanecem fora do
escopo.

---

## 12. Dependências e Restrições

- PostgreSQL configurado pelo projeto;
- migration `0002_add_documents (head)`;
- modelos documentais existentes;
- sessão SQLAlchemy administrada pelo request;
- nenhuma migration nova;
- nenhum acesso externo;
- nenhum documento real em Git;
- MCP+ 001 v1.1 permanece aplicável.

---

## 13. Condição para Início do Action Plan

O Action Plan somente poderá ser criado depois de:

- revisão deste Feature Intent;
- resolução de eventuais pendências;
- aprovação explícita do Human Lead Engineer;
- alteração do status para `Approved`;
- commit documental específico;
- sincronização da branch com o remoto.

Nenhum código de implementação da F01.6 poderá ser alterado antes da aprovação
e do commit do Action Plan.

---

## 14. Aprovação

- [x] **Human Lead Engineer aprovou este Feature Intent**
- **Data da aprovação:** 2026-07-30
- **Observações:** Aprovado sem pendências bloqueantes.
