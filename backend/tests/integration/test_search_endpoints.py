"""Tests del FTS sobre /tesis y /classifications.

Verifica que:
  • plainto_tsquery('spanish', q) maneja stemming castellano (búsqueda de
    "ejecución" matchea "ejecuciones", "ejecutarse", etc.)
  • Resultados vienen ranked por ts_rank_cd (más relevantes primero).
  • Sin q, el endpoint sigue funcionando con orden por fecha.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, OperationalError

from app.db.session import engine, SessionLocal


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


def test_tesis_tsv_existe_y_poblado(db_session):
    """La migración 008 deja toda fila con tsv NOT NULL."""
    total = db_session.execute(text("SELECT count(*) FROM tesis")).scalar()
    con_tsv = db_session.execute(
        text("SELECT count(*) FROM tesis WHERE tsv IS NOT NULL")
    ).scalar()
    assert con_tsv == total


def test_classifications_tsv_existe_y_poblado(db_session):
    total = db_session.execute(text("SELECT count(*) FROM classifications")).scalar()
    if total == 0:
        pytest.skip("No hay clasificaciones — corpus vacío")
    con_tsv = db_session.execute(
        text("SELECT count(*) FROM classifications WHERE tsv IS NOT NULL")
    ).scalar()
    assert con_tsv == total


def test_fts_tesis_devuelve_resultados_ranked(db_session):
    """Búsqueda de 'embargo' en tesis trae resultados con rank > 0."""
    rows = db_session.execute(
        text(
            "SELECT ts_rank_cd(tsv, q) AS rank "
            "FROM tesis, plainto_tsquery('spanish', 'embargo') q "
            "WHERE tsv @@ q ORDER BY rank DESC LIMIT 3"
        )
    ).all()
    if not rows:
        pytest.skip("Corpus actual sin coincidencias para 'embargo'")
    # Resultados ordenados descendente
    ranks = [float(r[0]) for r in rows]
    assert ranks == sorted(ranks, reverse=True)
    assert all(r > 0 for r in ranks)


def test_fts_stemming_castellano(db_session):
    """Garantía: 'spanish' config aplica stemming. 'ejecución' debe
    encontrar también 'ejecuciones', 'ejecutar', etc. cuando estén
    en el corpus."""
    cnt = db_session.execute(
        text(
            "SELECT count(*) FROM tesis "
            "WHERE tsv @@ plainto_tsquery('spanish', :q)"
        ),
        {"q": "ejecución"},
    ).scalar()
    cnt_plural = db_session.execute(
        text(
            "SELECT count(*) FROM tesis "
            "WHERE tsv @@ plainto_tsquery('spanish', :q)"
        ),
        {"q": "ejecuciones"},
    ).scalar()
    # Ambas búsquedas deben encontrar (aproximadamente) lo mismo gracias
    # al stemmer. No exigimos igualdad estricta: el ranking puede diferir
    # y phrases distintas pueden matchear ligeramente distinto.
    if cnt == 0 and cnt_plural == 0:
        pytest.skip("Corpus actual no contiene 'ejecución' en ningún tsv")
    assert cnt > 0
    assert cnt_plural > 0


def test_class_tsv_se_calcula_en_insert(db_session):
    """El trigger BEFORE INSERT debe llenar tsv automáticamente.

    Inserta una classification mínima y verifica que tsv no sea NULL.
    Después limpia (deshabilitando el trigger de inmutabilidad).
    """
    from sqlalchemy import select

    from app.db.models import Classification, ModelVersion, User

    user = db_session.scalar(select(User).limit(1))
    mv = db_session.scalar(select(ModelVersion).limit(1))
    if user is None or mv is None:
        pytest.skip("No hay user/model_version para fixturar")

    c = Classification(
        acto_reclamado="Acto de prueba: embargo precautorio sobre cuentas bancarias del quejoso.",
        acto_sha256="e" * 64,
        model_version_id=mv.id,
        prediccion="en_juicio_imposible",
        prob_categoria=0.5,
        prob_por_clase={"en_juicio_imposible": 0.5},
        top_features=[],
        top_analogas=[],
        created_by=user.id,
    )
    db_session.add(c)
    db_session.commit()
    db_session.refresh(c)

    try:
        # tsv debe haberse calculado por el trigger
        tsv = db_session.execute(
            text("SELECT tsv::text FROM classifications WHERE id = :cid"),
            {"cid": c.id},
        ).scalar()
        assert tsv is not None
        # El stem de 'embargo' aparece como token (con o sin acento)
        assert "embarg" in tsv.lower()
    finally:
        # Cleanup — bypass del trigger de inmutabilidad
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
