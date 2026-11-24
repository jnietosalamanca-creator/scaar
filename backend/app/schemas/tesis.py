from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

EtiquetaLabel = Literal[
    "fuera_juicio",
    "en_juicio_imposible",
    "en_juicio_diferida",
    "post_juicio_general",
    "post_juicio_ejecucion",
    "post_juicio_prematuro",
    "tercero_extrano",
    "sentencia_definitiva",
    "no_aplica",
]

TipoJurisprudencial = Literal[
    "regla",
    "excepcion",
    "aislada_dudosa",
    "derogada",
]


class TesisListItem(BaseModel):
    id: uuid.UUID
    registro_sjf: str
    epoca: str
    instancia: str
    tipo: Literal["jurisprudencia", "aislada"]
    rubro: str
    fecha_publ: date | None
    etiqueta: EtiquetaLabel | None
    etiquetada_por_email: str | None
    etiquetada_at: datetime | None
    fuente: str
    created_at: datetime
    es_doctrina_canonica: bool
    tipo_jurisprudencial: TipoJurisprudencial


class TesisListResponse(BaseModel):
    items: list[TesisListItem]
    total: int
    limit: int
    offset: int


class TesisDetail(BaseModel):
    id: uuid.UUID
    registro_sjf: str
    epoca: str
    instancia: str
    tipo: Literal["jurisprudencia", "aislada"]
    rubro: str
    texto: str
    etiqueta: EtiquetaLabel | None
    fecha_publ: date | None
    fuente: str
    etiquetada_por_email: str | None
    etiquetada_at: datetime | None
    created_at: datetime
    es_doctrina_canonica: bool
    tipo_jurisprudencial: TipoJurisprudencial
    notas_metodologicas: str | None


class LabelTesisRequest(BaseModel):
    etiqueta: EtiquetaLabel
    tipo_jurisprudencial: TipoJurisprudencial | None = None
    notas_metodologicas: str | None = None


class TipoJurisprudencialRequest(BaseModel):
    """Update solo del rol jurisprudencial (sin tocar etiqueta)."""

    tipo_jurisprudencial: TipoJurisprudencial
    notas_metodologicas: str | None = None


class ImportTesisItem(BaseModel):
    registro_sjf: str = Field(min_length=1, max_length=64)
    epoca: str
    instancia: str
    tipo: Literal["jurisprudencia", "aislada"]
    rubro: str
    texto: str = Field(min_length=20)
    etiqueta: EtiquetaLabel | None = None
    fecha_publ: date | None = None


class ImportTesisRequest(BaseModel):
    fuente: str = Field(default="import_jsonl", min_length=1, max_length=50)
    items: list[ImportTesisItem] = Field(min_length=1, max_length=2000)


class ImportTesisResponse(BaseModel):
    insertadas: int
    duplicadas: int
    errores: list[str]


class TopProb(BaseModel):
    categoria: str
    prob: float


class TesisInciertaItem(BaseModel):
    """Tesis pendiente con métricas de cuánto le cuesta al modelo predecir.

    `entropia` está normalizada a [0, 1]: 0 = el modelo está totalmente
    seguro, 1 = todas las clases son igualmente probables (máxima duda).
    Las tesis con entropía alta son las más informativas para etiquetar
    (active learning).
    """

    id: uuid.UUID
    registro_sjf: str
    instancia: str
    tipo: Literal["jurisprudencia", "aislada"]
    rubro: str
    texto: str
    fecha_publ: date | None
    fuente: str
    created_at: datetime
    entropia: float  # [0, 1]
    top_probs: list[TopProb]  # top 3 categorías más probables


class TesisAuditoriaItem(BaseModel):
    """Tesis YA ETIQUETADA donde el modelo activo discrepa con la etiqueta
    humana, O donde el modelo no está seguro de la etiqueta humana.

    Útil para:
      • Detectar etiquetas humanas posiblemente erróneas (modelo predice
        otra cosa con alta confianza).
      • Detectar casos donde el modelo aprendió mal (modelo predice la
        misma categoría pero con muy baja confianza).
    """

    id: uuid.UUID
    registro_sjf: str
    rubro: str
    etiqueta_humana: EtiquetaLabel
    etiquetada_por_email: str | None
    categoria_modelo: str  # lo que el modelo predeciría
    prob_categoria_modelo: float
    prob_de_etiqueta_humana: float  # cuánta probabilidad asigna el modelo a la etiqueta del humano
    discrepa: bool  # categoria_modelo != etiqueta_humana
    fuente: str


class CorpusStats(BaseModel):
    total: int
    etiquetadas: int
    pendientes: int
    # Conteos por categoría nueva (8 etiquetas)
    por_categoria: dict[str, int]
    por_fuente: dict[str, int]
    # "Listas para entrenar" = todas etiquetadas excepto no_aplica.
    # El modelo multiclase futuro entrenará con 7 categorías.
    listas_para_entrenar: int
    listas_para_train_limpio: int
    fuentes_excluidas: list[str]
    threshold_train_limpio: int
