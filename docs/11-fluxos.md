# 11 — Fluxos

## Introdução

Este documento apresenta os fluxogramas dos processos principais do Smart Training em diagramas Mermaid, servindo como referência visual para implementação e testes.

## Índice

- [Login e refresh token](#login-e-refresh-token)
- [Admin cadastra aluno e treino](#admin-cadastra-aluno-e-treino)
- [Ciclo de vida do treino](#ciclo-de-vida-do-treino)
- [Aluno consulta treino do dia](#aluno-consulta-treino-do-dia)
- [Aluno registra check-in](#aluno-registra-check-in)
- [Aluno envia foto de evolução](#aluno-envia-foto-de-evolução)
- [Admin visualiza relatório de frequência](#admin-visualiza-relatório-de-frequência)
- [Upload de imagem de exercício](#upload-de-imagem-de-exercício)
- [Documentos relacionados](#documentos-relacionados)

---

## Login e refresh token

```mermaid
flowchart TD
    Start([Cliente acessa app]) --> LoginForm[Exibe formulário login]
    LoginForm --> SubmitLogin[POST /auth/login]
    SubmitLogin --> ValidateCreds{Email e senha válidos?}
    ValidateCreds -->|Não| Error401[401 INVALID_CREDENTIALS]
    ValidateCreds -->|Sim| CheckActive{Usuário ativo?}
    CheckActive -->|Não| ErrorInactive[401 USER_INACTIVE]
    CheckActive -->|Sim| GenerateTokens[Gera access + refresh token]
    GenerateTokens --> SaveRefresh[Persiste hash refresh no DB]
    SaveRefresh --> ReturnTokens[200 tokens + expires_in]
    ReturnTokens --> StoreTokens[Cliente armazena tokens]
    StoreTokens --> Authenticated([Autenticado])

    Authenticated --> APICall[Requisição com Bearer token]
    APICall --> TokenValid{Access token válido?}
    TokenValid -->|Sim| ProcessRequest[Processa request]
    TokenValid -->|Não| RefreshFlow[POST /auth/refresh]
    RefreshFlow --> RefreshValid{Refresh válido e não revogado?}
    RefreshValid -->|Não| ForceLogin[Redireciona para login]
    RefreshValid -->|Sim| NewAccess[Novo access token]
    NewAccess --> APICall

    Authenticated --> Logout[POST /auth/logout]
    Logout --> RevokeRefresh[Revoga refresh token]
    RevokeRefresh --> LoggedOut([Deslogado])
```

---

## Admin cadastra aluno e treino

```mermaid
flowchart TD
    Start([Admin logado]) --> CreateStudent[POST /students]
    CreateStudent --> ValidateEmail{Email único?}
    ValidateEmail -->|Não| Error409[409 DUPLICATE_EMAIL]
    ValidateEmail -->|Sim| HashPassword[Hash bcrypt senha]
    HashPassword --> InsertUser[INSERT users role=student]
    InsertUser --> InsertProfile[INSERT student_profiles]
    InsertProfile --> StudentCreated[201 Aluno criado]

    StudentCreated --> CreateExercise[POST /exercises]
    CreateExercise --> ExerciseCreated[201 Exercício no catálogo]

    ExerciseCreated --> CreateTraining[POST /trainings status=draft]
    CreateTraining --> ValidateDates{start_date <= end_date?}
    ValidateDates -->|Não| Error400[400 INVALID_DATE_RANGE]
    ValidateDates -->|Sim| TrainingCreated[201 Treino draft]

    TrainingCreated --> AddDays[POST /trainings/id/days]
    AddDays --> AddExercises[POST .../days/id/exercises]
    AddExercises --> MoreDays{Mais dias?}
    MoreDays -->|Sim| AddDays
    MoreDays -->|Não| ActivateTraining[PUT /trainings/id status=active]

    ActivateTraining --> HasExercises{Tem dia com exercício?}
    HasExercises -->|Não| ErrorEmpty[400 TRAINING_EMPTY]
    HasExercises -->|Sim| CheckActive{Aluno tem treino ativo?}
    CheckActive -->|Sim| CompleteOld[Completa treino anterior]
    CheckActive -->|Não| SetActive[status = active]
    CompleteOld --> SetActive
    SetActive --> Done([Treino ativo para aluno])
```

---

## Ciclo de vida do treino

```mermaid
stateDiagram-v2
    [*] --> draft: Admin cria treino

    draft --> draft: Edita dias/exercícios
    draft --> active: Admin ativa
    draft --> cancelled: Admin cancela

    active --> active: Admin edita exercícios
    active --> completed: end_date atingida
    active --> completed: Novo treino ativado
    active --> cancelled: Admin cancela

    completed --> [*]
    cancelled --> [*]

    note right of draft
        Editável livremente
        Não visível ao aluno
    end note

    note right of active
        Visível ao aluno
        Check-in habilitado
        Máximo 1 por aluno
    end note

    note right of completed
        Somente leitura
        Aparece no histórico
    end note
```

---

## Aluno consulta treino do dia

```mermaid
flowchart TD
    Start([Aluno logado]) --> GetDay[Calcula day_of_week atual]
    GetDay --> APICall[GET /me/training/days/day_of_week]
    APICall --> HasActiveTraining{Treino ativo existe?}
    HasActiveTraining -->|Não| NoTraining[Exibe: Aguardando treino]
    HasActiveTraining -->|Sim| HasDay{Dia configurado?}
    HasDay -->|Não| RestDay[Exibe: Dia de descanso]
    HasDay -->|Sim| RenderExercises[Renderiza lista exercícios]
    RenderExercises --> ShowImages[Exibe imagens ilustrativas]
    ShowImages --> ShowDates[Exibe start_date / end_date]
    ShowDates --> ShowCheckIn{Já fez check-in hoje?}
    ShowCheckIn -->|Sim| CheckedIn[Badge: Presença registrada]
    ShowCheckIn -->|Não| CheckInBtn[Botão: Registrar presença]
    CheckedIn --> Done([Tela completa])
    CheckInBtn --> Done
```

---

## Aluno registra check-in

```mermaid
flowchart TD
    Start([Aluno clica Check-in]) --> APICall[POST /me/attendance/check-in]
    APICall --> HasActiveTraining{Treino ativo na data?}
    HasActiveTraining -->|Não| Error400[400 TRAINING_NOT_ACTIVE]
    HasActiveTraining -->|Sim| AlreadyChecked{Check-in hoje existe?}
    AlreadyChecked -->|Sim| Error409[409 DUPLICATE_CHECKIN]
    AlreadyChecked -->|Não| InsertRecord[INSERT attendance_records]
    InsertRecord --> Return201[201 Check-in registrado]
    Return201 --> UpdateUI[Atualiza UI: badge presença]
    UpdateUI --> Done([Sucesso])
```

---

## Aluno envia foto de evolução

```mermaid
flowchart TD
    Start([Aluno clica Enviar foto]) --> SelectFile[Seleciona arquivo câmera/galeria]
    SelectFile --> ClientValidate{Formato e tamanho OK?}
    ClientValidate -->|Não| ClientError[Exibe erro local]
    ClientValidate -->|Sim| FillForm[Preenche tipo, peso, data]
    FillForm --> Submit[POST /me/progress/photos multipart]
    Submit --> ServerValidate{Validação servidor}
    ServerValidate -->|MIME inválido| Error422[422 VALIDATION_ERROR]
    ServerValidate -->|> 5MB| Error422
    ServerValidate -->|OK| SaveFile[Salva em uploads/students/id/uuid.ext]
    SaveFile --> InsertDB[INSERT progress_photos]
    InsertDB --> Return201[201 Foto registrada]
    Return201 --> UpdateGallery[Atualiza galeria evolução]
    UpdateGallery --> Done([Sucesso])
```

---

## Admin visualiza relatório de frequência

```mermaid
flowchart TD
    Start([Admin acessa Relatórios]) --> SelectPeriod[Seleciona período]
    SelectPeriod --> APICall[GET /reports/attendance?start&end]
    APICall --> Aggregate[Service agrega check-ins por aluno]
    Aggregate --> CalcRate[Calcula taxa: check-ins / esperado]
    CalcRate --> Return200[200 Lista alunos + taxas]
    Return200 --> RenderTable[Renderiza tabela]
    RenderTable --> DrillDown{Admin clica aluno?}
    DrillDown -->|Sim| StudentDetail[GET /students/id/attendance]
    StudentDetail --> RenderCalendar[Renderiza calendário check-ins]
    DrillDown -->|Não| Done([Relatório exibido])
    RenderCalendar --> Done
```

### Cálculo da taxa de frequência

```
taxa = (check_ins_no_periodo / sessoes_esperadas) × 100

sessoes_esperadas = dias_de_treino_por_semana × semanas_no_periodo

Exemplo:
  Treino: seg, qua, sex (3 dias/semana)
  Período: 4 semanas
  Esperado: 12 sessões
  Check-ins: 9
  Taxa: 75%
```

---

## Upload de imagem de exercício

```mermaid
flowchart TD
    Start([Admin no exercício]) --> SelectImage[Seleciona imagem]
    SelectImage --> CheckCount{Já tem 5 imagens?}
    CheckCount -->|Sim| Error400[400 Limite atingido]
    CheckCount -->|Não| Submit[POST /exercises/id/images multipart]
    Submit --> ValidateFile{MIME + magic bytes OK?}
    ValidateFile -->|Não| Error422[422 VALIDATION_ERROR]
    ValidateFile -->|Sim| SaveFile[Salva uploads/exercises/id/uuid.ext]
    SaveFile --> InsertDB[INSERT exercise_images]
    InsertDB --> Return201[201 Imagem anexada]
    Return201 --> UpdateGallery[Atualiza galeria exercício]
    UpdateGallery --> Done([Sucesso])
```

---

## Documentos relacionados

- [02-regras-de-negocio.md](02-regras-de-negocio.md) — Regras RN-* referenciadas nos fluxos
- [04-autenticacao.md](04-autenticacao.md) — Detalhes JWT
- [05-api-rest.md](05-api-rest.md) — Endpoints de cada fluxo
- [06-dashboard-admin.md](06-dashboard-admin.md) — Telas admin
- [07-area-aluno.md](07-area-aluno.md) — Telas aluno
