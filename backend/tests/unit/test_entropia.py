"""Tests del cálculo de entropía usado por active learning.

Validan que la fórmula de Shannon normalizada produce:
  • 0 cuando una clase concentra toda la probabilidad.
  • 1 cuando la distribución es uniforme sobre todas las clases.
  • Valores monotónicos (más reparto → más entropía).
"""

from __future__ import annotations

import math

import pytest


def entropia_normalizada(probs: list[float]) -> float:
    """Replica de la función inline del endpoint /tesis/inciertas."""
    n = len(probs)
    if n <= 1:
        return 0.0
    log_max = math.log(n)
    h = -sum(p * math.log(p) for p in probs if p > 0)
    return h / log_max


def test_entropia_cero_cuando_clase_dominante_absoluta():
    """Una sola clase con 100% probabilidad → entropía 0 (modelo seguro)."""
    assert entropia_normalizada([1.0, 0.0, 0.0]) == pytest.approx(0.0)


def test_entropia_uno_cuando_uniforme():
    """Probabilidades repartidas equitativamente → entropía 1 (máxima duda).
    Normalización por log(n) garantiza este tope."""
    for n in [2, 3, 5, 8, 10]:
        probs = [1.0 / n] * n
        assert entropia_normalizada(probs) == pytest.approx(1.0, abs=1e-9)


def test_entropia_intermedia():
    """Caso típico: una clase domina pero hay duda residual.
    [0.7, 0.2, 0.1] / log(3) ≈ 0.73 — confirmado a mano."""
    h = entropia_normalizada([0.7, 0.2, 0.1])
    assert 0.5 < h < 0.85


def test_entropia_monotonia():
    """Más concentración → menos entropía."""
    h_concentrada = entropia_normalizada([0.9, 0.05, 0.05])
    h_dispersa = entropia_normalizada([0.4, 0.3, 0.3])
    assert h_concentrada < h_dispersa


def test_entropia_tolera_ceros():
    """log(0) explotaría — el filtro `if p > 0` lo evita."""
    h = entropia_normalizada([0.5, 0.5, 0.0, 0.0])
    # Equivale a entropía sobre 2 clases uniformes, normalizada por log(4)
    expected = math.log(2) / math.log(4)
    assert h == pytest.approx(expected, abs=1e-9)
