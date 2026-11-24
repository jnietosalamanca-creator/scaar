"""Computa el plan jurídico de un expediente: qué demandas presentar.

Reglas determinísticas a partir de la categoría VIGENTE de cada acto del
caso (la del veredicto del proyectista si existe; si no, la del modelo):

  • Cada acto cuya categoría implica "amparo indirecto inmediato" produce
    una demanda separada (fuera_juicio, en_juicio_imposible, post_juicio_*
    que ya tienen última resolución, tercero_extrano).
  • `en_juicio_diferida` se acumula a la demanda directa contra la sentencia
    definitiva del caso si existe; si no, se reclama "diferidamente — al
    momento de la sentencia definitiva".
  • `sentencia_definitiva` produce una demanda de amparo directo (con sus
    diferidas acumuladas).
  • `post_juicio_prematuro` NO produce demanda — alerta y queda como
    acumulable a la última resolución del procedimiento de ejecución.
  • `no_aplica` y categorías legacy adj/sus se ignoran o agrupan separadas.

La salida es declarativa — el frontend la renderiza tal cual.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from typing import Iterable

from app.ml.predict import VIA_INMEDIATEZ
from app.schemas.casos import ActoEnCaso, CasoResumen, DemandaSugerida

# Cuál es la "categoría efectiva" — el veredicto del proyectista si existe,
# si no la predicción del modelo.
def _categoria_efectiva(acto: ActoEnCaso) -> str:
    return acto.clasificacion_final or acto.categoria


# Mapping: categoría → tipo de demanda (texto operativo)
DEMANDA_TITULO = {
    "fuera_juicio": "Amparo indirecto inmediato (acto fuera de juicio)",
    "en_juicio_imposible": "Amparo indirecto inmediato (imposible reparación)",
    "tercero_extrano": "Amparo indirecto inmediato (tercero extraño)",
    "post_juicio_general": "Amparo indirecto (acto post-juicio)",
    "post_juicio_ejecucion": "Amparo indirecto (última resolución de ejecución)",
    "sentencia_definitiva": "Amparo directo contra sentencia definitiva",
}

DEMANDA_EXPLICACION = {
    "fuera_juicio": (
        "Acto de autoridad emitido fuera de procedimiento judicial. Procede "
        "amparo indirecto inmediato sin agotar definitividad."
    ),
    "en_juicio_imposible": (
        "Acto dentro de juicio que afecta materialmente derechos sustantivos "
        "(IV.2o.C. J/2). Procede amparo indirecto inmediato."
    ),
    "tercero_extrano": (
        "Persona ajena al juicio que resiente afectación. Procede amparo "
        "indirecto inmediato sin agotar definitividad."
    ),
    "post_juicio_general": (
        "Acto después de concluido el juicio, fuera de procedimiento de "
        "ejecución/remate. Procede amparo indirecto."
    ),
    "post_juicio_ejecucion": (
        "Última resolución del procedimiento de ejecución/remate. Procede "
        "amparo indirecto y se acumulan en esta demanda las violaciones "
        "intermedias del mismo procedimiento (art. 107.IV LA)."
    ),
    "sentencia_definitiva": (
        "Sentencia definitiva o resolución que pone fin al juicio. Procede "
        "amparo directo, con las violaciones procesales diferidas acumuladas."
    ),
}

INDIRECTO_INMEDIATO = {
    "fuera_juicio",
    "en_juicio_imposible",
    "tercero_extrano",
    "post_juicio_general",
    "post_juicio_ejecucion",
}


def construir_resumen(
    caso_id: uuid.UUID, actos: Iterable[ActoEnCaso]
) -> CasoResumen:
    actos_lista = list(actos)
    demandas: list[DemandaSugerida] = []
    prematuros: list[uuid.UUID] = []
    no_aplica: list[uuid.UUID] = []
    diferidas: list[uuid.UUID] = []  # en_juicio_diferida — se acumulan al directo
    sentencias: list[ActoEnCaso] = []

    # 1) Pasada principal: clasificar cada acto según su categoría efectiva
    for a in actos_lista:
        cat = _categoria_efectiva(a)
        if cat == "post_juicio_prematuro":
            prematuros.append(a.classification_id)
        elif cat == "en_juicio_diferida":
            diferidas.append(a.classification_id)
        elif cat == "sentencia_definitiva":
            sentencias.append(a)
        elif cat in INDIRECTO_INMEDIATO:
            via_info = VIA_INMEDIATEZ.get(cat, {"via": "indirecto", "inmediatez": "inmediato"})
            # Si es post_juicio_ejecucion, los prematuros del mismo caso se acumulan acá
            acumulables: list[uuid.UUID] = []
            if cat == "post_juicio_ejecucion":
                acumulables = list(prematuros)
            demandas.append(
                DemandaSugerida(
                    via=via_info["via"],  # type: ignore[arg-type]
                    titulo=DEMANDA_TITULO[cat],
                    explicacion=DEMANDA_EXPLICACION[cat],
                    actos=[a.classification_id],
                    inmediatez=via_info["inmediatez"],  # type: ignore[arg-type]
                    violaciones_acumulables=acumulables,
                    alerta=None,
                )
            )
        else:
            # no_aplica / legacy adj-sus / categoría desconocida
            no_aplica.append(a.classification_id)

    # 2) Demanda(s) de amparo directo: una por cada sentencia definitiva,
    #    con las en_juicio_diferida acumuladas (todas en la primera; si hay
    #    varias sentencias en el mismo caso, lo cual es raro, las diferidas
    #    se concentran en la primera y se anota en explicacion).
    if sentencias:
        for i, s in enumerate(sentencias):
            acumulables = list(diferidas) if i == 0 else []
            via_info = VIA_INMEDIATEZ.get("sentencia_definitiva", {"via": "directo", "inmediatez": "inmediato"})
            extra = ""
            if i == 0 and diferidas:
                extra = (
                    f" Acumula {len(diferidas)} violación(es) procesal(es) "
                    "diferida(s) del mismo expediente."
                )
            demandas.append(
                DemandaSugerida(
                    via=via_info["via"],  # type: ignore[arg-type]
                    titulo=DEMANDA_TITULO["sentencia_definitiva"],
                    explicacion=DEMANDA_EXPLICACION["sentencia_definitiva"] + extra,
                    actos=[s.classification_id],
                    inmediatez=via_info["inmediatez"],  # type: ignore[arg-type]
                    violaciones_acumulables=acumulables,
                    alerta=None,
                )
            )
    elif diferidas:
        # No hay sentencia definitiva todavía — las diferidas se reclaman
        # cuando la sentencia se dicte. Las dejo como "demanda diferida".
        demandas.append(
            DemandaSugerida(
                via="directo",
                titulo="Amparo directo (pendiente: esperar sentencia definitiva)",
                explicacion=(
                    "Estas violaciones procesales no son de imposible "
                    "reparación. Se acumularán a la demanda de amparo directo "
                    "que se presente contra la sentencia definitiva del juicio."
                ),
                actos=list(diferidas),
                inmediatez="diferido",
                violaciones_acumulables=[],
                alerta=(
                    "El expediente aún no tiene sentencia definitiva clasificada. "
                    "Cuando se dicte, agrégala como acto al caso para acumular "
                    "estas violaciones."
                ),
            )
        )

    # 3) Si hay prematuros pero ninguna post_juicio_ejecucion los recibió,
    #    quedan en "actos_prematuros" como recordatorio.
    prematuros_sin_acumular = list(prematuros)
    for d in demandas:
        for a_id in d.violaciones_acumulables:
            if a_id in prematuros_sin_acumular:
                prematuros_sin_acumular.remove(a_id)

    return CasoResumen(
        caso_id=caso_id,
        n_actos=len(actos_lista),
        demandas=demandas,
        actos_prematuros=prematuros_sin_acumular,
        actos_no_aplica=no_aplica,
    )
