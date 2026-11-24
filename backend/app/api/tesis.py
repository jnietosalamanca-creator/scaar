"""Endpoints para gestión del corpus: listar, ver, etiquetar, importar, stats."""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import case, func, select, text
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.core.config import settings
from app.db.models import Tesis, User
from app.db.session import get_db
from app.schemas.tesis import (
    CorpusStats,
    EtiquetaLabel,
    ImportTesisRequest,
    ImportTesisResponse,
    LabelTesisRequest,
    TesisDetail,
    TesisAuditoriaItem,
    TesisInciertaItem,
    TesisListItem,
    TesisListResponse,
    TipoJurisprudencialRequest,
    TopProb,
)

router = APIRouter(prefix="/tesis", tags=["tesis"])


def _require_role(user: User, *allowed: str) -> None:
    if user.rol not in allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Operación restringida a {allowed}; tu rol es '{user.rol}'.",
        )


@router.get("", response_model=TesisListResponse)
def list_tesis(
    estado: Literal["pendiente", "etiquetada", "no_aplica", "lista_train"] | None = None,
    fuente: str | None = None,
    q: str | None = Query(default=None, min_length=2, max_length=200),
    incluir_doctrinas: bool = False,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),  # noqa: ARG001
) -> TesisListResponse:
    # Si hay `q`, usamos full-text search en español con ranking; si no,
    # orden por created_at.
    using_fts = bool(q)
    if using_fts:
        # plainto_tsquery acepta texto libre y maneja stop words / stemming
        tsquery = func.plainto_tsquery("spanish", q)
        rank = func.ts_rank_cd(text("tsv"), tsquery)
        stmt = select(Tesis, rank.label("rank")).where(text("tsv @@ plainto_tsquery('spanish', :q)").bindparams(q=q))
        stmt = stmt.order_by(rank.desc())
    else:
        stmt = select(Tesis).order_by(Tesis.created_at.desc())

    # Por defecto las doctrinas canónicas no aparecen en el listado general —
    # se consultan vía GET /tesis/doctrinas-canonicas.
    if not incluir_doctrinas:
        stmt = stmt.where(Tesis.es_doctrina_canonica.is_(False))
    if estado == "pendiente":
        stmt = stmt.where(Tesis.etiqueta.is_(None))
    elif estado == "etiquetada":
        stmt = stmt.where(Tesis.etiqueta.is_not(None))
    elif estado == "no_aplica":
        stmt = stmt.where(Tesis.etiqueta == "no_aplica")
    elif estado == "lista_train":
        stmt = stmt.where(Tesis.etiqueta.in_(["adjetivo", "sustantivo"]))
    if fuente:
        stmt = stmt.where(Tesis.fuente == fuente)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    if using_fts:
        # Cuando hay FTS, el select trae (Tesis, rank) — extraemos solo Tesis
        result_rows = db.execute(stmt.limit(limit).offset(offset)).all()
        rows = [r[0] for r in result_rows]
    else:
        rows = list(db.scalars(stmt.limit(limit).offset(offset)).all())
    if not rows:
        return TesisListResponse(items=[], total=total, limit=limit, offset=offset)

    user_ids = {r.etiquetada_por for r in rows if r.etiquetada_por is not None}
    emails = (
        {u.id: u.email for u in db.scalars(select(User).where(User.id.in_(user_ids)))}
        if user_ids
        else {}
    )

    items = [
        TesisListItem(
            id=r.id,
            registro_sjf=r.registro_sjf,
            epoca=r.epoca,
            instancia=r.instancia,
            tipo=r.tipo,  # type: ignore[arg-type]
            rubro=r.rubro,
            fecha_publ=r.fecha_publ,
            etiqueta=r.etiqueta,  # type: ignore[arg-type]
            etiquetada_por_email=emails.get(r.etiquetada_por) if r.etiquetada_por else None,
            etiquetada_at=r.etiquetada_at,
            fuente=r.fuente,
            created_at=r.created_at,
            es_doctrina_canonica=r.es_doctrina_canonica,
            tipo_jurisprudencial=r.tipo_jurisprudencial,  # type: ignore[arg-type]
        )
        for r in rows
    ]
    return TesisListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/doctrinas-canonicas", response_model=list[TesisDetail])
def list_doctrinas(
    db: Session = Depends(get_db),
    user: User = Depends(current_user),  # noqa: ARG001
) -> list[TesisDetail]:
    """Devuelve todas las tesis marcadas como doctrina canónica (criterio aplicable).

    El frontend las muestra como referencia visible siempre en pantallas
    clave de etiquetado y clasificación.
    """
    rows = db.scalars(
        select(Tesis)
        .where(Tesis.es_doctrina_canonica.is_(True))
        .order_by(Tesis.fecha_publ.desc().nullslast())
    ).all()
    return [_to_detail(db, r) for r in rows]


@router.get("/stats", response_model=CorpusStats)
def stats(
    db: Session = Depends(get_db),
    user: User = Depends(current_user),  # noqa: ARG001
) -> CorpusStats:
    # Stats es la guía del flujo de etiquetado — las doctrinas canónicas NO
    # son ejemplos de entrenamiento, no entran en estos conteos.
    # Conteos por categoría — incluye 'pendiente' como pseudo-categoría para
    # tesis sin etiqueta. Se excluyen doctrinas canónicas.
    counts_by_label = dict(
        db.execute(
            select(
                case((Tesis.etiqueta.is_(None), "pendiente"), else_=Tesis.etiqueta).label("k"),
                func.count(Tesis.id),
            )
            .where(Tesis.es_doctrina_canonica.is_(False))
            .group_by("k")
        ).all()
    )
    # Asegurar que las 8 categorías existan en el dict (con 0 si no aparecen)
    for cat in (
        "fuera_juicio",
        "en_juicio_imposible",
        "en_juicio_diferida",
        "post_juicio_general",
        "post_juicio_ejecucion",
        "post_juicio_prematuro",
        "tercero_extrano",
        "sentencia_definitiva",
        "no_aplica",
        "pendiente",
    ):
        counts_by_label.setdefault(cat, 0)
    counts_by_fuente = dict(
        db.execute(
            select(Tesis.fuente, func.count(Tesis.id))
            .where(Tesis.es_doctrina_canonica.is_(False))
            .group_by(Tesis.fuente)
        ).all()
    )
    pendientes = int(counts_by_label.pop("pendiente", 0))
    no_aplica = int(counts_by_label.get("no_aplica", 0))
    # Listas para entrenar = todas etiquetadas excepto no_aplica
    train_categorias = [
        "fuera_juicio",
        "en_juicio_imposible",
        "en_juicio_diferida",
        "post_juicio_general",
        "post_juicio_ejecucion",
        "post_juicio_prematuro",
        "tercero_extrano",
        "sentencia_definitiva",
    ]
    listas_para_entrenar = sum(int(counts_by_label.get(c, 0)) for c in train_categorias)
    etiquetadas = listas_para_entrenar + no_aplica

    excluded = settings.excluded_fuentes_list
    # Mismo filtro que `train.py._load_corpus`: solo `regla` y fuentes confiables.
    listas_limpias = (
        db.scalar(
            select(func.count(Tesis.id)).where(
                Tesis.etiqueta.in_(train_categorias),
                Tesis.es_doctrina_canonica.is_(False),
                Tesis.tipo_jurisprudencial == "regla",
                Tesis.fuente.not_in(excluded) if excluded else True,
            )
        )
        or 0
    )

    return CorpusStats(
        total=etiquetadas + pendientes,
        etiquetadas=etiquetadas,
        pendientes=pendientes,
        por_categoria={k: int(v) for k, v in counts_by_label.items()},
        por_fuente={k: int(v) for k, v in counts_by_fuente.items()},
        listas_para_entrenar=listas_para_entrenar,
        listas_para_train_limpio=int(listas_limpias),
        fuentes_excluidas=excluded,
        threshold_train_limpio=settings.train_clean_threshold,
    )


@router.get("/siguiente-pendiente", response_model=TesisDetail | None)
def siguiente_pendiente(
    fuente: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),  # noqa: ARG001
) -> TesisDetail | None:
    """Devuelve la siguiente tesis pendiente (más reciente primero) o null.

    Las doctrinas canónicas se excluyen — no son ejemplos de entrenamiento.
    Con `?fuente=` el endpoint enfoca el flujo a un lote específico (útil
    cuando importas un lote dirigido y quieres etiquetar SOLO eso).
    """
    stmt = select(Tesis).where(
        Tesis.etiqueta.is_(None),
        Tesis.es_doctrina_canonica.is_(False),
    )
    if fuente:
        stmt = stmt.where(Tesis.fuente == fuente)
    r = db.execute(stmt.order_by(Tesis.created_at.desc()).limit(1)).scalar_one_or_none()
    if r is None:
        return None
    return _to_detail(db, r)


@router.get("/inciertas", response_model=list[TesisInciertaItem])
def tesis_inciertas(
    limit: int = Query(default=20, ge=1, le=100),
    fuente: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),  # noqa: ARG001
) -> list[TesisInciertaItem]:
    """Active learning: tesis pendientes ordenadas por incertidumbre del modelo.

    Devuelve las top K tesis con MAYOR entropía de Shannon sobre la
    distribución de probabilidades del modelo activo. Etiquetar éstas es
    ~5x más informativo que etiquetar pendientes al azar — el modelo
    necesita justo este caso para aprender la frontera de decisión.

    Costo computacional: clasifica TODAS las pendientes en memoria al
    invocar (típicamente <100 → <2s). Si crece a miles, conviene
    persistir el ranking en una tabla anexa.
    """
    import math

    from app.ml.loader import get_active_model
    from app.ml.preprocessing import normalize_text

    # Cargar todas las pendientes (sin doctrinas canónicas)
    stmt = select(Tesis).where(
        Tesis.etiqueta.is_(None),
        Tesis.es_doctrina_canonica.is_(False),
    )
    if fuente:
        stmt = stmt.where(Tesis.fuente == fuente)
    pendientes = list(db.scalars(stmt))
    if not pendientes:
        return []

    # Cargar modelo y clasificar todas en batch
    try:
        model = get_active_model(db)
    except RuntimeError:
        raise HTTPException(
            status_code=500,
            detail="No hay modelo activo — no se puede ordenar por incertidumbre.",
        )
    pipeline = model.artifact["pipeline"]
    textos_norm = [normalize_text(t.rubro + " " + t.texto) for t in pendientes]
    probas = pipeline.predict_proba(textos_norm)
    classes = list(pipeline.classes_)

    n_clases = len(classes)
    log_max = math.log(n_clases) if n_clases > 1 else 1.0

    def entropia_normalizada(p) -> float:
        h = -sum(pi * math.log(pi) for pi in p if pi > 0)
        return float(h / log_max)

    enriquecidos: list[tuple[float, list[TopProb], Tesis]] = []
    for i, t in enumerate(pendientes):
        p = probas[i]
        ent = entropia_normalizada(p)
        top = sorted(
            ((classes[j], float(p[j])) for j in range(n_clases)),
            key=lambda x: -x[1],
        )[:3]
        top_probs = [TopProb(categoria=c, prob=pp) for c, pp in top]
        enriquecidos.append((ent, top_probs, t))

    enriquecidos.sort(key=lambda x: -x[0])

    return [
        TesisInciertaItem(
            id=t.id,
            registro_sjf=t.registro_sjf,
            instancia=t.instancia,
            tipo=t.tipo,  # type: ignore[arg-type]
            rubro=t.rubro,
            texto=t.texto,
            fecha_publ=t.fecha_publ,
            fuente=t.fuente,
            created_at=t.created_at,
            entropia=ent,
            top_probs=top_probs,
        )
        for ent, top_probs, t in enriquecidos[:limit]
    ]


@router.get("/auditoria-discrepancias", response_model=list[TesisAuditoriaItem])
def tesis_auditoria_discrepancias(
    limit: int = Query(default=30, ge=1, le=200),
    solo_discrepantes: bool = True,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),  # noqa: ARG001
) -> list[TesisAuditoriaItem]:
    """Tesis ya etiquetadas donde el modelo discrepa con la etiqueta humana.

    Dos modos:
      • `solo_discrepantes=true` (default): solo casos donde categoria_modelo
        ≠ etiqueta_humana, ordenados por confianza del modelo (más alta
        primero — discrepancia más sospechosa de error humano).
      • `solo_discrepantes=false`: incluye también casos donde el modelo
        coincide pero con baja confianza (lo que sugiere que el modelo
        necesita más ejemplos similares).

    Excluye etiquetas 'no_aplica' (el modelo no predice esa categoría) y
    legacy adj/sus.
    """
    import math

    from app.ml.loader import get_active_model
    from app.ml.preprocessing import normalize_text

    # Solo etiquetadas con categorías del modelo nuevo (no legacy ni no_aplica)
    CATEGORIAS_MODELO = [
        "fuera_juicio",
        "en_juicio_imposible",
        "en_juicio_diferida",
        "post_juicio_general",
        "post_juicio_ejecucion",
        "post_juicio_prematuro",
        "tercero_extrano",
        "sentencia_definitiva",
    ]
    rows = list(
        db.scalars(
            select(Tesis).where(
                Tesis.etiqueta.in_(CATEGORIAS_MODELO),
                Tesis.es_doctrina_canonica.is_(False),
            )
        )
    )
    if not rows:
        return []

    try:
        model = get_active_model(db)
    except RuntimeError:
        raise HTTPException(status_code=500, detail="Sin modelo activo")
    pipeline = model.artifact["pipeline"]
    textos_norm = [normalize_text(t.rubro + " " + t.texto) for t in rows]
    probas = pipeline.predict_proba(textos_norm)
    classes = list(pipeline.classes_)
    class_idx = {c: i for i, c in enumerate(classes)}

    # Batch lookup de emails
    user_ids = {r.etiquetada_por for r in rows if r.etiquetada_por}
    emails = (
        {u.id: u.email for u in db.scalars(select(User).where(User.id.in_(user_ids)))}
        if user_ids
        else {}
    )

    items: list[tuple[float, TesisAuditoriaItem]] = []
    for i, t in enumerate(rows):
        p = probas[i]
        idx_modelo = int(p.argmax())
        cat_modelo = classes[idx_modelo]
        prob_modelo = float(p[idx_modelo])
        # Probabilidad que el modelo asigna a la etiqueta humana
        idx_humana = class_idx.get(t.etiqueta or "", -1)
        prob_humana = float(p[idx_humana]) if idx_humana >= 0 else 0.0
        discrepa = cat_modelo != t.etiqueta
        if solo_discrepantes and not discrepa:
            continue
        # Score de "interés para auditar": discrepa Y modelo seguro = alto.
        score = prob_modelo if discrepa else (1.0 - prob_humana)
        item = TesisAuditoriaItem(
            id=t.id,
            registro_sjf=t.registro_sjf,
            rubro=t.rubro,
            etiqueta_humana=t.etiqueta,  # type: ignore[arg-type]
            etiquetada_por_email=emails.get(t.etiquetada_por) if t.etiquetada_por else None,
            categoria_modelo=cat_modelo,
            prob_categoria_modelo=prob_modelo,
            prob_de_etiqueta_humana=prob_humana,
            discrepa=discrepa,
            fuente=t.fuente,
        )
        items.append((score, item))

    items.sort(key=lambda x: -x[0])
    return [it for _, it in items[:limit]]


@router.get("/{tesis_id}", response_model=TesisDetail)
def get_tesis(
    tesis_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),  # noqa: ARG001
) -> TesisDetail:
    r = db.get(Tesis, tesis_id)
    if r is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="no existe")
    return _to_detail(db, r)


@router.post("/{tesis_id}/marcar-doctrina", response_model=TesisDetail)
def marcar_doctrina(
    tesis_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> TesisDetail:
    """Marca una tesis como doctrina canónica.

    Efectos:
      • Se muestra siempre en `<DoctrinaAncla>` en /clasificar, /etiquetar,
        /clasificaciones/[id].
      • NO entra al training (train.py la excluye).
      • Si tenía etiqueta de entrenamiento, se borra (incoherente con doctrina).
    """
    _require_role(user, "socio", "admin")
    r = db.get(Tesis, tesis_id)
    if r is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="no existe")
    r.es_doctrina_canonica = True
    # Limpiar etiqueta de entrenamiento — una doctrina no es ejemplo.
    r.etiqueta = None
    r.etiquetada_por = None
    r.etiquetada_at = None
    db.commit()
    db.refresh(r)
    return _to_detail(db, r)


@router.post("/{tesis_id}/desmarcar-doctrina", response_model=TesisDetail)
def desmarcar_doctrina(
    tesis_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> TesisDetail:
    """Revierte el flag. La tesis vuelve a ser ejemplo etiquetable."""
    _require_role(user, "socio", "admin")
    r = db.get(Tesis, tesis_id)
    if r is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="no existe")
    r.es_doctrina_canonica = False
    db.commit()
    db.refresh(r)
    return _to_detail(db, r)


@router.post("/{tesis_id}/label", response_model=TesisDetail)
def label_tesis(
    tesis_id: uuid.UUID,
    body: LabelTesisRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> TesisDetail:
    _require_role(user, "proyectista", "socio", "admin")
    r = db.get(Tesis, tesis_id)
    if r is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="no existe")
    if r.es_doctrina_canonica:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede etiquetar una doctrina canónica — es criterio aplicable, no ejemplo de entrenamiento.",
        )
    r.etiqueta = body.etiqueta
    r.etiquetada_por = user.id
    r.etiquetada_at = dt.datetime.now(dt.UTC)
    # Si el etiquetador especifica rol jurisprudencial, lo aplicamos.
    # Si no, no tocamos (mantiene el valor previo o el default 'regla').
    if body.tipo_jurisprudencial is not None:
        r.tipo_jurisprudencial = body.tipo_jurisprudencial
    if body.notas_metodologicas is not None:
        r.notas_metodologicas = body.notas_metodologicas
    db.commit()
    db.refresh(r)
    return _to_detail(db, r)


@router.post("/{tesis_id}/tipo-jurisprudencial", response_model=TesisDetail)
def cambiar_tipo_jurisprudencial(
    tesis_id: uuid.UUID,
    body: TipoJurisprudencialRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> TesisDetail:
    """Cambia solo el rol jurisprudencial (regla/excepcion/...) sin tocar etiqueta.

    Útil cuando uno descubre que una tesis previamente etiquetada como
    `regla` es realmente una `excepcion` — el cambio se refleja en el
    próximo reentreno: el modelo deja de aprender de ella.
    """
    _require_role(user, "proyectista", "socio", "admin")
    r = db.get(Tesis, tesis_id)
    if r is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="no existe")
    r.tipo_jurisprudencial = body.tipo_jurisprudencial
    if body.notas_metodologicas is not None:
        r.notas_metodologicas = body.notas_metodologicas
    db.commit()
    db.refresh(r)
    return _to_detail(db, r)


@router.post("/import", response_model=ImportTesisResponse, status_code=201)
def import_tesis(
    body: ImportTesisRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> ImportTesisResponse:
    _require_role(user, "socio", "admin")

    incoming = {it.registro_sjf for it in body.items}
    existing = set(
        db.scalars(select(Tesis.registro_sjf).where(Tesis.registro_sjf.in_(incoming))).all()
    )

    insertadas = 0
    duplicadas = 0
    errores: list[str] = []
    for it in body.items:
        if it.registro_sjf in existing:
            duplicadas += 1
            continue
        try:
            r = Tesis(
                registro_sjf=it.registro_sjf,
                epoca=it.epoca,
                instancia=it.instancia,
                tipo=it.tipo,
                rubro=it.rubro,
                texto=it.texto,
                etiqueta=it.etiqueta,
                fecha_publ=it.fecha_publ,
                fuente=body.fuente,
            )
            if it.etiqueta is not None:
                r.etiquetada_por = user.id
                r.etiquetada_at = dt.datetime.now(dt.UTC)
            db.add(r)
            db.flush()  # detecta duplicados intra-batch
            insertadas += 1
            existing.add(it.registro_sjf)
        except Exception as e:  # noqa: BLE001
            db.rollback()
            errores.append(f"{it.registro_sjf}: {e}")
    db.commit()
    return ImportTesisResponse(insertadas=insertadas, duplicadas=duplicadas, errores=errores)


def _to_detail(db: Session, r: Tesis) -> TesisDetail:
    email = None
    if r.etiquetada_por:
        u = db.get(User, r.etiquetada_por)
        email = u.email if u else None
    return TesisDetail(
        id=r.id,
        registro_sjf=r.registro_sjf,
        epoca=r.epoca,
        instancia=r.instancia,
        tipo=r.tipo,  # type: ignore[arg-type]
        rubro=r.rubro,
        texto=r.texto,
        etiqueta=r.etiqueta,  # type: ignore[arg-type]
        fecha_publ=r.fecha_publ,
        fuente=r.fuente,
        etiquetada_por_email=email,
        etiquetada_at=r.etiquetada_at,
        created_at=r.created_at,
        es_doctrina_canonica=r.es_doctrina_canonica,
        tipo_jurisprudencial=r.tipo_jurisprudencial,  # type: ignore[arg-type]
        notas_metodologicas=r.notas_metodologicas,
    )
