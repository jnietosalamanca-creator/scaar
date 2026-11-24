"""Tests del endpoint POST /casos/import-ejecutorias.

Verifica que:
  • Crea un Caso por cada item con identificador=SJF-EXEC-{ius}, materia
    'sjf_ejecutoria', y descripcion con header + acto reclamado.
  • Es idempotente: re-importar el mismo ius por el mismo usuario suma
    a `duplicados`, no a `creados`.
  • Respeta el max_length=4000 de descripcion: si el acto es enorme, se
    trunca con elipsis sin reventar.
  • Requiere autenticación.
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError, OperationalError

from app.api.deps import current_user
from app.db.models import Caso, User
from app.db.session import SessionLocal, engine
from app.main import app


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
def user_proyectista(db_session):
    u = db_session.scalar(
        select(User).where(User.email == "proyectista@scaar.local")
    )
    if u is None:
        pytest.skip("Sin usuario proyectista")
    return u


@pytest.fixture
def client(user_proyectista):
    """TestClient con auth bypaseada al proyectista (vía dep override)."""
    app.dependency_overrides[current_user] = lambda: user_proyectista
    yield TestClient(app)
    app.dependency_overrides.pop(current_user, None)


@pytest.fixture
def cleanup_casos(db_session, user_proyectista):
    """Limpia casos SJF-EXEC creados por este usuario al final del test."""
    yield
    db_session.execute(
        text(
            "DELETE FROM cases WHERE created_by = :uid "
            "AND identificador LIKE 'SJF-EXEC-TEST-%'"
        ),
        {"uid": user_proyectista.id},
    )
    db_session.commit()


def _make_item(ius_suffix: str, acto_len: int = 200) -> dict:
    """Genera un item de import con ius='TEST-{suffix}' para no chocar con datos reales."""
    return {
        "registro_sjf": f"TEST-{ius_suffix}",
        "tipo_asunto": "AMPARO EN REVISIÓN 999/2025.",
        "rubro": "RUBRO DE PRUEBA PARA IMPORT — NO TOCAR.",
        "instancia": "Primera Sala SCJN",
        "promovente": "Quejoso de prueba",
        "fecha_publ": "2025-11-14",
        "url_semanario": "https://sjf2.scjn.gob.mx/test",
        "acto_reclamado_candidato": "Acto reclamado: " + ("x" * (acto_len - 20)) + ".",
        "metodo_extraccion": "antecedentes",
    }


def test_import_crea_casos(client, db_session, user_proyectista, cleanup_casos):
    payload = {
        "items": [
            _make_item("001"),
            _make_item("002"),
            _make_item("003"),
        ]
    }
    r = client.post("/casos/import-ejecutorias", json=payload)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["creados"] == 3
    assert body["duplicados"] == 0
    assert body["invalidos"] == 0
    assert len(body["caso_ids"]) == 3

    # Verificar en DB
    casos = list(
        db_session.scalars(
            select(Caso).where(
                Caso.created_by == user_proyectista.id,
                Caso.identificador.like("SJF-EXEC-TEST-%"),
            )
        )
    )
    assert len(casos) == 3
    for c in casos:
        assert c.materia == "sjf_ejecutoria"
        assert c.identificador.startswith("SJF-EXEC-TEST-")
        assert "AMPARO EN REVISIÓN" in (c.descripcion or "")
        assert "Acto reclamado:" in (c.descripcion or "")


def test_import_es_idempotente(client, db_session, user_proyectista, cleanup_casos):
    payload = {"items": [_make_item("IDEM-001"), _make_item("IDEM-002")]}
    r1 = client.post("/casos/import-ejecutorias", json=payload)
    assert r1.status_code == 201
    assert r1.json()["creados"] == 2

    # Re-import: mismo ius → debe sumar a duplicados, no a creados
    r2 = client.post("/casos/import-ejecutorias", json=payload)
    assert r2.status_code == 201
    body2 = r2.json()
    assert body2["creados"] == 0
    assert body2["duplicados"] == 2


def test_import_trunca_descripcion_larga(
    client, db_session, user_proyectista, cleanup_casos
):
    """Un acto reclamado de 8000 chars debe truncarse para caber en 4000."""
    item = _make_item("LARGO-001", acto_len=7900)
    r = client.post("/casos/import-ejecutorias", json={"items": [item]})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["creados"] == 1

    caso_id = uuid.UUID(body["caso_ids"][0])
    caso = db_session.get(Caso, caso_id)
    assert caso is not None
    assert caso.descripcion is not None
    # Debe terminar con elipsis y caber en el límite de la columna (Text, sin
    # límite duro de DB, pero la lógica del endpoint sí trunca a 4000).
    assert len(caso.descripcion) <= 4000
    assert caso.descripcion.endswith("…")


def test_import_requiere_auth():
    """Sin Bearer → 401."""
    payload = {"items": [_make_item("UNAUTH-001")]}
    # Cliente sin override
    raw = TestClient(app)
    r = raw.post("/casos/import-ejecutorias", json=payload)
    assert r.status_code == 401


def test_import_rechaza_payload_vacio(client):
    r = client.post("/casos/import-ejecutorias", json={"items": []})
    assert r.status_code == 422
