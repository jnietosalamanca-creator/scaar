from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

# Las 7 categorías que un proyectista puede asignar como corrección de un
# veredicto. 'no_aplica' NO está aquí — eso es decisión de etiquetado de
# corpus, no de procedencia de un caso real. Si el caso de verdad no aplica,
# la clasificación nunca debió iniciarse.
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


class ValidateRequest(BaseModel):
    veredicto: Literal["acepta", "rechaza"]
    clasificacion_corregida: VeredictoCategoria | None = None
    comentario: str | None = Field(default=None, max_length=4000)
    supersedes_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def coherencia(self) -> "ValidateRequest":
        if self.veredicto == "rechaza" and self.clasificacion_corregida is None:
            raise ValueError("veredicto=rechaza requiere clasificacion_corregida")
        if self.veredicto == "acepta" and self.clasificacion_corregida is not None:
            raise ValueError("veredicto=acepta no admite clasificacion_corregida")
        return self


class ValidateResponse(BaseModel):
    id: uuid.UUID
    classification_id: uuid.UUID
    validated_by: uuid.UUID
    validated_at: datetime
    veredicto: Literal["acepta", "rechaza"]
    clasificacion_corregida: VeredictoCategoria | None
    comentario: str | None
    firma_sha256: str
    supersedes_id: uuid.UUID | None
