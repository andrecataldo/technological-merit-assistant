#!/usr/bin/env bash
set -euo pipefail

fail() {
  echo "[I-001 scope violation] $1" >&2
  exit 1
}

if git ls-files | grep -E '\.(pdf|docx|xlsx|xls|csv|db|sqlite|sqlite3)$' >/dev/null; then
  fail "Documento ou banco proibido está rastreado pelo Git."
fi

if git grep -Eni '(openai|anthropic|gemini|bedrock|ollama|langchain|llamaindex|pgvector)' -- \
  ':!docs/**' ':!scripts/verify_i001_scope.sh' ':!pyproject.toml' >/dev/null 2>&1; then
  fail "Referência a provedor, LLM, RAG ou vector database encontrada no código da I-001."
fi

if grep -Eq '^EXTERNAL_PROCESSING_ENABLED=(true|1|yes)$' .env 2>/dev/null; then
  fail "Processamento externo foi habilitado."
fi

echo "Escopo I-001 verificado com sucesso."
