from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.casos import router as casos_router
from app.api.classify import router as classify_router
from app.api.modelo import router as modelo_router
from app.api.tesis import router as tesis_router
from app.api.validate import router as validate_router
from app.core.config import settings

app = FastAPI(
    title="SCAAR",
    description="Sistema de Clasificación Automatizada de Actos Reclamados",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(classify_router)
app.include_router(validate_router)
app.include_router(tesis_router)
app.include_router(casos_router)
app.include_router(modelo_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "env": settings.app_env,
        "active_model": settings.ml_active_model_version or "(query DB)",
    }
