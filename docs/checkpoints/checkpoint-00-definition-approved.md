# CHECKPOINT 00 — Definição do Produto Aprovada

<!-- CHECKPOINT OFICIAL -->

- **Projeto:** Assistente de Avaliação de Mérito Tecnológico
- **Produto:** Assistente de Avaliação de Mérito Tecnológico
- **Versão do workflow:** AI-Assisted SDLC Workflow v0.2
- **Versão do checkpoint:** v1.0
- **Data:** 2026-07-22
- **Responsável humano:** André Cataldo
- **Objetivo do checkpoint:** consolidar a definição do produto e autorizar a abertura da primeira iteração de implementação.

---

## 1. Contexto do Checkpoint

Este checkpoint encerra a fase de definição inicial do produto. Foram discutidos e aprovados o problema, o objetivo, o escopo, a arquitetura híbrida, os limites de atuação da IA, a identidade desacoplada de uma instituição específica e o plano macro de execução.

O produto será uma aplicação privada de apoio ao especialista humano. Seu núcleo será genérico e extensível por perfis de avaliação. O primeiro perfil contemplará a seleção Mais Inovação Brasil — Rodada 2 — Tecnologias Digitais, sem incorporar referência à Finep no nome do produto, repositório ou pacote principal.

Este checkpoint também normaliza os identificadores dos Decision Locks. Rascunhos anteriores reutilizaram ou deslocaram alguns IDs; a lista abaixo passa a ser o registro canônico vigente.

---

## 2. Estado Atual Consolidado

### 2.1 O que está concluído

- Nome do produto definido: **Assistente de Avaliação de Mérito Tecnológico**.
- Nome recomendado do repositório: `technological-merit-assistant`.
- Nome recomendado do pacote Python: `merit_assistant`.
- PRD-Lite v0.1 definido e aprovado.
- Context Pack v0.1 definido e aprovado.
- Guidelines Técnicas v0.1 definidas e aprovadas.
- Visão de Arquitetura v0.1 definida e aprovada.
- Plano de Execução v0.1 definido e aprovado.
- Arquitetura híbrida aprovada, com custódia local dos dados por padrão.
- Responsabilidade humana e uso assistivo da IA estabelecidos.
- Primeiro incremento delimitado: fundação técnica e ingestão documental local.

### 2.2 O que NÃO está concluído

- Repositório privado ainda não criado.
- Estrutura de código ainda não implementada.
- Perfil inicial ainda não materializado em arquivos de configuração.
- Ingestão e extração de PDFs ainda não implementadas.
- Modelo de domínio, matriz de evidências e regras ainda não implementados.
- RAG, embeddings e analisadores especializados ainda não implementados.
- Data Egress Gateway ainda não implementado.
- Nenhum provedor externo foi autorizado para documentos reais.
- Projeto CodeLocal BR ainda não foi processado pelo aplicativo.
- Não existe golden dataset de respostas humanas validadas.

### 2.3 Decision Locks vigentes — registro canônico

| ID | Decisão vigente | Justificativa |
|---|---|---|
| DL-001 | O produto se chama **Assistente de Avaliação de Mérito Tecnológico**. | Preservar identidade genérica e reutilização em outros programas. |
| DL-002 | O núcleo não fará referência à Finep em nome de repositório, pacote ou módulos centrais. | Evitar acoplamento institucional. |
| DL-003 | Regras específicas serão implementadas em perfis de avaliação versionados. | Separar núcleo genérico de normas de cada programa. |
| DL-004 | A aplicação é assistiva; não aprova, reprova nem submete avaliações. | Preservar responsabilidade humana. |
| DL-005 | Toda afirmação factual relevante deve ser vinculada a documento e página. | Garantir rastreabilidade. |
| DL-006 | Ausência de informação não será convertida silenciosamente em evidência negativa ou positiva. | Evitar inferências indevidas. |
| DL-007 | A arquitetura será híbrida, com documentos, extração, persistência, recuperação e auditoria locais ou privadas. | Proteger confidencialidade e manter flexibilidade computacional. |
| DL-008 | Processamento externo ficará desabilitado por padrão e dependerá de gateway, sanitização, provedor autorizado e aprovação humana. | Controlar saída de dados. |
| DL-009 | Nenhum documento integral poderá ser enviado a provedor externo. | Minimizar risco de exposição. |
| DL-010 | Documentos reais e dados privados não serão versionados em Git. | Cumprir requisitos de confidencialidade. |
| DL-011 | Respostas terão limite configurável de 4.000 caracteres e alvo operacional entre 3.600 e 3.800. | Preservar margem para revisão humana. |
| DL-012 | Novidade mundial não será confirmada apenas pela declaração da proponente. | Exigir evidência adequada de estado da técnica. |
| DL-013 | O MVP será um monólito modular. | Reduzir complexidade prematura. |
| DL-014 | Regras determinísticas terão precedência sobre inferências de LLM. | Aumentar confiabilidade e reprodutibilidade. |

---

## 3. Artefatos Válidos neste Momento

Lista normativa para retomada:

- **PRD-Lite:** `docs/prd/prd-lite-v0.1.md`
- **Context Pack:** `docs/context/context-pack-v0.1.md`
- **Guidelines Técnicas:** `docs/guidelines/technical-guidelines-v0.1.md`
- **Visão de Arquitetura:** `docs/architecture/architecture-vision-v0.1.md`
- **Plano de Execução:** `docs/planning/execution-plan-v0.1.md`
- **Checkpoint vigente:** `docs/checkpoints/checkpoint-00-definition-approved.md`
- **MCP+ seguinte:** `docs/mcp/mcp-plus-001-foundation-ingestion.md`

Os caminhos representam a estrutura prevista para o futuro repositório privado. Até sua criação, o conteúdo aprovado nesta conversa é a referência de origem.

Artefatos não listados nesta seção não devem prevalecer sobre os documentos acima.

---

## 4. Principais Restrições Ativas

- Escopo do primeiro incremento limitado à fundação técnica e ingestão documental local.
- Nenhum LLM será integrado na primeira iteração.
- Nenhuma API externa será chamada pela aplicação na primeira iteração.
- Nenhum RAG, embedding ou banco vetorial será implementado na primeira iteração.
- Nenhuma avaliação de mérito será gerada na primeira iteração.
- Documentos reais permanecerão somente no ambiente local e fora do Git.
- A implementação deverá funcionar em Ubuntu e ser reproduzível com Docker Compose.
- O primeiro perfil poderá ser selecionado, mas conterá apenas metadados mínimos nesta iteração.

---

## 5. Riscos ou Pontos de Atenção

- PDFs podem não possuir camada textual adequada; OCR permanece fora do primeiro escopo.
- A extração nativa pode preservar mal tabelas ou colunas.
- A escolha prematura de abstrações pode criar complexidade sem evidência.
- O uso de documentos reais no desenvolvimento pode gerar vazamento por logs, fixtures ou commits acidentais.
- A estrutura genérica de perfis pode ser superdimensionada antes do segundo caso de uso.
- A qualidade de busca lexical será limitada, mas é suficiente para validar a fundação antes do RAG.

---

## 6. Próximo Passo Recomendado

**Abrir a Iteração I-001 por meio do MCP+ 001 — Fundação Técnica e Ingestão Documental Local.**

Justificativa: o maior risco técnico inicial não é a geração por IA, mas a capacidade de receber, armazenar, extrair, localizar e exibir conteúdo documental com confidencialidade e rastreabilidade.

---

## 7. Regras de Retomada

Ao retomar:

1. Ler este checkpoint primeiro.
2. Considerar os Decision Locks desta versão como registro canônico.
3. Ler o MCP+ 001 antes de gerar código ou alterar arquitetura.
4. Não reabrir decisões bloqueadas sem criar novo checkpoint e nova versão do MCP+.
5. Não incorporar OCR, RAG, LLM, avaliação automática ou integração externa durante a Iteração I-001.

---

## 8. Observações Finais

O produto foi intencionalmente desacoplado da instituição do primeiro perfil. Isso não significa tornar o domínio abstrato desde o início: o núcleo será genérico, mas o primeiro perfil será concreto, versionado e testado com a documentação da seleção escolhida.

---

## TAG DE RETOMADA

**RETOMADA:** Ler `checkpoint-00-definition-approved.md` e executar somente o `mcp-plus-001-foundation-ingestion.md`; arquitetura híbrida aprovada, dados locais por padrão e nenhuma IA na primeira iteração.
