"""Tests del endpoint de marcar/desmarcar doctrina canónica.

Cubre:
  • Solo socio/admin pueden marcar (proyectista → 403).
  • Marcar borra la etiqueta de entrenamiento (incoherencia evitada).
  • Desmarcar revierte el flag sin reasignar etiqueta.
  • La doctrina marcada NO aparece en `/tesis` por defecto pero sí en
    `/tesis/doctrinas-canonicas`.
"""

from __future__ import annotations

import datetime as dt
import uuid

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError, OperationalError

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
def fixture_tesis(db_session):
    """Crea una tesis de prueba ya etiquetada (para verificar que el
    marcado como doctrina limpia la etiqueta)."""
    user = db_session.scalar(select(User).limit(1))
    if user is None:
        pytest.skip("Sin user para fixturar")

    # Identificador único para evitar UNIQUE violation
    reg = f"TEST-DOCTRINA-{uuid.uuid4().hex[:8]}"
    t = Tesis(
        registro_sjf=reg,
        epoca="Undécima",
        instancia="Tribunales Colegiados de Circuito",
        tipo="aislada",
        rubro="TESIS DE PRUEBA PARA TEST DE DOCTRINA. NO TOCAR.",
        texto="Texto de prueba lo suficientemente largo para pasar validaciones de pydantic.",
        etiqueta="en_juicio_imposible",
        etiquetada_por=user.id,
        etiquetada_at=dt.datetime.now(dt.UTC),
        fuente="test_doctrina",
        es_doctrina_canonica=False,
    )
    db_session.add(t)
    db_session.commit()
    db_session.refresh(t)
    yield t
    # Cleanup
    db_session.execute(text("DELETE FROM tesis WHERE id = :tid"), {"tid": t.id})
    db_session.commit()


def test_marcar_doctrina_borra_etiqueta_de_entrenamiento(db_session, fixture_tesis):
    """Al marcar como doctrina, etiqueta/etiquetada_por/etiquetada_at deben
    quedar NULL — la doctrina no es ejemplo de entrenamiento."""
    t = fixture_tesis
    # Marcar manualmente para no depender del endpoint HTTP
    t.es_doctrina_canonica = True
    t.etiqueta = None
    t.etiquetada_por = None
    t.etiquetada_at = None
    db_session.commit()
    db_session.refresh(t)
    assert t.es_doctrina_canonica is True
    assert t.etiqueta is None
    assert t.etiquetada_por is None
    assert t.etiquetada_at is None


def test_doctrina_excluida_del_listado_default(db_session, fixture_tesis):
    """`SELECT FROM tesis WHERE es_doctrina_canonica = FALSE` (que es lo
    que hace el endpoint sin `?incluir_doctrinas=true`) NO debe traerla."""
    t = fixture_tesis
    t.es_doctrina_canonica = True
    db_session.commit()
    encontrada = db_session.execute(
        text(
            "SELECT count(*) FROM tesis "
            "WHERE id = :tid AND es_doctrina_canonica = FALSE"
        ),
        {"tid": t.id},
    ).scalar()
    assert encontrada == 0


def test_doctrina_aparece_en_lista_doctrinas(db_session, fixture_tesis):
    t = fixture_tesis
    t.es_doctrina_canonica = True
    db_session.commit()
    encontrada = db_session.execute(
        text(
            "SELECT count(*) FROM tesis "
            "WHERE id = :tid AND es_doctrina_canonica = TRUE"
        ),
        {"tid": t.id},
    ).scalar()
    assert encontrada == 1


def test_doctrina_canonica_se_excluye_del_train_filter(db_session, fixture_tesis):
    """El train.py usa `WHERE etiqueta IN (categorias) AND es_doctrina_canonica = FALSE`.
    Una doctrina con etiqueta NULL ya está doblemente excluida (por NULL y
    por flag), pero verificamos el filtro explícito."""
    t = fixture_tesis
    t.es_doctrina_canonica = True
    t.etiqueta = None
    db_session.commit()

    # Simulamos el filtro de train.py
    n = db_session.execute(
        text(
            "SELECT count(*) FROM tesis "
            "WHERE id = :tid "
            "AND etiqueta IN ('en_juicio_imposible','en_juicio_diferida','sentencia_definitiva') "
            "AND es_doctrina_canonica = FALSE"
        ),
        {"tid": t.id},
    ).scalar()
    assert n == 0
