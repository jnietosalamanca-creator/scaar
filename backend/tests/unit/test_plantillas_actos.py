"""Tests del generador de actos sintéticos paramétricos.

Cubre:
  • Cada categoría tiene plantillas definidas.
  • generar_acto produce texto no vacío y de longitud razonable.
  • La sustitución de variables NO deja marcadores `{var}` sin reemplazar.
  • Con seed fija, la generación es reproducible.
"""

from __future__ import annotations

import random
import re

import pytest

from app.data.plantillas_actos import (
    CATEGORIAS_DISPONIBLES,
    PLANTILLAS,
    generar_acto,
)


CATEGORIAS_ESPERADAS = {
    "fuera_juicio",
    "en_juicio_imposible",
    "en_juicio_diferida",
    "post_juicio_general",
    "post_juicio_ejecucion",
    "post_juicio_prematuro",
    "tercero_extrano",
    "sentencia_definitiva",
}


def test_todas_las_categorias_tienen_plantillas():
    """Las 8 categorías de procedencia (sin no_aplica) deben tener al menos
    una plantilla. Si alguien agrega una categoría nueva al universo de
    veredictos, este test grita que falta plantilla."""
    assert set(PLANTILLAS.keys()) == CATEGORIAS_ESPERADAS


def test_cada_categoria_tiene_al_menos_3_plantillas():
    """3 es el mínimo razonable para evitar overfitting al patrón si el
    usuario practica seguido. Si una cae bajo 3, hay que sumar variedad."""
    for cat, plantillas in PLANTILLAS.items():
        assert len(plantillas) >= 3, f"{cat} tiene solo {len(plantillas)} plantilla(s)"


@pytest.mark.parametrize("categoria", sorted(CATEGORIAS_ESPERADAS))
def test_generar_acto_no_deja_marcadores_sin_reemplazar(categoria):
    """Genera 20 veces por categoría con seeds variados. Ningún texto debe
    salir con `{var}` literal — eso indicaría una plantilla con marcador
    sin valor en los pools."""
    for seed in range(20):
        texto = generar_acto(categoria, rng=random.Random(seed))
        marcadores = re.findall(r"\{[a-z_]+\}", texto)
        assert not marcadores, (
            f"Categoría {categoria}, seed {seed}: marcadores sin reemplazar: "
            f"{marcadores} en texto: {texto[:200]}"
        )


@pytest.mark.parametrize("categoria", sorted(CATEGORIAS_ESPERADAS))
def test_generar_acto_produce_longitud_razonable(categoria):
    """El acto debe tener al menos 80 caracteres (suficiente para que TF-IDF
    extraiga señal) y no más de 800 (no son tesis enteras)."""
    texto = generar_acto(categoria, rng=random.Random(0))
    assert 80 <= len(texto) <= 800, f"{categoria}: longitud {len(texto)}"


def test_seed_fija_es_reproducible():
    """Con la misma seed, el texto debe ser idéntico — clave para tests
    deterministicos del servicio completo."""
    t1 = generar_acto("en_juicio_imposible", rng=random.Random(123))
    t2 = generar_acto("en_juicio_imposible", rng=random.Random(123))
    assert t1 == t2


def test_seeds_distintas_dan_textos_diferentes():
    """Sanity: distintas seeds deben producir variedad."""
    textos = set()
    for seed in range(50):
        textos.add(generar_acto("en_juicio_imposible", rng=random.Random(seed)))
    # Con 50 seeds y 5 plantillas + pools de valores, esperamos al menos 10
    # textos distintos. Si solo hay 1-2, algo está roto.
    assert len(textos) >= 10, f"Solo {len(textos)} textos únicos en 50 seeds"


def test_categorias_disponibles_export_coincide_con_plantillas():
    """`CATEGORIAS_DISPONIBLES` se usa en el endpoint para validar input;
    debe ser exactamente las keys de `PLANTILLAS`."""
    assert set(CATEGORIAS_DISPONIBLES) == set(PLANTILLAS.keys())


def test_generar_acto_falla_con_categoria_invalida():
    with pytest.raises(KeyError):
        generar_acto("no_aplica")  # no_aplica no es categoría de procedencia
    with pytest.raises(KeyError):
        generar_acto("categoria_inexistente")
