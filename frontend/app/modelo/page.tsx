"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  getModeloStats,
  listModelVersiones,
  reentrenarModelo,
} from "../lib/api";
import { TODAS_LAS_CATEGORIAS, labelBadgeClass, labelMeta } from "../lib/labels";
import { useRequireAuth } from "../lib/useRequireAuth";
import type {
  EtiquetaTesis,
  ModeloStats,
  ModelVersionListItem,
} from "../lib/types";

export default function ModeloPage() {
  const { ready } = useRequireAuth();
  const [stats, setStats] = useState<ModeloStats | null>(null);
  const [versiones, setVersiones] = useState<ModelVersionListItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!ready) return;
    let alive = true;
    Promise.all([getModeloStats(), listModelVersiones()])
      .then(([s, v]) => {
        if (!alive) return;
        setStats(s);
        setVersiones(v);
      })
      .catch((e: Error) => alive && setError(e.message));
    return () => {
      alive = false;
    };
  }, [ready]);

  if (!ready) return null;
  if (error)
    return (
      <div className="rounded-md border border-rose-300 bg-rose-50 px-3 py-2 text-sm text-rose-800">
        {error}
      </div>
    );
  if (!stats) return <p className="text-sm text-slate-500">Cargando…</p>;

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">
          Salud del modelo
        </h1>
        <p className="mt-1 text-sm text-slate-600">
          Modelo activo:{" "}
          <code className="font-mono font-semibold">{stats.version}</code>
          {" · "}
          {stats.algoritmo}
          {" · "}entrenado con <strong>{stats.n_tesis_train}</strong> tesis
        </p>
      </header>

      <MetricasCV stats={stats} />

      <div className="grid gap-4 lg:grid-cols-2">
        <DistribucionPredicciones stats={stats} />
        <TasaAceptacion stats={stats} />
      </div>

      <MatrizCorrecciones stats={stats} />
      <ClasesNoPredichas stats={stats} />
      <HistorialVersiones versiones={versiones} />
    </div>
  );
}

function MetricasCV({ stats }: { stats: ModeloStats }) {
  const m = stats.metricas as Record<string, unknown>;
  const f1macro = typeof m.f1_macro === "number" ? m.f1_macro : null;
  const f1micro = typeof m.f1_micro === "number" ? m.f1_micro : null;
  // Extraer f1_<categoria>
  const porClase: { cat: string; f1: number; n: number }[] = [];
  for (const [k, v] of Object.entries(m)) {
    if (k.startsWith("f1_") && k !== "f1_macro" && k !== "f1_micro" && typeof v === "number") {
      const cat = k.slice(3);
      const support = typeof m[`support_${cat}`] === "number" ? (m[`support_${cat}`] as number) : 0;
      porClase.push({ cat, f1: v, n: support });
    }
  }
  porClase.sort((a, b) => b.f1 - a.f1);

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-700">
        Métricas de cross-validation
      </h2>
      <p className="mt-1 text-xs text-slate-500">
        Calculadas al entrenar el modelo via StratifiedKFold sobre las tesis
        curadas. No reflejan necesariamente performance en producción.
      </p>
      <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
        {f1macro !== null && <BigMetric k="f1 macro" v={f1macro.toFixed(3)} />}
        {f1micro !== null && <BigMetric k="f1 micro" v={f1micro.toFixed(3)} />}
        <BigMetric k="tesis train" v={String(stats.n_tesis_train)} />
        <BigMetric k="fecha corte" v={stats.fecha_corte} />
      </div>
      <div className="mt-4">
        <div className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
          f1 por categoría (CV)
        </div>
        <ul className="space-y-1">
          {porClase.map((p) => {
            const meta = labelMeta(p.cat as EtiquetaTesis);
            const pct = Math.round(p.f1 * 100);
            const color =
              p.f1 >= 0.6 ? "bg-emerald-400"
              : p.f1 >= 0.4 ? "bg-amber-400"
              : "bg-rose-400";
            return (
              <li key={p.cat} className="text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-medium">{meta.short}</span>
                  <span className="font-mono text-slate-600">
                    f1={p.f1.toFixed(2)} · n={p.n}
                  </span>
                </div>
                <div className="mt-0.5 h-1.5 w-full overflow-hidden rounded bg-slate-100">
                  <div className={`h-full ${color}`} style={{ width: `${pct}%` }} />
                </div>
              </li>
            );
          })}
        </ul>
      </div>
    </section>
  );
}

function BigMetric({ k, v }: { k: string; v: string }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-wider text-slate-500">{k}</div>
      <div className="mt-0.5 font-mono text-xl font-semibold text-slate-800">{v}</div>
    </div>
  );
}

function DistribucionPredicciones({ stats }: { stats: ModeloStats }) {
  const max = Math.max(1, ...Object.values(stats.distribucion_predicciones));
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-700">
        Distribución de predicciones
      </h2>
      <p className="mt-1 text-xs text-slate-500">
        Cuántas veces el modelo ha predicho cada categoría en producción
        ({stats.total_clasificaciones} clasificaciones totales).
      </p>
      <ul className="mt-3 space-y-1">
        {TODAS_LAS_CATEGORIAS.filter((c) => c !== "no_aplica").map((c) => {
          const n = stats.distribucion_predicciones[c] ?? 0;
          const meta = labelMeta(c);
          const pct = (n / max) * 100;
          return (
            <li key={c} className="text-xs">
              <div className="flex items-center justify-between">
                <span
                  className={`rounded px-2 py-0.5 ${labelBadgeClass(meta.color)}`}
                  title={meta.via}
                >
                  {meta.short}
                </span>
                <span className="font-mono text-slate-700">{n}</span>
              </div>
              <div className="mt-0.5 h-1.5 w-full overflow-hidden rounded bg-slate-100">
                <div
                  className="h-full bg-slate-700"
                  style={{ width: `${pct}%` }}
                />
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

function TasaAceptacion({ stats }: { stats: ModeloStats }) {
  const tasa = stats.tasa_aceptacion;
  const pct = tasa !== null ? Math.round(tasa * 100) : null;
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-700">
        Tasa de aceptación del proyectista
      </h2>
      <p className="mt-1 text-xs text-slate-500">
        De {stats.n_validadas} veredictos firmados sobre este modelo,
        cuántos confirmaron la predicción.
      </p>
      {stats.n_validadas === 0 ? (
        <p className="mt-4 text-center text-sm text-slate-500">
          Aún no hay veredictos firmados sobre {stats.version}.
        </p>
      ) : (
        <div className="mt-4 grid grid-cols-3 gap-3">
          <div>
            <div className="text-[10px] uppercase tracking-wider text-slate-500">
              Aceptadas
            </div>
            <div className="mt-0.5 font-mono text-2xl font-semibold text-emerald-700">
              {stats.n_aceptadas}
            </div>
          </div>
          <div>
            <div className="text-[10px] uppercase tracking-wider text-slate-500">
              Corregidas
            </div>
            <div className="mt-0.5 font-mono text-2xl font-semibold text-rose-700">
              {stats.n_corregidas}
            </div>
          </div>
          <div>
            <div className="text-[10px] uppercase tracking-wider text-slate-500">
              Tasa
            </div>
            <div
              className={`mt-0.5 font-mono text-2xl font-semibold ${
                (pct ?? 0) >= 70
                  ? "text-emerald-700"
                  : (pct ?? 0) >= 40
                  ? "text-amber-700"
                  : "text-rose-700"
              }`}
            >
              {pct ?? "—"}%
            </div>
          </div>
        </div>
      )}
    </section>
  );
}

function MatrizCorrecciones({ stats }: { stats: ModeloStats }) {
  if (stats.correcciones.length === 0) return null;
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-700">
        Matriz de correcciones del proyectista
      </h2>
      <p className="mt-1 text-xs text-slate-500">
        Pares (predicha → veredicto final). Las filas con muchos cambios
        son donde el modelo necesita más corpus.
      </p>
      <table className="mt-3 w-full text-xs">
        <thead>
          <tr className="text-left text-[10px] uppercase tracking-wider text-slate-500">
            <th className="pb-1">Modelo predijo</th>
            <th className="pb-1">Veredicto final</th>
            <th className="pb-1 text-right">n</th>
          </tr>
        </thead>
        <tbody>
          {stats.correcciones.map((p, i) => {
            const igual = p.predicha === p.final;
            const mp = labelMeta(p.predicha as EtiquetaTesis);
            const mf = labelMeta(p.final as EtiquetaTesis);
            return (
              <tr
                key={i}
                className={`border-t border-slate-100 ${
                  igual ? "" : "bg-rose-50"
                }`}
              >
                <td className="py-1">
                  <span className={`rounded px-2 py-0.5 ${labelBadgeClass(mp.color)}`}>
                    {mp.short}
                  </span>
                </td>
                <td className="py-1">
                  {igual ? (
                    <span className="text-emerald-700">✓ {mf.short}</span>
                  ) : (
                    <span className="text-rose-700">→ {mf.short}</span>
                  )}
                </td>
                <td className="py-1 text-right font-mono text-slate-700">{p.n}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </section>
  );
}

function ClasesNoPredichas({ stats }: { stats: ModeloStats }) {
  if (stats.clases_no_predichas.length === 0) return null;
  return (
    <section className="rounded-md border-2 border-amber-300 bg-amber-50 p-4 text-sm text-amber-900">
      <p className="font-semibold">⚠ Clases que el modelo nunca predice</p>
      <p className="mt-1 text-xs">
        Estas categorías no aparecen en ninguna predicción del modelo
        activo. O no tenían suficiente corpus de entrenamiento, o el
        modelo simplemente las descarta. Necesitan más tesis etiquetadas.
      </p>
      <ul className="mt-2 flex flex-wrap gap-1">
        {stats.clases_no_predichas.map((c) => {
          const m = labelMeta(c as EtiquetaTesis);
          return (
            <li key={c}>
              <span className={`rounded px-2 py-0.5 text-xs ${labelBadgeClass(m.color)}`}>
                {m.short}
              </span>
            </li>
          );
        })}
      </ul>
      <p className="mt-3 text-[11px]">
        <Link href="/corpus/etiquetar" className="font-medium underline">
          Etiquetar más tesis →
        </Link>
      </p>
    </section>
  );
}

function HistorialVersiones({
  versiones,
}: {
  versiones: ModelVersionListItem[];
}) {
  const [nuevaVersion, setNuevaVersion] = useState("v0.5.0");
  const [lanzando, setLanzando] = useState(false);
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Sugiere la próxima versión incrementando el patch
  useEffect(() => {
    if (versiones.length === 0) return;
    const ultima = versiones[0].version.replace(/^v/, "");
    const partes = ultima.split(".").map((n) => parseInt(n, 10));
    if (partes.length === 3 && !partes.some(isNaN)) {
      partes[2] += 1;
      setNuevaVersion(`v${partes.join(".")}`);
    }
  }, [versiones]);

  async function lanzar() {
    setLanzando(true);
    setMensaje(null);
    setError(null);
    try {
      const r = await reentrenarModelo(nuevaVersion);
      setMensaje(
        `Reentrenamiento de ${r.version} lanzado. Log en ${r.log_path}. Recarga en 30s para ver la nueva versión.`
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLanzando(false);
    }
  }

  if (versiones.length === 0) return null;
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-700">
        Historial de versiones
      </h2>
      <p className="mt-1 text-xs text-slate-500">
        Cada reentrenamiento produce una fila inmutable. Sólo una activa a la
        vez (automáticamente la última entrenada).
      </p>
      <ul className="mt-3 space-y-1 text-xs">
        {versiones.map((v) => (
          <li
            key={v.id}
            className="flex items-center justify-between rounded border border-slate-100 px-3 py-2"
          >
            <div className="flex items-center gap-2">
              <code className="font-mono font-semibold">{v.version}</code>
              {v.activo && (
                <span className="rounded bg-slate-900 px-2 py-0.5 text-[10px] text-white">
                  ACTIVO
                </span>
              )}
              <span className="text-slate-500">{v.algoritmo}</span>
            </div>
            <div className="font-mono text-slate-600">
              n={v.n_tesis_train}
              {v.f1_macro !== null && (
                <span className="ml-2">f1={v.f1_macro.toFixed(2)}</span>
              )}
            </div>
          </li>
        ))}
      </ul>

      <div className="mt-4 rounded-md border-2 border-dashed border-slate-300 p-3">
        <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-600">
          Reentrenar (admin/socio)
        </div>
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <input
            type="text"
            value={nuevaVersion}
            onChange={(e) => setNuevaVersion(e.target.value)}
            placeholder="v0.5.0"
            className="w-32 rounded-md border border-slate-300 px-2 py-1 font-mono text-xs focus:border-indigo-400 focus:outline-none"
          />
          <button
            type="button"
            disabled={lanzando}
            onClick={lanzar}
            className="rounded-md bg-slate-900 px-3 py-1 text-xs font-medium text-white hover:bg-slate-800 disabled:opacity-50"
          >
            {lanzando ? "Lanzando…" : "Reentrenar"}
          </button>
          <span className="text-[10px] text-slate-500">
            usa el corpus actual (excluye fuentes obsoletas)
          </span>
        </div>
        {mensaje && (
          <p className="mt-2 rounded bg-emerald-50 px-2 py-1 text-xs text-emerald-800">
            {mensaje}
          </p>
        )}
        {error && (
          <p className="mt-2 rounded bg-rose-50 px-2 py-1 text-xs text-rose-800">
            {error}
          </p>
        )}
      </div>
    </section>
  );
}
