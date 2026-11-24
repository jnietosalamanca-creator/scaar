"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { labelTesis, listAuditoriaDiscrepancias } from "../../lib/api";
import { labelBadgeClass, labelMeta } from "../../lib/labels";
import { useRequireAuth } from "../../lib/useRequireAuth";
import type { EtiquetaTesis, TesisAuditoriaItem } from "../../lib/types";

/**
 * Auditoría asistida: tesis YA etiquetadas donde el modelo activo discrepa
 * con la decisión humana. Útil para detectar etiquetas mal puestas y
 * casos donde el modelo aprendió mejor que el etiquetador.
 *
 * Action: click en "Aceptar criterio del modelo" sobreescribe la etiqueta
 * humana con la predicción del modelo. Click "Mantener mi criterio" la deja
 * tal cual.
 */
export default function AuditoriaPage() {
  const { ready } = useRequireAuth();
  const [items, setItems] = useState<TesisAuditoriaItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  useEffect(() => {
    if (!ready) return;
    let alive = true;
    setLoading(true);
    setError(null);
    listAuditoriaDiscrepancias(50, true)
      .then((d) => alive && setItems(d))
      .catch((e: Error) => alive && setError(e.message))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [ready]);

  async function aceptarCriterioModelo(it: TesisAuditoriaItem) {
    setBusyId(it.id);
    try {
      await labelTesis(it.id, it.categoria_modelo as EtiquetaTesis);
      setItems((xs) => xs.filter((x) => x.id !== it.id));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusyId(null);
    }
  }

  function mantenerHumana(it: TesisAuditoriaItem) {
    // Lo único es sacarlo del listado local — la BD ya tiene la etiqueta
    // humana, no hay que tocar nada.
    setItems((xs) => xs.filter((x) => x.id !== it.id));
  }

  if (!ready) return null;

  return (
    <div className="space-y-6">
      <header>
        <Link href="/corpus" className="text-xs text-slate-500 hover:text-slate-900">
          ← Corpus
        </Link>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight">
          Auditoría asistida de etiquetas
        </h1>
        <p className="mt-1 text-sm text-slate-600">
          Tesis ya etiquetadas donde el modelo activo predice una categoría
          distinta a la que pusiste. <strong>No significa que estés mal</strong>;
          es solo una segunda opinión automática. Ordenadas por confianza del
          modelo (mayor confianza = discrepancia más sospechosa).
        </p>
      </header>

      {error && (
        <div className="rounded-md border border-rose-300 bg-rose-50 px-3 py-2 text-sm text-rose-800">
          {error}
        </div>
      )}

      {loading ? (
        <p className="text-sm text-slate-500">
          Cargando… (esto carga el modelo y clasifica todas las etiquetadas, puede tardar ~5s)
        </p>
      ) : items.length === 0 ? (
        <div className="rounded-lg border-2 border-emerald-300 bg-emerald-50 p-8 text-center">
          <p className="text-lg font-semibold text-emerald-900">
            ✓ Sin discrepancias.
          </p>
          <p className="mt-1 text-sm text-emerald-800">
            El modelo activo está de acuerdo con todas tus etiquetas (o ya
            revisaste todas). Buen reentreno candidato.
          </p>
        </div>
      ) : (
        <>
          <p className="text-xs text-slate-500">
            Mostrando {items.length} casos a revisar.
          </p>
          <ul className="space-y-3">
            {items.map((it) => (
              <DiscrepanciaCard
                key={it.id}
                it={it}
                busy={busyId === it.id}
                onAceptarModelo={() => aceptarCriterioModelo(it)}
                onMantener={() => mantenerHumana(it)}
              />
            ))}
          </ul>
        </>
      )}
    </div>
  );
}

function DiscrepanciaCard({
  it,
  busy,
  onAceptarModelo,
  onMantener,
}: {
  it: TesisAuditoriaItem;
  busy: boolean;
  onAceptarModelo: () => void;
  onMantener: () => void;
}) {
  const mh = labelMeta(it.etiqueta_humana);
  const mm = labelMeta(it.categoria_modelo as EtiquetaTesis);
  const confianzaPct = Math.round(it.prob_categoria_modelo * 100);
  return (
    <li className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex flex-wrap items-center gap-2 text-xs text-slate-600">
        <code className="font-mono">{it.registro_sjf}</code>
        <span className="rounded bg-slate-100 px-2 py-0.5">{it.fuente}</span>
      </div>
      <p className="mt-2 font-medium text-slate-900">{it.rubro}</p>

      <div className="mt-3 grid grid-cols-2 gap-3 text-xs">
        <div className="rounded-md border border-slate-200 p-2">
          <div className="text-[10px] uppercase tracking-wider text-slate-500">
            Tu etiqueta
          </div>
          <span
            className={`mt-1 inline-block rounded px-2 py-0.5 font-medium ${labelBadgeClass(mh.color)}`}
          >
            {mh.display}
          </span>
          <div className="mt-1 text-[10px] text-slate-500">
            Modelo le da {(it.prob_de_etiqueta_humana * 100).toFixed(0)}% de probabilidad
          </div>
        </div>
        <div className="rounded-md border-2 border-amber-300 bg-amber-50 p-2">
          <div className="text-[10px] uppercase tracking-wider text-amber-800">
            Modelo sugiere
          </div>
          <span
            className={`mt-1 inline-block rounded px-2 py-0.5 font-medium ${labelBadgeClass(mm.color)}`}
          >
            {mm.display}
          </span>
          <div className="mt-1 text-[10px] text-amber-800">
            Confianza: {confianzaPct}%
          </div>
        </div>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <Link
          href={`/corpus/${it.id}`}
          className="rounded-md border border-slate-300 bg-white px-3 py-1 text-xs hover:bg-slate-50"
        >
          Ver tesis completa →
        </Link>
        <button
          type="button"
          disabled={busy}
          onClick={onAceptarModelo}
          className="rounded-md bg-amber-600 px-3 py-1 text-xs font-medium text-white hover:bg-amber-700 disabled:opacity-50"
        >
          Aceptar sugerencia ({mm.short})
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={onMantener}
          className="rounded-md border border-slate-300 bg-white px-3 py-1 text-xs text-slate-700 hover:bg-slate-50 disabled:opacity-50"
        >
          Mantener mi etiqueta
        </button>
      </div>
    </li>
  );
}
