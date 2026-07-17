# 05 — API REST

## Introdução

Referência completa da API REST do Smart Training. Base URL: `http://localhost:8000/api/v1`. Documentação interativa disponível em `/docs` (Swagger) e `/redoc`.

## Índice

- [Convenções gerais](#convenções-gerais)
- [Autenticação](#autenticação)
- [Alunos (Admin)](#alunos-admin)
- [Exercícios (Admin)](#exercícios-admin)
- [Treinos (Admin)](#treinos-admin)
- [Dias e exercícios do treino (Admin)](#dias-e-exercícios-do-treino-admin)
- [Acompanhamento (Admin)](#acompanhamento-admin)
- [Relatórios (Admin)](#relatórios-admin)
- [Área do aluno](#área-do-aluno)
- [Uploads](#uploads)
- [Health check](#health-check)
- [Documentos relacionados](#documentos-relacionados)

---

## Convenções gerais

### Headers

| Header | Valor | Obrigatório |
|--------|-------|:-----------:|
| `Content-Type` | `application/json` | Em POST/PUT/PATCH com body |
| `Authorization` | `Bearer <access_token>` | Rotas autenticadas |
| `Accept` | `application/json` | Recomendado |

### Paginação

Query params padrão em listagens:

| Param | Tipo | Default | Descrição |
|-------|------|---------|-----------|
| `page` | int | 1 | Página (1-based) |
| `limit` | int | 20 | Itens por página (max 100) |
| `sort_by` | string | `created_at` | Campo de ordenação |
| `sort_order` | string | `desc` | `asc` ou `desc` |

Resposta paginada:

```json
{
  "items": [],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 45,
    "total_pages": 3
  }
}
```

### Envelope de erro

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Erro de validação nos campos enviados.",
    "details": {
      "email": ["Email inválido."]
    }
  }
}
```

### Códigos HTTP utilizados

| Código | Uso |
|:------:|-----|
| 200 | Sucesso (GET, PUT, PATCH) |
| 201 | Recurso criado |
| 204 | Sucesso sem body (DELETE, logout) |
| 400 | Regra de negócio violada |
| 401 | Não autenticado |
| 403 | Sem permissão |
| 404 | Recurso não encontrado |
| 409 | Conflito (duplicata, recurso em uso) |
| 422 | Validação Pydantic |
| 500 | Erro interno |

---

## Autenticação

### POST /auth/login

**Objetivo:** Autenticar usuário e obter tokens.

**Auth:** Não

**Body:**

```json
{
  "email": "admin@smarttraining.local",
  "password": "Admin123!"
}
```

**Resposta 200:**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 900
}
```

**Erros:** 401 `INVALID_CREDENTIALS`, 401 `USER_INACTIVE`

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@smarttraining.local","password":"Admin123!"}'
```

---

### POST /auth/refresh

**Objetivo:** Renovar access token.

**Auth:** Não

**Body:**

```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

**Resposta 200:**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 900
}
```

**Erros:** 401 `TOKEN_EXPIRED`, 401 `TOKEN_REVOKED`, 401 `TOKEN_INVALID`

---

### POST /auth/logout

**Objetivo:** Revogar refresh token.

**Auth:** Bearer (access token)

**Body:**

```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

**Resposta:** 204 No Content

---

### GET /auth/me

**Objetivo:** Retornar perfil do usuário autenticado.

**Auth:** Bearer

**Resposta 200 (admin):**

```json
{
  "id": "uuid",
  "email": "admin@smarttraining.local",
  "role": "admin",
  "is_active": true,
  "profile": {
    "full_name": "João Personal",
    "cref": "012345-G/SP",
    "phone": "+5511987654321",
    "bio": null
  },
  "created_at": "2026-01-15T10:00:00Z"
}
```

**Resposta 200 (student):**

```json
{
  "id": "uuid",
  "email": "maria@email.com",
  "role": "student",
  "is_active": true,
  "profile": {
    "full_name": "Maria Silva",
    "phone": "+5511999999999",
    "birth_date": "1990-05-15",
    "height_cm": 165.0,
    "weight_kg": 62.5,
    "goal": "Hipertrofia"
  },
  "created_at": "2026-02-01T14:30:00Z"
}
```

---

## Alunos (Admin)

Todas requerem `Authorization: Bearer` + role `admin`.

### GET /students

**Objetivo:** Listar alunos do admin autenticado.

**Query params:**

| Param | Tipo | Descrição |
|-------|------|-----------|
| `page`, `limit` | int | Paginação |
| `search` | string | Busca por nome ou email |
| `is_active` | bool | Filtrar ativos/inativos |

**Resposta 200:**

```json
{
  "items": [
    {
      "id": "uuid",
      "email": "maria@email.com",
      "full_name": "Maria Silva",
      "phone": "+5511999999999",
      "is_active": true,
      "active_training": {
        "id": "uuid",
        "title": "Hipertrofia Q1",
        "start_date": "2026-01-01",
        "end_date": "2026-03-31",
        "status": "active"
      },
      "created_at": "2026-02-01T14:30:00Z"
    }
  ],
  "pagination": { "page": 1, "limit": 20, "total": 1, "total_pages": 1 }
}
```

---

### POST /students

**Objetivo:** Cadastrar novo aluno.

**Body:**

```json
{
  "email": "maria@email.com",
  "password": "Senha123!",
  "full_name": "Maria Silva",
  "phone": "+5511999999999",
  "birth_date": "1990-05-15",
  "height_cm": 165,
  "weight_kg": 62.5,
  "goal": "Hipertrofia e condicionamento",
  "notes": "Iniciante, sem restrições"
}
```

**Resposta 201:** Objeto aluno completo (mesmo schema do GET /students/{id})

**Erros:** 409 `DUPLICATE_EMAIL`, 422 `VALIDATION_ERROR`

---

### GET /students/{id}

**Objetivo:** Detalhe de um aluno.

**Resposta 200:**

```json
{
  "id": "uuid",
  "email": "maria@email.com",
  "full_name": "Maria Silva",
  "phone": "+5511999999999",
  "birth_date": "1990-05-15",
  "height_cm": 165.0,
  "weight_kg": 62.5,
  "goal": "Hipertrofia",
  "notes": "Iniciante",
  "is_active": true,
  "trainings_count": 2,
  "last_check_in": "2026-07-15",
  "created_at": "2026-02-01T14:30:00Z"
}
```

**Erros:** 404 `NOT_FOUND`, 403 `FORBIDDEN`

---

### PUT /students/{id}

**Objetivo:** Atualizar dados do aluno.

**Body:** Campos parciais permitidos (exceto email se regra futura restringir).

```json
{
  "full_name": "Maria Silva Santos",
  "weight_kg": 61.0,
  "goal": "Definição muscular",
  "notes": "Evolutionando bem"
}
```

**Resposta 200:** Aluno atualizado

---

### DELETE /students/{id}

**Objetivo:** Soft delete do aluno.

**Resposta:** 204 No Content

**Efeito:** `users.deleted_at` e `student_profiles.deleted_at` preenchidos; login bloqueado.

---

### PATCH /students/{id}/status

**Objetivo:** Ativar/desativar aluno.

**Body:**

```json
{
  "is_active": false
}
```

**Resposta 200:** Aluno com status atualizado

---

## Exercícios (Admin)

### GET /exercises

**Objetivo:** Listar catálogo de exercícios do admin.

**Query params:** `page`, `limit`, `search`, `muscle_group`

**Resposta 200:**

```json
{
  "items": [
    {
      "id": "uuid",
      "name": "Supino Reto",
      "description": "Supino com barra no banco reto",
      "muscle_group": "peito",
      "default_sets": 4,
      "default_reps": 10,
      "default_rest_seconds": 90,
      "images_count": 2,
      "created_at": "2026-01-10T08:00:00Z"
    }
  ],
  "pagination": { "page": 1, "limit": 20, "total": 15, "total_pages": 1 }
}
```

---

### POST /exercises

**Objetivo:** Criar exercício no catálogo.

**Body:**

```json
{
  "name": "Supino Reto",
  "description": "Supino com barra no banco reto",
  "muscle_group": "peito",
  "default_sets": 4,
  "default_reps": 10,
  "default_rest_seconds": 90
}
```

**Resposta 201:** Exercício criado

**Erros:** 409 `DUPLICATE_EMAIL` → usar `DUPLICATE_EXERCISE_NAME` (nome único por admin)

---

### GET /exercises/{id}

**Objetivo:** Detalhe do exercício com imagens.

**Resposta 200:**

```json
{
  "id": "uuid",
  "name": "Supino Reto",
  "description": "Supino com barra no banco reto",
  "muscle_group": "peito",
  "default_sets": 4,
  "default_reps": 10,
  "default_rest_seconds": 90,
  "images": [
    {
      "id": "uuid",
      "url": "/api/v1/uploads/exercises/uuid/file.jpg",
      "sort_order": 0
    }
  ],
  "created_at": "2026-01-10T08:00:00Z"
}
```

---

### PUT /exercises/{id}

**Objetivo:** Atualizar exercício.

**Body:** Campos parciais do POST.

**Resposta 200:** Exercício atualizado

---

### DELETE /exercises/{id}

**Objetivo:** Soft delete do exercício.

**Erros:** 409 `EXERCISE_IN_USE` se vinculado a treino ativo

**Resposta:** 204 No Content

---

### POST /exercises/{id}/images

**Objetivo:** Anexar imagem ilustrativa.

**Content-Type:** `multipart/form-data`

**Form fields:**

| Campo | Tipo | Obrigatório |
|-------|------|:-----------:|
| `file` | file | Sim |
| `sort_order` | int | Não |

**Resposta 201:**

```json
{
  "id": "uuid",
  "url": "/api/v1/uploads/exercises/uuid/file.jpg",
  "original_filename": "supino.jpg",
  "sort_order": 0
}
```

**Erros:** 400 se > 5 imagens ou arquivo inválido

---

### DELETE /exercises/{id}/images/{image_id}

**Objetivo:** Remover imagem do exercício.

**Resposta:** 204 No Content

---

## Treinos (Admin)

### GET /trainings

**Objetivo:** Listar treinos dos alunos do admin.

**Query params:** `page`, `limit`, `student_id`, `status`, `start_date`, `end_date`

**Resposta 200:**

```json
{
  "items": [
    {
      "id": "uuid",
      "student_id": "uuid",
      "student_name": "Maria Silva",
      "title": "Hipertrofia Q1",
      "start_date": "2026-01-01",
      "end_date": "2026-03-31",
      "status": "active",
      "days_count": 4,
      "created_at": "2025-12-28T10:00:00Z"
    }
  ],
  "pagination": { "page": 1, "limit": 20, "total": 5, "total_pages": 1 }
}
```

---

### POST /trainings

**Objetivo:** Criar treino (status inicial: `draft`).

**Body:**

```json
{
  "student_id": "uuid",
  "title": "Hipertrofia Q1",
  "description": "Treino focado em hipertrofia - 4 dias",
  "start_date": "2026-01-01",
  "end_date": "2026-03-31"
}
```

**Resposta 201:** Treino criado

**Erros:** 400 `INVALID_DATE_RANGE`, 404 aluno não encontrado

---

### GET /trainings/{id}

**Objetivo:** Detalhe completo do treino com dias e exercícios.

**Resposta 200:**

```json
{
  "id": "uuid",
  "student_id": "uuid",
  "student_name": "Maria Silva",
  "title": "Hipertrofia Q1",
  "description": "Treino focado em hipertrofia",
  "start_date": "2026-01-01",
  "end_date": "2026-03-31",
  "status": "active",
  "days": [
    {
      "id": "uuid",
      "day_of_week": 0,
      "day_name": "Segunda-feira",
      "label": "Peito e Tríceps",
      "exercises": [
        {
          "id": "uuid",
          "exercise_id": "uuid",
          "exercise_name": "Supino Reto",
          "sets": 4,
          "reps": 10,
          "load_kg": 40.0,
          "rest_seconds": 90,
          "sort_order": 0,
          "images": [{ "url": "/api/v1/uploads/exercises/..." }]
        }
      ]
    }
  ],
  "created_at": "2025-12-28T10:00:00Z",
  "updated_at": "2026-01-02T08:00:00Z"
}
```

---

### PUT /trainings/{id}

**Objetivo:** Atualizar metadados do treino.

**Body:**

```json
{
  "title": "Hipertrofia Q1 - Revisado",
  "description": "Ajuste de volume",
  "start_date": "2026-01-01",
  "end_date": "2026-04-30",
  "status": "active"
}
```

**Regras:**
- Mudança para `active` exige ao menos 1 dia com exercícios (RN-043)
- Treino `completed`/`cancelled` retorna 400

**Erros:** 409 `ACTIVE_TRAINING_EXISTS` ao ativar se já existe outro ativo

**Resposta 200:** Treino atualizado

---

### DELETE /trainings/{id}

**Objetivo:** Excluir treino (apenas `draft` ou `cancelled`).

**Erros:** 400 se status `active` ou `completed`

**Resposta:** 204 No Content

---

## Dias e exercícios do treino (Admin)

### POST /trainings/{id}/days

**Objetivo:** Adicionar dia da semana ao treino.

**Body:**

```json
{
  "day_of_week": 0,
  "label": "Peito e Tríceps",
  "notes": "Aquecimento 10 min",
  "sort_order": 0
}
```

**Resposta 201:** Dia criado

**Erros:** 409 `DUPLICATE_DAY`

---

### PUT /trainings/{id}/days/{day_id}

**Objetivo:** Atualizar dia do treino.

**Body:** Campos parciais do POST.

**Resposta 200:** Dia atualizado

---

### DELETE /trainings/{id}/days/{day_id}

**Objetivo:** Remover dia (cascade nos exercícios do dia).

**Resposta:** 204 No Content

---

### POST /trainings/{id}/days/{day_id}/exercises

**Objetivo:** Adicionar exercício ao dia.

**Body:**

```json
{
  "exercise_id": "uuid",
  "sets": 4,
  "reps": 10,
  "load_kg": 40.0,
  "rest_seconds": 90,
  "sort_order": 0,
  "notes": "Cadência 3-1-2"
}
```

**Resposta 201:** Exercício vinculado

---

### PUT /trainings/{id}/days/{day_id}/exercises/{exercise_entry_id}

**Objetivo:** Atualizar configuração do exercício no dia.

**Body:** Campos parciais (sets, reps, load_kg, rest_seconds, notes, sort_order)

**Resposta 200:** Entry atualizada

---

### DELETE /trainings/{id}/days/{day_id}/exercises/{exercise_entry_id}

**Objetivo:** Remover exercício do dia.

**Resposta:** 204 No Content

---

## Acompanhamento (Admin)

### GET /students/{id}/attendance

**Objetivo:** Frequência do aluno.

**Query params:** `start_date`, `end_date`, `page`, `limit`

**Resposta 200:**

```json
{
  "student_id": "uuid",
  "summary": {
    "total_check_ins": 12,
    "period_start": "2026-01-01",
    "period_end": "2026-03-31",
    "attendance_rate_pct": 75.0
  },
  "items": [
    {
      "id": "uuid",
      "check_in_date": "2026-07-15",
      "checked_in_at": "2026-07-15T08:30:00Z",
      "training_id": "uuid",
      "training_title": "Hipertrofia Q1"
    }
  ],
  "pagination": { "page": 1, "limit": 20, "total": 12, "total_pages": 1 }
}
```

---

### GET /students/{id}/progress/photos

**Objetivo:** Timeline de fotos de evolução.

**Query params:** `start_date`, `end_date`, `photo_type`

**Resposta 200:**

```json
{
  "items": [
    {
      "id": "uuid",
      "url": "/api/v1/uploads/students/uuid/photo.jpg",
      "photo_type": "front",
      "weight_kg": 61.5,
      "notes": "4 semanas de treino",
      "taken_at": "2026-07-01",
      "created_at": "2026-07-01T19:00:00Z"
    }
  ],
  "pagination": { "page": 1, "limit": 20, "total": 3, "total_pages": 1 }
}
```

---

### GET /students/{id}/progress/metrics

**Objetivo:** Métricas corporais do aluno.

**Resposta 200:**

```json
{
  "items": [
    {
      "id": "uuid",
      "metric_date": "2026-07-01",
      "weight_kg": 61.5,
      "body_fat_pct": 22.5,
      "measurements": {
        "chest_cm": 95.0,
        "waist_cm": 76.0
      }
    }
  ]
}
```

---

## Relatórios (Admin)

### GET /reports/overview

**Objetivo:** KPIs gerais do dashboard.

**Resposta 200:**

```json
{
  "total_students": 25,
  "active_students": 22,
  "students_with_active_training": 20,
  "trainings_expiring_soon": 3,
  "avg_weekly_attendance_pct": 68.5,
  "check_ins_this_week": 45,
  "new_progress_photos_this_month": 8
}
```

---

### GET /reports/students/{id}

**Objetivo:** Relatório individual do aluno.

**Resposta 200:**

```json
{
  "student": {
    "id": "uuid",
    "full_name": "Maria Silva",
    "goal": "Hipertrofia"
  },
  "current_training": {
    "title": "Hipertrofia Q1",
    "start_date": "2026-01-01",
    "end_date": "2026-03-31",
    "days_remaining": 45,
    "completion_pct": 55.0
  },
  "attendance": {
    "total_check_ins": 12,
    "expected_sessions": 16,
    "rate_pct": 75.0
  },
  "progress": {
    "initial_weight_kg": 62.5,
    "latest_weight_kg": 61.0,
    "weight_delta_kg": -1.5,
    "photos_count": 4
  }
}
```

---

### GET /reports/attendance

**Objetivo:** Relatório agregado de frequência.

**Query params:** `start_date`, `end_date`, `student_id` (opcional)

**Resposta 200:**

```json
{
  "period": { "start": "2026-07-01", "end": "2026-07-31" },
  "items": [
    {
      "student_id": "uuid",
      "student_name": "Maria Silva",
      "check_ins": 8,
      "expected": 12,
      "rate_pct": 66.7
    }
  ]
}
```

---

## Área do aluno

Todas requerem role `student`. Dados restritos ao próprio aluno.

### GET /me/training

**Objetivo:** Treino ativo completo do aluno.

**Resposta 200:** Mesmo schema de GET /trainings/{id}

**Erros:** 404 se nenhum treino ativo

---

### GET /me/training/days/{day_of_week}

**Objetivo:** Treino de um dia específico (0–6).

**Resposta 200:**

```json
{
  "day_of_week": 0,
  "day_name": "Segunda-feira",
  "label": "Peito e Tríceps",
  "training": {
    "id": "uuid",
    "title": "Hipertrofia Q1",
    "start_date": "2026-01-01",
    "end_date": "2026-03-31"
  },
  "exercises": [
    {
      "exercise_name": "Supino Reto",
      "sets": 4,
      "reps": 10,
      "load_kg": 40.0,
      "rest_seconds": 90,
      "notes": "Cadência 3-1-2",
      "images": [{ "url": "/api/v1/uploads/exercises/..." }]
    }
  ],
  "checked_in_today": false
}
```

**Erros:** 404 se dia não configurado ou sem treino ativo

---

### GET /me/history

**Objetivo:** Histórico de treinos e check-ins.

**Query params:** `page`, `limit`

**Resposta 200:**

```json
{
  "trainings": [
    {
      "id": "uuid",
      "title": "Adaptação Inicial",
      "start_date": "2025-10-01",
      "end_date": "2025-12-31",
      "status": "completed"
    }
  ],
  "recent_check_ins": [
    {
      "check_in_date": "2026-07-15",
      "training_title": "Hipertrofia Q1"
    }
  ]
}
```

---

### GET /me/progress

**Objetivo:** Resumo de evolução do aluno.

**Resposta 200:**

```json
{
  "latest_weight_kg": 61.0,
  "initial_weight_kg": 62.5,
  "weight_delta_kg": -1.5,
  "photos_count": 4,
  "last_photo_at": "2026-07-01",
  "check_ins_total": 12
}
```

---

### POST /me/progress/photos

**Objetivo:** Enviar foto de evolução.

**Content-Type:** `multipart/form-data`

**Form fields:**

| Campo | Tipo | Obrigatório |
|-------|------|:-----------:|
| `file` | file | Sim |
| `photo_type` | string | Não (default: other) |
| `weight_kg` | float | Não |
| `notes` | string | Não |
| `taken_at` | date | Não (default: hoje) |

**Resposta 201:**

```json
{
  "id": "uuid",
  "url": "/api/v1/uploads/students/uuid/photo.jpg",
  "photo_type": "front",
  "weight_kg": 61.0,
  "taken_at": "2026-07-16",
  "created_at": "2026-07-16T20:00:00Z"
}
```

---

### GET /me/progress/photos

**Objetivo:** Listar próprias fotos de evolução.

**Resposta 200:** Mesmo schema de GET /students/{id}/progress/photos

---

### POST /me/attendance/check-in

**Objetivo:** Registrar presença do dia.

**Body (opcional):**

```json
{
  "notes": "Treino completo, boa energia"
}
```

**Resposta 201:**

```json
{
  "id": "uuid",
  "check_in_date": "2026-07-16",
  "checked_in_at": "2026-07-16T08:15:00Z",
  "training_id": "uuid",
  "training_title": "Hipertrofia Q1"
}
```

**Erros:** 409 `DUPLICATE_CHECKIN`, 400 `TRAINING_NOT_ACTIVE`

```bash
curl -X POST http://localhost:8000/api/v1/me/attendance/check-in \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"notes":"Treino completo"}'
```

---

## Uploads

### POST /uploads/photos

**Objetivo:** Upload genérico de foto (uso interno; preferir endpoints específicos).

**Auth:** Bearer (admin ou student)

**Content-Type:** `multipart/form-data`

**Resposta 201:**

```json
{
  "file_path": "students/uuid/abc123.jpg",
  "url": "/api/v1/uploads/students/uuid/abc123.jpg"
}
```

---

### GET /uploads/{category}/{filename}

**Objetivo:** Servir arquivo de upload.

**Auth:** Bearer — valida permissão sobre recurso vinculado

**Params:**

| Param | Valores |
|-------|---------|
| `category` | `students`, `exercises` |

**Resposta 200:** Binary (image/jpeg, image/png, image/webp)

**Erros:** 403 `FORBIDDEN`, 404 `NOT_FOUND`

---

## Health check

### GET /health

**Objetivo:** Verificar saúde da API e conexão com banco.

**Auth:** Não

**Resposta 200:**

```json
{
  "status": "healthy",
  "database": "connected",
  "version": "1.0.0"
}
```

---

## Resumo de rotas

| # | Método | Rota | Auth | Role |
|---|--------|------|:----:|------|
| 1 | POST | /auth/login | — | — |
| 2 | POST | /auth/refresh | — | — |
| 3 | POST | /auth/logout | ✓ | * |
| 4 | GET | /auth/me | ✓ | * |
| 5 | GET | /students | ✓ | admin |
| 6 | POST | /students | ✓ | admin |
| 7 | GET | /students/{id} | ✓ | admin |
| 8 | PUT | /students/{id} | ✓ | admin |
| 9 | DELETE | /students/{id} | ✓ | admin |
| 10 | PATCH | /students/{id}/status | ✓ | admin |
| 11 | GET | /exercises | ✓ | admin |
| 12 | POST | /exercises | ✓ | admin |
| 13 | GET | /exercises/{id} | ✓ | admin |
| 14 | PUT | /exercises/{id} | ✓ | admin |
| 15 | DELETE | /exercises/{id} | ✓ | admin |
| 16 | POST | /exercises/{id}/images | ✓ | admin |
| 17 | DELETE | /exercises/{id}/images/{image_id} | ✓ | admin |
| 18 | GET | /trainings | ✓ | admin |
| 19 | POST | /trainings | ✓ | admin |
| 20 | GET | /trainings/{id} | ✓ | admin |
| 21 | PUT | /trainings/{id} | ✓ | admin |
| 22 | DELETE | /trainings/{id} | ✓ | admin |
| 23 | POST | /trainings/{id}/days | ✓ | admin |
| 24 | PUT | /trainings/{id}/days/{day_id} | ✓ | admin |
| 25 | DELETE | /trainings/{id}/days/{day_id} | ✓ | admin |
| 26 | POST | /trainings/{id}/days/{day_id}/exercises | ✓ | admin |
| 27 | PUT | /trainings/{id}/days/{day_id}/exercises/{entry_id} | ✓ | admin |
| 28 | DELETE | /trainings/{id}/days/{day_id}/exercises/{entry_id} | ✓ | admin |
| 29 | GET | /students/{id}/attendance | ✓ | admin |
| 30 | GET | /students/{id}/progress/photos | ✓ | admin |
| 31 | GET | /students/{id}/progress/metrics | ✓ | admin |
| 32 | GET | /reports/overview | ✓ | admin |
| 33 | GET | /reports/students/{id} | ✓ | admin |
| 34 | GET | /reports/attendance | ✓ | admin |
| 35 | GET | /me/training | ✓ | student |
| 36 | GET | /me/training/days/{day_of_week} | ✓ | student |
| 37 | GET | /me/history | ✓ | student |
| 38 | GET | /me/progress | ✓ | student |
| 39 | POST | /me/progress/photos | ✓ | student |
| 40 | GET | /me/progress/photos | ✓ | student |
| 41 | POST | /me/attendance/check-in | ✓ | student |
| 42 | POST | /uploads/photos | ✓ | * |
| 43 | GET | /uploads/{category}/{filename} | ✓ | * |
| 44 | GET | /health | — | — |

---

## Documentos relacionados

- [04-autenticacao.md](04-autenticacao.md) — Detalhes JWT
- [06-dashboard-admin.md](06-dashboard-admin.md) — Consumo no painel admin
- [07-area-aluno.md](07-area-aluno.md) — Consumo no portal aluno
- [03-modelagem-banco.md](03-modelagem-banco.md) — Schema de dados
