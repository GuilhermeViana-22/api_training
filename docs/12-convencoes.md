# 12 — Convenções

## Introdução

Este documento estabelece os padrões de código, nomenclatura, testes, commits, logging e tratamento de exceções para o projeto Smart Training. Toda contribuição deve seguir estas convenções.

## Índice

- [Python e FastAPI](#python-e-fastapi)
- [Nomenclatura](#nomenclatura)
- [Estrutura de arquivos](#estrutura-de-arquivos)
- [Schemas Pydantic](#schemas-pydantic)
- [SQLAlchemy models](#sqlalchemy-models)
- [Testes](#testes)
- [Git e commits](#git-e-commits)
- [Logging](#logging)
- [Tratamento de exceções](#tratamento-de-exceções)
- [Segurança](#segurança)
- [Code review checklist](#code-review-checklist)
- [Documentos relacionados](#documentos-relacionados)

---

## Python e FastAPI

### Estilo

| Padrão | Convenção |
|--------|-----------|
| Style guide | PEP 8 |
| Formatter | Ruff format |
| Linter | Ruff check |
| Type hints | Obrigatório em funções públicas |
| Docstrings | Google style em services e repositories |
| Imports | isort via Ruff; stdlib → third-party → local |
| Async | Routers async; services/repositories sync (SQLAlchemy sync) |

### Exemplo

```python
def create_student(
    db: Session,
    admin_id: str,
    data: StudentCreate,
) -> StudentResponse:
    """Cria um novo aluno vinculado ao admin.

    Args:
        db: Sessão SQLAlchemy.
        admin_id: UUID do administrador.
        data: Dados de criação do aluno.

    Returns:
        StudentResponse com dados do aluno criado.

    Raises:
        BusinessError: Se email já cadastrado.
    """
    ...
```

### Configuração Ruff (`pyproject.toml`)

```toml
[tool.ruff]
target-version = "py313"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP", "B", "SIM"]

[tool.ruff.format]
quote-style = "double"
```

---

## Nomenclatura

| Contexto | Convenção | Exemplo |
|----------|-----------|---------|
| Tabelas MySQL | snake_case plural | `student_profiles` |
| Colunas MySQL | snake_case | `check_in_date` |
| SQLAlchemy models | PascalCase singular | `StudentProfile` |
| Pydantic schemas | PascalCase | `StudentCreate`, `StudentResponse` |
| Services | snake_case + `_service` | `student_service.py` |
| Repositories | snake_case + `_repository` | `student_repository.py` |
| Routers | snake_case plural | `students.py` |
| URLs API | kebab-case ou snake | `/students/{id}/progress/photos` |
| Variáveis | snake_case | `admin_id` |
| Constantes | UPPER_SNAKE_CASE | `MAX_UPLOAD_SIZE_MB` |
| Enums | PascalCase class, lowercase values | `TrainingStatus.active` |
| Arquivos | snake_case | `training_service.py` |
| Testes | `test_` + módulo | `test_student_service.py` |

---

## Estrutura de arquivos

### Um router por recurso

```
app/api/v1/routers/students.py    # CRUD alunos
app/api/v1/routers/me.py          # Endpoints do aluno (/me/*)
```

### Um service por domínio

```
app/services/student_service.py
app/services/training_service.py
```

### Um model por tabela

```
app/models/student_profile.py
app/models/training.py
```

---

## Schemas Pydantic

### Padrão Create / Update / Response

```python
class StudentCreate(BaseModel):
    """Request body para criação."""
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str

class StudentUpdate(BaseModel):
    """Request body para atualização (campos opcionais)."""
    full_name: str | None = None
    phone: str | None = None
    weight_kg: float | None = None

class StudentResponse(BaseModel):
    """Response serializado."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    full_name: str
    is_active: bool
    created_at: datetime
```

### Regras

- `Create`: campos obrigatórios para criação
- `Update`: todos os campos `Optional` (PATCH semantics)
- `Response`: `from_attributes=True` para ORM
- Validações de negócio simples no schema; complexas no service

---

## SQLAlchemy models

```python
from sqlalchemy import CHAR, String, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base

class StudentProfile(Base):
    __tablename__ = "student_profiles"

    user_id: Mapped[str] = mapped_column(CHAR(36), ForeignKey("users.id"), primary_key=True)
    admin_id: Mapped[str] = mapped_column(CHAR(36), ForeignKey("users.id"), nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(6), nullable=True)

    user: Mapped["User"] = relationship(back_populates="student_profile")
    trainings: Mapped[list["Training"]] = relationship(back_populates="student")
```

### Regras

- SQLAlchemy 2.0 style (`Mapped`, `mapped_column`)
- UUIDs como `CHAR(36)`
- Datetimes como `DateTime(6)`
- Relationships com `back_populates`
- Não usar `lazy="dynamic"` (deprecated pattern)

---

## Testes

### Stack

| Ferramenta | Uso |
|------------|-----|
| pytest | Test runner |
| pytest-asyncio | Testes async (routers) |
| httpx | AsyncClient para testes de API |
| factory-boy ou fixtures | Dados de teste |
| pytest-cov | Cobertura |

### Estrutura

```
tests/
├── conftest.py              # Fixtures: db, client, admin_token, student_token
├── unit/
│   ├── test_auth_service.py
│   ├── test_student_service.py
│   └── test_training_service.py
└── integration/
    ├── test_auth_api.py
    ├── test_students_api.py
    └── test_trainings_api.py
```

### Fixture base

```python
# tests/conftest.py
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database.session import get_db

@pytest.fixture
async def client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()

@pytest.fixture
async def admin_token(client):
    response = await client.post("/api/v1/auth/login", json={
        "email": "admin@test.com",
        "password": "Admin123!",
    })
    return response.json()["access_token"]
```

### Exemplo teste unitário

```python
def test_create_student_duplicate_email(db, admin_user):
    student_service.create(db, admin_id=admin_user.id, data=valid_data)
    with pytest.raises(BusinessError) as exc:
        student_service.create(db, admin_id=admin_user.id, data=valid_data)
    assert exc.value.code == "DUPLICATE_EMAIL"
```

### Exemplo teste integração

```python
@pytest.mark.asyncio
async def test_list_students_as_admin(client, admin_token):
    response = await client.get(
        "/api/v1/students",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert "items" in response.json()
```

### Cobertura mínima

| Camada | Meta |
|--------|:----:|
| services | 80% |
| repositories | 70% |
| routers (integration) | 60% |
| **Total** | **75%** |

```bash
pytest --cov=app --cov-report=term-missing --cov-fail-under=75
```

---

## Git e commits

### Branches

| Prefixo | Uso | Exemplo |
|---------|-----|---------|
| `feature/` | Nova funcionalidade | `feature/training-crud` |
| `fix/` | Correção de bug | `fix/checkin-duplicate` |
| `refactor/` | Refatoração | `refactor/auth-service` |
| `docs/` | Documentação | `docs/api-endpoints` |
| `test/` | Testes | `test/student-service` |

### Conventional Commits

```
<type>(<scope>): <description>

[optional body]
```

| Type | Uso |
|------|-----|
| `feat` | Nova feature |
| `fix` | Bug fix |
| `docs` | Documentação |
| `refactor` | Refatoração |
| `test` | Testes |
| `chore` | Manutenção (deps, CI) |

Exemplos:

```
feat(auth): implement JWT login and refresh
feat(students): add CRUD endpoints for admin
fix(training): prevent duplicate active training per student
test(attendance): add check-in integration tests
docs: add API REST reference
```

### Pull Request

- Título segue Conventional Commits
- Descrição com: o que, por que, como testar
- Mínimo 1 review antes de merge
- CI deve passar (lint + tests)

---

## Logging

### Desenvolvimento

Formato legível:

```
2026-07-16 20:15:30 INFO [request_id=abc123] POST /api/v1/students 201 45ms
```

### Produção

JSON estruturado:

```json
{
  "timestamp": "2026-07-16T20:15:30.123Z",
  "level": "INFO",
  "request_id": "abc123",
  "method": "POST",
  "path": "/api/v1/students",
  "status_code": 201,
  "duration_ms": 45,
  "user_id": "uuid"
}
```

### Regras

- Nunca logar senhas, tokens ou dados sensíveis
- Usar `request_id` (middleware) para correlação
- Level INFO para requests; WARNING para 4xx; ERROR para 5xx
- DEBUG apenas em `APP_DEBUG=true`

```python
import logging
logger = logging.getLogger(__name__)

logger.info("Student created", extra={"student_id": student.id, "admin_id": admin_id})
```

---

## Tratamento de exceções

### Hierarquia

```
Exception
├── BusinessError          # Regras de negócio (400, 409)
├── NotFoundError          # Recurso não encontrado (404)
├── ForbiddenError         # Sem permissão (403)
└── UnauthorizedError      # Auth falhou (401)
```

### Handler centralizado

```python
@app.exception_handler(BusinessError)
async def business_error_handler(request: Request, exc: BusinessError):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details or {},
            }
        },
    )

@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Erro de validação nos campos enviados.",
                "details": exc.errors(),
            }
        },
    )
```

### Regras

- Services lançam `BusinessError`, nunca `HTTPException`
- Routers não capturam exceções de negócio (handlers globais)
- Mensagens de erro user-friendly em português
- `details` contém informação técnica para debug

---

## Segurança

| Prática | Implementação |
|---------|---------------|
| Senhas | bcrypt, nunca plaintext |
| JWT secret | Min 256 bits, env var |
| SQL injection | SQLAlchemy parameterized queries |
| File upload | MIME validation + magic bytes |
| CORS | Whitelist via `CORS_ORIGINS` |
| Rate limiting | Slowapi nos endpoints `/auth/*` (MVP) |
| HTTPS | Obrigatório em produção (reverse proxy) |
| Headers | `X-Request-ID`, sem expor stack traces |

---

## Code review checklist

- [ ] Type hints em funções públicas
- [ ] Testes para lógica de negócio nova
- [ ] Regras RN-* respeitadas
- [ ] Isolamento por `admin_id` / `student_id`
- [ ] Schemas Pydantic para input/output
- [ ] Sem lógica de negócio em routers ou repositories
- [ ] Migrations Alembic incluídas (se schema changed)
- [ ] Sem secrets hardcoded
- [ ] Documentação Swagger atualizada (docstrings routers)
- [ ] Conventional commit message

---

## Documentos relacionados

- [09-estrutura-do-projeto.md](09-estrutura-do-projeto.md) — Organização de pastas
- [02-regras-de-negocio.md](02-regras-de-negocio.md) — Regras a validar nos testes
- [05-api-rest.md](05-api-rest.md) — Contratos da API
- [08-docker.md](08-docker.md) — Ambiente de execução
