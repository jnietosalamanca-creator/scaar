"""Genera casos sintéticos (paramétricos, sin LLM externo) para práctica.

Los casos generados:
  • Tienen `materia='sintetico'` y un identificador `SINT-<timestamp>` con
    sufijo aleatorio para evitar choques de UNIQUE.
  • Sus actos se clasifican con el modelo activo igual que cualquier otro,
    PERO la fuente queda marcada como sintética en la descripción del
    caso — no entran al training del modelo porque las `classifications`
    sí, pero el dataset de reentreno (`v_corpus_reentreno`) solo toma las
    aprobadas por socio.

El usuario aprovecha estos casos para:
  • Practicar el flujo (clasificar → firmar → ver resumen).
  • Probar el modelo en una distribución conocida de categorías.
  • Detectar bugs del servicio de resumen con configuraciones específicas
    (ej. caso con 3 prematuros + 1 ejecución).
"""

from __future__ import annotations

import datetime as dt
import random
import uuid

from sqlalchemy.orm import Session

from app.data.plantillas_actos import (
    CATEGORIAS_DISPONIBLES,
    generar_acto,
)
from app.db.models import Caso, User
from app.services.classifier import classify_and_log


def _identificador_unico() -> str:
    """SINT-YYYYMMDD-HHMMSS-XXXX (sufijo aleatorio para evitar colisiones
    si el usuario genera varios casos en el mismo segundo)."""
    now = dt.datetime.now(dt.UTC)
    sufijo = uuid.uuid4().hex[:4].upper()
    return f"SINT-{now:%Y%m%d-%H%M%S}-{sufijo}"


def _seleccionar_categorias(
    n_actos: int,
    categorias_objetivo: list[str] | None,
    seed: int | None,
) -> list[str]:
    """Devuelve la lista de categorías que tendrá cada acto del caso.

    Si `categorias_objetivo` está dado, se respeta como universo. Si no, se
    elige al azar de las 8 disponibles (excluyendo no_aplica que no es un
    veredicto de procedencia).
    """
    rng = random.Random(seed)
    universo = categorias_objetivo or CATEGORIAS_DISPONIBLES
    return [rng.choice(universo) for _ in range(n_actos)]


def generar_caso_sintetico(
    db: Session,
    user: User,
    n_actos: int = 4,
    categorias_objetivo: list[str] | None = None,
    seed: int | None = None,
) -> Caso:
    """Crea un caso sintético + clasifica N actos generados.

    Devuelve el `Caso` ya commiteado. Las classifications quedan asociadas
    vía `case_id`. El usuario puede entrar a `/casos/<id>` y ver el plan
    jurídico del caso completo.

    Raises:
        ValueError si n_actos < 1 o > 12, o si alguna categoría objetivo
        no es válida.
    """
    if not 1 <= n_actos <= 12:
        raise ValueError("n_actos debe estar entre 1 y 12")
    if categorias_objetivo:
        invalidas = [c for c in categorias_objetivo if c not in CATEGORIAS_DISPONIBLES]
        if invalidas:
            raise ValueError(f"categorías inválidas: {invalidas}")

    rng = random.Random(seed)
    categorias = _seleccionar_categorias(n_actos, categorias_objetivo, seed)

    # Crear el caso primero
    caso = Caso(
        identificador=_identificador_unico(),
        descripcion=(
            f"🎲 Caso sintético generado para práctica con {n_actos} actos "
            f"({', '.join(sorted(set(categorias)))}). Los textos vienen de "
            "plantillas paramétricas — no son casos reales."
        ),
        materia="sintetico",
        created_by=user.id,
    )
    db.add(caso)
    db.commit()
    db.refresh(caso)

    # Para cada categoría objetivo, generamos un texto y dejamos que el
    # modelo activo lo clasifique (eso le da realismo al ejercicio — el
    # usuario verá si el modelo acierta o no).
    for cat in categorias:
        texto = generar_acto(cat, rng=rng)
        classify_and_log(
            db=db,
            acto_reclamado=texto,
            user_id=user.id,
            case_id=caso.id,
        )

    return caso
