from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=200)
    password: str = Field(min_length=1, max_length=200)


class MeResponse(BaseModel):
    id: uuid.UUID
    email: str
    nombre_completo: str
    rol: Literal["proyectista", "socio", "admin"]


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: MeResponse
