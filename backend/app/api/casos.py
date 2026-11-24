"""Endpoints de casos (expedientes del despacho).

CRUD básico + endpoint de detalle que devuelve los actos asociados con su
veredicto vigente, y el resumen jurídico computado por reglas.
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import case, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.classify import _via_inmediatez
from app.api.deps import current_user
from app.db.models import Caso, Classification, ClassificationValidation, User
from app.db.session import get_db
from app.schemas.casos import (
    ActoEnCaso,
    CasoCreate,
    CasoDetail,
    CasoListItem,
    CasoListResponse,
    CasoResumen,
    CasoSinteticoRequest,
    CasoUpdate,
    EjecutoriasImportRequest,
    EjecutoriasImportResponse,
)
from app.services.caso_resumen import construir_resumen
from app.services.caso_sintetico import generar_caso_sintetico

router = APIRouter(prefix="/casos", tags=["casos"])


@router.get("", response_model=CasoListResponse)
def list_casos(
    archived: Literal["activos", "archivados", "todos"] = "activos",
    q: str | None = Query(default=None, min_length=2, max_length=200),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),  # noqa: ARG001
) -> CasoListResponse:
    stmt = select(Caso).order_by(Caso.updated_at.desc())
    if archived == "activos":
        stmt = stmt.where(Caso.archived_at.is_(None))
    elif archived == "archivados":
        stmt = stmt.where(Caso.archived_at.is_not(None))
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(
            func.lower(Caso.identificador).like(like)
            | func.lower(Caso.descripcion).like(like)
        )

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    casos = db.scalars(stmt.limit(limit).offset(offset)).all()

    if not casos:
        return CasoListResponse(items=[], total=total, limit=limit, offset=offset)

    # Conteos por caso en una sola query (case_id IN ...)
    caso_ids = [c.id for c in casos]
    counts = dict(
        db.execute(
            select(Classification.case_id, func.count(Classification.id))
            .where(Classification.case_id.in_(caso_ids))
            .group_by(Classification.case_id)
        ).all()
    )
    indirectos_q = dict(
        db.execute(
            select(Classification.case_id, func.count(Classification.id))
            .where(
                Classification.case_id.in_(caso_ids),
                Classification.prediccion.in_(
                    [
                        "fuera_juicio",
                        "en_juicio_imposible",
                        "tercero_extrano",
                        "post_juicio_general",
                        "post_juicio_ejecucion",
                        "adjetivo",  # legacy
                    ]
                ),
            )
            .group_by(Classification.case_id)
        ).all()
    )
    directos_q = dict(
        db.execute(
            select(Classification.case_id, func.count(Classification.id))
            .where(
                Classification.case_id.in_(caso_ids),
                Classification.prediccion.in_(
                    ["en_juicio_diferida", "sentencia_definitiva", "sustantivo"]
                ),
            )
            .group_by(Classification.case_id)
        ).all()
    )
    prematuros_q = dict(
        db.execute(
            select(Classification.case_id, func.count(Classification.id))
            .where(
                Classification.case_id.in_(caso_ids),
                Classification.prediccion == "post_juicio_prematuro",
            )
            .group_by(Classification.case_id)
        ).all()
    )

    items = [
        CasoListItem(
            id=c.id,
            identificador=c.identificador,
            descripcion=c.descripcion,
            materia=c.materia,
            created_at=c.created_at,
            archived_at=c.archived_at,
            n_actos=int(counts.get(c.id, 0)),
            n_indirectos=int(indirectos_q.get(c.id, 0)),
            n_directos=int(directos_q.get(c.id, 0)),
            n_prematuros=int(prematuros_q.get(c.id, 0)),
        )
        for c in casos
    ]
    return CasoListResponse(items=items, total=total, limit=limit, offset=offset)


@router.post("", response_model=CasoDetail, status_code=201)
def create_caso(
    body: CasoCreate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> CasoDetail:
    caso = Caso(
        identificador=body.identificador.strip(),
        descripcion=body.descripcion,
        materia=body.materia,
        created_by=user.id,
    )
    db.add(caso)
    try:
        db.commit()
    except IntegrityError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Identificador '{body.identificador}' ya existe para este usuario.",
        ) from e
    db.refresh(caso)
    return _to_detail(db, caso)


@router.post("/sintetico-aleatorio", response_model=CasoDetail, status_code=201)
def crear_caso_sintetico(
    body: CasoSinteticoRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> CasoDetail:
    """Crea un caso de práctica con N actos generados de plantillas
    paramétricas. El modelo activo los clasifica como faría con cualquier
    acto real — eso permite al proyectista practicar firmar / corregir.

    Marcado con `materia='sintetico'` para distinguirlo de expedientes
    reales. NO contamina el corpus de reentreno: el dataset de reentreno
    sólo toma classifications con `aprobado_para_corpus=TRUE`, lo que
    requiere acción explícita de un socio.
    """
    try:
        caso = generar_caso_sintetico(
            db=db,
            user=user,
            n_actos=body.n_actos,
            categorias_objetivo=body.categorias_objetivo or None,
            seed=body.seed,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _to_detail(db, caso)


@router.post(
    "/import-ejecutorias",
    response_model=EjecutoriasImportResponse,
    status_code=201,
)
def import_ejecutorias(
    body: EjecutoriasImportRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> EjecutoriasImportResponse:
    """Crea un `Caso` por cada ejecutoria de amparo del SJF.

    - `identificador`: `SJF-EXEC-{ius}` (único por usuario via índice DB).
    - `descripcion`: encabezado con metadata SJF + extracto del acto reclamado.
    - `materia`: `sjf_ejecutoria`.

    Los duplicados (mismo ius re-importado por el mismo usuario) se ignoran
    silenciosamente. No crea `Classification` — el proyectista entra al caso,
    lee la descripción, identifica el acto reclamado preciso, y dispara
    `POST /classify` con `case_id` para asociarlo.
    """
    creados = 0
    duplicados = 0
    invalidos = 0
    caso_ids: list[uuid.UUID] = []

    for item in body.items:
        identificador = f"SJF-EXEC-{item.registro_sjf}"

        # Pre-check: existencia idempotente para este usuario.
        existe = db.scalar(
            select(Caso.id).where(
                Caso.created_by == user.id,
                Caso.identificador == identificador,
            )
        )
        if existe is not None:
            duplicados += 1
            continue

        # Encabezado compacto + acto reclamado. Cabe en max_length=4000.
        header_lines = [
            f"SJF ius={item.registro_sjf} · {item.tipo_asunto}",
            item.rubro,
            f"[extracción: {item.metodo_extraccion}]"
            + (f" · publ. {item.fecha_publ}" if item.fecha_publ else "")
            + (f" · {item.instancia}" if item.instancia else ""),
        ]
        if item.url_semanario:
            header_lines.append(item.url_semanario)
        header = "\n".join(header_lines)

        acto = item.acto_reclamado_candidato.strip()
        # Reserva ~200 chars al header, deja resto para acto.
        max_acto = 4000 - len(header) - 10  # 10 = '\n\n---\n\n'
        if len(acto) > max_acto:
            acto = acto[: max_acto - 1].rstrip() + "…"
        descripcion = f"{header}\n\n---\n\n{acto}"

        caso = Caso(
            identificador=identificador,
            descripcion=descripcion,
            materia="sjf_ejecutoria",
            created_by=user.id,
        )
        db.add(caso)
        try:
            db.commit()
        except IntegrityError:
            # Race: alguien lo insertó entre el check y el commit. Suma duplicado.
            db.rollback()
            duplicados += 1
            continue
        except Exception:  # noqa: BLE001
            db.rollback()
            invalidos += 1
            continue

        db.refresh(caso)
        caso_ids.append(caso.id)
        creados += 1

    return EjecutoriasImportResponse(
        creados=creados,
        duplicados=duplicados,
        invalidos=invalidos,
        caso_ids=caso_ids,
    )


@router.get("/{caso_id}", response_model=CasoDetail)
def get_caso(
    caso_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),  # noqa: ARG001
) -> CasoDetail:
    caso = db.get(Caso, caso_id)
    if caso is None:
        raise HTTPException(status_code=404, detail="caso no existe")
    return _to_detail(db, caso)


@router.patch("/{caso_id}", response_model=CasoDetail)
def update_caso(
    caso_id: uuid.UUID,
    body: CasoUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> CasoDetail:
    caso = db.get(Caso, caso_id)
    if caso is None:
        raise HTTPException(status_code=404, detail="caso no existe")
    if caso.created_by != user.id and user.rol not in ("socio", "admin"):
        raise HTTPException(status_code=403, detail="solo el creador o un socio")
    if body.identificador is not None:
        caso.identificador = body.identificador.strip()
    if body.descripcion is not None:
        caso.descripcion = body.descripcion
    if body.materia is not None:
        caso.materia = body.materia
    if body.archived is not None:
        caso.archived_at = dt.datetime.now(dt.UTC) if body.archived else None
    try:
        db.commit()
    except IntegrityError as e:
        raise HTTPException(status_code=409, detail=f"identificador duplicado: {e.orig}") from e
    db.refresh(caso)
    return _to_detail(db, caso)


@router.get("/{caso_id}/resumen", response_model=CasoResumen)
def get_resumen(
    caso_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),  # noqa: ARG001
) -> CasoResumen:
    caso = db.get(Caso, caso_id)
    if caso is None:
        raise HTTPException(status_code=404, detail="caso no existe")
    actos = _build_actos(db, caso_id)
    return construir_resumen(caso_id, actos)


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def _build_actos(db: Session, caso_id: uuid.UUID) -> list[ActoEnCaso]:
    classifications = list(
        db.scalars(
            select(Classification)
            .where(Classification.case_id == caso_id)
            .order_by(Classification.created_at.asc())
        )
    )
    if not classifications:
        return []

    class_ids = [c.id for c in classifications]
    # validations vigentes: las que NO son superseded por ninguna otra
    vals = list(
        db.scalars(
            select(ClassificationValidation).where(
                ClassificationValidation.classification_id.in_(class_ids)
            )
        )
    )
    superseded = {v.supersedes_id for v in vals if v.supersedes_id}
    vigentes_por_class: dict[uuid.UUID, ClassificationValidation] = {}
    for v in vals:
        if v.id in superseded:
            continue
        vigentes_por_class[v.classification_id] = v

    actos: list[ActoEnCaso] = []
    for c in classifications:
        v = vigentes_por_class.get(c.id)
        veredicto = v.veredicto if v else None
        clasif_final = (
            v.clasificacion_corregida
            if v and v.veredicto == "rechaza"
            else (c.prediccion if v and v.veredicto == "acepta" else None)
        )
        via, inmediatez, alerta = _via_inmediatez(c.prediccion)
        prob = (
            float(c.prob_categoria)
            if c.prob_categoria is not None
            else (float(c.prob_adjetivo) if c.prob_adjetivo is not None else None)
        )
        from app.api.classify import _requires_review

        preview = c.acto_reclamado.strip()
        if len(preview) > 220:
            preview = preview[:220].rstrip() + "…"
        actos.append(
            ActoEnCaso(
                classification_id=c.id,
                acto_preview=preview,
                categoria=c.prediccion,  # type: ignore[arg-type]
                via=via,  # type: ignore[arg-type]
                inmediatez=inmediatez,  # type: ignore[arg-type]
                alerta=alerta,
                prob_categoria=prob,
                requiere_revision_humana=_requires_review(prob),
                veredicto_vigente=veredicto,  # type: ignore[arg-type]
                clasificacion_final=clasif_final,  # type: ignore[arg-type]
                created_at=c.created_at,
            )
        )
    return actos


def _to_detail(db: Session, caso: Caso) -> CasoDetail:
    creator = db.get(User, caso.created_by)
    actos = _build_actos(db, caso.id)
    resumen = construir_resumen(caso.id, actos)
    return CasoDetail(
        id=caso.id,
        identificador=caso.identificador,
        descripcion=caso.descripcion,
        materia=caso.materia,
        created_by=caso.created_by,
        created_by_email=creator.email if creator else str(caso.created_by),
        created_at=caso.created_at,
        updated_at=caso.updated_at,
        archived_at=caso.archived_at,
        actos=actos,
        resumen=resumen,
    )
