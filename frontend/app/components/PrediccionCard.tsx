import { labelBadgeClass, labelMeta } from "../lib/labels";
import type {
  InmediatezAmparo,
  PrediccionCategoria,
  ViaAmparo,
} from "../lib/types";

type Props = {
  categoria: PrediccionCategoria;
  via: ViaAmparo;
  inmediatez: InmediatezAmparo;
  alerta: string | null;
  prob_categoria: number;
  prob_por_clase: Record<string, number>;
  requiere_revision_humana: boolean;
  model_version: string;
};

const VIA_LABEL: Record<ViaAmparo, string> = {
  indirecto: "Amparo indirecto",
  directo: "Amparo directo",
  ninguna: "No procede aún",
};

const INMEDIATEZ_LABEL: Record<InmediatezAmparo, string> = {
  inmediato: "Inmediato",
  diferido: "Diferido",
  esperar_ultima_resolucion: "Esperar última resolución",
};

export function PrediccionCard({
  categoria,
  via,
  inmediatez,
  alerta,
  prob_categoria,
  prob_por_clase,
  requiere_revision_humana,
  model_version,
}: Props) {
  const meta = labelMeta(categoria);
  const pct = (prob_categoria * 100).toFixed(1);

  // Top 3 categorías por probabilidad para distribución
  const ranked = Object.entries(prob_por_clase)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5);

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="text-xs uppercase tracking-wider text-slate-500">
            Predicción del modelo
          </div>
          <div className={`mt-1 text-2xl font-semibold text-${meta.color}-700`}>
            <span className={meta.color === "rose" ? "text-rose-700" : ""}>
              {meta.display}
            </span>
          </div>
          <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-slate-600">
            <span className="font-medium">{VIA_LABEL[via]}</span>
            <span>·</span>
            <span>{INMEDIATEZ_LABEL[inmediatez]}</span>
            <span>·</span>
            <span className="font-mono text-slate-500">{categoria}</span>
          </div>
        </div>
        <div className="text-right">
          <div className="text-xs uppercase tracking-wider text-slate-500">
            Modelo
          </div>
          <div className="font-mono text-sm">{model_version}</div>
          <div className="mt-1 text-[10px] text-slate-500">
            confianza: <span className="font-mono">{pct}%</span>
          </div>
        </div>
      </div>

      {alerta && (
        <div className="mt-4 rounded-md border-2 border-rose-300 bg-rose-50 p-3 text-sm text-rose-900">
          <strong>⚠ Alerta procesal:</strong> {alerta}
        </div>
      )}

      {requiere_revision_humana && !alerta && (
        <div className="mt-4 rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900">
          <strong>Requiere revisión humana.</strong> El modelo no está
          suficientemente seguro (confianza {pct}% &lt;{" "}
          {Math.round(0.7 * 100)}%). Antes de presentar la demanda, valide
          manualmente con las tesis análogas y el criterio aplicable abajo.
        </div>
      )}

      <div className="mt-5">
        <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
          Distribución de probabilidades
        </div>
        <ul className="mt-2 space-y-1">
          {ranked.map(([cat, p]) => {
            const m = labelMeta(cat as PrediccionCategoria);
            const isTop = cat === categoria;
            const w = Math.max(2, Math.round(p * 100));
            return (
              <li key={cat} className="flex items-center gap-2 text-xs">
                <span
                  className={`min-w-[150px] rounded px-2 py-0.5 ${labelBadgeClass(
                    m.color
                  )} ${isTop ? "ring-2 ring-slate-700" : ""}`}
                  title={m.via === "ninguna" ? m.inmediatez : `${m.via} · ${m.inmediatez}`}
                >
                  {m.short}
                </span>
                <div className="relative h-2 flex-1 overflow-hidden rounded-full bg-slate-100">
                  <div
                    className={`h-full ${
                      isTop ? "bg-slate-700" : "bg-slate-300"
                    }`}
                    style={{ width: `${w}%` }}
                  />
                </div>
                <span className="w-12 text-right font-mono text-slate-600">
                  {(p * 100).toFixed(1)}%
                </span>
              </li>
            );
          })}
        </ul>
        {Object.keys(prob_por_clase).length > 5 && (
          <p className="mt-1 text-[10px] text-slate-400">
            Mostrando top 5 de {Object.keys(prob_por_clase).length} clases del
            modelo activo.
          </p>
        )}
      </div>
    </div>
  );
}
