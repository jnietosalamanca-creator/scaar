"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getDuplicados } from "../lib/api";
import { labelMeta } from "../lib/labels";
import type { DuplicadosResponse } from "../lib/types";

/**
 * Detecta si el `texto` ya fue clasificado antes (mismo SHA-256 normalizado).
 * Se ejecuta con debounce de 600ms para no martillar el endpoint en cada
 * keystroke. Solo se activa con texto >= 30 caracteres.
 *
 * Si encuentra previas, muestra un banner ámbar con resumen + links.
 * Si no, no renderiza nada (no obstruye el flujo de captura).
 */
export function DetectorDuplicados({ texto }: { texto: string }) {
  const [data, setData] = useState<DuplicadosResponse | null>(null);

  useEffect(() => {
    const t = texto.trim();
    if (t.length < 30) {
      setData(null);
      return;
    }
    const handle = setTimeout(() => {
      getDuplicados(t)
        .then((r) => setData(r))
        .catch(() => {
          // Falla silenciosa — no obstruir captura por bug del detector
          setData(null);
        });
    }, 600);
    return () => clearTimeout(handle);
  }, [texto]);

  if (!data || data.n_previas === 0) return null;

  // Resumen de veredictos vigentes en las previas
  const conVeredicto = data.previas.filter((p) => p.veredicto_vigente !== null);
  const sinVeredicto = data.previas.length - conVeredicto.length;
  const categoriasFinales = new Set(
    conVeredicto
      .map((p) => p.clasificacion_final)
      .filter((c): c is NonNullable<typeof c> => c !== null)
  );

  return (
    <div className="rounded-md border-2 border-amber-300 bg-amber-50 p-4 text-sm text-amber-900">
      <p className="font-semibold">
        ⚠ Este acto ya fue clasificado {data.n_previas} {data.n_previas === 1 ? "vez" : "veces"} antes.
      </p>
      <p className="mt-1 text-xs">
        El SHA-256 del texto normalizado coincide con clasificaciones previas
        en la base de datos. Antes de volver a clasificar, considera revisar
        el historial para mantener coherencia entre expedientes.
      </p>

      {categoriasFinales.size > 0 && (
        <p className="mt-2 text-xs">
          Veredictos vigentes encontrados:{" "}
          {[...categoriasFinales].map((cat, i) => {
            const m = labelMeta(cat);
            return (
              <span key={cat}>
                {i > 0 && ", "}
                <strong>{m.short}</strong>
              </span>
            );
          })}
          {sinVeredicto > 0 && (
            <span className="text-amber-700">
              {" "}· {sinVeredicto} sin firmar
            </span>
          )}
        </p>
      )}

      <details className="mt-2">
        <summary className="cursor-pointer text-xs font-medium">
          Ver las {data.n_previas} clasificaciones previas
        </summary>
        <ul className="mt-2 space-y-1 text-xs">
          {data.previas.map((p) => {
            const meta = labelMeta(p.categoria_predicha);
            const finalMeta = p.clasificacion_final
              ? labelMeta(p.clasificacion_final)
              : null;
            return (
              <li key={p.classification_id} className="border-l-2 border-amber-300 pl-2">
                <Link
                  href={`/clasificaciones/${p.classification_id}`}
                  className="font-mono text-[10px] underline hover:text-amber-700"
                >
                  {p.classification_id.slice(0, 8)}
                </Link>
                {" — "}
                <span>modelo: {meta.short}</span>
                {finalMeta && (
                  <>
                    {" → vigente: "}
                    <strong>{finalMeta.short}</strong>
                  </>
                )}
                {p.case_identificador && (
                  <>
                    {" · caso "}
                    <Link
                      href={`/casos/${p.case_id}`}
                      className="font-mono underline hover:text-amber-700"
                    >
                      {p.case_identificador}
                    </Link>
                  </>
                )}
                <span className="text-amber-700">
                  {" · "}
                  {new Date(p.created_at).toLocaleDateString("es-MX")}
                </span>
              </li>
            );
          })}
        </ul>
      </details>

      <p className="mt-2 text-[10px] text-amber-700">
        SHA: <code className="font-mono">{data.acto_sha256.slice(0, 32)}…</code>
      </p>
    </div>
  );
}
