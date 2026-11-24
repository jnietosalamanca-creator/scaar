"""Firma HMAC-SHA256 del veredicto del proyectista.

El payload se serializa de forma **canónica** (sort_keys, separators sin
espacios, ensure_ascii=False) para que la firma sea reproducible. Cualquier
auditor con el secreto puede recalcular y verificar — no necesita la app.

Si en el futuro se rota el secreto, `key_version` permite distinguir firmas
viejas de nuevas y mantener verificabilidad histórica.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

from app.core.config import settings


def build_canonical_payload(
    *,
    classification_id: str,
    acto_sha256: str,
    model_version_id: str,
    prediccion_modelo: str,
    validated_by: str,
    validated_at_iso: str,
    veredicto: str,
    clasificacion_corregida: str | None,
    comentario: str | None,
    supersedes_id: str | None,
) -> dict[str, Any]:
    return {
        "schema": "scaar.verdict.v1",
        "key_version": settings.verdict_hmac_key_version,
        "classification_id": classification_id,
        "acto_sha256": acto_sha256,
        "model_version_id": model_version_id,
        "prediccion_modelo": prediccion_modelo,
        "validated_by": validated_by,
        "validated_at": validated_at_iso,
        "veredicto": veredicto,
        "clasificacion_corregida": clasificacion_corregida,
        "comentario": comentario,
        "supersedes_id": supersedes_id,
    }


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sign(payload: dict[str, Any]) -> str:
    secret = settings.verdict_hmac_secret.encode("utf-8")
    msg = _canonical_json(payload).encode("utf-8")
    return hmac.new(secret, msg, hashlib.sha256).hexdigest()


def verify(payload: dict[str, Any], firma: str) -> bool:
    """Comparación constant-time para prevenir timing attacks."""
    return hmac.compare_digest(sign(payload), firma)
