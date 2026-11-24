from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

# Conjunto completo de categorías que pueden aparecer como `prediccion`
# (incluye legacy 'adjetivo'/'sustantivo' por compat con logs viejos).
PrediccionCategoria = Literal[
    "adjetivo",
    "sustantivo",
    "fuera_juicio",
    "en_juicio_imposible",
    "en_juicio_diferida",
    "post_juicio_general",
    "post_juicio_ejecucion",
    "post_juicio_prematuro",
    "tercero_extrano",
    "sentencia_definitiva",
]

# Las que un proyectista puede usar como corrección (sin no_aplica, sin legacy).
VeredictoCategoria = Literal[
    "fuera_juicio",
    "en_juicio_imposible",
    "en_juicio_diferida",
    "post_juicio_general",
    "post_juicio_ejecucion",
    "post_juicio_prematuro",
    "tercero_extrano",
    "sentencia_definitiva",
]

ViaAmparo = Literal["indirecto", "directo", "ninguna"]
Inmediatez = Literal["inmediato", "diferido", "esperar_ultima_resolucion"]


class ClassifyRequest(BaseModel):
    acto_reclamado: str = Field(min_length=10, max_length=20000)
    case_id: uuid.UUID | None = None  # asociación opcional a un expediente


class DuplicadoItem(BaseModel):
    """Resumen mínimo de una clasificación previa con el mismo SHA del acto."""

    classification_id: uuid.UUID
    created_at: datetime
    created_by_email: str
    categoria_predicha: PrediccionCategoria
    veredicto_vigente: Literal["acepta", "rechaza"] | None
    clasificacion_final: PrediccionCategoria | None
    case_id: uuid.UUID | None
    case_identificador: str | None


class DuplicadosResponse(BaseModel):
    """Histórico de clasificaciones del mismo SHA. Si vacío, es nuevo."""

    acto_sha256: str
    n_previas: int
    previas: list[DuplicadoItem]


class TopFeature(BaseModel):
    token: str
    contribucion: float
    tfidf: float


class TopAnaloga(BaseModel):
    tesis_id: str
    registro_sjf: str
    rubro: str
    etiqueta: str  # cualquier categoría del corpus (incl. no_aplica)
    similitud: float


class ClassifyResponse(BaseModel):
    classification_id: uuid.UUID
    acto_sha256: str
    model_version: str
    # Multiclase: el modelo activo predice 1 de N categorías.
    categoria: PrediccionCategoria
    via: ViaAmparo
    inmediatez: Inmediatez
    alerta: str | None
    prob_categoria: float
    prob_por_clase: dict[str, float]
    requiere_revision_humana: bool
    top_features: list[TopFeature]
    top_analogas: list[TopAnaloga]
    created_at: datetime


class ValidationDetail(BaseModel):
    id: uuid.UUID
    validated_by: uuid.UUID
    validated_by_email: str
    validated_at: datetime
    veredicto: Literal["acepta", "rechaza"]
    # Compat: puede ser una de las 7 nuevas o legacy 'adjetivo'/'sustantivo'.
    clasificacion_corregida: PrediccionCategoria | None
    comentario: str | None
    firma_sha256: str
    firma_valida: bool
    supersedes_id: uuid.UUID | None
    es_vigente: bool


class ClassificationDetail(BaseModel):
    id: uuid.UUID
    acto_reclamado: str
    acto_sha256: str
    model_version: str
    categoria: PrediccionCategoria
    via: ViaAmparo
    inmediatez: Inmediatez
    alerta: str | None
    prob_categoria: float | None
    prob_por_clase: dict[str, float] | None
    requiere_revision_humana: bool
    top_features: list[TopFeature]
    top_analogas: list[TopAnaloga]
    created_at: datetime
    created_by: uuid.UUID
    created_by_email: str
    historia_validaciones: list[ValidationDetail]
    vigente: ValidationDetail | None


class ClassificationListItem(BaseModel):
    id: uuid.UUID
    acto_sha256: str
    acto_preview: str
    model_version: str
    categoria: PrediccionCategoria
    via: ViaAmparo
    prob_categoria: float | None
    requiere_revision_humana: bool
    created_at: datetime
    created_by_email: str
    veredicto_vigente: Literal["acepta", "rechaza"] | None
    clasificacion_final: PrediccionCategoria | None
    n_validaciones: int


class ClassificationListResponse(BaseModel):
    items: list[ClassificationListItem]
    total: int
    limit: int
    offset: int
