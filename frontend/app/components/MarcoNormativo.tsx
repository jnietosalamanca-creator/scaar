"use client";

import { useState } from "react";
import { marcoPara } from "../data/marco_normativo";
import type { PrediccionCategoria } from "../lib/types";

/**
 * Render de la(s) fracción(es) del 107 LA aplicables a una categoría.
 * Variante "compacto" muestra solo títulos y permite expandir; "completo"
 * muestra el texto inline.
 */
export function MarcoNormativo({
  categoria,
  variant = "compacto",
}: {
  categoria: PrediccionCategoria | null | undefined;
  variant?: "compacto" | "completo";
}) {
  const fracciones = marcoPara(categoria);
  const [expandido, setExpandido] = useState<Record<string, boolean>>({});

  if (fracciones.length === 0) return null;

  return (
    <section
      className="rounded-lg border-2 border-violet-200 bg-violet-50/40 p-5 shadow-sm"
      aria-label="Marco normativo aplicable"
    >
      <header className="flex items-baseline justify-between">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-violet-900">
          📖 Marco normativo aplicable
        </h3>
        <span className="text-[10px] text-violet-800">
          Ley de Amparo (DOF 13-03-2025)
        </span>
      </header>

      <ul className="mt-3 space-y-3">
        {fracciones.map((f, i) => {
          const key = `${f.cita}-${i}`;
          const open = variant === "completo" || expandido[key];
          return (
            <li
              key={key}
              className="rounded border border-violet-200 bg-white p-3 text-sm"
            >
              <div className="flex flex-wrap items-baseline gap-2">
                <code className="font-mono text-xs font-semibold text-violet-900">
                  {f.cita}
                </code>
                <span className="text-xs text-slate-700">{f.titulo}</span>
              </div>
              {open ? (
                <p className="mt-2 whitespace-pre-wrap text-[13px] leading-relaxed text-slate-800">
                  {f.texto}
                </p>
              ) : (
                <button
                  type="button"
                  onClick={() => setExpandido((e) => ({ ...e, [key]: true }))}
                  className="mt-1 text-xs font-medium text-violet-800 underline hover:text-violet-900"
                >
                  Ver texto literal
                </button>
              )}
              {f.notas && open && (
                <div className="mt-2 rounded bg-violet-50 px-2 py-1 text-[11px] text-violet-900">
                  <strong>Nota:</strong> {f.notas}
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
