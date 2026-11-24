from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel


class CategoriaPair(BaseModel):
    """Cruce predicción del modelo → veredicto final del proyectista.
    Sirve como matriz de confusión simplificada para diagnosticar dónde el
    modelo más se equivoca en producción."""

    predicha: str
    final: str
    n: int


class ModeloStats(BaseModel):
    version: str
    algoritmo: str
    n_tesis_train: int
    fecha_corte: date
    metricas: dict[str, Any]
    activo: bool

    # Métricas operativas (sobre classifications reales en producción)
    total_clasificaciones: int
    distribucion_predicciones: dict[str, int]  # categoría → cuántas veces se predijo
    n_validadas: int  # con veredicto vigente firmado
    n_aceptadas: int
    n_corregidas: int
    tasa_aceptacion: float | None  # n_aceptadas / n_validadas

    # Matriz simplificada: solo pares (predicha, final) con n >= 1.
    correcciones: list[CategoriaPair]

    # Diagnóstico: clases cuya distribución de predicciones es 0
    # (el modelo nunca las dice)
    clases_no_predichas: list[str]


class ModelVersionListItem(BaseModel):
    id: uuid.UUID
    version: str
    algoritmo: str
    n_tesis_train: int
    fecha_corte: date
    activo: bool
    created_at: datetime
    f1_macro: float | None
