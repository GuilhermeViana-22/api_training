#!/usr/bin/env bash
# Teste integrado Smart Training API
set -euo pipefail

BASE="http://localhost:8001/api/v1"
PASS=0
FAIL=0

ok() { echo "✅ $1"; PASS=$((PASS+1)); }
fail() { echo "❌ $1"; FAIL=$((FAIL+1)); }

echo "=========================================="
echo " SMART TRAINING — TESTES DE INTEGRAÇÃO"
echo "=========================================="

# ── 1. REGISTER público (não existe — esperado 404) ──
echo -e "\n[1] POST /auth/register (rota pública — não implementada)"
HTTP=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"Senha123!"}')
if [ "$HTTP" = "404" ] || [ "$HTTP" = "405" ]; then
  ok "Register público ausente (HTTP $HTTP) — aluno é cadastrado pelo admin via POST /students"
else
  fail "Register público retornou HTTP $HTTP (esperado 404/405)"
fi

# ── 2. Login admin ──
echo -e "\n[2] POST /auth/login — Administrador"
ADMIN_RESP=$(curl -s -X POST "$BASE/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@smarttraining.com","password":"Admin123!"}')
ADMIN_TOKEN=$(echo "$ADMIN_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null || echo "")
if [ -n "$ADMIN_TOKEN" ]; then
  ok "Admin login OK — token recebido"
else
  fail "Admin login falhou: $ADMIN_RESP"
  exit 1
fi

# ── 3. Admin /me ──
echo -e "\n[3] GET /auth/me — Admin"
ME=$(curl -s "$BASE/auth/me" -H "Authorization: Bearer $ADMIN_TOKEN")
ROLE=$(echo "$ME" | python3 -c "import sys,json; print(json.load(sys.stdin).get('role',''))" 2>/dev/null || echo "")
if [ "$ROLE" = "admin" ]; then
  ok "Admin /me OK — role=admin"
else
  fail "Admin /me falhou: $ME"
fi

# ── 4. Cadastro aluno (register via admin) ──
echo -e "\n[4] POST /students — Cadastro aluno (register pelo admin)"
STUDENT_EMAIL="pedro.teste.$(date +%s)@test.com"
STUDENT_RESP=$(curl -s -X POST "$BASE/students" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$STUDENT_EMAIL\",\"password\":\"Senha123!\",\"full_name\":\"Pedro Teste\",\"goal\":\"Definição muscular\",\"weight_kg\":75}")
STUDENT_ID=$(echo "$STUDENT_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null || echo "")
if [ -n "$STUDENT_ID" ]; then
  ok "Aluno cadastrado — id=$STUDENT_ID email=$STUDENT_EMAIL"
else
  fail "Cadastro aluno falhou: $STUDENT_RESP"
fi

# ── 5. Login aluno ──
echo -e "\n[5] POST /auth/login — Aluno"
STUDENT_LOGIN=$(curl -s -X POST "$BASE/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$STUDENT_EMAIL\",\"password\":\"Senha123!\"}")
STUDENT_TOKEN=$(echo "$STUDENT_LOGIN" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null || echo "")
if [ -n "$STUDENT_TOKEN" ]; then
  ok "Aluno login OK"
else
  fail "Aluno login falhou: $STUDENT_LOGIN"
fi

# ── 6. Aluno /me ──
echo -e "\n[6] GET /auth/me — Aluno"
ST_ME=$(curl -s "$BASE/auth/me" -H "Authorization: Bearer $STUDENT_TOKEN")
ST_ROLE=$(echo "$ST_ME" | python3 -c "import sys,json; print(json.load(sys.stdin).get('role',''))" 2>/dev/null || echo "")
if [ "$ST_ROLE" = "student" ]; then
  ok "Aluno /me OK — role=student"
else
  fail "Aluno /me falhou: $ST_ME"
fi

# ── 7. Admin — listar alunos, opções, relatórios ──
echo -e "\n[7] Rotas admin — students, options, reports"
HTTP_ST=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/students" -H "Authorization: Bearer $ADMIN_TOKEN")
HTTP_OPT=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/students/options" -H "Authorization: Bearer $ADMIN_TOKEN")
HTTP_REP=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/reports/students" -H "Authorization: Bearer $ADMIN_TOKEN")
HTTP_OVR=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/reports/overview" -H "Authorization: Bearer $ADMIN_TOKEN")
[ "$HTTP_ST" = "200" ] && ok "GET /students — 200" || fail "GET /students — $HTTP_ST"
[ "$HTTP_OPT" = "200" ] && ok "GET /students/options — 200" || fail "GET /students/options — $HTTP_OPT"
[ "$HTTP_REP" = "200" ] && ok "GET /reports/students — 200" || fail "GET /reports/students — $HTTP_REP"
[ "$HTTP_OVR" = "200" ] && ok "GET /reports/overview — 200" || fail "GET /reports/overview — $HTTP_OVR"

# ── 8. Criar exercício com descrição completa ──
echo -e "\n[8] POST /exercises — Exercício com descrição"
EX_NAME="Agachamento Livre $(date +%s)"
EX_RESP=$(curl -s -X POST "$BASE/exercises" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"$EX_NAME\",
    \"description\": \"Posicione a barra sobre os trapézios, pés na largura dos ombros, desça até coxa paralela ao chão mantendo coluna neutra. Exercício composto para quadríceps e glúteos.\",
    \"muscle_group\": \"pernas\",
    \"default_sets\": 4,
    \"default_reps\": 12,
    \"default_rest_seconds\": 90
  }")
EX_ID=$(echo "$EX_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null || echo "")
if [ -n "$EX_ID" ]; then
  ok "Exercício criado — id=$EX_ID"
else
  fail "Criar exercício falhou: $EX_RESP"
fi

# ── 9. Upload imagem ilustrativa ──
echo -e "\n[9] POST /exercises/{id}/images — Imagem auxiliar"
# Cria PNG mínimo válido (1x1 pixel)
IMG_FILE="/tmp/test_exercise.png"
python3 -c "
from PIL import Image
img = Image.new('RGB', (100, 100), color=(73, 109, 137))
img.save('$IMG_FILE')
"
IMG_RESP=$(curl -s -X POST "$BASE/exercises/$EX_ID/images" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -F "file=@$IMG_FILE" -F "sort_order=0")
IMG_TYPE=$(echo "$IMG_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('media_type',''))" 2>/dev/null || echo "")
if [ "$IMG_TYPE" = "image" ]; then
  ok "Imagem auxiliar upload OK — media_type=image"
else
  fail "Upload imagem falhou: $IMG_RESP"
fi

# ── 10. Upload vídeo auxiliar (mp4 mínimo) ──
echo -e "\n[10] POST /exercises/{id}/images — Vídeo auxiliar"
# Cria mp4 mínimo (ftyp box) — suficiente para teste de upload
VID_FILE="/tmp/test_exercise.mp4"
printf '\x00\x00\x00\x20ftypmp42\x00\x00\x00\x00mp42isom' > "$VID_FILE"
VID_RESP=$(curl -s -X POST "$BASE/exercises/$EX_ID/images" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -F "file=@$VID_FILE;type=video/mp4" -F "sort_order=1")
VID_TYPE=$(echo "$VID_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('media_type',''))" 2>/dev/null || echo "")
if [ "$VID_TYPE" = "video" ]; then
  ok "Vídeo auxiliar upload OK — media_type=video"
else
  fail "Upload vídeo falhou: $VID_RESP"
fi

# ── 11. Treino completo com reps, descrição e mídia ──
echo -e "\n[11] POST /trainings/complete — Treino completo vinculado ao aluno"
CAT_ID=$(curl -s "$BASE/training-categories" -H "Authorization: Bearer $ADMIN_TOKEN" | python3 -c "import sys,json; print(next(x['id'] for x in json.load(sys.stdin) if x['slug']=='musculacao'))" 2>/dev/null || echo "")
TR_RESP=$(curl -s -X POST "$BASE/trainings/complete" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"student_id\": \"$STUDENT_ID\",
    \"title\": \"Treino Definição — 8 semanas\",
    \"description\": \"Programa focado em definição muscular com treino de pernas na segunda e upper body na quarta. Progressão de carga semanal.\",
    \"category_id\": \"$CAT_ID\",
    \"start_date\": \"2026-07-01\",
    \"end_date\": \"2026-08-31\",
    \"activate\": true,
    \"days\": [
      {
        \"day_of_week\": 0,
        \"label\": \"Segunda — Pernas\",
        \"notes\": \"Aquecimento 10 min bike\",
        \"exercises\": [
          {\"exercise_id\": \"$EX_ID\", \"sets\": 4, \"reps\": 12, \"load_kg\": 60, \"rest_seconds\": 90, \"notes\": \"Cadência 3-1-2\"}
        ]
      },
      {
        \"day_of_week\": 2,
        \"label\": \"Quarta — Upper\",
        \"exercises\": [
          {\"exercise_id\": \"$EX_ID\", \"sets\": 3, \"reps\": 15, \"load_kg\": 40, \"rest_seconds\": 60}
        ]
      }
    ]
  }")
TR_STATUS=$(echo "$TR_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status',''))" 2>/dev/null || echo "")
TR_DAYS=$(echo "$TR_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('days',[])))" 2>/dev/null || echo "0")
TR_REPS=$(echo "$TR_RESP" | python3 -c "
import sys,json
d=json.load(sys.stdin)
if d.get('days'):
  print(d['days'][0]['exercises'][0].get('reps',''))
else:
  print('')
" 2>/dev/null || echo "")
TR_MEDIA=$(echo "$TR_RESP" | python3 -c "
import sys,json
d=json.load(sys.stdin)
if d.get('days') and d['days'][0].get('exercises'):
  imgs = d['days'][0]['exercises'][0].get('images',[])
  print(len(imgs))
else:
  print(0)
" 2>/dev/null || echo "0")

if [ "$TR_STATUS" = "active" ] && [ "$TR_DAYS" = "2" ] && [ "$TR_REPS" = "12" ] && [ "$TR_MEDIA" -ge 1 ]; then
  ok "Treino completo OK — status=active, 2 dias, 12 reps, mídias=$TR_MEDIA"
else
  fail "Treino completo falhou — status=$TR_STATUS days=$TR_DAYS reps=$TR_REPS media=$TR_MEDIA"
  echo "   Resposta: $(echo "$TR_RESP" | python3 -m json.tool 2>/dev/null | head -30)"
fi

# ── 12. Aluno visualiza treino ──
echo -e "\n[12] GET /me/training — Aluno vê treino com mídia"
MY_TR=$(curl -s "$BASE/me/training" -H "Authorization: Bearer $STUDENT_TOKEN")
MY_TITLE=$(echo "$MY_TR" | python3 -c "import sys,json; print(json.load(sys.stdin).get('title',''))" 2>/dev/null || echo "")
MY_EX=$(echo "$MY_TR" | python3 -c "
import sys,json
d=json.load(sys.stdin)
days=d.get('days',[])
if days:
  print(days[0]['exercises'][0].get('reps',''))
else:
  print('')
" 2>/dev/null || echo "")
if [ -n "$MY_TITLE" ] && [ "$MY_EX" = "12" ]; then
  ok "Aluno vê treino — '$MY_TITLE' com $MY_EX reps"
else
  fail "Aluno treino falhou: title=$MY_TITLE reps=$MY_EX"
fi

# ── 13. Relatório individual ──
echo -e "\n[13] GET /reports/students/{id}/monitoring"
MON=$(curl -s "$BASE/reports/students/$STUDENT_ID/monitoring" -H "Authorization: Bearer $ADMIN_TOKEN")
MON_NAME=$(echo "$MON" | python3 -c "import sys,json; print(json.load(sys.stdin).get('student',{}).get('full_name',''))" 2>/dev/null || echo "")
MON_DAYS=$(echo "$MON" | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('training_schedule',[])))" 2>/dev/null || echo "0")
if [ "$MON_NAME" = "Pedro Teste" ] && [ "$MON_DAYS" = "2" ]; then
  ok "Relatório individual OK — $MON_NAME, $MON_DAYS dias de treino"
else
  fail "Relatório falhou: name=$MON_NAME days=$MON_DAYS"
fi

# ── 14. Aluno sem acesso admin ──
echo -e "\n[14] Controle de acesso — aluno bloqueado em rota admin"
HTTP_FORB=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/students" -H "Authorization: Bearer $STUDENT_TOKEN")
if [ "$HTTP_FORB" = "403" ]; then
  ok "Aluno recebe 403 em GET /students"
else
  fail "Aluno deveria receber 403, recebeu $HTTP_FORB"
fi

# ── 15. Categorias de treino (presets) ──
echo -e "\n[15] GET /training-categories — Presets musculação/cardio/calistenia"
CAT_RESP=$(curl -s "$BASE/training-categories" -H "Authorization: Bearer $ADMIN_TOKEN")
CAT_COUNT=$(echo "$CAT_RESP" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo "0")
CAT_SLUGS=$(echo "$CAT_RESP" | python3 -c "import sys,json; print(','.join(sorted(x['slug'] for x in json.load(sys.stdin))))" 2>/dev/null || echo "")
if [ "$CAT_COUNT" = "3" ] && echo "$CAT_SLUGS" | grep -q "musculacao"; then
  ok "Categorias OK — 3 presets ($CAT_SLUGS)"
else
  fail "Categorias falhou: count=$CAT_COUNT slugs=$CAT_SLUGS"
fi
CAT_ID=$(echo "$CAT_RESP" | python3 -c "import sys,json; print(next(x['id'] for x in json.load(sys.stdin) if x['slug']=='musculacao'))" 2>/dev/null || echo "")

# ── 16. Perfil do aluno ──
echo -e "\n[16] PUT /me/profile, /me/password, /me/email — Área do aluno"
PROF_RESP=$(curl -s -X PUT "$BASE/me/profile" \
  -H "Authorization: Bearer $STUDENT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"full_name":"Pedro Teste Atualizado","goal":"Hipertrofia","weight_kg":74.5}')
PROF_NAME=$(echo "$PROF_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('profile',{}).get('full_name',''))" 2>/dev/null || echo "")
PASS_RESP=$(curl -s -X PUT "$BASE/me/password" \
  -H "Authorization: Bearer $STUDENT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"current_password":"Senha123!","new_password":"NovaSenha123!"}')
NEW_EMAIL="pedro.novo.$(date +%s)@test.com"
EMAIL_RESP=$(curl -s -X PUT "$BASE/me/email" \
  -H "Authorization: Bearer $STUDENT_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"new_email\":\"$NEW_EMAIL\",\"password\":\"NovaSenha123!\"}")
EMAIL_OK=$(echo "$EMAIL_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('email',''))" 2>/dev/null || echo "")
if [ "$PROF_NAME" = "Pedro Teste Atualizado" ] && echo "$PASS_RESP" | grep -q "Senha alterada"; then
  ok "Perfil e senha atualizados"
else
  fail "Perfil/senha falhou: name=$PROF_NAME pass=$PASS_RESP"
fi
if [ "$EMAIL_OK" = "$NEW_EMAIL" ]; then
  ok "Email alterado — $NEW_EMAIL"
  STUDENT_EMAIL="$NEW_EMAIL"
  STUDENT_LOGIN=$(curl -s -X POST "$BASE/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$STUDENT_EMAIL\",\"password\":\"NovaSenha123!\"}")
  STUDENT_TOKEN=$(echo "$STUDENT_LOGIN" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null || echo "")
else
  fail "Alterar email falhou: $EMAIL_RESP"
fi

# ── 17. Conclusão de exercícios e dia ──
echo -e "\n[17] POST /me/training/days/{dow}/exercises/{id}/complete"
DAY_RESP=$(curl -s "$BASE/me/training/days/0" -H "Authorization: Bearer $STUDENT_TOKEN")
ENTRY_ID=$(echo "$DAY_RESP" | python3 -c "import sys,json; ex=json.load(sys.stdin).get('exercises',[]); print(ex[0]['id'] if ex else '')" 2>/dev/null || echo "")
if [ -n "$ENTRY_ID" ]; then
  COMP_RESP=$(curl -s -X POST "$BASE/me/training/days/0/exercises/$ENTRY_ID/complete" \
    -H "Authorization: Bearer $STUDENT_TOKEN")
  DAY_DONE=$(echo "$COMP_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('day_completed',False))" 2>/dev/null || echo "False")
  if [ "$DAY_DONE" = "True" ]; then
    ok "Exercício concluído — dia automaticamente finalizado"
  else
    ok "Exercício concluído — aguardando demais exercícios"
    curl -s -X POST "$BASE/me/training/days/0/complete" -H "Authorization: Bearer $STUDENT_TOKEN" >/dev/null
  fi
  DAY_STATUS=$(curl -s "$BASE/me/training/days/0" -H "Authorization: Bearer $STUDENT_TOKEN" | python3 -c "import sys,json; print(json.load(sys.stdin).get('day_completed',False))" 2>/dev/null || echo "False")
  [ "$DAY_STATUS" = "True" ] && ok "Dia de treino marcado como concluído" || fail "Dia não concluído: $DAY_STATUS"
else
  fail "Sem exercícios no dia 0 para testar conclusão"
fi

# ── 18. Foto por dia de treino ──
echo -e "\n[18] POST /me/training/days/{dow}/photos — Evolução por dia"
PHOTO_RESP=$(curl -s -X POST "$BASE/me/training/days/0/photos" \
  -H "Authorization: Bearer $STUDENT_TOKEN" \
  -F "file=@$IMG_FILE" -F "photo_type=front" -F "weight_kg=74.0")
PHOTO_DOW=$(echo "$PHOTO_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('day_of_week',''))" 2>/dev/null || echo "")
if [ "$PHOTO_DOW" = "0" ]; then
  ok "Foto de evolução por dia OK — day_of_week=0"
else
  fail "Foto por dia falhou: $PHOTO_RESP"
fi

echo -e "\n=========================================="
echo " RESULTADO: $PASS passou | $FAIL falhou"
echo "=========================================="
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
