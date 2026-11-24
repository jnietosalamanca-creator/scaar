# SCAAR

**Sistema de Clasificación Automatizada de Actos Reclamados.**
Clasificador binario para juicio de amparo en México: determina si el acto reclamado es de imposible reparación **adjetiva** (amparo indirecto inmediato) o **sustantiva** (diferida al amparo directo).

> Decisión Gate-2 de alta consecuencia: equivocarse implica desechamiento de la demanda. La clasificación del modelo siempre es revisada por un proyectista; el sistema produce un **Log de Razonamiento Jurídico** inmutable como evidencia.

## Estado actual

Pipeline end-to-end completo con corpus dummy:
- Esquema PostgreSQL con triggers de inmutabilidad para el log.
- Modelos SQLAlchemy 2.x.
- Pipeline ML (TF-IDF + LinearSVC calibrado) con explicación: top-5 features y top-3 análogas por similitud coseno.
- Endpoint `POST /classify` que persiste el log inmutable.
- Smoke test del ML probado: 0.830 P(adj) en caso adjetivo claro, 0.117 en sustantivo claro, ambigüedad detectada en el caso intermedio.

Pendientes: auth JWT real, endpoint de validación con firma HMAC, frontend.

## Estructura

```
scaar/
├── backend/         FastAPI + scikit-learn (Python 3.11+)
├── frontend/        Next.js + Tailwind
├── db/
│   └── schema.sql   DDL completo (corre en init de Postgres)
├── docker-compose.yml
└── .env.example
```

## Levantar en local

Necesitas Docker Desktop (o equivalente: OrbStack, Colima).

```bash
cp .env.example .env
# edita JWT_SECRET_KEY y VERDICT_HMAC_SECRET con valores aleatorios:
#   python3 -c "import secrets; print(secrets.token_urlsafe(48))"

# 1. Levantar Postgres + backend
docker compose up -d --build
docker compose logs db | grep -i "ready\|error"

# 2. Sembrar usuarios y corpus dummy (una sola vez)
docker compose exec backend python -m app.scripts.seed_users
docker compose exec backend python -m app.scripts.seed_corpus

# 3. Entrenar el primer modelo
docker compose exec backend python -m app.ml.train --version v0.1.0

# 4. Probar el endpoint
curl -X POST http://localhost:8000/classify \
  -H "Content-Type: application/json" \
  -H "X-User-Email: proyectista@scaar.local" \
  -d '{"acto_reclamado": "El juez negó la admisión de la prueba pericial ofrecida en tiempo, lo que afecta las defensas del quejoso y trasciende al resultado del fallo."}'
```

El `schema.sql` se aplica una sola vez, en el primer arranque del volumen `scaar_pgdata`. Para reaplicar:
```bash
docker compose down -v && docker compose up -d --build
```

### Smoke test del pipeline ML (sin DB)

Útil mientras Docker no está disponible o para probar cambios al modelo sin sembrar BD:

```bash
python3 -m venv .venv-test
.venv-test/bin/pip install scikit-learn numpy scipy joblib unidecode
.venv-test/bin/python scripts/smoke_ml.py
```

## Modelo de datos — decisiones clave

| Tabla | Mutabilidad | Razón |
|---|---|---|
| `users` | mutable | datos administrativos |
| `tesis` | mutable | corpus crece con el tiempo |
| `model_versions` | append-only de facto | un modelo entrenado nunca cambia |
| `classifications` | **inmutable (trigger)** | log de evidencia jurídica |
| `classification_validations` | **append-only con supersede** | línea temporal del veredicto |

**Por qué importa:**
- Si el desechamiento se litiga, el despacho debe poder demostrar *qué dijo el modelo el día X y qué firmó el proyectista*. La inmutabilidad de `classifications` es la columna vertebral de esa defensa.
- `top_features` y `top_analogas` se guardan **denormalizados (JSONB)** en la fila para que el log sea reproducible aunque cambie el corpus.
- La firma del proyectista es **HMAC-SHA256** sobre payload canónico — verificable sin la app, fuera del MVP se puede agregar FIEL.
- `aprobado_para_corpus` separa "el proyectista corrigió" de "este caso entra al dataset de reentreno" — sólo un socio puede activar el segundo, evitando envenenamiento del corpus por errores de juniors.

## Próximos pasos

- [x] Pipeline ML con corpus dummy end-to-end + smoke test.
- [x] Endpoint `POST /classify` que persiste el log completo.
- [x] Auth JWT real (reemplaza el header `X-User-Email`).
- [x] Endpoint `POST /classifications/{id}/validate` con firma HMAC.
- [x] Endpoint `GET /classifications/{id}` para auditoría.
- [x] Threshold de confianza: si `0.30 ≤ P(adj) ≤ 0.70` el frontend marca `requiere_revision_humana`.
- [x] UI Next.js: home con listado, /clasificar, /clasificaciones/[id], /corpus, /corpus/etiquetar, /corpus/importar.
- [x] Infraestructura de corpus real: importación, etiquetado humano, reentrenamiento.
- [x] Fetcher SJF (`python -m app.scripts.fetch_sjf`) que baja tesis reales por rango de IUS.
- [ ] Etiquetar suficiente corpus real (~80 tesis adj/sus) para sustituir al dummy en producción.
- [ ] Cambiar localStorage por httpOnly cookie cuando salga de localhost.

## Crecer el corpus real

El corpus arranca con 20 tesis dummy. Para construir uno usable:

1. **Bajar tesis recientes del SJF** filtrando por keywords del dominio:
   ```bash
   cd backend
   .venv/bin/python -m app.scripts.fetch_sjf \
     --ius-from 2031000 --ius-to 2031500 \
     --out /tmp/sjf_lote.jsonl
   ```
   Toma ~80 segundos. Por cada 50 IUS ~30-40 tesis matchean keywords del dominio amparo.

2. **Importar** vía la UI (`/corpus/importar` con rol socio/admin) o vía API:
   ```bash
   curl -X POST http://localhost:8000/tesis/import \
     -H "Authorization: Bearer $TOKEN_ADMIN" \
     -H "Content-Type: application/json" \
     -d "$(jq -s '{fuente:"sjf_scraping", items: .}' /tmp/sjf_lote.jsonl)"
   ```

3. **Etiquetar** una por una en `/corpus/etiquetar` (shortcuts: A=adjetivo, S=sustantivo, N=no_aplica). El modelo SOLO entrena con `adj` y `sus`.

4. **Reentrenar** cuando tengas suficiente:
   ```bash
   .venv/bin/python -m app.ml.train --version v0.3.0
   ```
   Cada `--version` es única e inmutable. Activa automáticamente la nueva.
