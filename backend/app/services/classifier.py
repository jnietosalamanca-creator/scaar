"""Orquesta predict + persistencia inmutable del log (Riesgo 9)."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.db.models import Classification
from app.ml.loader import get_active_model
from app.ml.predict import predict
from app.ml.preprocessing import acto_sha256

# Categorías para las que mantenemos la columna legacy `prob_adjetivo`
# poblada (semánticamente equivale a la prob del binario derogado).
LEGACY_ADJETIVO_EQUIVS = {"adjetivo", "en_juicio_imposible"}


def classify_and_log(
    db: Session,
    acto_reclamado: str,
    user_id: uuid.UUID,
    case_id: uuid.UUID | None = None,
) -> Classification:
    """Clasifica un acto reclamado y persiste el log de razonamiento.

    Side effects: INSERT en `classifications` (la tabla es append-only por
    trigger). Si la transacción falla después, no queda log fantasma.
    """
    model = get_active_model(db)
    result = predict(model, acto_reclamado)

    prob_categoria = result.prob_por_clase.get(result.categoria, 0.0)
    # Compat legacy: prob_adjetivo solo se llena cuando la categoría
    # equivale a "imposible reparación" en el viejo binario.
    prob_adj_legacy = (
        prob_categoria if result.categoria in LEGACY_ADJETIVO_EQUIVS else None
    )

    record = Classification(
        acto_reclamado=acto_reclamado,
        acto_sha256=acto_sha256(acto_reclamado),
        model_version_id=uuid.UUID(model.version_id),
        prediccion=result.categoria,
        prob_adjetivo=prob_adj_legacy,
        prob_categoria=prob_categoria,
        prob_por_clase=result.prob_por_clase,
        top_features=result.top_features,
        top_analogas=result.top_analogas,
        created_by=user_id,
        case_id=case_id,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record
