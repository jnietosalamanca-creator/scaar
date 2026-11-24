"""Endpoints de salud del modelo activo.

Proveen métricas operativas que complementan las de cross-validation:
  • Distribución de predicciones (qué categorías el modelo realmente dice).
  • Tasa de aceptación del proyectista (cuántas firmas son 'acepta' vs 'rechaza').
  • Matriz simplificada de correcciones (predicha → final) para detectar
    qué clases necesitan más corpus.

El f1 CV del momento del training puede no reflejar el comportamiento en
producción si el corpus inicial era pequeño o sesgado — estas métricas dan
el ángulo complementario.
"""

from __future__ import annotations

import datetime as dt
import subprocess
import sys
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.db.models import (
    Classification,
    ClassificationValidation,
    ModelVersion,
    User,
)
from app.db.session import get_db
from app.schemas.modelo import (
    CategoriaPair,
    ModeloStats,
    ModelVersionListItem,
)

router = APIRouter(prefix="/modelo", tags=["modelo"])

# Universo de categorías nuevas (excluye legacy adj/sus que ya no se predicen)
CATEGORIAS = [
    "fuera_juicio",
    "en_juicio_imposible",
    "en_juicio_diferida",
    "post_juicio_general",
    "post_juicio_ejecucion",
    "post_juicio_prematuro",
    "tercero_extrano",
    "sentencia_definitiva",
]


@router.get("/stats", response_model=ModeloStats)
def modelo_stats(
    db: Session = Depends(get_db),
    user: User = Depends(current_user),  # noqa: ARG001
) -> ModeloStats:
    activo = db.scalar(select(ModelVersion).where(ModelVersion.activo.is_(True)))
    if activo is None:
        # Sin modelo activo no hay nada que reportar
        return ModeloStats(
            version="",
            algoritmo="",
            n_tesis_train=0,
            fecha_corte=__import__("datetime").date.today(),
            metricas={},
            activo=False,
            total_clasificaciones=0,
            distribucion_predicciones={},
            n_validadas=0,
            n_aceptadas=0,
            n_corregidas=0,
            tasa_aceptacion=None,
            correcciones=[],
            clases_no_predichas=list(CATEGORIAS),
        )

    # Distribución de predicciones del modelo activo en TODA la historia.
    dist = dict(
        db.execute(
            select(Classification.prediccion, func.count(Classification.id))
            .where(Classification.model_version_id == activo.id)
            .group_by(Classification.prediccion)
        ).all()
    )
    total = sum(int(v) for v in dist.values())
    no_predichas = [c for c in CATEGORIAS if c not in dist]

    # Validaciones vigentes: las que NO han sido superseded por otra
    val_alias = ClassificationValidation
    superseded_ids_sq = (
        select(val_alias.supersedes_id)
        .where(val_alias.supersedes_id.is_not(None))
        .subquery()
    )
    vigentes = list(
        db.scalars(
            select(val_alias).where(
                val_alias.id.not_in(select(superseded_ids_sq.c.supersedes_id))
            )
        )
    )
    # Filtrar las vigentes que pertenecen a classifications del modelo activo
    class_ids_activo = set(
        db.scalars(
            select(Classification.id).where(Classification.model_version_id == activo.id)
        ).all()
    )
    vigentes_activo = [v for v in vigentes if v.classification_id in class_ids_activo]
    n_validadas = len(vigentes_activo)
    n_aceptadas = sum(1 for v in vigentes_activo if v.veredicto == "acepta")
    n_corregidas = n_validadas - n_aceptadas
    tasa = (n_aceptadas / n_validadas) if n_validadas else None

    # Matriz: (predicha, final) → n. Necesitamos la predicción de cada
    # classification asociada a las validaciones vigentes corregidas.
    pred_por_class = dict(
        db.execute(
            select(Classification.id, Classification.prediccion).where(
                Classification.id.in_([v.classification_id for v in vigentes_activo])
            )
        ).all()
    )
    pares: dict[tuple[str, str], int] = {}
    for v in vigentes_activo:
        pred = pred_por_class.get(v.classification_id, "?")
        final = (
            v.clasificacion_corregida
            if v.veredicto == "rechaza"
            else pred  # acepta = final == predicha
        )
        if final is None:
            continue
        key = (pred, final)
        pares[key] = pares.get(key, 0) + 1

    correcciones = [
        CategoriaPair(predicha=p, final=f, n=n)
        for (p, f), n in sorted(pares.items(), key=lambda kv: -kv[1])
    ]

    return ModeloStats(
        version=activo.version,
        algoritmo=activo.algoritmo,
        n_tesis_train=activo.n_tesis_train,
        fecha_corte=activo.fecha_corte,
        metricas=activo.metricas,
        activo=True,
        total_clasificaciones=total,
        distribucion_predicciones={k: int(v) for k, v in dist.items()},
        n_validadas=n_validadas,
        n_aceptadas=n_aceptadas,
        n_corregidas=n_corregidas,
        tasa_aceptacion=tasa,
        correcciones=correcciones,
        clases_no_predichas=no_predichas,
    )


class ReentrenarRequest(BaseModel):
    version: str = Field(min_length=3, max_length=40, pattern=r"^v?\d+\.\d+\.\d+$")
    user_email: str = "system@scaar.local"


class ReentrenarResponse(BaseModel):
    status: str  # "started"
    version: str
    log_path: str
    pid: int | None
    nota: str


def _run_training(version: str, user_email: str, log_path: str) -> None:
    """Lanza `python -m app.ml.train` como subprocess detached."""
    backend_root = Path(__file__).resolve().parents[2]
    cmd = [
        sys.executable,
        "-m",
        "app.ml.train",
        "--version",
        version,
        "--user-email",
        user_email,
    ]
    with open(log_path, "wb") as log:
        subprocess.Popen(
            cmd,
            cwd=str(backend_root),
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )


@router.post("/reentrenar", response_model=ReentrenarResponse, status_code=202)
def reentrenar(
    body: ReentrenarRequest,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> ReentrenarResponse:
    """Dispara reentrenamiento en background. NO bloquea el request.

    Sólo admin/socio pueden lanzar. El proceso corre como subprocess
    independiente — sobrevive aunque uvicorn se reinicie. El log se
    escribe a /tmp/scaar_train_<version>_<ts>.log.

    Para ver progreso/resultado: leer el log o consultar
    `GET /modelo/versiones` después de unos segundos.
    """
    if user.rol not in ("socio", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Reentrenar requiere rol socio o admin.",
        )
    version = body.version if body.version.startswith("v") else f"v{body.version}"
    # Validar que la versión no exista todavía
    existing = db.scalar(select(ModelVersion).where(ModelVersion.version == version))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"La versión {version} ya existe. Usa otra.",
        )
    ts = dt.datetime.now(dt.UTC).strftime("%Y%m%dT%H%M%SZ")
    log_path = f"/tmp/scaar_train_{version}_{ts}.log"
    background.add_task(_run_training, version, body.user_email, log_path)
    return ReentrenarResponse(
        status="started",
        version=version,
        log_path=log_path,
        pid=None,
        nota=(
            "Reentrenamiento lanzado. Tarda ~5-30 segundos según el tamaño "
            "del corpus. Verifica con GET /modelo/versiones o leyendo el log."
        ),
    )


@router.get("/versiones", response_model=list[ModelVersionListItem])
def list_versiones(
    db: Session = Depends(get_db),
    user: User = Depends(current_user),  # noqa: ARG001
) -> list[ModelVersionListItem]:
    rows = db.scalars(
        select(ModelVersion).order_by(ModelVersion.created_at.desc())
    ).all()
    return [
        ModelVersionListItem(
            id=r.id,
            version=r.version,
            algoritmo=r.algoritmo,
            n_tesis_train=r.n_tesis_train,
            fecha_corte=r.fecha_corte,
            activo=r.activo,
            created_at=r.created_at,
            f1_macro=(
                float(r.metricas.get("f1_macro"))
                if isinstance(r.metricas, dict) and r.metricas.get("f1_macro") is not None
                else None
            ),
        )
        for r in rows
    ]
