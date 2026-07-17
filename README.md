# Smart Training — Documentação Oficial

Plataforma de gestão de treinos para Personal Trainers e seus alunos.

## Stack

| Camada | Tecnologia |
|--------|------------|
| Backend | FastAPI (Python 3.13+) |
| Banco de dados | MySQL 8.0 |
| ORM | SQLAlchemy 2.x |
| Migrações | Alembic |
| Autenticação | JWT Bearer Token |
| Infraestrutura | Docker + Docker Compose |
| Documentação API | Swagger/OpenAPI (FastAPI) |

## Perfis de usuário

- **Administrador** — Personal Trainer com controle total do sistema
- **Aluno** — Acesso restrito ao próprio treino, histórico e evolução

## Índice da documentação

| # | Documento | Descrição |
|---|-----------|-----------|
| 01 | [Visão Geral](01-visao-geral.md) | Missão, personas, stack e glossário |
| 02 | [Regras de Negócio](02-regras-de-negocio.md) | RBAC, validações e estados do sistema |
| 03 | [Modelagem de Banco](03-modelagem-banco.md) | ER diagram, DDL, índices e migrações |
| 04 | [Autenticação](04-autenticacao.md) | JWT, login, refresh e segurança |
| 05 | [API REST](05-api-rest.md) | Todas as rotas, payloads e exemplos |
| 06 | [Dashboard Admin](06-dashboard-admin.md) | Funcionalidades do Personal Trainer |
| 07 | [Área do Aluno](07-area-aluno.md) | Experiência e regras de visualização |
| 08 | [Docker](08-docker.md) | Compose, Dockerfile, env e deploy |
| 09 | [Estrutura do Projeto](09-estrutura-do-projeto.md) | Pastas, camadas e responsabilidades |
| 10 | [Roadmap](10-roadmap.md) | Fases, critérios de aceite e backlog |
| 11 | [Fluxos](11-fluxos.md) | Fluxogramas dos processos principais |
| 12 | [Convenções](12-convencoes.md) | Padrões de código, testes e commits |

## Início rápido (referência)

```bash
# Clone e configure
cp .env.example .env

# Suba os serviços
docker compose up -d

# Execute migrações
docker compose exec api alembic upgrade head

# Acesse a API
open http://localhost:8000/docs
```

Consulte [08-docker.md](08-docker.md) para instruções completas de desenvolvimento e produção.

## Backend — Desenvolvimento local

### Pré-requisitos

- Python 3.12+
- Docker (MySQL local)

### Subir MySQL

```bash
cd /home/guilherme/Projetos/smart_training
docker compose up -d db
```

MySQL disponível em `localhost:3310` (usuário: `smart_user`, senha: `smart_pass`, database: `smart_training`).

### Instalar e rodar API

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # se ainda não existir
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

- Swagger: http://localhost:8001/docs
- Health: http://localhost:8001/health

### Credenciais padrão (admin seed)

| Campo | Valor |
|-------|-------|
| Email | `admin@smarttraining.com` |
| Senha | `Admin123!` |

### Testar no Insomnia

**1. Login**

```
POST http://localhost:8001/api/v1/auth/login
Content-Type: application/json

{
  "email": "admin@smarttraining.com",
  "password": "Admin123!"
}
```

Copie o `access_token` da resposta.

**2. Requisições autenticadas**

Adicione header em todas as rotas protegidas:

```
Authorization: Bearer <access_token>
```

**3. Fluxo completo — cadastrar treino por aluno**

```
# 1. Listar alunos para dropdown (id + nome)
GET /api/v1/students/options

# 2. Cadastrar treino completo (dias + exercícios) vinculado ao aluno
POST /api/v1/trainings/complete

{
  "student_id": "uuid-do-aluno",
  "title": "Hipertrofia Q1",
  "start_date": "2026-01-01",
  "end_date": "2026-06-30",
  "activate": true,
  "days": [
    {
      "day_of_week": 0,
      "label": "Peito e Tríceps",
      "exercises": [
        { "exercise_id": "uuid-exercicio", "sets": 4, "reps": 10, "load_kg": 40 }
      ]
    },
    {
      "day_of_week": 2,
      "label": "Costas e Bíceps",
      "exercises": [
        { "exercise_id": "uuid-exercicio", "sets": 3, "reps": 12, "load_kg": 30 }
      ]
    }
  ]
}
```

`day_of_week`: 0=Segunda, 1=Terça, 2=Quarta, 3=Quinta, 4=Sexta, 5=Sábado, 6=Domingo

**4. Guia de relatórios — acompanhamento individual**

```
GET /api/v1/reports/students                              # lista todos os alunos
GET /api/v1/reports/students/{student_id}/monitoring      # detalhe individual completo
GET /api/v1/reports/students/{student_id}                 # resumo
GET /api/v1/reports/attendance?start_date=2026-07-01      # frequência agregada
```

**5. Exemplos adicionais**

| Ação | Método | URL |
|------|--------|-----|
| Treinos de um aluno | GET | `/api/v1/students/{id}/trainings` |
| Ativar treino | POST | `/api/v1/trainings/{id}/activate` |
| Dashboard KPIs | GET | `/api/v1/reports/overview` |

Use email/senha definidos ao criar o aluno via `POST /students`.

### Deploy Dokploy

Use o `Dockerfile` na raiz. Configure `DATABASE_URL` apontando para o MySQL do Dokploy e as variáveis JWT/ADMIN_*.

## Ordem de leitura recomendada

Para implementar o sistema do zero, siga esta sequência:

1. `01-visao-geral.md` → contexto
2. `02-regras-de-negocio.md` → regras
3. `03-modelagem-banco.md` → schema
4. `09-estrutura-do-projeto.md` → scaffolding
5. `04-autenticacao.md` → auth
6. `05-api-rest.md` → endpoints
7. `08-docker.md` → infraestrutura
8. `06-dashboard-admin.md` + `07-area-aluno.md` → integração frontend
9. `11-fluxos.md` + `12-convencoes.md` → referência contínua
