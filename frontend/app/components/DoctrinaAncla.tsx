"use client";

import { useEffect, useState } from "react";
import { listDoctrinasCanonicas } from "../lib/api";
import type { TesisDetail } from "../lib/types";

/**
 * Muestra la(s) tesis marcada(s) como doctrina canónica — el criterio jurídico
 * vigente que ancla las etiquetas adj/sus. Visible en pantallas clave.
 *
 * Variante "compacto": solo rubro + metadata, expandible.
 * Variante "completo" (default): rubro + texto completo desde el inicio.
 *
 * Si la API falla o no hay doctrinas, no renderiza nada — no obstruye flow.
 */
export function DoctrinaAncla({
  variant = "completo",
  titulo = "Doctrina aplicable",
}: {
  variant?: "compacto" | "completo";
  titulo?: string;
}) {
  const [doctrinas, setDoctrinas] = useState<TesisDetail[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  useEffect(() => {
    let alive = true;
    listDoctrinasCanonicas()
      .then((d) => alive && setDoctrinas(d))
      .catch(() => {
        // Silencioso — no obstruir si falla
      })
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, []);

  if (loading || doctrinas.length === 0) return null;

  return (
    <section
      className="rounded-lg border-2 border-amber-300 bg-amber-50/40 p-5 shadow-sm"
      aria-label="Doctrina jurídica aplicable"
    >
      <div className="flex items-baseline justify-between">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-amber-900">
          ⚖ {titulo}
        </h3>
        <span className="text-[10px] text-amber-800">
          {doctrinas.length === 1 ? "1 criterio vigente" : `${doctrinas.length} criterios`}
        </span>
      </div>

      <ul className="mt-3 space-y-3">
        {doctrinas.map((d) => {
          const isExpanded = expanded[d.id] ?? variant === "completo";
          return (
            <li
              key={d.id}
              className="rounded border border-amber-200 bg-white p-3 text-sm"
            >
              <div className="flex flex-wrap items-center gap-2 text-[10px] text-slate-600">
                <code className="font-mono">SJF {d.registro_sjf}</code>
                <span>·</span>
                <span>{d.instancia}</span>
                <span>·</span>
                <span>{d.epoca}</span>
                <span>·</span>
                <span className="rounded border border-slate-200 bg-slate-50 px-1.5 py-0.5">
                  {d.tipo}
                </span>
                {d.fecha_publ && (
                  <>
                    <span>·</span>
                    <span>{d.fecha_publ}</span>
                  </>
                )}
              </div>
              <p className="mt-2 text-sm font-medium leading-snug text-slate-900">
                {d.rubro}
              </p>
              {isExpanded ? (
                <p className="mt-3 whitespace-pre-wrap text-[13px] leading-relaxed text-slate-700">
                  {d.texto}
                </p>
              ) : (
                <button
                  type="button"
                  onClick={() => setExpanded((e) => ({ ...e, [d.id]: true }))}
                  className="mt-2 text-xs font-medium text-amber-800 underline hover:text-amber-900"
                >
                  Ver criterio completo
                </button>
              )}
              {isExpanded && variant === "compacto" && (
                <button
                  type="button"
                  onClick={() => setExpanded((e) => ({ ...e, [d.id]: false }))}
                  className="mt-2 text-xs text-amber-800 underline"
                >
                  Ocultar
                </button>
              )}
            </li>
          );
        })}
      </ul>

      <p className="mt-3 text-[11px] text-amber-800">
        Aplica este criterio al etiquetar/clasificar. Una violación procesal pura
        (aunque sea de grado predominante o superior) <strong>NO</strong> es
        imposible reparación bajo la Ley de Amparo de 2013 — solo lo es cuando
        afecta materialmente derechos sustantivos del gobernado (embargo, multa,
        alimentos, arresto, etc.).
      </p>
    </section>
  );
}
