"""Entrenamiento del modelo SCAAR — multiclase.

Entrena con las categorías de la taxonomía nueva (8 clases + 'no_aplica' que
se excluye). Detecta automáticamente las clases viables (≥ MIN_PER_CLASS
ejemplos); las que no llegan se EXCLUYEN del modelo activo, no se predicen,
pero siguen existiendo en BD para etiquetado y crecimiento futuro.

Uso:
    python -m app.ml.train --version v0.3.0 --user-email system@scaar.local
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

import joblib
import numpy as np
from sklearn.metrics import classification_report, f1_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sqlalchemy import select, update

from app.core.config import settings
from app.db.models import ModelVersion, Tesis, User
from app.db.session import SessionLocal
from app.ml.pipeline import build_pipeline
from app.ml.preprocessing import normalize_text

# Categorías que NUNCA entran al training (no son veredictos de procedencia)
NEVER_TRAIN = {"no_aplica"}

# Mínimo de ejemplos para que una clase entre al training
MIN_PER_CLASS = 3


def _load_corpus(db) -> tuple[list[str], list[str], list[dict]]:
    """Tesis con etiqueta de procedencia, no doctrina canónica, fuente confiable,
    rol jurisprudencial = `regla`.

    Las excepciones / aisladas dudosas / derogadas NO entran al training
    para evitar que el modelo aprenda señal contradictoria con el mismo
    vocabulario.
    """
    excluded = settings.excluded_fuentes_list
    stmt = select(Tesis).where(
        Tesis.etiqueta.is_not(None),
        Tesis.etiqueta.not_in(NEVER_TRAIN),
        Tesis.es_doctrina_canonica.is_(False),
        Tesis.tipo_jurisprudencial == "regla",
    )
    if excluded:
        stmt = stmt.where(Tesis.fuente.not_in(excluded))
    rows = db.execute(stmt).scalars().all()
    print(f"[train] fuentes excluidas: {excluded}", file=sys.stderr)
    print("[train] filtro tipo_jurisprudencial='regla' aplicado", file=sys.stderr)
    if not rows:
        raise SystemExit(
            "No hay tesis etiquetadas elegibles para entrenar. "
            f"(fuentes excluidas: {excluded}, NEVER_TRAIN: {NEVER_TRAIN})"
        )
    textos = [normalize_text(r.texto) for r in rows]
    etiquetas = [r.etiqueta for r in rows]
    meta = [
        {
            "tesis_id": str(r.id),
            "registro_sjf": r.registro_sjf,
            "rubro": r.rubro,
            "etiqueta": r.etiqueta,
        }
        for r in rows
    ]
    return textos, etiquetas, meta


def _filter_viable(
    textos: list[str], etiquetas: list[str], meta: list[dict]
) -> tuple[list[str], list[str], list[dict], list[str], dict[str, int]]:
    """Conserva solo ejemplos de clases con al menos MIN_PER_CLASS ejemplos.

    Devuelve (textos_v, etiquetas_v, meta_v, clases_viables, conteo_full).
    """
    counts = dict(Counter(etiquetas))
    viables = sorted(c for c, n in counts.items() if n >= MIN_PER_CLASS)
    if not viables:
        raise SystemExit(
            f"Ninguna clase llega a {MIN_PER_CLASS} ejemplos. Conteo: {counts}"
        )
    keep = set(viables)
    paired = [(t, e, m) for t, e, m in zip(textos, etiquetas, meta) if e in keep]
    textos_v = [p[0] for p in paired]
    etiquetas_v = [p[1] for p in paired]
    meta_v = [p[2] for p in paired]
    return textos_v, etiquetas_v, meta_v, viables, counts


def _evaluate(
    pipeline, textos: list[str], etiquetas: list[str], clases: list[str]
) -> dict:
    """Cross-validation con n_splits ajustado a la clase minoritaria."""
    y = np.array(etiquetas)
    n_min = min((y == c).sum() for c in clases)
    n_splits = int(min(5, n_min))
    if n_splits < 2:
        return {
            "warning": f"clase minoritaria con {n_min} ejemplos; no se hizo CV",
            "n_train": len(textos),
        }
    cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
    y_pred = cross_val_predict(pipeline, textos, y, cv=cv)
    report = classification_report(
        y, y_pred, labels=clases, output_dict=True, zero_division=0
    )
    metrics: dict = {
        "cv_n_splits": n_splits,
        "f1_macro": float(f1_score(y, y_pred, average="macro", labels=clases)),
        "f1_micro": float(f1_score(y, y_pred, average="micro", labels=clases)),
    }
    for c in clases:
        cdata = report.get(c, {})
        metrics[f"f1_{c}"] = float(cdata.get("f1-score", 0.0))
        metrics[f"support_{c}"] = int(cdata.get("support", 0))
    return metrics


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def train(version: str, user_email: str, activate: bool = True) -> None:
    artifacts_dir = Path(settings.ml_artifacts_dir)
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = artifacts_dir / f"{version}.joblib"
    if artifact_path.exists():
        raise SystemExit(f"Artefacto ya existe: {artifact_path}. Usa otra versión.")

    with SessionLocal() as db:
        user = db.execute(select(User).where(User.email == user_email)).scalar_one_or_none()
        if user is None:
            raise SystemExit(
                f"Usuario {user_email} no existe. Corre: python -m app.scripts.seed_users"
            )

        textos_full, etiquetas_full, meta_full = _load_corpus(db)
        textos, etiquetas, meta, clases, conteo_full = _filter_viable(
            textos_full, etiquetas_full, meta_full
        )
        excluded_classes = {
            c: n for c, n in conteo_full.items() if n < MIN_PER_CLASS
        }
        print(
            f"[train] corpus total: {len(textos_full)} | "
            f"viables ({len(textos)}) en {len(clases)} clases: {clases}",
            file=sys.stderr,
        )
        if excluded_classes:
            print(
                f"[train] CLASES EXCLUIDAS por <{MIN_PER_CLASS} ejemplos: "
                f"{excluded_classes}",
                file=sys.stderr,
            )

        pipeline = build_pipeline()
        metricas = _evaluate(pipeline, textos, etiquetas, clases)
        metricas["clases_viables"] = clases
        metricas["clases_excluidas_por_baja_muestra"] = excluded_classes
        metricas["min_per_class"] = MIN_PER_CLASS
        print(f"[train] eval: {json.dumps(metricas, indent=2, ensure_ascii=False)}")

        # Fit final sobre todo el corpus viable
        pipeline.fit(textos, etiquetas)

        tfidf = pipeline.named_steps["tfidf"]
        corpus_X = tfidf.transform(textos)

        artifact = {
            "version": version,
            "pipeline": pipeline,
            "corpus_X": corpus_X,
            "corpus_meta": meta,
            "labels": clases,  # ahora multiclase: las viables
            "trained_at": dt.datetime.now(dt.UTC).isoformat(),
        }
        joblib.dump(artifact, artifact_path, compress=3)
        artifact_sha = _file_sha256(artifact_path)
        print(f"[train] artefacto: {artifact_path} ({artifact_sha[:12]}...)")

        if activate:
            db.execute(update(ModelVersion).values(activo=False).where(ModelVersion.activo))
        mv = ModelVersion(
            version=version,
            algoritmo=f"tfidf+linearsvc-multiclass-calibrated[{len(clases)}c]",
            fecha_corte=dt.date.today(),
            n_tesis_train=len(textos),
            metricas=metricas,
            artifact_path=str(artifact_path),
            artifact_sha256=artifact_sha,
            activo=activate,
            created_by=user.id,
        )
        db.add(mv)
        db.commit()
        print(f"[train] model_version registrada: id={mv.id} activo={activate}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True, help="ej. v0.3.0")
    ap.add_argument("--user-email", default="system@scaar.local")
    ap.add_argument("--no-activate", action="store_true")
    args = ap.parse_args()
    train(version=args.version, user_email=args.user_email, activate=not args.no_activate)


if __name__ == "__main__":
    main()
