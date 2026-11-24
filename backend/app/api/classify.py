import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.core.config import settings
from app.db.models import (
    Caso,
    Classification,
    ClassificationValidation,
    ModelVersion,
    User,
)
from app.db.session import get_db
from app.ml.predict import ALERTA_PREMATURIDAD, VIA_INMEDIATEZ
from app.ml.preprocessing import acto_sha256
from app.schemas.classify import (
    ClassificationDetail,
    ClassificationListItem,
    ClassificationListResponse,
    ClassifyRequest,
    ClassifyResponse,
    DuplicadoItem,
    DuplicadosResponse,
    ValidationDetail,
)
from app.services.classifier import classify_and_log
from app.services.signature import verify

router = APIRouter(tags=["classify"])


def _requires_review(prob: float | None) -> bool:
    """True si la categoría dominante no supera ampliamente el umbral.

    Para multiclase: prob_categoria es la prob de la categoría dominante.
    Si está debajo de classify_review_upper, el modelo no está seguro.
    """
    if prob is None:
        return True
    return prob < settings.classify_review_upper


def _via_inmediatez(categoria: str) -> tuple[str, str, str | None]:
    derivado = VIA_INMEDIATEZ.get(categoria, {"via": "ninguna", "inmediatez": "inmediato"})
    alerta = ALERTA_PREMATURIDAD if categoria == "post_juicio_prematuro" else None
    return derivado["via"], derivado["inmediatez"], alerta


@router.post("/classify", response_model=ClassifyResponse, status_code=201)
def classify(
    body: ClassifyRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> ClassifyResponse:
    record = classify_and_log(
        db=db,
        acto_reclamado=body.acto_reclamado,
        user_id=user.id,
        case_id=body.case_id,
    )
    mv_version = db.get(ModelVersion, record.model_version_id).version
    p = float(record.prob_categoria) if record.prob_categoria is not None else 0.0
    via, inmediatez, alerta = _via_inmediatez(record.prediccion)
    return ClassifyResponse(
        classification_id=record.id,
        acto_sha256=record.acto_sha256,
        model_version=mv_version,
        categoria=record.prediccion,  # type: ignore[arg-type]
        via=via,  # type: ignore[arg-type]
        inmediatez=inmediatez,  # type: ignore[arg-type]
        alerta=alerta,
        prob_categoria=p,
        prob_por_clase=record.prob_por_clase or {},
        requiere_revision_humana=_requires_review(p),
        top_features=record.top_features,
        top_analogas=record.top_analogas,
        created_at=record.created_at,
    )


@router.get("/classifications", response_model=ClassificationListResponse)
def list_classifications(
    sha: str | None = Query(default=None, min_length=2, max_length=64),
    q: str | None = Query(default=None, min_length=2, max_length=200),
    categoria: str | None = None,
    estado: Literal["pendiente", "validada"] | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),  # noqa: ARG001
) -> ClassificationListResponse:
    using_fts = bool(q)
    if using_fts:
        # FTS sobre acto_reclamado (tsv pre-calculado por trigger BEFORE INSERT)
        rank = func.ts_rank_cd(text("tsv"), func.plainto_tsquery("spanish", q))
        stmt = (
            select(Classification, rank.label("rank"))
            .where(text("tsv @@ plainto_tsquery('spanish', :q)").bindparams(q=q))
            .order_by(rank.desc())
        )
    else:
        stmt = select(Classification).order_by(Classification.created_at.desc())
    if sha:
        stmt = stmt.where(Classification.acto_sha256.ilike(f"{sha.lower()}%"))
    if categoria:
        stmt = stmt.where(Classification.prediccion == categoria)
    if estado:
        validated_ids_subq = (
            select(ClassificationValidation.classification_id).distinct().scalar_subquery()
        )
        if estado == "validada":
            stmt = stmt.where(Classification.id.in_(validated_ids_subq))
        else:
            stmt = stmt.where(Classification.id.not_in(validated_ids_subq))

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    if using_fts:
        rows = db.execute(stmt.limit(limit).offset(offset)).all()
        classifications = [r[0] for r in rows]
    else:
        classifications = list(db.scalars(stmt.limit(limit).offset(offset)).all())

    if not classifications:
        return ClassificationListResponse(items=[], total=total, limit=limit, offset=offset)

    class_ids = [c.id for c in classifications]
    mv_ids = {c.model_version_id for c in classifications}
    user_ids = {c.created_by for c in classifications}

    mv_versions: dict[uuid.UUID, str] = {
        mv.id: mv.version
        for mv in db.scalars(select(ModelVersion).where(ModelVersion.id.in_(mv_ids)))
    }
    user_emails: dict[uuid.UUID, str] = {
        u.id: u.email for u in db.scalars(select(User).where(User.id.in_(user_ids)))
    }
    all_vals = list(
        db.scalars(
            select(ClassificationValidation).where(
                ClassificationValidation.classification_id.in_(class_ids)
            )
        )
    )
    superseded = {v.supersedes_id for v in all_vals if v.supersedes_id is not None}
    vals_by_class: dict[uuid.UUID, list[ClassificationValidation]] = {}
    for v in all_vals:
        vals_by_class.setdefault(v.classification_id, []).append(v)

    items: list[ClassificationListItem] = []
    for c in classifications:
        vals = vals_by_class.get(c.id, [])
        vigente = next((v for v in vals if v.id not in superseded), None)
        if vigente is None:
            veredicto_vigente = None
            clasificacion_final = None
        else:
            veredicto_vigente = vigente.veredicto
            clasificacion_final = (
                vigente.clasificacion_corregida
                if vigente.veredicto == "rechaza"
                else c.prediccion
            )
        preview = c.acto_reclamado.strip()
        if len(preview) > 200:
            preview = preview[:200].rstrip() + "…"
        # via derivado de la categoría persistida
        via, _, _ = _via_inmediatez(c.prediccion)
        prob = (
            float(c.prob_categoria)
            if c.prob_categoria is not None
            else (float(c.prob_adjetivo) if c.prob_adjetivo is not None else None)
        )
        items.append(
            ClassificationListItem(
                id=c.id,
                acto_sha256=c.acto_sha256,
                acto_preview=preview,
                model_version=mv_versions.get(c.model_version_id, ""),
                categoria=c.prediccion,  # type: ignore[arg-type]
                via=via,  # type: ignore[arg-type]
                prob_categoria=prob,
                requiere_revision_humana=_requires_review(prob),
                created_at=c.created_at,
                created_by_email=user_emails.get(c.created_by, ""),
                veredicto_vigente=veredicto_vigente,  # type: ignore[arg-type]
                clasificacion_final=clasificacion_final,  # type: ignore[arg-type]
                n_validaciones=len(vals),
            )
        )

    return ClassificationListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/classifications/duplicados", response_model=DuplicadosResponse)
def duplicados_de_acto(
    texto: str = Query(min_length=10, max_length=20000),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),  # noqa: ARG001
) -> DuplicadosResponse:
    """Devuelve clasificaciones previas con el MISMO SHA256 (texto normalizado).

    El SHA se calcula sobre texto normalizado (lowercase, sin acentos,
    espacios colapsados) — eso significa que pegar el mismo acto con
    formato distinto produce el mismo hash. Útil para:

      • Avisar al proyectista "este acto ya fue clasificado N veces antes".
      • Mostrar el veredicto vigente de la primera clasificación para
        mantener coherencia entre expedientes.
      • Evitar contaminar el log con duplicados (aunque la inmutabilidad
        permite tenerlos, mejor advertir).

    Esta ruta se registra ANTES de `/classifications/{classification_id}`
    para que FastAPI no la confunda con un UUID inválido.
    """
    sha = acto_sha256(texto)
    rows = list(
        db.scalars(
            select(Classification)
            .where(Classification.acto_sha256 == sha)
            .order_by(Classification.created_at.asc())
        )
    )
    if not rows:
        return DuplicadosResponse(acto_sha256=sha, n_previas=0, previas=[])

    # Batch lookups: emails de autores, validaciones vigentes, identificador de caso
    user_ids = {r.created_by for r in rows}
    emails = {
        u.id: u.email
        for u in db.scalars(select(User).where(User.id.in_(user_ids)))
    }
    case_ids = {r.case_id for r in rows if r.case_id is not None}
    casos_map: dict[uuid.UUID, str] = {}
    if case_ids:
        for c in db.scalars(select(Caso).where(Caso.id.in_(case_ids))):
            casos_map[c.id] = c.identificador

    # Vigentes por classification
    class_ids = [r.id for r in rows]
    vals = list(
        db.scalars(
            select(ClassificationValidation).where(
                ClassificationValidation.classification_id.in_(class_ids)
            )
        )
    )
    superseded = {v.supersedes_id for v in vals if v.supersedes_id is not None}
    vigentes: dict[uuid.UUID, ClassificationValidation] = {}
    for v in vals:
        if v.id in superseded:
            continue
        vigentes[v.classification_id] = v

    previas: list[DuplicadoItem] = []
    for r in rows:
        v = vigentes.get(r.id)
        veredicto = v.veredicto if v else None
        if v and v.veredicto == "rechaza":
            clasif_final = v.clasificacion_corregida
        elif v and v.veredicto == "acepta":
            clasif_final = r.prediccion
        else:
            clasif_final = None
        previas.append(
            DuplicadoItem(
                classification_id=r.id,
                created_at=r.created_at,
                created_by_email=emails.get(r.created_by, str(r.created_by)),
                categoria_predicha=r.prediccion,  # type: ignore[arg-type]
                veredicto_vigente=veredicto,  # type: ignore[arg-type]
                clasificacion_final=clasif_final,  # type: ignore[arg-type]
                case_id=r.case_id,
                case_identificador=casos_map.get(r.case_id) if r.case_id else None,
            )
        )

    return DuplicadosResponse(
        acto_sha256=sha, n_previas=len(previas), previas=previas
    )


@router.get("/classifications/{classification_id}", response_model=ClassificationDetail)
def get_classification(
    classification_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),  # noqa: ARG001  enforce auth
) -> ClassificationDetail:
    c = db.get(Classification, classification_id)
    if c is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="no existe")

    mv = db.get(ModelVersion, c.model_version_id)
    creator = db.get(User, c.created_by)

    validations = (
        db.execute(
            select(ClassificationValidation)
            .where(ClassificationValidation.classification_id == classification_id)
            .order_by(ClassificationValidation.validated_at.asc())
        )
        .scalars()
        .all()
    )
    superseded_ids = {v.supersedes_id for v in validations if v.supersedes_id is not None}

    user_cache: dict[uuid.UUID, str] = {}

    def _email(uid: uuid.UUID) -> str:
        if uid not in user_cache:
            u = db.get(User, uid)
            user_cache[uid] = u.email if u else str(uid)
        return user_cache[uid]

    historia = [
        ValidationDetail(
            id=v.id,
            validated_by=v.validated_by,
            validated_by_email=_email(v.validated_by),
            validated_at=v.validated_at,
            veredicto=v.veredicto,
            clasificacion_corregida=v.clasificacion_corregida,
            comentario=v.comentario,
            firma_sha256=v.firma_sha256,
            firma_valida=verify(v.firma_payload, v.firma_sha256),
            supersedes_id=v.supersedes_id,
            es_vigente=(v.id not in superseded_ids),
        )
        for v in validations
    ]
    vigente = next((h for h in historia if h.es_vigente), None)

    via, inmediatez, alerta = _via_inmediatez(c.prediccion)
    prob = (
        float(c.prob_categoria)
        if c.prob_categoria is not None
        else (float(c.prob_adjetivo) if c.prob_adjetivo is not None else None)
    )
    return ClassificationDetail(
        id=c.id,
        acto_reclamado=c.acto_reclamado,
        acto_sha256=c.acto_sha256,
        model_version=mv.version,
        categoria=c.prediccion,  # type: ignore[arg-type]
        via=via,  # type: ignore[arg-type]
        inmediatez=inmediatez,  # type: ignore[arg-type]
        alerta=alerta,
        prob_categoria=prob,
        prob_por_clase=c.prob_por_clase,
        requiere_revision_humana=_requires_review(prob),
        top_features=c.top_features,
        top_analogas=c.top_analogas,
        created_at=c.created_at,
        created_by=c.created_by,
        created_by_email=creator.email if creator else str(c.created_by),
        historia_validaciones=historia,
        vigente=vigente,
    )
