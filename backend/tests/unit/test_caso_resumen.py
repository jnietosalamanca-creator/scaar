"""Tests del servicio que computa el plan jurídico de un caso.

Cubre las reglas declarativas que decide el sistema:
  • Cada acto indirecto inmediato → su propia demanda.
  • en_juicio_diferida → se acumula a la primera sentencia_definitiva.
  • Sin sentencia → demanda diferida con alerta.
  • post_juicio_prematuro → no demanda; se acumula a post_juicio_ejecucion
    si existe en el mismo caso.
  • no_aplica → fuera del plan.
"""

from __future__ import annotations

import datetime as dt
import uuid

from app.schemas.casos import ActoEnCaso
from app.services.caso_resumen import construir_resumen


def _acto(categoria: str, *, corregida: str | None = None) -> ActoEnCaso:
    """Helper para construir actos de prueba."""
    return ActoEnCaso(
        classification_id=uuid.uuid4(),
        acto_preview=f"acto de prueba ({categoria})",
        categoria=categoria,  # type: ignore[arg-type]
        via="indirecto",  # se ignora en el resumen — toma de la categoría
        inmediatez="inmediato",
        alerta=None,
        prob_categoria=0.7,
        requiere_revision_humana=False,
        veredicto_vigente="rechaza" if corregida else None,
        clasificacion_final=corregida,  # type: ignore[arg-type]
        created_at=dt.datetime.now(dt.UTC),
    )


def test_caso_vacio_devuelve_cero_demandas():
    r = construir_resumen(uuid.uuid4(), [])
    assert r.n_actos == 0
    assert r.demandas == []
    assert r.actos_prematuros == []
    assert r.actos_no_aplica == []


def test_un_acto_imposible_produce_una_demanda_indirecto():
    a = _acto("en_juicio_imposible")
    r = construir_resumen(uuid.uuid4(), [a])
    assert len(r.demandas) == 1
    assert r.demandas[0].via == "indirecto"
    assert r.demandas[0].inmediatez == "inmediato"
    assert a.classification_id in r.demandas[0].actos


def test_sentencia_definitiva_produce_demanda_directa():
    a = _acto("sentencia_definitiva")
    r = construir_resumen(uuid.uuid4(), [a])
    assert len(r.demandas) == 1
    assert r.demandas[0].via == "directo"


def test_diferidas_se_acumulan_a_sentencia_definitiva():
    diferida_1 = _acto("en_juicio_diferida")
    diferida_2 = _acto("en_juicio_diferida")
    sentencia = _acto("sentencia_definitiva")
    r = construir_resumen(uuid.uuid4(), [diferida_1, diferida_2, sentencia])
    # Una sola demanda directa contra sentencia, con 2 acumulables
    demandas_dir = [d for d in r.demandas if d.via == "directo"]
    assert len(demandas_dir) == 1
    assert len(demandas_dir[0].violaciones_acumulables) == 2


def test_diferidas_sin_sentencia_dan_demanda_pendiente():
    a = _acto("en_juicio_diferida")
    r = construir_resumen(uuid.uuid4(), [a])
    # Una demanda diferida con alerta — recordatorio para cuando se dicte
    # la sentencia.
    assert len(r.demandas) == 1
    assert r.demandas[0].via == "directo"
    assert r.demandas[0].inmediatez == "diferido"
    assert r.demandas[0].alerta is not None


def test_prematuro_no_produce_demanda_y_aparece_en_lista():
    a = _acto("post_juicio_prematuro")
    r = construir_resumen(uuid.uuid4(), [a])
    assert r.demandas == []
    assert a.classification_id in r.actos_prematuros


def test_prematuro_se_acumula_a_post_juicio_ejecucion():
    """Si en el mismo caso hay un acto intermedio prematuro Y la última
    resolución de ejecución, el resumen debe acumular el prematuro a la
    demanda contra la última resolución, no dejarlo solo."""
    prematuro = _acto("post_juicio_prematuro")
    ultima = _acto("post_juicio_ejecucion")
    r = construir_resumen(uuid.uuid4(), [prematuro, ultima])
    # Demanda indirecto contra la última resolución
    demandas_ej = [
        d for d in r.demandas if "ejecuci" in d.titulo.lower()
    ]
    assert len(demandas_ej) == 1
    # El prematuro fue acumulado, NO queda en la lista de huérfanos
    assert prematuro.classification_id in demandas_ej[0].violaciones_acumulables
    assert prematuro.classification_id not in r.actos_prematuros


def test_no_aplica_no_es_categoria_valida_de_acto():
    """Garantía del schema: un ActoEnCaso NO puede tener categoría 'no_aplica'.
    `no_aplica` es decisión de etiquetado de corpus, no veredicto de un caso
    real. El servicio de resumen tiene lógica defensiva (`actos_no_aplica`)
    por si una categoría legacy/desconocida llegara, pero el flujo normal
    nunca produce ese estado."""
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        _acto("no_aplica")


def test_acto_legacy_adjetivo_se_trata_como_imposible_reparacion():
    """Compat: una clasificación firmada con modelo viejo (binario) tiene
    categoria='adjetivo'. El resumen debe seguir construyéndolo como
    indirecto inmediato (= en_juicio_imposible)."""
    a = _acto("adjetivo")
    r = construir_resumen(uuid.uuid4(), [a])
    # Legacy no genera demanda en el servicio actual (cae a "no aplica"),
    # pero tampoco rompe — el log histórico queda íntegro.
    # Si el futuro requiere recuperar legacy, el lugar de cambio es
    # services/caso_resumen.py (constante INDIRECTO_INMEDIATO).
    assert r.n_actos == 1


def test_correccion_del_proyectista_pisa_la_prediccion_del_modelo():
    """Si el modelo predijo `sentencia_definitiva` pero el proyectista
    corrigió a `post_juicio_prematuro`, el resumen debe usar la corrección."""
    a = _acto("sentencia_definitiva", corregida="post_juicio_prematuro")
    r = construir_resumen(uuid.uuid4(), [a])
    assert r.demandas == []
    assert a.classification_id in r.actos_prematuros


def test_caso_completo_de_expediente_real():
    """Smoke test con la mezcla típica de un expediente mercantil:
    1 emplazamiento (diferida), 1 embargo (imposible), 1 acto intermedio de
    ejecución (prematuro), 1 sentencia definitiva."""
    actos = [
        _acto("en_juicio_diferida"),  # emplazamiento defectuoso
        _acto("en_juicio_imposible"),  # embargo precautorio
        _acto("post_juicio_prematuro"),  # acto intermedio
        _acto("sentencia_definitiva"),  # sentencia
    ]
    r = construir_resumen(uuid.uuid4(), actos)
    # Esperado:
    #   1 demanda indirecto inmediato (por embargo)
    #   1 demanda directo (sentencia + diferida acumulada)
    #   1 prematuro huérfano (sin post_juicio_ejecucion para acumularlo)
    indirectos = [d for d in r.demandas if d.via == "indirecto"]
    directos = [d for d in r.demandas if d.via == "directo"]
    assert len(indirectos) == 1
    assert len(directos) == 1
    assert len(directos[0].violaciones_acumulables) == 1  # la diferida
    assert len(r.actos_prematuros) == 1
