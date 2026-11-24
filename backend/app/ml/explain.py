"""Explicación del modelo: top features y top análogas (multiclase).

Sin dependencias de DB — recibe el pipeline ya cargado y los artefactos del
corpus. Esto permite testearlo aisladamente y reusarlo desde cualquier punto.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity


def _coefs_para_clase(cal, clase: str) -> np.ndarray:
    """Coeficientes promedio (sobre los CV folds) del LinearSVC base para `clase`.

    Soporta dos casos:
      • Binario: cada `cal.calibrated_classifiers_[k].estimator` tiene coef_
        shape (1, n_features). El signo se ajusta según `cal.classes_`.
      • Multiclase (OvR): cada estimator tiene coef_ shape (n_classes, n_feats)
        — extraemos la fila correspondiente a `clase`.
    """
    classes = list(cal.classes_)
    idx = classes.index(clase)

    coefs_list = []
    for c in cal.calibrated_classifiers_:
        coef = c.estimator.coef_
        if coef.shape[0] == 1:
            # Binario: coef_[0] favorece classes[1]. Si la clase pedida es
            # classes[0], invertimos el signo.
            sign = 1.0 if classes[1] == clase else -1.0
            coefs_list.append(coef[0] * sign)
        else:
            coefs_list.append(coef[idx])
    return np.mean(coefs_list, axis=0)


def top_features(
    pipeline, texto_norm: str, clase: str, k: int = 5
) -> list[dict[str, Any]]:
    """k tokens que más empujaron hacia `clase` (contribución = coef × tfidf)."""
    tfidf = pipeline.named_steps["tfidf"]
    cal = pipeline.named_steps["clf"]
    feature_names = np.array(tfidf.get_feature_names_out())

    coefs = _coefs_para_clase(cal, clase)
    x = tfidf.transform([texto_norm])
    contrib = (x.multiply(coefs)).toarray()[0]
    nz_idx = np.flatnonzero(contrib)
    if nz_idx.size == 0:
        return []
    top = nz_idx[np.argsort(-np.abs(contrib[nz_idx]))[:k]]
    return [
        {
            "token": str(feature_names[i]),
            "contribucion": float(contrib[i]),
            "tfidf": float(x[0, i]),
        }
        for i in top
    ]


def top_analogas(
    pipeline, texto_norm: str, corpus_X, corpus_meta: list[dict], k: int = 3
) -> list[dict[str, Any]]:
    tfidf = pipeline.named_steps["tfidf"]
    x = tfidf.transform([texto_norm])
    sims = cosine_similarity(x, corpus_X)[0]
    idx = np.argsort(-sims)[:k]
    return [
        {
            "tesis_id": corpus_meta[i]["tesis_id"],
            "registro_sjf": corpus_meta[i]["registro_sjf"],
            "rubro": corpus_meta[i]["rubro"],
            "etiqueta": corpus_meta[i]["etiqueta"],
            "similitud": float(sims[i]),
        }
        for i in idx
    ]
