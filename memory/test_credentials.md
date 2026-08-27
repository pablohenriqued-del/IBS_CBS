# FiscalCore — Credenciais de teste

## Admin (seed automático via .env)
- **E-mail:** admin@fiscalcore.local
- **Senha:** FiscalCore@2026
- **Papel:** admin
- **Origem:** semeado no startup a partir de `ADMIN_EMAIL` / `ADMIN_PASSWORD` (idempotente)

## Endpoints de autenticação
- `POST /api/auth/login`  · body: `{email, password}` → retorna user + `access_token`
- `POST /api/auth/logout` · (autenticado)
- `GET  /api/auth/me`     · (autenticado)
- `POST /api/auth/register` · (admin) body: `{email, password, name, role}` (role ∈ fiscal|auditoria|admin)
- `GET  /api/auth/users`   · (admin)

## Papéis e permissões
- **fiscal**: pode calcular, importar documentos, ver apuração
- **auditoria**: read-only + acesso ao ledger de auditoria e verificação
- **admin**: tudo, incluindo criação de usuários

## Como usar em testes
Nos testes via TestClient, cookies `secure=True + samesite=none` são dropados. O login
retorna também `access_token` no body — os testes usam `Authorization: Bearer <token>`.
