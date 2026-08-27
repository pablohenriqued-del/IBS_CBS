# FiscalCore Motor — PRD

## Problem statement (original, em pt-BR)
Construir uma API FastAPI ("fiscalcore-motor") que calcule IBS e CBS de operações
fiscais brasileiras de forma **determinística e auditável**. Princípios inegociáveis:

- Usar `Decimal`, nunca `float`.
- Base "por fora": o imposto não entra na própria base nem um na base do outro.
- Imposto Seletivo **entra** na base de IBS/CBS.
- Regras são **dado versionado**: resolver ruleset pela `dataOperacao`.
- Testes automatizados contra os casos-ouro; não simplificar a lógica fiscal.
- MVP em MongoDB (append-only); PostgreSQL na virada de produção AWS.

## User personas
- Engenheiros integrando ERPs/emissores DF-e com a Reforma Tributária 2026.
- Contadores validando tributação em cenários "carga hoje vs. carga nova".
- Auditores fiscais: trilha reproduzível bit-a-bit com verificação de integridade.

## Core requirements (estáticos)
- `POST /api/v1/calcular` — contrato exato definido em `api-calcular-ibs-cbs.md`.
- Base "por fora"; IS entra na base; UF+Município separados; memória de cálculo por item.
- Rulesets versionados com `id`, `hash` SHA-256, vigência; resolvidos por `dataOperacao`.
- Auditoria append-only por cálculo + trilha ledger com hash encadeado por evento.
- Nunca "adivinhar" alíquotas: `cClassTrib` desconhecido → HTTP 422 explícito.
- Todos os valores monetários em `Decimal`, arredondamento `ROUND_HALF_UP` a 2 casas.

## What's been implemented

### Módulo 1 (2026-01-27) — Motor + API
- Motor de cálculo (`app/motor.py`) 100% em Decimal, base "por fora", IS na base,
  redução via `cClassTrib`, IBS partilhado UF/Município, memória passo a passo.
- `POST /api/v1/calcular`, `GET /api/v1/rulesets`, `GET /api/v1/health`.
- Rulesets seed: `ruleset:2026-fase-teste` (CBS 0,9% + IBS 0,1%) e
  `ruleset:2026-regime-pleno-v1` (CBS 8,8% + IBS-UF 12% + IBS-Mun 5,7%).
- 17 testes pytest — 3 casos-ouro do contrato batem número por número.
- Frontend playground editorial (Fraunces + IBM Plex + JetBrains) com dark/light
  theme switch, logotipo custom SVG, paleta bronze/âmbar.

### Módulo 2 (2026-01-27) — Ingestão + Auth + Ledger
- **Autenticação JWT + bcrypt** com 3 papéis (fiscal, auditoria, admin), brute-force
  lockout (5 tentativas → 15min), Bearer fallback para navegadores cross-origin.
  Seed admin idempotente (`admin@fiscalcore.local` / `FiscalCore@2026`).
- **Ingestão de NF-e**: `POST /api/v1/documentos/importar` com parser XML
  (`app/nfe_parser.py`) que aceita `nfeProc` ou `NFe` nu, extrai chave (44 dígitos),
  emitente/destinatário, itens, grupo IBSCBS e IS. Idempotência por chave (409).
- **Apuração por período**: `POST /api/v1/apuracao/periodo` que soma débitos
  (saídas) menos créditos (entradas), agrupado por competência.
- **Ledger de auditoria** com hash SHA-256 encadeado (`app/audit_ledger.py`):
  cada evento (login, register, import, calcular, apuracao) referencia o hash
  do anterior. `GET /api/v1/auditoria/verificar` recomputa a cadeia e aponta
  o `seq` de quebra caso haja adulteração.
- **Frontend** com react-router: `/login`, `/` (playground), `/documentos` (dropzone
  + toggle direção + tabela), `/apuracao` (débitos vs créditos + apurado),
  `/auditoria` (ledger + status íntegra/quebrada — auditoria/admin), `/usuarios`
  (form de criação — admin).
- 31 testes pytest verdes (17 golden + 14 do Módulo 2 cobrindo auth, ingestão,
  idempotência, apuração e integridade do ledger).

### Módulo 3 (2026-02-01) — LinkedIn Kit + SAP-sim
- **Página `/sobre`** (portfolio C-level) com assinatura Pablo Duarte, footer com
  link do LinkedIn, e conteúdo posicionando o motor como solução de engenharia.
  **Rota pública desde 2026-02-01** (sem `ProtectedRoute`) — pronta para virar
  link direto de portfólio no LinkedIn e assinatura de e-mail.
- **`LINKEDIN-POST.md`** — kit com 3 versões (executiva, técnica, híbrida) +
  storyboard de carrossel de 6 slides + estratégia de publicação em 2 semanas.
- **`LINKEDIN-POST-SHORT.md`** — versão curta (~155 palavras) mobile-first,
  tom C-level, sem emojis, com CTA "comenta 'FiscalCore' que envio o link do repo".
  Agendada para publicar hoje 00h50 (nicho de baixa competição / alto sinal).
- **Carrossel PDF (`/app/FiscalCore-LinkedIn-Carousel.pdf`)** — 6 slides
  1080x1080 gerados via Playwright headless a partir das páginas reais.
- **SAP-sim (`POST /api/v1/sap/pricing`)**:
  - Aceita payload no formato KOMV (VBELN, KPOSN, MATNR, KBETR, KWERT...)
  - Devolve tabela KOMV com condition types `Z-namespace`: **ZCBS**, **ZIBU**,
    **ZIBM**, **ZISE** — nos STUNR corretos do pricing schema `ZFISC01`.
  - `GET /api/v1/sap/exemplo` — payload pré-montado.
  - Frontend: botão "Simular chamada S/4HANA" no Playground abre modal com
    cabeçalho SAP, totais (net/tax/gross) e tabela KOMV completa.
- **IDOC INVOIC02 parser (`POST /api/v1/sap/idoc/parse`)**:
  - Parser XML tolerante para segmentos EDI_DC40, E1EDK01, E1EDP01, E1EDP19,
    E1EDP04 (multi-linha), E1EDS01 e extensão custom Z1FISC_CLASTRIB.
  - `GET /api/v1/sap/idoc/samples` + `GET /api/v1/sap/idoc/samples/{id}` para
    baixar amostras (uma convergente, uma com 2 divergências propositais).
- **Reconciliação SAP × FiscalCore (`POST /api/v1/sap/reconciliar`)**:
  - Recebe IDOC parseado + contexto fiscal → recalcula com o motor autoritativo.
  - Devolve tabela linha a linha por `(KPOSN, KSCHL)` com valor SAP, valor
    FiscalCore, delta em reais, status (`match|diverge|sap_faltante|fiscalcore_faltante`).
  - Veredicto final: **convergente** ou **divergente**, com tolerância configurável
    (padrão ±R$ 0,02).
  - Página `/sap` com dropzone IDOC + botões de amostras + painel veredicto +
    tabela detalhada por condition type.
- **Export CSV Apuração**: botão "Baixar CSV (Excel · UTF-8)" na tela `/apuracao`
  gera CSV com BOM, cabeçalho de metadados do período, blocos de débitos/créditos/
  apurado e linha detalhada por documento — pronto para o time contábil.
- Grava eventos auditáveis no ledger: `sap.pricing`, `sap.idoc.parsed`, `sap.reconciliar`.
- **Total: 80 testes pytest verdes** (70 anteriores + 10 novos: 3 parser puro,
  4 endpoint IDOC, 3 reconciliação com convergente + divergente + veredicto no ledger).

## Prioritized backlog

### P0 — próximas para produção
- Migração MongoDB → PostgreSQL (ACID para auditoria em produção).
- Rate limit por API key/tenant.
- Idempotency-Key para POST /calcular: hoje é registrada mas não desduplica.

### P1 — features do produto
- **Export PDF da apuração** (o CSV já foi entregue no Módulo 3; falta o PDF
  com layout de relatório mensal formatado).
- Password reset flow.
- Rate limit por API key/tenant (proteção do endpoint SAP quando exposto).
- Conciliação IBS/CBS × PIS/Cofins do mesmo período (compensação 2026).
- Adaptador DF-e (resposta → grupos IBS/CBS/IS de NF-e/NFC-e/NFS-e).

### P2 — enriquecimento fiscal
- Catálogo completo de `cClassTrib` (hoje 2 códigos).
- Isenções, alíquota zero (CST 400), imunidades, monofasia.
- Regimes especiais: Simples/MEI (créditos e limitações).
- Split-payment / cashback (destinatário PF consumidor final).

## Estrutura
```
/app
├── backend/
│   ├── app/
│   │   ├── motor.py          # Cálculo em Decimal
│   │   ├── rulesets.py       # Rulesets seed + resolução por data + hash SHA-256
│   │   ├── models.py         # Pydantic (contrato)
│   │   ├── auth.py           # JWT + bcrypt + roles + seed admin
│   │   ├── nfe_parser.py     # Parser XML NF-e
│   │   ├── audit_ledger.py   # Ledger append-only com hash encadeado
│   │   ├── servicos.py       # Ingestão + apuração
│   │   ├── routes.py         # POST /calcular
│   │   ├── routes_auth.py    # /api/auth/*
│   │   ├── routes_docs.py    # /api/v1/documentos/*, /apuracao/*, /auditoria/*
│   │   └── db.py             # Mongo (append-only rulesets + auditoria)
│   ├── server.py             # FastAPI + lifespan (seed admin + rulesets + indexes)
│   └── tests/                # 31 testes pytest
└── frontend/
    └── src/
        ├── api.js            # axios + Bearer fallback + error formatter
        ├── AuthContext.js    # provider + useAuth
        ├── App.js            # BrowserRouter + rotas protegidas
        └── components/
            ├── Shared.js     # Logo, Metric, useTheme, ThemeToggle
            ├── Header.js     # nav com role-based visibility + logout
            ├── Login.js      # login form + ProtectedRoute
            ├── PlaygroundPage.js
            ├── DocumentosPage.js
            ├── ApuracaoPage.js
            ├── AuditoriaPage.js
            └── UsuariosPage.js
```
