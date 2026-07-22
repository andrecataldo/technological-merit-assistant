# Política de Dados — Iteração I-001

## Regra principal

Documentos reais, conteúdo extraído, bancos locais e logs de execução não podem ser versionados nem incluídos em imagens de contêiner.

## Locais permitidos

- documentos reais: `data/private/`;
- logs locais: `logs/`;
- volumes do PostgreSQL: volume local gerenciado pelo Docker.

Todos esses locais são excluídos do Git e do contexto de build do Docker.

## Conteúdo proibido em logs

- texto integral de páginas;
- CPF, e-mail ou telefone;
- conteúdo integral de prompts ou respostas futuras;
- dados bancários;
- segredos e credenciais.

## Processamento externo

Está bloqueado na Iteração I-001. A variável `EXTERNAL_PROCESSING_ENABLED` deve permanecer como `false`.

## Testes

Somente PDFs sintéticos ou públicos poderão ser usados como fixtures. PDFs reais do piloto não entram no repositório nem na CI.

## Exclusão local

Para remover os dados de desenvolvimento:

```bash
docker compose down -v
rm -rf data/private/* logs/*
```

Preserve os arquivos `.gitkeep` quando necessário.
