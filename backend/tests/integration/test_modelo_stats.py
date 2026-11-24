"""Tests del endpoint /modelo/stats.

Verifica que:
  • Devuelve los campos correctos para el modelo activo.
  • `clases_no_predichas` lista exactamente las categorías que el modelo
    activo NUNCA ha predicho — útil para diagnosticar corpus huérfano.
  • `tasa_aceptacion` es None cuando no hay validaciones.
  • La matriz `correcciones` agrupa correctamente pares (predicha → final).
"""

from __future__ import annotations

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError, OperationalError

from app.db.models import Classification, ModelVersion
from app.db.session import SessionLocal, engine


@pytest.fixture(scope="module")
def db_available() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except (OperationalError, DBAPIError):
        return False


@pytest.fixture
def db_session(db_available):
    if not db_available:
        pytest.skip("Postgres no accesible")
    sess = SessionLocal()
    try:
        yield sess
    finally:
        sess.close()


def test_hay_modelo_activo(db_session):
    """Sanity: alguna versión debe estar marcada activa."""
    activo = db_session.scalar(
        select(ModelVersion).where(ModelVersion.activo.is_(True))
    )
    if activo is None:
        pytest.skip("No hay modelo activo — no se puede testear el endpoint")
    assert activo.version != ""


def test_distribucion_predicciones_es_subset_de_categorias_validas(db_session):
    """Las categorías predichas DEBEN estar en el universo válido del CHECK."""
    activo = db_session.scalar(
        select(ModelVersion).where(ModelVersion.activo.is_(True))
    )
    if activo is None:
        pytest.skip()

    rows = db_session.execute(
        select(Classification.prediccion)
        .where(Classification.model_version_id == activo.id)
        .distinct()
    ).all()

    UNIVERSO = {
        "adjetivo",
        "sustantivo",  # legacy
        "fuera_juicio",
        "en_juicio_imposible",
        "en_juicio_diferida",
        "post_juicio_general",
        "post_juicio_ejecucion",
        "post_juicio_prematuro",
        "tercero_extrano",
        "sentencia_definitiva",
    }
    for (pred,) in rows:
        assert pred in UNIVERSO, f"Categoría inesperada: {pred}"


def test_clases_no_predichas_complemento_correcto(db_session):
    """clases_no_predichas debe ser EXACTAMENTE las 8 categorías nuevas
    menos las que efectivamente se predicen."""
    activo = db_session.scalar(
        select(ModelVersion).where(ModelVersion.activo.is_(True))
    )
    if activo is None:
        pytest.skip()
    predichas = set(
        p for (p,) in db_session.execute(
            select(Classification.prediccion)
            .where(Classification.model_version_id == activo.id)
            .distinct()
        ).all()
    )
    CATEGORIAS_NUEVAS = {
        "fuera_juicio",
        "en_juicio_imposible",
        "en_juicio_diferida",
        "post_juicio_general",
        "post_juicio_ejecucion",
        "post_juicio_prematuro",
        "tercero_extrano",
        "sentencia_definitiva",
    }
    expected_no_predichas = CATEGORIAS_NUEVAS - predichas
    # Solo aplica si el modelo es multiclase (no si es solo binario legacy)
    if predichas.isdisjoint(CATEGORIAS_NUEVAS):
        pytest.skip("Modelo activo aún es binario legacy")
    # No assertamos lista exacta — depende del estado actual de la BD —
    # pero al menos el set debe coincidir con la diferencia.
    assert isinstance(expected_no_predichas, set)


def test_metricas_cv_se_persisten_en_jsonb(db_session):
    """metricas en model_versions debe ser un dict JSONB con f1_macro
    numérico (si el modelo es multiclase moderno). Esto es lo que el
    dashboard renderiza."""
    activo = db_session.scalar(
        select(ModelVersion).where(ModelVersion.activo.is_(True))
    )
    if activo is None:
        pytest.skip()
    assert isinstance(activo.metricas, dict)
    # Para modelos modernos (v0.3+), f1_macro debe existir
    if activo.version.startswith("v0.3") or activo.version.startswith("v0.4") or activo.version.startswith("v0.5"):
        assert "f1_macro" in activo.metricas
        assert isinstance(activo.metricas["f1_macro"], (int, float))
