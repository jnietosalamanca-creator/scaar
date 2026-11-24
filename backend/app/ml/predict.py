"""Predicción multiclase + outputs derivados (vía / inmediatez / alerta)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.ml.explain import top_analogas, top_features
from app.ml.loader import LoadedModel
from app.ml.preprocessing import normalize_text

# Reglas determinísticas: dada la categoría predicha, la vía y la inmediatez
# son función pura. Si en el futuro hay reglas más finas (ej. distinción
# fuera_juicio judicial vs admin), aquí es donde se ramifican.
VIA_INMEDIATEZ: dict[str, dict[str, str]] = {
    "fuera_juicio": {"via": "indirecto", "inmediatez": "inmediato"},
    "en_juicio_imposible": {"via": "indirecto", "inmediatez": "inmediato"},
    "en_juicio_diferida": {"via": "directo", "inmediatez": "diferido"},
    "post_juicio_general": {"via": "indirecto", "inmediatez": "inmediato"},
    "post_juicio_ejecucion": {"via": "indirecto", "inmediatez": "inmediato"},
    "post_juicio_prematuro": {
        "via": "ninguna",
        "inmediatez": "esperar_ultima_resolucion",
    },
    "tercero_extrano": {"via": "indirecto", "inmediatez": "inmediato"},
    "sentencia_definitiva": {"via": "directo", "inmediatez": "inmediato"},
    # Compat legacy (modelos viejos que aún predigan binario)
    "adjetivo": {"via": "indirecto", "inmediatez": "inmediato"},
    "sustantivo": {"via": "directo", "inmediatez": "diferido"},
}

ALERTA_PREMATURIDAD = (
    "Art. 107.IV LA — acto intermedio de ejecución de sentencia o remate. "
    "NO procede amparo todavía. Espera la última resolución del procedimiento; "
    "las violaciones cometidas durante éste se acumularán a la demanda contra "
    "esa última resolución."
)


@dataclass
class PredictionResult:
    categoria: str
    via: str
    inmediatez: str
    alerta: str | None
    prob_por_clase: dict[str, float]  # incluye SOLO las clases del modelo activo
    top_features: list[dict[str, Any]]
    top_analogas: list[dict[str, Any]]


def predict(model: LoadedModel, acto_reclamado: str) -> PredictionResult:
    texto = normalize_text(acto_reclamado)
    pipeline = model.artifact["pipeline"]

    proba = pipeline.predict_proba([texto])[0]
    classes = list(pipeline.classes_)
    prob_por_clase = {c: float(p) for c, p in zip(classes, proba)}
    # argmax
    categoria = max(prob_por_clase, key=prob_por_clase.get)  # type: ignore[arg-type]

    derivado = VIA_INMEDIATEZ.get(categoria, {"via": "ninguna", "inmediatez": "inmediato"})
    alerta = ALERTA_PREMATURIDAD if categoria == "post_juicio_prematuro" else None

    return PredictionResult(
        categoria=categoria,
        via=derivado["via"],
        inmediatez=derivado["inmediatez"],
        alerta=alerta,
        prob_por_clase=prob_por_clase,
        top_features=top_features(pipeline, texto, categoria, k=5),
        top_analogas=top_analogas(
            pipeline,
            texto,
            corpus_X=model.artifact["corpus_X"],
            corpus_meta=model.artifact["corpus_meta"],
            k=3,
        ),
    )
