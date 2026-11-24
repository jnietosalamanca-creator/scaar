"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getCorpusStats } from "../lib/api";
import type { CorpusStats } from "../lib/types";

/**
 * Aviso visible mientras el modelo activo todavía es binario
 * (Imposible reparación / Diferida) y la taxonomía nueva de 8 categorías
 * existe en BD pero no se ha entrenado aún.
 *
 * Se oculta solo cuando el modelo activo ya conozca las 8 categorías
 * (señalable en el futuro vía model_versions.algoritmo o un flag).
 *
 * Por ahora se muestra siempre que `listas_para_train_limpio < threshold`.
 */
export function BannerModeloBinario() {
  const [stats, setStats] = useState<CorpusStats | null>(null);
  useEffect(() => {
    let alive = true;
    getCorpusStats()
      .then((s) => alive && setStats(s))
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, []);

  if (!stats) return null;

  const ready = stats.listas_para_train_limpio >= stats.threshold_train_limpio;
  const faltan = Math.max(0, stats.threshold_train_limpio - stats.listas_para_train_limpio);

  return (
    <div className="rounded-md border border-amber-300 bg-amber-50 px-4 py-2 text-xs text-amber-900">
      <strong>Modelo activo: clasificador binario (transición).</strong> Las
      predicciones son “Imposible reparación / Diferida” — un subconjunto de la
      taxonomía nueva de 8 categorías que ya existe en el corpus.
      {ready ? (
        <>
          {" "}
          Hay <strong>{stats.listas_para_train_limpio}</strong> tesis curadas
          listas: ya puedes reentrenar para tener clasificación multiclase
          (corre <code className="font-mono">python -m app.ml.train</code>).
        </>
      ) : (
        <>
          {" "}
          Faltan <strong>{faltan}</strong> tesis etiquetadas con la taxonomía
          nueva para reentrenar (de fuentes confiables, no obsoletas).{" "}
          <Link href="/corpus/etiquetar" className="underline">
            Etiquetar →
          </Link>
        </>
      )}
    </div>
  );
}
