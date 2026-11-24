"""Tests de integración contra Postgres real.

Verifica que los triggers PL/pgSQL bloquean UPDATE/DELETE en las tablas
inmutables (`classifications`, parcialmente `classification_validations`).
Estos triggers son la columna vertebral de la defensibilidad del log
(Riesgo 9). Si se rompen sin advertir, todo el sistema pierde su
propiedad principal.

Requiere:
  - Postgres corriendo en localhost:5432
  - DB `scaar` accesible con la conexión de settings.database_url
  - Datos mínimos: al menos un user, un model_version y una classification.

Si la DB no está disponible, los tests se skippan limpiamente.
"""

from __future__ import annotations

import datetime as dt
import uuid

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError, OperationalError

from app.db.models import (
    Classification,
    ClassificationValidation,
    ModelVersion,
    User,
)
from app.db.session import SessionLocal, engine


@pytest.fixture(scope="module")
def db_available() -> bool:
    """Skip todos los tests si Postgres no está accesible."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except (OperationalError, DBAPIError):
        return False


@pytest.fixture
def db_session(db_available):
    if not db_available:
        pytest.skip("Postgres no accesible — los tests de integración necesitan DB")
    sess = SessionLocal()
    try:
        yield sess
    finally:
        sess.close()


@pytest.fixture
def fixture_classification(db_session):
    """Crea (o usa una existente) una classification para probar el trigger.

    Limpieza: al final del test, deshabilita el trigger y borra la fila
    creada — para no contaminar la BD del usuario.
    """
    # ¿Hay usuario y model_version disponibles?
    user = db_session.scalar(select(User).limit(1))
    mv = db_session.scalar(select(ModelVersion).limit(1))
    if user is None or mv is None:
        pytest.skip("No hay user/model_version en la BD para fixturar")

    c = Classification(
        acto_reclamado="ACTO DE PRUEBA — test de inmutabilidad. NO TOCAR.",
        acto_sha256="f" * 64,
        model_version_id=mv.id,
        prediccion="en_juicio_imposible",
        prob_adjetivo=None,
        prob_categoria=0.5,
        prob_por_clase={"en_juicio_imposible": 0.5, "fuera_juicio": 0.5},
        top_features=[],
        top_analogas=[],
        created_by=user.id,
    )
    db_session.add(c)
    db_session.commit()
    db_session.refresh(c)
    yield c
    # Cleanup: deshabilitar trigger temporalmente para borrar la fila de prueba
    try:
        db_session.execute(
            text("ALTER TABLE classifications DISABLE TRIGGER no_modify_classifications")
        )
        db_session.execute(
            text("DELETE FROM classification_validations WHERE classification_id = :cid"),
            {"cid": c.id},
        )
        db_session.execute(
            text("DELETE FROM classifications WHERE id = :cid"),
            {"cid": c.id},
        )
        db_session.execute(
            text("ALTER TABLE classifications ENABLE TRIGGER no_modify_classifications")
        )
        db_session.commit()
    except Exception:
        db_session.rollback()


def test_update_classification_lanza_error(db_session, fixture_classification):
    """El trigger debe bloquear cualquier UPDATE sobre classifications."""
    c = fixture_classification
    with pytest.raises(DBAPIError) as exc_info:
        db_session.execute(
            text("UPDATE classifications SET prediccion = 'fuera_juicio' WHERE id = :cid"),
            {"cid": c.id},
        )
        db_session.commit()
    db_session.rollback()
    assert "append-only" in str(exc_info.value).lower() or "riesgo 9" in str(exc_info.value).lower()


def test_delete_classification_lanza_error(db_session, fixture_classification):
    """El trigger debe bloquear cualquier DELETE sobre classifications."""
    c = fixture_classification
    with pytest.raises(DBAPIError) as exc_info:
        db_session.execute(
            text("DELETE FROM classifications WHERE id = :cid"),
            {"cid": c.id},
        )
        db_session.commit()
    db_session.rollback()
    assert "append-only" in str(exc_info.value).lower() or "riesgo 9" in str(exc_info.value).lower()


def test_validation_update_de_campo_inmutable_lanza_error(
    db_session, fixture_classification
):
    """En `classification_validations` el trigger permite SOLO actualizar
    aprobado_para_corpus/aprobado_por/aprobado_at. Cualquier otro UPDATE
    debe lanzar."""
    user = db_session.scalar(select(User).limit(1))
    v = ClassificationValidation(
        classification_id=fixture_classification.id,
        validated_by=user.id,
        validated_at=dt.datetime.now(dt.UTC),
        veredicto="acepta",
        clasificacion_corregida=None,
        comentario="test",
        firma_sha256="a" * 64,
        firma_payload={"k": "v"},
    )
    db_session.add(v)
    db_session.commit()

    # Intentar modificar el comentario — debe fallar
    with pytest.raises(DBAPIError) as exc_info:
        db_session.execute(
            text("UPDATE classification_validations SET comentario = 'tampered' WHERE id = :vid"),
            {"vid": v.id},
        )
        db_session.commit()
    db_session.rollback()
    assert "modificable" in str(exc_info.value).lower() or "append-only" in str(exc_info.value).lower()


def test_validation_update_de_aprobacion_si_se_permite(
    db_session, fixture_classification
):
    """Update SÍ permitido: campos de aprobación posterior por socio."""
    user = db_session.scalar(select(User).limit(1))
    v = ClassificationValidation(
        classification_id=fixture_classification.id,
        validated_by=user.id,
        validated_at=dt.datetime.now(dt.UTC),
        veredicto="acepta",
        firma_sha256="b" * 64,
        firma_payload={"k": "v"},
    )
    db_session.add(v)
    db_session.commit()

    # Activar aprobacion_para_corpus — esto SÍ debe funcionar
    db_session.execute(
        text(
            "UPDATE classification_validations SET "
            "aprobado_para_corpus = TRUE, aprobado_por = :uid, "
            "aprobado_at = now() WHERE id = :vid"
        ),
        {"uid": user.id, "vid": v.id},
    )
    db_session.commit()
    db_session.refresh(v)
    assert v.aprobado_para_corpus is True
    assert v.aprobado_por == user.id


def test_classifications_immutable_trigger_existe(db_session):
    """Sanity check: el trigger existe. Si alguien lo droppea sin advertir,
    este test grita."""
    res = db_session.execute(
        text(
            "SELECT count(*) FROM pg_trigger "
            "WHERE tgname = 'no_modify_classifications' AND NOT tgisinternal"
        )
    ).scalar()
    assert res == 1


def test_validations_immutable_trigger_existe(db_session):
    res = db_session.execute(
        text(
            "SELECT count(*) FROM pg_trigger "
            "WHERE tgname = 'no_modify_validations' AND NOT tgisinternal"
        )
    ).scalar()
    assert res == 1
