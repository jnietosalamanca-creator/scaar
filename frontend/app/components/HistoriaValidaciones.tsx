import { labelMeta } from "../lib/labels";
import type { ValidationDetail } from "../lib/types";

export function HistoriaValidaciones({
  historia,
}: {
  historia: ValidationDetail[];
}) {
  if (historia.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-slate-300 bg-white p-5 text-center text-sm text-slate-500">
        Sin veredictos aún. Firme uno con el bloque de la derecha.
      </div>
    );
  }
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-700">
        Historia de validaciones
      </h3>
      <ol className="mt-3 space-y-3">
        {historia.map((v) => (
          <li
            key={v.id}
            className={`rounded-md border p-3 text-sm ${
              v.es_vigente
                ? "border-slate-900 bg-slate-50"
                : "border-slate-200 bg-white opacity-70"
            }`}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span
                  className={`rounded px-2 py-0.5 text-xs font-medium uppercase ${
                    v.veredicto === "acepta"
                      ? "bg-indigo-100 text-indigo-700"
                      : "bg-rose-100 text-rose-700"
                  }`}
                >
                  {v.veredicto}
                </span>
                {v.clasificacion_corregida && (
                  <span className="text-xs text-slate-600">
                    → corrige a{" "}
                    <strong title={labelMeta(v.clasificacion_corregida).via}>
                      {labelMeta(v.clasificacion_corregida).display}
                    </strong>
                  </span>
                )}
                {v.es_vigente && (
                  <span className="rounded bg-slate-900 px-2 py-0.5 text-[10px] uppercase text-white">
                    vigente
                  </span>
                )}
              </div>
              <div
                className={`text-xs ${
                  v.firma_valida ? "text-emerald-700" : "text-rose-700"
                }`}
                title={v.firma_sha256}
              >
                {v.firma_valida ? "✓ firma válida" : "✗ firma inválida"}
              </div>
            </div>
            {v.comentario && (
              <p className="mt-2 whitespace-pre-wrap text-xs text-slate-700">
                {v.comentario}
              </p>
            )}
            <div className="mt-2 text-[10px] text-slate-500">
              {new Date(v.validated_at).toLocaleString("es-MX")} ·{" "}
              {v.validated_by_email}
            </div>
            <div className="mt-1 break-all font-mono text-[10px] text-slate-400">
              firma {v.firma_sha256.slice(0, 32)}…
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}
