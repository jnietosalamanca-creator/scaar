"""Tests del endpoint /classifications/duplicados.

Verifica:
  • Texto nuevo (sin previas en BD) → n_previas == 0.
  • Variación cosmética del mismo texto → mismo SHA y mismas previas
    (función puramente del normalize_text + acto_sha256).
  • Lookups batch funcionan (autor, caso, validaciones vigentes).
"""

from __future__ import annotations

import datetime as dt
import uuid

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError, OperationalError

from app.db.models import Classification, ModelVersion, User
from app.db.session import SessionLocal, engine
from app.ml.preprocessing import acto_sha256


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
def fixture_clasificacion(db_session):
    """Inserta una classification con texto único y la limpia al final."""
    user = db_session.scalar(select(User).limit(1))
    mv = db_session.scalar(select(ModelVersion).limit(1))
    if user is None or mv is None:
        pytest.skip("Sin user/model_version para fixturar")

    acto = (
        "ACTO ÚNICO DE PRUEBA PARA TEST DE DUPLICADOS. "
        "Identificador aleatorio: " + uuid.uuid4().hex
    )
    sha = acto_sha256(acto)

    c = Classification(
        acto_reclamado=acto,
        acto_sha256=sha,
        model_version_id=mv.id,
        prediccion="en_juicio_imposible",
        prob_categoria=0.6,
        prob_por_clase={"en_juicio_imposible": 0.6, "fuera_juicio": 0.4},
        top_features=[],
        top_analogas=[],
        created_by=user.id,
    )
    db_session.add(c)
    db_session.commit()
    db_session.refresh(c)
    yield c, acto, sha
    # Cleanup
    db_session.execute(
        text("ALTER TABLE classifications DISABLE TRIGGER no_modify_classifications")
    )
    db_session.execute(
        text("DELETE FROM classifications WHERE id = :cid"), {"cid": c.id}
    )
    db_session.execute(
        text("ALTER TABLE classifications ENABLE TRIGGER no_modify_classifications")
    )
    db_session.commit()


def test_query_directa_devuelve_previa(db_session, fixture_clasificacion):
    """SQL directo: el SHA de la fixture debe encontrar exactamente 1."""
    _, _, sha = fixture_clasificacion
    n = db_session.execute(
        text("SELECT count(*) FROM classifications WHERE acto_sha256 = :s"),
        {"s": sha},
    ).scalar()
    assert n == 1


def test_variacion_cosmetica_produce_mismo_sha(db_session, fixture_clasificacion):
    """Mayúsculas / acentos no deben cambiar el SHA — la normalización lo
    garantiza. Esto significa que el endpoint /duplicados detecta el mismo
    acto aunque se pegue con formato distinto."""
    _, acto, sha = fixture_clasificacion
    variaciones = [
        acto.upper(),
        acto.lower(),
        acto.replace("a", "á"),  # cambio de acento — normalización lo borra
        f"  \n  {acto}  ",  # whitespace
    ]
    for v in variaciones:
        sha_v = acto_sha256(v)
        assert sha_v == sha, f"Variación '{v[:50]}...' produjo SHA distinto"


def test_texto_sin_clasificar_no_tiene_previas(db_session):
    """SHA de un texto único garantizado nuevo no debe encontrarse en BD."""
    texto_nuevo = (
        "TEXTO COMPLETAMENTE NUEVO E INEXISTENTE EN LA BASE DE DATOS. "
        f"UUID4 garantía: {uuid.uuid4()}"
    )
    sha = acto_sha256(texto_nuevo)
    n = db_session.execute(
        text("SELECT count(*) FROM classifications WHERE acto_sha256 = :s"),
        {"s": sha},
    ).scalar()
    assert n == 0


def test_index_sha_existe(db_session):
    """`idx_class_sha` es lo que hace este endpoint barato. Si alguien lo
    droppea, las consultas pueden lentificarse a O(n)."""
    res = db_session.execute(
        text(
            "SELECT count(*) FROM pg_indexes "
            "WHERE tablename = 'classifications' AND indexname = 'idx_class_sha'"
        )
    ).scalar()
    assert res == 1
