"use client";

import { useEffect, useState, use } from "react";
import Link from "next/link";
import { getCaso, updateCaso } from "../../lib/api";
import { useRequireAuth } from "../../lib/useRequireAuth";
import { labelBadgeClass, labelMeta } from "../../lib/labels";
import type {
  ActoEnCaso,
  CasoDetail,
  DemandaSugerida,
  ViaAmparo,
} from "../../lib/types";

export default function CasoDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { ready } = useRequireAuth();
  const [data, setData] = useState<CasoDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    if (!ready) return;
    let alive = true;
    getCaso(id)
      .then((d) => alive && setData(d))
      .catch((e: Error) => alive && setError(e.message));
    return () => {
      alive = false;
    };
  }, [ready, id, tick]);

  async function toggleArchive() {
    if (!data) return;
    await updateCaso(data.id, { archived: !data.archived_at });
    setTick((t) => t + 1);
  }

  if (!ready) return null;
  if (error)
    return (
      <div className="rounded-md border border-rose-300 bg-rose-50 px-4 py-3 text-sm text-rose-800">
        {error}
      </div>
    );
  if (!data) return <p className="text-sm text-slate-500">Cargando…</p>;

  const archivado = data.archived_at !== null;

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <Link href="/casos" className="text-xs text-slate-500 hover:text-slate-900">
            ← Casos
          </Link>
          <div className="mt-1 flex items-center gap-3">
            <h1 className="font-mono text-2xl font-semibold tracking-tight">
              {data.identificador}
            </h1>
            {data.materia && (
              <span className="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-700">
                {data.materia}
              </span>
            )}
            {archivado && (
              <span className="rounded border border-slate-300 px-2 py-0.5 text-xs text-slate-500">
                archivado
              </span>
            )}
          </div>
          {data.descripcion && (
            <p className="mt-1 max-w-3xl text-sm text-slate-600">
              {data.descripcion}
            </p>
          )}
          <p className="mt-1 text-[11px] text-slate-400">
            Creado por {data.created_by_email} ·{" "}
            {new Date(data.created_at).toLocaleString("es-MX")}
          </p>
        </div>
        <div className="flex gap-2">
          <Link
            href={`/clasificar?case=${data.id}`}
            className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-slate-800"
          >
            + Agregar acto
          </Link>
          <button
            type="button"
            onClick={toggleArchive}
            className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm hover:bg-slate-50"
          >
            {archivado ? "Reabrir" : "Archivar"}
          </button>
        </div>
      </header>

      <ResumenJuridico resumen={data.resumen} actos={data.actos} />

      <ActosDelCaso actos={data.actos} />
    </div>
  );
}

function ResumenJuridico({
  resumen,
  actos,
}: {
  resumen: CasoDetail["resumen"];
  actos: ActoEnCaso[];
}) {
  if (resumen.n_actos === 0) {
    return (
      <div className="rounded-lg border border-dashed border-slate-300 bg-white p-8 text-center">
        <p className="text-sm font-medium text-slate-700">
          Este caso aún no tiene actos.
        </p>
        <p className="mt-1 text-sm text-slate-500">
          Agrega el primer acto reclamado para que el sistema sugiera qué
          demanda(s) presentar.
        </p>
      </div>
    );
  }

  const actoMap = new Map(actos.map((a) => [a.classification_id, a]));

  return (
    <section className="rounded-lg border-2 border-indigo-200 bg-indigo-50/30 p-5 shadow-sm">
      <header>
        <h2 className="text-sm font-semibold uppercase tracking-wider text-indigo-900">
          Plan jurídico del expediente
        </h2>
        <p className="mt-1 text-xs text-indigo-800">
          Computado por reglas a partir de la categoría vigente de cada acto.
          Si corriges un veredicto, este resumen se recalcula al recargar.
        </p>
      </header>

      <div className="mt-4 space-y-3">
        {resumen.demandas.map((d, i) => (
          <DemandaCard
            key={i}
            num={i + 1}
            demanda={d}
            actoMap={actoMap}
          />
        ))}
        {resumen.demandas.length === 0 && (
          <div className="rounded border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900">
            Ningún acto del caso justifica una demanda procedente todavía.
          </div>
        )}
        {resumen.actos_prematuros.length > 0 && (
          <div className="rounded-md border-2 border-rose-300 bg-rose-50 p-3">
            <p className="text-sm font-semibold text-rose-900">
              ⚠ {resumen.actos_prematuros.length} acto(s) prematuro(s) — NO
              presentar amparo todavía.
            </p>
            <p className="mt-1 text-xs text-rose-800">
              Las violaciones intermedias del procedimiento de ejecución se
              acumulan a la demanda contra la última resolución (art. 107.IV LA).
            </p>
            <ul className="mt-2 space-y-1">
              {resumen.actos_prematuros.map((aid) => {
                const a = actoMap.get(aid);
                return a ? (
                  <li key={aid} className="text-xs text-rose-900">
                    ·{" "}
                    <Link
                      href={`/clasificaciones/${aid}`}
                      className="underline"
                    >
                      {a.acto_preview.slice(0, 100)}…
                    </Link>
                  </li>
                ) : null;
              })}
            </ul>
          </div>
        )}
        {resumen.actos_no_aplica.length > 0 && (
          <div className="rounded-md border border-slate-200 bg-white px-3 py-2 text-xs text-slate-600">
            {resumen.actos_no_aplica.length} acto(s) marcados como “no aplica” o
            sin clasificación efectiva — quedan fuera del plan.
          </div>
        )}
      </div>
    </section>
  );
}

const VIA_BG: Record<ViaAmparo, string> = {
  indirecto: "bg-indigo-50 border-indigo-200",
  directo: "bg-emerald-50 border-emerald-200",
  ninguna: "bg-rose-50 border-rose-200",
};

function DemandaCard({
  num,
  demanda,
  actoMap,
}: {
  num: number;
  demanda: DemandaSugerida;
  actoMap: Map<string, ActoEnCaso>;
}) {
  return (
    <article
      className={`rounded-md border-2 p-4 ${VIA_BG[demanda.via]}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
            Demanda {num}
          </div>
          <h3 className="mt-1 text-base font-semibold text-slate-900">
            {demanda.titulo}
          </h3>
          <p className="mt-1 text-xs text-slate-700">{demanda.explicacion}</p>
        </div>
        <span className="rounded bg-white px-2 py-0.5 text-[10px] font-mono text-slate-600">
          {demanda.via} · {demanda.inmediatez}
        </span>
      </div>

      {demanda.alerta && (
        <div className="mt-3 rounded border border-amber-300 bg-amber-50 px-2 py-1 text-xs text-amber-900">
          {demanda.alerta}
        </div>
      )}

      <div className="mt-3 text-xs">
        <span className="font-semibold text-slate-700">
          {demanda.actos.length === 1 ? "Reclama:" : `Reclama ${demanda.actos.length} actos:`}
        </span>
        <ul className="mt-1 space-y-1">
          {demanda.actos.map((aid) => {
            const a = actoMap.get(aid);
            return a ? (
              <li key={aid}>
                ·{" "}
                <Link
                  href={`/clasificaciones/${aid}`}
                  className="underline hover:text-slate-900"
                >
                  {a.acto_preview.slice(0, 120)}…
                </Link>
              </li>
            ) : null;
          })}
        </ul>
      </div>

      {demanda.violaciones_acumulables.length > 0 && (
        <div className="mt-2 rounded bg-white/60 px-2 py-1 text-xs text-slate-700">
          <strong>Acumula {demanda.violaciones_acumulables.length}</strong>{" "}
          violación(es) procesal(es) diferida(s) o intermedia(s) del mismo
          expediente.
        </div>
      )}
    </article>
  );
}

function ActosDelCaso({ actos }: { actos: ActoEnCaso[] }) {
  if (actos.length === 0) return null;
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-700">
        Actos del expediente ({actos.length})
      </h2>
      <ul className="mt-3 space-y-2">
        {actos.map((a) => {
          const meta = labelMeta(a.categoria);
          const finalMeta = a.clasificacion_final
            ? labelMeta(a.clasificacion_final)
            : null;
          const display = finalMeta ?? meta;
          return (
            <li key={a.classification_id}>
              <Link
                href={`/clasificaciones/${a.classification_id}`}
                className="block rounded border border-slate-200 p-3 transition hover:border-slate-400"
              >
                <div className="flex flex-wrap items-center gap-2 text-xs">
                  <span
                    className={`rounded px-2 py-0.5 font-medium ${labelBadgeClass(
                      display.color
                    )}`}
                    title={display.via === "ninguna" ? display.inmediatez : display.via}
                  >
                    {display.short}
                  </span>
                  {a.veredicto_vigente === "rechaza" && (
                    <span className="rounded bg-rose-100 px-2 py-0.5 text-rose-700">
                      ✗ corregido (modelo dijo {meta.short})
                    </span>
                  )}
                  {a.veredicto_vigente === "acepta" && (
                    <span className="rounded bg-emerald-100 px-2 py-0.5 text-emerald-700">
                      ✓ aceptado
                    </span>
                  )}
                  {a.veredicto_vigente === null && (
                    <span className="rounded border border-amber-300 bg-amber-50 px-2 py-0.5 text-amber-800">
                      sin firmar
                    </span>
                  )}
                  {a.requiere_revision_humana && a.veredicto_vigente === null && (
                    <span className="rounded bg-amber-100 px-2 py-0.5 text-amber-800">
                      ⚠ revisar
                    </span>
                  )}
                </div>
                <p className="mt-2 line-clamp-2 text-sm text-slate-800">
                  {a.acto_preview}
                </p>
              </Link>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
