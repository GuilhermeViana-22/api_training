# 04 — Autenticação

## Introdução

O Smart Training utiliza autenticação baseada em **JWT Bearer Token** com par access/refresh token. Este documento descreve o fluxo completo, estrutura dos tokens, implementação de segurança e integração com FastAPI.

## Índice

- [Visão geral](#visão-geral)
- [Fluxo de autenticação](#fluxo-de-autenticação)
- [Estrutura JWT](#estrutura-jwt)
- [Configuração](#configuração)
- [Hash de senhas](#hash-de-senhas)
- [Implementação FastAPI](#implementação-fastapi)
- [Endpoints de auth](#endpoints-de-auth)
- [Revogação de tokens](#revogação-de-tokens)
- [Tratamento de erros](#tratamento-de-erros)
- [Exemplos práticos](#exemplos-práticos)
- [Documentos relacionados](#documentos-relacionados)

---

## Visão geral

| Aspecto | Decisão |
|---------|---------|
| Esquema | Bearer Token (RFC 6750) |
| Algoritmo | HS256 |
| Access token TTL | 15 minutos |
| Refresh token TTL | 7 dias |
| Armazenamento refresh | Banco (`refresh_tokens`) com hash SHA-256 |
| Hash senha | bcrypt via passlib |
| Header | `Authorization: Bearer <access_token>` |

---

## Fluxo de autenticação

```mermaid
sequenceDiagram
    participant C as Cliente
    participant API as FastAPI
    participant DB as MySQL

    C->>API: POST /auth/login {email, password}
    API->>DB: Busca user + verifica bcrypt
    DB-->>API: User válido
    API->>API: Gera access_token (15min)
    API->>API: Gera refresh_token (7d)
    API->>DB: Persiste hash refresh_token
    API-->>C: {access_token, refresh_token, token_type, expires_in}

    Note over C,API: Requisições autenticadas
    C->>API: GET /students (Authorization: Bearer access_token)
    API->>API: Valida JWT + role admin
    API-->>C: 200 OK

    Note over C,API: Access token expirado
    C->>API: POST /auth/refresh {refresh_token}
    API->>DB: Valida hash + expires_at + revoked_at
    API->>API: Gera novo access_token
    API-->>C: {access_token, expires_in}

    Note over C,API: Logout
    C->>API: POST /auth/logout {refresh_token}
    API->>DB: SET revoked_at = NOW()
    API-->>C: 204 No Content
```

---

## Estrutura JWT

### Access Token Payload

```json
{
  "sub": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "role": "admin",
  "admin_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "type": "access",
  "exp": 1720000000,
  "iat": 1719999100
}
```

| Claim | Descrição |
|-------|-----------|
| `sub` | UUID do usuário (`users.id`) |
| `role` | `admin` ou `student` |
| `admin_id` | Para admin: igual a `sub`. Para student: UUID do admin vinculado |
| `type` | Sempre `access` |
| `exp` | Timestamp Unix de expiração |
| `iat` | Timestamp Unix de emissão |

### Refresh Token Payload

```json
{
  "sub": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "type": "refresh",
  "jti": "f9e8d7c6-b5a4-3210-fedc-ba9876543210",
  "exp": 1720604800,
  "iat": 1719999100
}
```

| Claim | Descrição |
|-------|-----------|
| `jti` | UUID único do refresh token (PK em `refresh_tokens`) |
| `type` | Sempre `refresh` |

---

## Configuração

Variáveis em `.env`:

```env
JWT_SECRET_KEY=your-256-bit-secret-key-change-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
```

Classe `Settings` (Pydantic):

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    class Config:
        env_file = ".env"
```

---

## Hash de senhas

```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)
```

Requisitos de senha (validados no schema Pydantic):
- Mínimo 8 caracteres
- Ao menos 1 letra e 1 número

---

## Implementação FastAPI

### Dependencies

```python
# app/auth/dependencies.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    token = credentials.credentials
    payload = decode_access_token(token)
    if payload is None or payload.get("type") != "access":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail={
            "error": {"code": "TOKEN_INVALID", "message": "Token inválido."}
        })
    user = user_repo.get_by_id(db, payload["sub"])
    if not user or not user.is_active or user.deleted_at:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail={
            "error": {"code": "USER_INACTIVE", "message": "Usuário inativo."}
        })
    return user

def require_role(*roles: str):
    async def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail={
                "error": {"code": "FORBIDDEN", "message": "Permissão negada."}
            })
        return user
    return checker

RequireAdmin = Depends(require_role("admin"))
RequireStudent = Depends(require_role("student"))
```

### Uso em routers

```python
@router.get("/students")
async def list_students(
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    return student_service.list_by_admin(db, admin_id=user.id)
```

---

## Endpoints de auth

Resumo — detalhes completos em [05-api-rest.md](05-api-rest.md#autenticação).

| Método | Rota | Auth | Descrição |
|--------|------|:----:|-----------|
| POST | `/api/v1/auth/login` | Não | Login |
| POST | `/api/v1/auth/refresh` | Não | Renovar access token |
| POST | `/api/v1/auth/logout` | Sim | Revogar refresh token |
| GET | `/api/v1/auth/me` | Sim | Perfil autenticado |

---

## Revogação de tokens

1. No login, refresh token é persistido: `token_hash = SHA256(token)`, `expires_at`, `jti`
2. No refresh, verifica: token existe, não revogado, não expirado
3. No logout, `revoked_at = NOW()` no registro correspondente
4. Tokens revogados retornam `401 TOKEN_REVOKED`

Rotação opcional (recomendada em produção): ao fazer refresh, revogar token anterior e emitir novo par.

---

## Tratamento de erros

| Situação | HTTP | Code |
|----------|:----:|------|
| Credenciais inválidas | 401 | `INVALID_CREDENTIALS` |
| Token ausente | 401 | `NOT_AUTHENTICATED` |
| Token expirado | 401 | `TOKEN_EXPIRED` |
| Token inválido/malformado | 401 | `TOKEN_INVALID` |
| Refresh revogado | 401 | `TOKEN_REVOKED` |
| Role insuficiente | 403 | `FORBIDDEN` |
| Usuário inativo | 401 | `USER_INACTIVE` |

Formato padrão:

```json
{
  "error": {
    "code": "TOKEN_EXPIRED",
    "message": "Token expirado. Utilize o refresh token.",
    "details": {}
  }
}
```

---

## Exemplos práticos

### Login

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@smarttraining.local", "password": "Admin123!"}'
```

Resposta:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 900
}
```

### Requisição autenticada

```bash
curl http://localhost:8000/api/v1/students \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..."
```

### Refresh

```bash
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "eyJhbGciOiJIUzI1NiIs..."}'
```

### Me

```bash
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..."
```

Resposta (admin):

```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "email": "admin@smarttraining.local",
  "role": "admin",
  "profile": {
    "full_name": "João Personal",
    "cref": "012345-G/SP",
    "phone": "+5511987654321"
  }
}
```

---

## Documentos relacionados

- [02-regras-de-negocio.md](02-regras-de-negocio.md) — RBAC e regras de usuário
- [03-modelagem-banco.md](03-modelagem-banco.md) — Tabelas `users` e `refresh_tokens`
- [05-api-rest.md](05-api-rest.md) — Especificação completa dos endpoints
- [12-convencoes.md](12-convencoes.md) — Padrões de segurança
