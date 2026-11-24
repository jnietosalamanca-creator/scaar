"""Cache del modelo activo en memoria del proceso.

`get_active_model()` lee `model_versions.activo=TRUE`, carga el .joblib y lo
guarda en caché. Si la versión activa cambia (otro proceso entrenó), invalida.
"""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from typing import Any

import joblib
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ModelVersion


@dataclass
class LoadedModel:
    version_id: str
    version: str
    artifact: dict[str, Any]


_cache: LoadedModel | None = None
_lock = Lock()


def get_active_model(db: Session) -> LoadedModel:
    global _cache

    active = db.execute(
        select(ModelVersion).where(ModelVersion.activo.is_(True))
    ).scalar_one_or_none()
    if active is None:
        raise RuntimeError("No hay modelo activo. Corre `python -m app.ml.train`.")

    with _lock:
        if _cache is None or _cache.version_id != str(active.id):
            artifact = joblib.load(active.artifact_path)
            _cache = LoadedModel(
                version_id=str(active.id),
                version=active.version,
                artifact=artifact,
            )
        return _cache


def invalidate_cache() -> None:
    global _cache
    with _lock:
        _cache = None
