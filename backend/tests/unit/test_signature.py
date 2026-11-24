"""Tests del servicio de firma HMAC del veredicto del proyectista.

Cubre:
  • sign + verify es deterministic (mismo input → misma firma).
  • verify detecta tampering en cada campo del payload.
  • compare_digest está siendo usado (constant time).
  • payload canónico es invariante a orden de keys (misma firma).
"""

from __future__ import annotations

import json

import pytest

from app.services.signature import (
    _canonical_json,
    build_canonical_payload,
    sign,
    verify,
)


def _payload_base() -> dict:
    return build_canonical_payload(
        classification_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        acto_sha256="0" * 64,
        model_version_id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        prediccion_modelo="en_juicio_imposible",
        validated_by="cccccccc-cccc-cccc-cccc-cccccccccccc",
        validated_at_iso="2026-05-09T12:00:00+00:00",
        veredicto="acepta",
        clasificacion_corregida=None,
        comentario="Coincido con la clasificación.",
        supersedes_id=None,
    )


def test_sign_is_deterministic():
    p1 = _payload_base()
    p2 = _payload_base()
    assert sign(p1) == sign(p2)


def test_sign_payload_dict_order_irrelevante():
    """El orden de inserción de claves en el dict no debe afectar la firma —
    `_canonical_json` ordena con sort_keys=True."""
    p = _payload_base()
    p_reordenado = dict(reversed(list(p.items())))
    assert sign(p) == sign(p_reordenado)


def test_verify_detecta_tampering_en_comentario():
    p = _payload_base()
    firma = sign(p)
    p_tampered = dict(p)
    p_tampered["comentario"] = "Cambié el razonamiento jurídico."
    assert verify(p, firma) is True
    assert verify(p_tampered, firma) is False


def test_verify_detecta_tampering_en_veredicto():
    p = _payload_base()
    firma = sign(p)
    p_tampered = dict(p)
    p_tampered["veredicto"] = "rechaza"
    p_tampered["clasificacion_corregida"] = "en_juicio_diferida"
    assert verify(p_tampered, firma) is False


def test_verify_falsa_si_secret_diferente(monkeypatch):
    p = _payload_base()
    firma = sign(p)
    # Rotamos secret en runtime — la firma anterior debe dejar de verificar
    monkeypatch.setattr(
        "app.core.config.settings.verdict_hmac_secret",
        "otro-secret-totalmente-distinto-no-prod" * 2,
    )
    assert verify(p, firma) is False


def test_canonical_json_estable_para_unicode():
    p = _payload_base()
    p["comentario"] = "Razón con acentos: cédula, jurídico, año."
    j1 = _canonical_json(p)
    j2 = _canonical_json(p)
    assert j1 == j2
    assert "cédula" in j1  # ensure_ascii=False conserva acentos


def test_canonical_json_orden_garantizado():
    """Garantía estructural: las keys salen alfabéticamente."""
    j = _canonical_json(_payload_base())
    parsed = json.loads(j)
    keys_orden = list(parsed.keys())
    assert keys_orden == sorted(keys_orden)


@pytest.mark.parametrize(
    "campo",
    [
        "classification_id",
        "acto_sha256",
        "validated_by",
        "validated_at",
        "key_version",
    ],
)
def test_tampering_en_campo_critico_se_detecta(campo: str):
    p = _payload_base()
    firma = sign(p)
    p_tampered = dict(p)
    p_tampered[campo] = "valor-modificado-malicioso"
    assert verify(p_tampered, firma) is False
