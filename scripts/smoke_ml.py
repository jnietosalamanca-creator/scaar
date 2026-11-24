"""Smoke test del pipeline ML sin tocar DB.

Carga el corpus JSONL, entrena, predice un acto de prueba y muestra el log
completo (predicción, prob, top-features, top-análogas). Útil para verificar
el pipeline antes de levantar Postgres.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.ml.explain import top_analogas, top_features  # noqa: E402
from app.ml.pipeline import build_pipeline  # noqa: E402
from app.ml.preprocessing import acto_sha256, normalize_text  # noqa: E402


def main() -> None:
    corpus_path = ROOT / "backend" / "corpus" / "tesis_dummy.jsonl"
    rows = [json.loads(l) for l in corpus_path.read_text().splitlines() if l.strip()]
    textos = [normalize_text(r["texto"]) for r in rows]
    etiquetas = [r["etiqueta"] for r in rows]
    meta = [
        {
            "tesis_id": str(i),
            "registro_sjf": r["registro_sjf"],
            "rubro": r["rubro"],
            "etiqueta": r["etiqueta"],
        }
        for i, r in enumerate(rows)
    ]
    print(f"corpus: {len(rows)} tesis ({etiquetas.count('adjetivo')} adj / {etiquetas.count('sustantivo')} sus)")

    pipeline = build_pipeline()
    pipeline.fit(textos, etiquetas)

    tfidf = pipeline.named_steps["tfidf"]
    corpus_X = tfidf.transform(textos)

    casos = [
        ("ADJ esperado", "El juez del juicio natural negó la admisión de la prueba pericial ofrecida en tiempo y forma, lo que afecta las defensas del quejoso y trasciende al resultado del fallo."),
        ("SUS esperado", "La sentencia definitiva que condena al pago resuelve el fondo del asunto y debe impugnarse vía amparo directo, donde se hacen valer las violaciones procesales de manera diferida."),
        ("Ambiguo", "La resolución del juez admite la demanda en sus términos."),
    ]
    classes = list(pipeline.classes_)
    idx_adj = classes.index("adjetivo")
    for label, texto in casos:
        t = normalize_text(texto)
        proba = pipeline.predict_proba([t])[0]
        p_adj = float(proba[idx_adj])
        pred = "adjetivo" if p_adj >= 0.5 else "sustantivo"
        print(f"\n[{label}]")
        print(f"  acto_sha256: {acto_sha256(texto)[:16]}...")
        print(f"  predicción : {pred}  P(adjetivo)={p_adj:.3f}")
        feats = top_features(pipeline, t, k=5)
        print("  top features:")
        for f in feats:
            print(f"    {f['token']:<35} contrib={f['contribucion_adjetivo']:+.3f}  tfidf={f['tfidf']:.3f}")
        ana = top_analogas(pipeline, t, corpus_X, meta, k=3)
        print("  top análogas:")
        for a in ana:
            print(f"    sim={a['similitud']:.3f}  [{a['etiqueta']}]  {a['registro_sjf']}  {a['rubro'][:60]}")


if __name__ == "__main__":
    main()
