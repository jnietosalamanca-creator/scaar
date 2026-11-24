import { labelMeta } from "../lib/labels";
import type { TopAnaloga, TopFeature } from "../lib/types";

export function ReasoningLog({
  features,
  analogas,
  acto_sha256,
}: {
  features: TopFeature[];
  analogas: TopAnaloga[];
  acto_sha256: string;
}) {
  return (
    <div className="grid gap-4 md:grid-cols-2">
      <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-700">
          Top features (TF-IDF × coeficiente)
        </h3>
        <p className="mt-1 text-xs text-slate-500">
          Tokens que más empujaron hacia la categoría predicha. Positivo = a
          favor; negativo = en contra.
        </p>
        <ul className="mt-3 space-y-2">
          {features.map((f) => {
            const sign = f.contribucion >= 0;
            const mag = Math.abs(f.contribucion);
            const pct = Math.min(100, mag * 1500); // visual scale only
            return (
              <li key={f.token} className="text-sm">
                <div className="flex items-center justify-between">
                  <code className="font-mono text-xs text-slate-700">
                    {f.token}
                  </code>
                  <span
                    className={`font-mono text-xs ${
                      sign ? "text-indigo-700" : "text-rose-700"
                    }`}
                  >
                    {sign ? "+" : "−"}
                    {mag.toFixed(4)}
                  </span>
                </div>
                <div className="mt-1 h-1.5 w-full overflow-hidden rounded bg-slate-100">
                  <div
                    className={`h-full ${
                      sign ? "bg-indigo-400" : "bg-rose-400"
                    }`}
                    style={{ width: `${pct}%` }}
                  />
                </div>
              </li>
            );
          })}
        </ul>
      </div>

      <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-700">
          Tesis análogas (similitud coseno)
        </h3>
        <p className="mt-1 text-xs text-slate-500">
          Las 3 tesis del corpus más similares al acto reclamado.
        </p>
        <ul className="mt-3 space-y-3">
          {analogas.map((a) => (
            <li
              key={a.tesis_id}
              className="rounded border border-slate-100 bg-slate-50/50 p-3"
            >
              <div className="flex items-center justify-between text-xs">
                <span className="font-mono text-slate-600">
                  SJF {a.registro_sjf}
                </span>
                {(() => {
                  const m = labelMeta(a.etiqueta as never);
                  return (
                    <span
                      className={`rounded px-2 py-0.5 font-medium ${
                        m.color === "indigo"
                          ? "bg-indigo-100 text-indigo-700"
                          : m.color === "emerald"
                          ? "bg-emerald-100 text-emerald-700"
                          : m.color === "amber"
                          ? "bg-amber-100 text-amber-700"
                          : m.color === "rose"
                          ? "bg-rose-100 text-rose-700"
                          : m.color === "sky"
                          ? "bg-sky-100 text-sky-700"
                          : m.color === "violet"
                          ? "bg-violet-100 text-violet-700"
                          : "bg-slate-200 text-slate-700"
                      }`}
                      title={m.via === "ninguna" ? m.inmediatez : m.via}
                    >
                      {m.short}
                    </span>
                  );
                })()}
              </div>
              <p className="mt-1 text-xs text-slate-700">{a.rubro}</p>
              <div className="mt-2 flex items-center gap-2">
                <div className="h-1 flex-1 overflow-hidden rounded bg-slate-200">
                  <div
                    className="h-full bg-slate-700"
                    style={{ width: `${a.similitud * 100}%` }}
                  />
                </div>
                <span className="font-mono text-[10px] text-slate-500">
                  {(a.similitud * 100).toFixed(1)}%
                </span>
              </div>
            </li>
          ))}
        </ul>
        <div className="mt-4 border-t border-slate-100 pt-3 text-[10px] text-slate-400">
          <span className="font-semibold">SHA-256 del acto: </span>
          <code className="break-all font-mono">{acto_sha256}</code>
        </div>
      </div>
    </div>
  );
}
