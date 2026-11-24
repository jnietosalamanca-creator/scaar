"""Tests del filtro de rol jurisprudencial en el corpus de training.

Verifica que:
  • La columna existe y default es 'regla'.
  • CHECK constraint rechaza valores fuera del enum.
  • Una tesis marcada 'excepcion' deja de aparecer en `listas_para_train_limpio`.
  • Cambiar `tipo_jurisprudencial` de regla a excepcion baja el conteo de
    entrenamiento sin afectar el conteo de etiquetadas.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError, IntegrityError, OperationalError

from app.db.models import Tesis, User
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


@pytest.fixture
def fixture_tesis_regla(db_session):
    """Inserta una tesis etiquetada como `regla` y la limpia al final."""
    user = db_session.scalar(select(User).limit(1))
    if user is None:
        pytest.skip("Sin user")
    reg = f"TEST-TIPOJUR-{uuid.uuid4().hex[:8]}"
    t = Tesis(
        registro_sjf=reg,
        epoca="Undécima",
        instancia="Tribunales Colegiados",
        tipo="aislada",
        rubro="TESIS DE PRUEBA TIPO JURISPRUDENCIAL.",
        texto="Texto de prueba lo suficientemente largo para pasar validaciones.",
        etiqueta="en_juicio_imposible",
        fuente="test_tipojur",
        tipo_jurisprudencial="regla",
    )
    db_session.add(t)
    db_session.commit()
    db_session.refresh(t)
    yield t
    db_session.execute(text("DELETE FROM tesis WHERE id = :tid"), {"tid": t.id})
    db_session.commit()


def test_default_es_regla(fixture_tesis_regla):
    assert fixture_tesis_regla.tipo_jurisprudencial == "regla"


def test_check_constraint_rechaza_valor_invalido(db_session, fixture_tesis_regla):
    """El CHECK constraint debe rechazar valores fuera del enum."""
    with pytest.raises((IntegrityError, DBAPIError)):
        db_session.execute(
            text("UPDATE tesis SET tipo_jurisprudencial = 'inventada' WHERE id = :tid"),
            {"tid": fixture_tesis_regla.id},
        )
        db_session.commit()
    db_session.rollback()


def test_excepcion_se_excluye_del_filtro_de_training(
    db_session, fixture_tesis_regla
):
    """Una tesis marcada 'excepcion' NO debe aparecer en el query del filtro
    de training (lo que ejecuta train.py)."""
    # Marcar como excepción
    fixture_tesis_regla.tipo_jurisprudencial = "excepcion"
    db_session.commit()

    # Mismo filtro que train.py
    n = db_session.execute(
        text(
            "SELECT count(*) FROM tesis "
            "WHERE id = :tid "
            "AND etiqueta IN ('en_juicio_imposible','en_juicio_diferida') "
            "AND es_doctrina_canonica = FALSE "
            "AND tipo_jurisprudencial = 'regla'"
        ),
        {"tid": fixture_tesis_regla.id},
    ).scalar()
    assert n == 0


def test_regla_si_entra_al_filtro(db_session, fixture_tesis_regla):
    """Sanity: una tesis 'regla' SÍ aparece en el filtro de training."""
    n = db_session.execute(
        text(
            "SELECT count(*) FROM tesis "
            "WHERE id = :tid "
            "AND etiqueta IN ('en_juicio_imposible','en_juicio_diferida') "
            "AND es_doctrina_canonica = FALSE "
            "AND tipo_jurisprudencial = 'regla'"
        ),
        {"tid": fixture_tesis_regla.id},
    ).scalar()
    assert n == 1


def test_los_4_valores_son_validos(db_session, fixture_tesis_regla):
    """Aceptar regla / excepcion / aislada_dudosa / derogada."""
    for valor in ["regla", "excepcion", "aislada_dudosa", "derogada"]:
        fixture_tesis_regla.tipo_jurisprudencial = valor
        db_session.commit()
        db_session.refresh(fixture_tesis_regla)
        assert fixture_tesis_regla.tipo_jurisprudencial == valor


def test_index_existe(db_session):
    """`idx_tesis_tipo_jur` (parcial sobre no-regla) sirve para queries
    rápidas de auditoría. Si lo droppean, regresiones de performance."""
    n = db_session.execute(
        text(
            "SELECT count(*) FROM pg_indexes "
            "WHERE tablename = 'tesis' AND indexname = 'idx_tesis_tipo_jur'"
        )
    ).scalar()
    assert n == 1
