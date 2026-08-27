# FiscalCore Motor — PRD

## Problem statement (original, em pt-BR)
Construir uma API FastAPI ("fiscalcore-motor") que calcule IBS e CBS de operações
fiscais brasileiras de forma **determinística e auditável**. Princípios inegociáveis:

- Usar `Decimal`, nunca `float`.
- Base "por fora": o imposto não entra na própria base nem um na base do outro.
- Imposto Seletivo **entra** na base de IBS/CBS.
- Regras são **dado versionado**: resolver ruleset pela `dataOperacao` (nunca "o mais recente").
- Testes automatizados contra os casos-ouro; não simplificar a lógica fiscal.
- MVP em MongoDB (append-only para rulesets + auditoria); PostgreSQL entra na virada de produção.

## User personas
- Engenheiros integrando ERPs/emissores DF-e com a Reforma Tributária 2026.
- Contadores validando tributação em cenários "carga hoje vs. carga nova".
- Auditores fiscais (fiscalização): trilha reproduzível bit-a-bit.

## Core requirements (estáticos)
- `POST /api/v1/calcular` — contrato exato definido em `api-calcular-ibs-cbs.md`.
- Base "por fora"; IS entra na base; UF+Município separados; memória de cálculo por item.
- Rulesets versionados com `id`, `hash` SHA-256, vigência; resolvidos por `dataOperacao`.
- Auditoria append-only por cálculo (input + rulesetId + hash + output).
- Nunca "adivinhar" alíquotas: `cClassTrib` desconhecido → HTTP 422 explícito.
- Todos os valores monetários em `Decimal`, arredondamento `ROUND_HALF_UP` a 2 casas.

## What's been implemented (2026-01-27)
- **Motor de cálculo** (`app/motor.py`) 100% em Decimal, com base "por fora", IS na base,
  redução via `cClassTrib`, IBS partilhado UF/Município, memória de cálculo passo a passo.
- **Endpoints**:
  - `POST /api/v1/calcular` — cálculo principal (retorna `auditoriaId`).
  - `GET  /api/v1/rulesets` — lista rulesets carregados.
  - `GET  /api/v1/auditoria/{id}` — recupera snapshot completo (reproduzível).
  - `GET  /api/v1/health`.
- **Rulesets seed**:
  - `ruleset:2026-fase-teste` (vig. 2026-01-01 → 2026-06-30) — CBS 0,9% + IBS-UF 0,1%.
  - `ruleset:2026-regime-pleno-v1` (vig. 2026-07-01 →) — CBS 8,8% + IBS-UF 12% + IBS-Mun 5,7%.
- **Persistência**: MongoDB collections `rulesets` (append-only, dedupe por (id, hash))
  e `auditoria` (append-only puro).
- **Testes automatizados**: `pytest` — **17/17 verdes**, incluindo os **3 casos-ouro** do contrato
  batendo número por número (Cadeira 1000/265; Medicamento 500/53; Bebida 200 com IS 20/78.30;
  totais: base 1720, CBS 124.96, IBS 251.34, tributosTotais 376.30).
- **Playground web** em `/` — split-pane estilo Stripe API docs, dark mode ("Tactical Minimalism"),
  formulário pré-carregado com os 3 itens golden, visualização "visual" ou "json bruto".

## Prioritized backlog

### P0 — próximas para produção
- Autenticação por API key por tenant (hoje MVP está aberto; TODO no `server.py`).
- Migração MongoDB → PostgreSQL (ACID exigido para auditoria em produção).
- Idempotency-Key: hoje é registrada mas não desduplica; implementar cache de resposta por chave.

### P1 — features do produto
- `POST /api/v1/simular` (cenário "carga hoje vs. carga nova"; contrato §9).
- Adaptador de emissão DF-e (mapeamento response → grupos IBS/CBS/IS de NF-e/NFC-e/NFS-e).
- Rate limit e cobrança por API key.
- Endpoints administrativos: upload de novo ruleset, comparação entre revisões.

### P2 — enriquecimento fiscal
- Catálogo completo de `cClassTrib` (hoje apenas 2 códigos: 000001 e 200052).
- Isenções, alíquota zero (CST 400), imunidades, monofasia.
- Regimes especiais: Simples/MEI (créditos e limitações).
- Split-payment / cashback (destinatário PF consumidor final).

## Estrutura
```
/app
├── backend/
│   ├── app/
│   │   ├── motor.py       # Cálculo em Decimal (coração)
│   │   ├── rulesets.py    # Rulesets seed + resolução por data + hash SHA-256
│   │   ├── models.py      # Pydantic (contrato)
│   │   ├── routes.py      # Endpoints
│   │   └── db.py          # Mongo (append-only)
│   ├── server.py          # FastAPI entrypoint + lifespan (seed)
│   └── tests/             # pytest — 17 testes, incl. 3 casos-ouro
└── frontend/              # React playground (dark, split-pane)
```
