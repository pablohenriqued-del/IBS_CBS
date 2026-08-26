[README.md](https://github.com/user-attachments/files/31490983/README.md)
# FiscalCore · Infraestrutura (AWS CDK)

Esqueleto de produção do **motor de apuração IBS/CBS** — serverless na AWS,
com CI/CD via GitHub Actions + OIDC e segurança/LGPD by design.
Região padrão: **`sa-east-1` (São Paulo)**.

> Companion do documento de arquitetura `FiscalCore-Arquitetura-Roadmap-Seguranca.md`
> e do pacote de build para o Emergent. Para migrar o MVP do Emergent para cá,
> veja [`docs/emergent-to-aws.md`](docs/emergent-to-aws.md).

## Arquitetura (stacks)

| Stack | Conteúdo |
|---|---|
| `Network` | VPC privada, subnets isoladas, VPC Endpoints (S3, DynamoDB, Secrets, KMS, SQS, SFN) |
| `Security` | KMS CMK com rotação (criptografia de dados fiscais/LGPD) |
| `Data` | DynamoDB (documentos, regras), Aurora Serverless v2, S3 (landing + lake), SG de app |
| `Ingestion` | API Gateway HTTP, SQS + DLQ, Lambda de recepção |
| `Calculation` | Step Functions (Validação→Base→Débito→Crédito→Apuração), Lambdas, deploy canário |
| `Consumption` | API REST, Cognito (papéis + MFA), WAF, Lambda de consulta |
| `Observability` | Dashboard + alarmes (DLQ, falhas de apuração) |

## Estrutura

```
fiscalcore-infra/
├── bin/fiscalcore.ts          # entrypoint: instancia os stacks por ambiente
├── lib/                       # um arquivo por stack + config.ts
├── src/                       # handlers Lambda (esqueleto) + lógica pura de cálculo
│   ├── shared/calculo.ts      # cálculo "por fora", vigência, apuração (testado)
│   ├── ingestion/ validation/ calculation/ consumption/
├── test/                      # testes unitários do motor
├── .github/workflows/         # ci.yml (gates) e cd.yml (deploy OIDC)
└── docs/emergent-to-aws.md    # playbook de migração
```

## Pré-requisitos

- Node.js 20+, npm
- AWS CDK v2 (`npx cdk`), conta(s) AWS (idealmente uma por ambiente)
- `cdk bootstrap` em cada conta/região antes do primeiro deploy

## Comandos

```bash
npm ci
npm run typecheck        # tsc --noEmit
npm test                 # testes do motor de cálculo
npm run synth            # cdk synth (env=dev por padrão)
CDK_NAG=1 npm run synth  # revisão de segurança (cdk-nag / AWS Solutions)

# deploy por ambiente
npx cdk deploy --all -c env=dev
npx cdk deploy --all -c env=homolog
npx cdk deploy --all -c env=prod
```

Ambiente selecionado por `-c env=<dev|homolog|prod>` ou `CDK_ENV`.
Contas por ambiente via `CDK_DEV_ACCOUNT`, `CDK_HML_ACCOUNT`, `CDK_PRD_ACCOUNT`.

## CI/CD (GitHub Actions + OIDC)

**CI** (`ci.yml`, em cada PR): typecheck, testes, **SAST** (CodeQL), **SCA**
(`npm audit` + Trivy), **secret scanning** (gitleaks) e **IaC scan** (Checkov sobre o synth).

**CD** (`cd.yml`, em `main`): deploy DEV → integração → HOMOLOG + **DAST** (OWASP ZAP)
→ **aprovação manual** (GitHub Environment `prod` com *required reviewers*) → PROD canário.

### Configurar o OIDC (sem chaves de longa duração)

1. Crie um **IAM OIDC provider** para `token.actions.githubusercontent.com` em cada conta.
2. Crie uma **role de deploy** com trust policy restrita ao seu repositório/branch e
   permissões de deploy (CloudFormation/CDK).
3. Nos **Environments** do GitHub (`dev`, `homolog`, `prod`), defina os secrets:
   - `AWS_DEPLOY_ROLE_ARN` — ARN da role assumida via OIDC
   - `HOMOLOG_API_URL` — alvo do DAST (apenas homolog)
4. No Environment `prod`, habilite **Required reviewers** para criar o gate de aprovação.

## Banco de dados (Aurora)

O schema do livro fiscal está em [`db/migrations/0001_init.sql`](db/migrations/0001_init.sql):
tabelas `documento`, `item_documento`, `apuracao`, `regra_vigencia` e a trilha
`auditoria_log`. Destaques:

- **Trilha de auditoria imutável**: um *trigger* preenche `hash_atual = SHA-256(hash_anterior || payload)` (ledger encadeado) e outro **bloqueia UPDATE/DELETE**. A função `verificar_integridade_auditoria()` aponta qualquer elo quebrado.
- **Regra de 2026 já semeada**: IBS 0,1% / CBS 0,9%.

Aplicar a migração (via bastion/psql com o segredo do Secrets Manager, ou uma Lambda de migração):

```bash
psql "$FISCALCORE_DB_URL" -f db/migrations/0001_init.sql
```

## Fluxo ponta a ponta (implementado)

```
POST /documentos ──▶ IngestFn ──▶ S3 (landing) + DynamoDB (idempotente) ──▶ SQS
        │
        ▼
   DispatchFn ──▶ StartExecution ──▶ Step Functions:
        Validate (lê XML no S3, parseia NF-e)
     ─▶ Base (depura a base — R1–R3)
     ─▶ Debito (lê RulesTable, calcula "por fora")
     ─▶ Credito (não cumulatividade)
     ─▶ Apuracao (grava documento/itens/apuração no Aurora + auditoria imutável)

GET /apuracao?periodo=AAAA-MM ──▶ QueryFn ──▶ Aurora
```

Os handlers estão em `src/**` usando AWS SDK v3; a lógica pura de cálculo (testada)
vive em `src/shared/calculo.ts`.

## Segurança

- Criptografia em repouso (KMS CMK) em Aurora, DynamoDB, S3, filas e logs; TLS em trânsito.
- Rede privada (subnets isoladas + PrivateLink); WAF na API de consulta.
- Cognito com MFA e papéis (fiscal/auditoria/admin).
- `cdk-nag` disponível para auditoria de configuração (`CDK_NAG=1`).
- Trilha de auditoria imutável (append-only + hash encadeado) já no schema.
- **Pontos que restam para produção** (marcados como `TODO(prod)` no código):
  validação de NCM na TIPI, apropriação de crédito por item nas entradas,
  derivação de saída/entrada por `tpNF`, e fixar o CA bundle da RDS no TLS.

## Status

- ✅ `tsc --noEmit` limpo
- ✅ 8 testes passando (motor de cálculo + parser de NF-e)
- ✅ `cdk synth` dos 7 stacks (dev e homolog), com bundling esbuild dos handlers
- ✅ schema SQL validado (parser Postgres) · runtime `nodejs22.x`
