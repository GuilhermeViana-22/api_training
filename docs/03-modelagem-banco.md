# 03 — Modelagem de Banco de Dados

## Introdução

Este documento descreve o schema completo do MySQL 8.0 para o Smart Training: diagrama ER, DDL de referência, descrição de colunas, chaves, índices e estratégia de migrações com Alembic.

## Índice

- [Visão geral](#visão-geral)
- [Diagrama ER](#diagrama-er)
- [Convenções](#convenções)
- [Tabelas](#tabelas)
- [DDL completo](#ddl-completo)
- [Índices sugeridos](#índices-sugeridos)
- [Seeds iniciais](#seeds-iniciais)
- [Estratégia Alembic](#estratégia-alembic)
- [Documentos relacionados](#documentos-relacionados)

---

## Visão geral

| Item | Valor |
|------|-------|
| SGBD | MySQL 8.0+ |
| Charset | `utf8mb4` |
| Collation | `utf8mb4_unicode_ci` |
| Engine | InnoDB |
| Total de tabelas | 12 |

---

## Diagrama ER

```mermaid
erDiagram
    users {
        char id PK
        varchar email UK
        varchar password_hash
        enum role
        boolean is_active
        datetime deleted_at
        datetime created_at
        datetime updated_at
    }

    admin_profiles {
        char user_id PK_FK
        varchar full_name
        varchar cref
        varchar phone
        text bio
    }

    student_profiles {
        char user_id PK_FK
        char admin_id FK
        varchar full_name
        varchar phone
        date birth_date
        decimal height_cm
        decimal weight_kg
        varchar goal
        text notes
        datetime deleted_at
    }

    exercises {
        char id PK
        char admin_id FK
        varchar name
        text description
        varchar muscle_group
        int default_sets
        int default_reps
        int default_rest_seconds
        datetime deleted_at
    }

    exercise_images {
        char id PK
        char exercise_id FK
        varchar file_path
        varchar original_filename
        int sort_order
        datetime created_at
    }

    trainings {
        char id PK
        char admin_id FK
        char student_id FK
        varchar title
        text description
        date start_date
        date end_date
        enum status
        datetime created_at
        datetime updated_at
    }

    training_days {
        char id PK
        char training_id FK
        tinyint day_of_week
        varchar label
        text notes
        int sort_order
    }

    training_exercises {
        char id PK
        char training_day_id FK
        char exercise_id FK
        int sets
        int reps
        decimal load_kg
        int rest_seconds
        int sort_order
        text notes
    }

    attendance_records {
        char id PK
        char student_id FK
        char training_id FK
        date check_in_date
        datetime checked_in_at
        text notes
    }

    progress_photos {
        char id PK
        char student_id FK
        varchar file_path
        enum photo_type
        decimal weight_kg
        text notes
        date taken_at
        datetime created_at
    }

    progress_metrics {
        char id PK
        char student_id FK
        date metric_date
        decimal weight_kg
        decimal body_fat_pct
        json measurements
        datetime created_at
    }

    refresh_tokens {
        char id PK
        char user_id FK
        varchar token_hash
        datetime expires_at
        datetime revoked_at
        datetime created_at
    }

    users ||--o| admin_profiles : has
    users ||--o| student_profiles : has
    users ||--o{ refresh_tokens : owns
    admin_profiles ||--o{ student_profiles : manages
    student_profiles ||--o{ trainings : receives
    trainings ||--o{ training_days : contains
    training_days ||--o{ training_exercises : lists
    exercises ||--o{ training_exercises : referenced_by
    exercises ||--o{ exercise_images : illustrates
    student_profiles ||--o{ attendance_records : checks_in
    student_profiles ||--o{ progress_photos : uploads
    student_profiles ||--o{ progress_metrics : tracks
    trainings ||--o{ attendance_records : context
```

---

## Convenções

| Convenção | Padrão |
|-----------|--------|
| PK | `CHAR(36)` — UUID v4 |
| Timestamps | `DATETIME(6)` UTC |
| Soft delete | Coluna `deleted_at` nullable |
| FK naming | `fk_{tabela}_{referencia}` |
| Index naming | `idx_{tabela}_{colunas}` |
| Enum values | lowercase snake_case |

---

## Tabelas

### `users`

Credenciais e role de autenticação.

| Coluna | Tipo | Null | Default | Descrição |
|--------|------|:----:|---------|-----------|
| `id` | CHAR(36) | NO | — | PK, UUID v4 |
| `email` | VARCHAR(255) | NO | — | Email único, login |
| `password_hash` | VARCHAR(255) | NO | — | Hash bcrypt |
| `role` | ENUM('admin','student') | NO | — | Papel do usuário |
| `is_active` | TINYINT(1) | NO | 1 | Conta ativa |
| `deleted_at` | DATETIME(6) | YES | NULL | Soft delete |
| `created_at` | DATETIME(6) | NO | CURRENT_TIMESTAMP | — |
| `updated_at` | DATETIME(6) | NO | CURRENT_TIMESTAMP ON UPDATE | — |

**Índices:** `UNIQUE uk_users_email (email)`, `idx_users_role (role)`

---

### `admin_profiles`

Dados do Personal Trainer.

| Coluna | Tipo | Null | Default | Descrição |
|--------|------|:----:|---------|-----------|
| `user_id` | CHAR(36) | NO | — | PK, FK → users.id |
| `full_name` | VARCHAR(150) | NO | — | Nome completo |
| `cref` | VARCHAR(20) | YES | NULL | Registro CREF |
| `phone` | VARCHAR(20) | YES | NULL | Telefone |
| `bio` | TEXT | YES | NULL | Biografia |

**FK:** `user_id` → `users.id` ON DELETE CASCADE

---

### `student_profiles`

Dados do aluno vinculado a um admin.

| Coluna | Tipo | Null | Default | Descrição |
|--------|------|:----:|---------|-----------|
| `user_id` | CHAR(36) | NO | — | PK, FK → users.id |
| `admin_id` | CHAR(36) | NO | — | FK → users.id (admin) |
| `full_name` | VARCHAR(150) | NO | — | Nome completo |
| `phone` | VARCHAR(20) | YES | NULL | Telefone |
| `birth_date` | DATE | YES | NULL | Data nascimento |
| `height_cm` | DECIMAL(5,2) | YES | NULL | Altura em cm |
| `weight_kg` | DECIMAL(5,2) | YES | NULL | Peso em kg |
| `goal` | VARCHAR(255) | YES | NULL | Objetivo |
| `notes` | TEXT | YES | NULL | Observações do admin |
| `deleted_at` | DATETIME(6) | YES | NULL | Soft delete |

**Índices:** `idx_student_profiles_admin_id (admin_id)`

**FKs:**
- `user_id` → `users.id` ON DELETE CASCADE
- `admin_id` → `users.id` ON DELETE RESTRICT

---

### `exercises`

Catálogo de exercícios do admin.

| Coluna | Tipo | Null | Default | Descrição |
|--------|------|:----:|---------|-----------|
| `id` | CHAR(36) | NO | — | PK |
| `admin_id` | CHAR(36) | NO | — | FK → users.id |
| `name` | VARCHAR(150) | NO | — | Nome do exercício |
| `description` | TEXT | YES | NULL | Descrição |
| `muscle_group` | VARCHAR(50) | YES | NULL | Grupo muscular |
| `default_sets` | INT | YES | NULL | Séries padrão |
| `default_reps` | INT | YES | NULL | Repetições padrão |
| `default_rest_seconds` | INT | YES | NULL | Descanso padrão (s) |
| `deleted_at` | DATETIME(6) | YES | NULL | Soft delete |
| `created_at` | DATETIME(6) | NO | CURRENT_TIMESTAMP | — |
| `updated_at` | DATETIME(6) | NO | CURRENT_TIMESTAMP ON UPDATE | — |

**Índices:** `UNIQUE uk_exercises_admin_name (admin_id, name)`, `idx_exercises_admin_id (admin_id)`

---

### `exercise_images`

Imagens ilustrativas de exercícios.

| Coluna | Tipo | Null | Default | Descrição |
|--------|------|:----:|---------|-----------|
| `id` | CHAR(36) | NO | — | PK |
| `exercise_id` | CHAR(36) | NO | — | FK → exercises.id |
| `file_path` | VARCHAR(500) | NO | — | Caminho relativo |
| `original_filename` | VARCHAR(255) | YES | NULL | Nome original |
| `sort_order` | INT | NO | 0 | Ordem exibição |
| `created_at` | DATETIME(6) | NO | CURRENT_TIMESTAMP | — |

**FK:** `exercise_id` → `exercises.id` ON DELETE CASCADE

---

### `trainings`

Treino atribuído a um aluno.

| Coluna | Tipo | Null | Default | Descrição |
|--------|------|:----:|---------|-----------|
| `id` | CHAR(36) | NO | — | PK |
| `admin_id` | CHAR(36) | NO | — | FK → users.id |
| `student_id` | CHAR(36) | NO | — | FK → student_profiles.user_id |
| `title` | VARCHAR(150) | NO | — | Título |
| `description` | TEXT | YES | NULL | Descrição |
| `start_date` | DATE | NO | — | Data inicial |
| `end_date` | DATE | NO | — | Data final |
| `status` | ENUM('draft','active','completed','cancelled') | NO | 'draft' | Status |
| `created_at` | DATETIME(6) | NO | CURRENT_TIMESTAMP | — |
| `updated_at` | DATETIME(6) | NO | CURRENT_TIMESTAMP ON UPDATE | — |

**Índices:**
- `idx_trainings_admin_id (admin_id)`
- `idx_trainings_student_id (student_id)`
- `idx_trainings_status_dates (status, start_date, end_date)`

---

### `training_days`

Dias da semana dentro de um treino.

| Coluna | Tipo | Null | Default | Descrição |
|--------|------|:----:|---------|-----------|
| `id` | CHAR(36) | NO | — | PK |
| `training_id` | CHAR(36) | NO | — | FK → trainings.id |
| `day_of_week` | TINYINT | NO | — | 0=seg … 6=dom |
| `label` | VARCHAR(100) | YES | NULL | Ex: "Peito e Tríceps" |
| `notes` | TEXT | YES | NULL | Observações |
| `sort_order` | INT | NO | 0 | Ordem |

**Índices:** `UNIQUE uk_training_days_training_dow (training_id, day_of_week)`

**FK:** `training_id` → `trainings.id` ON DELETE CASCADE

---

### `training_exercises`

Exercícios configurados em um dia de treino.

| Coluna | Tipo | Null | Default | Descrição |
|--------|------|:----:|---------|-----------|
| `id` | CHAR(36) | NO | — | PK |
| `training_day_id` | CHAR(36) | NO | — | FK → training_days.id |
| `exercise_id` | CHAR(36) | NO | — | FK → exercises.id |
| `sets` | INT | NO | — | Séries |
| `reps` | INT | NO | — | Repetições |
| `load_kg` | DECIMAL(6,2) | YES | NULL | Carga em kg |
| `rest_seconds` | INT | YES | NULL | Descanso (s) |
| `sort_order` | INT | NO | 0 | Ordem no dia |
| `notes` | TEXT | YES | NULL | Observações |

**FKs:**
- `training_day_id` → `training_days.id` ON DELETE CASCADE
- `exercise_id` → `exercises.id` ON DELETE RESTRICT

---

### `attendance_records`

Registro de frequência (check-in).

| Coluna | Tipo | Null | Default | Descrição |
|--------|------|:----:|---------|-----------|
| `id` | CHAR(36) | NO | — | PK |
| `student_id` | CHAR(36) | NO | — | FK → student_profiles.user_id |
| `training_id` | CHAR(36) | NO | — | FK → trainings.id |
| `check_in_date` | DATE | NO | — | Data do check-in |
| `checked_in_at` | DATETIME(6) | NO | CURRENT_TIMESTAMP | Timestamp |
| `notes` | TEXT | YES | NULL | Observações |

**Índices:** `UNIQUE uk_attendance_student_date (student_id, check_in_date)`

---

### `progress_photos`

Fotos de evolução enviadas pelo aluno.

| Coluna | Tipo | Null | Default | Descrição |
|--------|------|:----:|---------|-----------|
| `id` | CHAR(36) | NO | — | PK |
| `student_id` | CHAR(36) | NO | — | FK → student_profiles.user_id |
| `file_path` | VARCHAR(500) | NO | — | Caminho relativo |
| `photo_type` | ENUM('front','side','back','other') | NO | 'other' | Tipo |
| `weight_kg` | DECIMAL(5,2) | YES | NULL | Peso no momento |
| `notes` | TEXT | YES | NULL | Observações |
| `taken_at` | DATE | NO | — | Data da foto |
| `created_at` | DATETIME(6) | NO | CURRENT_TIMESTAMP | — |

**Índices:** `idx_progress_photos_student_taken (student_id, taken_at DESC)`

---

### `progress_metrics`

Métricas corporais periódicas.

| Coluna | Tipo | Null | Default | Descrição |
|--------|------|:----:|---------|-----------|
| `id` | CHAR(36) | NO | — | PK |
| `student_id` | CHAR(36) | NO | — | FK → student_profiles.user_id |
| `metric_date` | DATE | NO | — | Data da medição |
| `weight_kg` | DECIMAL(5,2) | YES | NULL | Peso |
| `body_fat_pct` | DECIMAL(4,2) | YES | NULL | % gordura |
| `measurements` | JSON | YES | NULL | Medidas extras |
| `created_at` | DATETIME(6) | NO | CURRENT_TIMESTAMP | — |

**Exemplo `measurements`:**

```json
{
  "chest_cm": 98.5,
  "waist_cm": 78.0,
  "hip_cm": 95.0,
  "arm_cm": 32.0
}
```

---

### `refresh_tokens`

Tokens de refresh para revogação.

| Coluna | Tipo | Null | Default | Descrição |
|--------|------|:----:|---------|-----------|
| `id` | CHAR(36) | NO | — | PK |
| `user_id` | CHAR(36) | NO | — | FK → users.id |
| `token_hash` | VARCHAR(255) | NO | — | SHA-256 do token |
| `expires_at` | DATETIME(6) | NO | — | Expiração |
| `revoked_at` | DATETIME(6) | YES | NULL | Revogação |
| `created_at` | DATETIME(6) | NO | CURRENT_TIMESTAMP | — |

**Índices:** `idx_refresh_tokens_user_id (user_id)`, `idx_refresh_tokens_hash (token_hash)`

---

## DDL completo

```sql
CREATE DATABASE IF NOT EXISTS smart_training
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE smart_training;

CREATE TABLE users (
    id CHAR(36) NOT NULL PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('admin', 'student') NOT NULL,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    deleted_at DATETIME(6) NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    UNIQUE KEY uk_users_email (email),
    KEY idx_users_role (role)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE admin_profiles (
    user_id CHAR(36) NOT NULL PRIMARY KEY,
    full_name VARCHAR(150) NOT NULL,
    cref VARCHAR(20) NULL,
    phone VARCHAR(20) NULL,
    bio TEXT NULL,
    CONSTRAINT fk_admin_profiles_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE student_profiles (
    user_id CHAR(36) NOT NULL PRIMARY KEY,
    admin_id CHAR(36) NOT NULL,
    full_name VARCHAR(150) NOT NULL,
    phone VARCHAR(20) NULL,
    birth_date DATE NULL,
    height_cm DECIMAL(5,2) NULL,
    weight_kg DECIMAL(5,2) NULL,
    goal VARCHAR(255) NULL,
    notes TEXT NULL,
    deleted_at DATETIME(6) NULL,
    KEY idx_student_profiles_admin_id (admin_id),
    CONSTRAINT fk_student_profiles_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_student_profiles_admin FOREIGN KEY (admin_id) REFERENCES users(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE exercises (
    id CHAR(36) NOT NULL PRIMARY KEY,
    admin_id CHAR(36) NOT NULL,
    name VARCHAR(150) NOT NULL,
    description TEXT NULL,
    muscle_group VARCHAR(50) NULL,
    default_sets INT NULL,
    default_reps INT NULL,
    default_rest_seconds INT NULL,
    deleted_at DATETIME(6) NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    UNIQUE KEY uk_exercises_admin_name (admin_id, name),
    KEY idx_exercises_admin_id (admin_id),
    CONSTRAINT fk_exercises_admin FOREIGN KEY (admin_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE exercise_images (
    id CHAR(36) NOT NULL PRIMARY KEY,
    exercise_id CHAR(36) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    original_filename VARCHAR(255) NULL,
    sort_order INT NOT NULL DEFAULT 0,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    KEY idx_exercise_images_exercise_id (exercise_id),
    CONSTRAINT fk_exercise_images_exercise FOREIGN KEY (exercise_id) REFERENCES exercises(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE trainings (
    id CHAR(36) NOT NULL PRIMARY KEY,
    admin_id CHAR(36) NOT NULL,
    student_id CHAR(36) NOT NULL,
    title VARCHAR(150) NOT NULL,
    description TEXT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status ENUM('draft', 'active', 'completed', 'cancelled') NOT NULL DEFAULT 'draft',
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    KEY idx_trainings_admin_id (admin_id),
    KEY idx_trainings_student_id (student_id),
    KEY idx_trainings_status_dates (status, start_date, end_date),
    CONSTRAINT fk_trainings_admin FOREIGN KEY (admin_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_trainings_student FOREIGN KEY (student_id) REFERENCES student_profiles(user_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE training_days (
    id CHAR(36) NOT NULL PRIMARY KEY,
    training_id CHAR(36) NOT NULL,
    day_of_week TINYINT NOT NULL,
    label VARCHAR(100) NULL,
    notes TEXT NULL,
    sort_order INT NOT NULL DEFAULT 0,
    UNIQUE KEY uk_training_days_training_dow (training_id, day_of_week),
    CONSTRAINT fk_training_days_training FOREIGN KEY (training_id) REFERENCES trainings(id) ON DELETE CASCADE,
    CONSTRAINT chk_day_of_week CHECK (day_of_week BETWEEN 0 AND 6)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE training_exercises (
    id CHAR(36) NOT NULL PRIMARY KEY,
    training_day_id CHAR(36) NOT NULL,
    exercise_id CHAR(36) NOT NULL,
    sets INT NOT NULL,
    reps INT NOT NULL,
    load_kg DECIMAL(6,2) NULL,
    rest_seconds INT NULL,
    sort_order INT NOT NULL DEFAULT 0,
    notes TEXT NULL,
    KEY idx_training_exercises_day (training_day_id),
    CONSTRAINT fk_training_exercises_day FOREIGN KEY (training_day_id) REFERENCES training_days(id) ON DELETE CASCADE,
    CONSTRAINT fk_training_exercises_exercise FOREIGN KEY (exercise_id) REFERENCES exercises(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE attendance_records (
    id CHAR(36) NOT NULL PRIMARY KEY,
    student_id CHAR(36) NOT NULL,
    training_id CHAR(36) NOT NULL,
    check_in_date DATE NOT NULL,
    checked_in_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    notes TEXT NULL,
    UNIQUE KEY uk_attendance_student_date (student_id, check_in_date),
    KEY idx_attendance_training_id (training_id),
    CONSTRAINT fk_attendance_student FOREIGN KEY (student_id) REFERENCES student_profiles(user_id) ON DELETE CASCADE,
    CONSTRAINT fk_attendance_training FOREIGN KEY (training_id) REFERENCES trainings(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE progress_photos (
    id CHAR(36) NOT NULL PRIMARY KEY,
    student_id CHAR(36) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    photo_type ENUM('front', 'side', 'back', 'other') NOT NULL DEFAULT 'other',
    weight_kg DECIMAL(5,2) NULL,
    notes TEXT NULL,
    taken_at DATE NOT NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    KEY idx_progress_photos_student_taken (student_id, taken_at DESC),
    CONSTRAINT fk_progress_photos_student FOREIGN KEY (student_id) REFERENCES student_profiles(user_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE progress_metrics (
    id CHAR(36) NOT NULL PRIMARY KEY,
    student_id CHAR(36) NOT NULL,
    metric_date DATE NOT NULL,
    weight_kg DECIMAL(5,2) NULL,
    body_fat_pct DECIMAL(4,2) NULL,
    measurements JSON NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    KEY idx_progress_metrics_student_date (student_id, metric_date DESC),
    CONSTRAINT fk_progress_metrics_student FOREIGN KEY (student_id) REFERENCES student_profiles(user_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE refresh_tokens (
    id CHAR(36) NOT NULL PRIMARY KEY,
    user_id CHAR(36) NOT NULL,
    token_hash VARCHAR(255) NOT NULL,
    expires_at DATETIME(6) NOT NULL,
    revoked_at DATETIME(6) NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    KEY idx_refresh_tokens_user_id (user_id),
    KEY idx_refresh_tokens_hash (token_hash),
    CONSTRAINT fk_refresh_tokens_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

---

## Índices sugeridos

| Índice | Tabela | Colunas | Motivo |
|--------|--------|---------|--------|
| `uk_users_email` | users | email | Login único |
| `idx_student_profiles_admin_id` | student_profiles | admin_id | Listagem alunos por admin |
| `uk_exercises_admin_name` | exercises | admin_id, name | Unicidade catálogo |
| `idx_trainings_status_dates` | trainings | status, start_date, end_date | Treino ativo por data |
| `uk_training_days_training_dow` | training_days | training_id, day_of_week | Un dia por semana |
| `uk_attendance_student_date` | attendance_records | student_id, check_in_date | 1 check-in/dia |
| `idx_progress_photos_student_taken` | progress_photos | student_id, taken_at | Timeline evolução |

---

## Seeds iniciais

Migration `seed_admin_user` cria admin padrão a partir de variáveis de ambiente:

```python
# alembic/versions/xxxx_seed_admin.py
admin_email = os.getenv("ADMIN_EMAIL", "admin@smarttraining.local")
admin_password = os.getenv("ADMIN_PASSWORD", "Admin123!")
# Hash bcrypt + insert users + admin_profiles
```

---

## Estratégia Alembic

```
alembic/
├── env.py
├── script.py.mako
└── versions/
    ├── 001_initial_schema.py
    ├── 002_seed_admin_user.py
    └── ...
```

| Prática | Descrição |
|---------|-----------|
| Nomenclatura | `{revision}_{descricao_snake}.py` |
| Autogenerate | `alembic revision --autogenerate -m "descricao"` |
| Upgrade | `alembic upgrade head` |
| Downgrade | `alembic downgrade -1` |
| SQLAlchemy models | Fonte da verdade em `app/models/` |

---

## Documentos relacionados

- [02-regras-de-negocio.md](02-regras-de-negocio.md) — Regras que o schema implementa
- [04-autenticacao.md](04-autenticacao.md) — Tabela `refresh_tokens`
- [05-api-rest.md](05-api-rest.md) — Payloads que mapeiam para estas tabelas
- [09-estrutura-do-projeto.md](09-estrutura-do-projeto.md) — Localização dos models SQLAlchemy
