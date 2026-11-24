from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.classify import (
    Inmediatez,
    PrediccionCategoria,
    ViaAmparo,
)

# Alias coherente con el nombre que usa el frontend
InmediatezAmparo = Inmediatez


class CasoCreate(BaseModel):
    identificador: str = Field(min_length=1, max_length=200)
    descripcion: str | None = Field(default=None, max_length=4000)
    materia: str | None = Field(default=None, max_length=80)


class CasoSinteticoRequest(BaseModel):
    """Configuración para generar un caso al azar (práctica)."""

    n_actos: int = Field(default=4, ge=1, le=12)
    # Si está vacía, se elige aleatoriamente de las 8 categorías. Si está
    # dada, cada acto sale de esa lista (con repetición).
    categorias_objetivo: list[
        Literal[
            "fuera_juicio",
            "en_juicio_imposible",
            "en_juicio_diferida",
            "post_juicio_general",
            "post_juicio_ejecucion",
            "post_juicio_prematuro",
            "tercero_extrano",
            "sentencia_definitiva",
        ]
    ] = Field(default_factory=list)
    # Seed opcional para reproducibilidad (útil en tests / demos).
    seed: int | None = None


class CasoUpdate(BaseModel):
    identificador: str | None = Field(default=None, min_length=1, max_length=200)
    descripcion: str | None = Field(default=None, max_length=4000)
    materia: str | None = Field(default=None, max_length=80)
    archived: bool | None = None


class CasoListItem(BaseModel):
    id: uuid.UUID
    identificador: str
    descripcion: str | None
    materia: str | None
    created_at: datetime
    archived_at: datetime | None
    n_actos: int
    n_indirectos: int
    n_directos: int
    n_prematuros: int


class CasoListResponse(BaseModel):
    items: list[CasoListItem]
    total: int
    limit: int
    offset: int


class ActoEnCaso(BaseModel):
    classification_id: uuid.UUID
    acto_preview: str
    categoria: PrediccionCategoria
    via: ViaAmparo
    inmediatez: InmediatezAmparo
    alerta: str | None
    prob_categoria: float | None
    requiere_revision_humana: bool
    veredicto_vigente: Literal["acepta", "rechaza"] | None
    clasificacion_final: PrediccionCategoria | None
    created_at: datetime


class DemandaSugerida(BaseModel):
    """Una demanda concreta a presentar (1 o N actos agrupados)."""

    via: ViaAmparo
    titulo: str  # ej. "Amparo indirecto inmediato"
    explicacion: str  # narrativa: por qué presentar esto
    actos: list[uuid.UUID]  # classification_id de los actos que se reclaman
    inmediatez: InmediatezAmparo
    violaciones_acumulables: list[uuid.UUID]  # actos que se acumulan en la demanda
    alerta: str | None


class CasoResumen(BaseModel):
    """Plan jurídico del expediente: qué demandas presentar y en qué orden."""

    caso_id: uuid.UUID
    n_actos: int
    demandas: list[DemandaSugerida]
    actos_prematuros: list[uuid.UUID]  # esperar última resolución
    actos_no_aplica: list[uuid.UUID]  # categoría no_aplica o sin clasificar


class CasoDetail(BaseModel):
    id: uuid.UUID
    identificador: str
    descripcion: str | None
    materia: str | None
    created_by: uuid.UUID
    created_by_email: str
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None
    actos: list[ActoEnCaso]
    resumen: CasoResumen


class EjecutoriaImportItem(BaseModel):
    """Un caso real extraído del SJF (output de fetch_ejecutorias.py)."""

    registro_sjf: str = Field(min_length=1, max_length=20)
    tipo_asunto: str = Field(min_length=1, max_length=200)
    # SJF a veces emite rubros muy largos (vi 651 chars). Tope generoso.
    rubro: str = Field(min_length=1, max_length=2000)
    instancia: str = Field(min_length=1, max_length=200)
    promovente: str | None = None
    fecha_publ: str | None = None  # YYYY-MM-DD
    url_semanario: str | None = None
    acto_reclamado_candidato: str = Field(min_length=20, max_length=8000)
    # 'antecedentes' (más confiable) | 'regex_acto' | 'fallback_head'
    metodo_extraccion: Literal["antecedentes", "regex_acto", "fallback_head"]


class EjecutoriasImportRequest(BaseModel):
    items: list[EjecutoriaImportItem] = Field(min_length=1, max_length=500)


class EjecutoriasImportResponse(BaseModel):
    creados: int
    duplicados: int  # ya existían para este usuario
    invalidos: int  # error de inserción
    caso_ids: list[uuid.UUID]  # ids de los creados (en orden)
