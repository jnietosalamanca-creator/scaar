"""Crea el veredicto del proyectista, lo firma con HMAC y persiste."""

from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy.orm import Session

from app.db.models import Classification, ClassificationValidation, User
from app.services.signature import build_canonical_payload, sign


class ValidationError(ValueError):
    """Error de regla de negocio en la validación."""


# Mapping: predicción binaria del modelo activo → su equivalente en la
# taxonomía de 7. Si el proyectista corrige a la equivalente, es semánti-
# camente "acepta" y debemos forzar ese veredicto en lugar de "rechaza".
BINARY_TO_TAXONOMY = {
    "adjetivo": "en_juicio_imposible",
    "sustantivo": "en_juicio_diferida",
}


def validate_classification(
    db: Session,
    *,
    classification_id: uuid.UUID,
    user: User,
    veredicto: str,
    clasificacion_corregida: str | None,
    comentario: str | None,
    supersedes_id: uuid.UUID | None,
) -> ClassificationValidation:
    classification = db.get(Classification, classification_id)
    if classification is None:
        raise ValidationError("classification_id inexistente")

    if veredicto == "rechaza" and not clasificacion_corregida:
        raise ValidationError("veredicto=rechaza requiere clasificacion_corregida")
    if veredicto == "acepta" and clasificacion_corregida is not None:
        raise ValidationError("veredicto=acepta no admite clasificacion_corregida")
    if clasificacion_corregida is not None:
        # El modelo activo es binario (adj/sus); su equivalente en la
        # taxonomía de 7 es en_juicio_imposible / en_juicio_diferida.
        # Bloquear si la corrección coincide con esa equivalencia.
        equivalente = BINARY_TO_TAXONOMY.get(classification.prediccion)
        if (
            clasificacion_corregida == classification.prediccion
            or clasificacion_corregida == equivalente
        ):
            raise ValidationError(
                f"clasificacion_corregida='{clasificacion_corregida}' es "
                f"equivalente a la predicción del modelo — usa veredicto=acepta."
            )

    if supersedes_id is not None:
        prev = db.get(ClassificationValidation, supersedes_id)
        if prev is None:
            raise ValidationError("supersedes_id inexistente")
        if prev.classification_id != classification_id:
            raise ValidationError(
                "supersedes_id pertenece a otra classification"
            )

    validated_at = dt.datetime.now(dt.UTC)
    payload = build_canonical_payload(
        classification_id=str(classification_id),
        acto_sha256=classification.acto_sha256,
        model_version_id=str(classification.model_version_id),
        prediccion_modelo=classification.prediccion,
        validated_by=str(user.id),
        validated_at_iso=validated_at.isoformat(),
        veredicto=veredicto,
        clasificacion_corregida=clasificacion_corregida,
        comentario=comentario,
        supersedes_id=str(supersedes_id) if supersedes_id else None,
    )
    firma = sign(payload)

    record = ClassificationValidation(
        classification_id=classification_id,
        validated_by=user.id,
        validated_at=validated_at,
        veredicto=veredicto,
        clasificacion_corregida=clasificacion_corregida,
        comentario=comentario,
        firma_sha256=firma,
        firma_payload=payload,
        supersedes_id=supersedes_id,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record
