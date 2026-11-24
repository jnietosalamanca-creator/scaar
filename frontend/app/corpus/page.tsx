"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getCorpusStats, listTesis } from "../lib/api";
import { TODAS_LAS_CATEGORIAS, labelMeta, labelBadgeClass } from "../lib/labels";
import { useRequireAuth } from "../lib/useRequireAuth";
import type { CorpusStats, TesisListItem, TesisListQuery } from "../lib/types";

const PAGE_SIZE = 50;
type Estado = "todas" | "pendiente" | "etiquetada" | "no_aplica" | "lista_train";

export default function CorpusPage() {
  const { ready } = useRequireAuth();
  const [stats, setStats] = useState<CorpusStats | null>(null);
  const [items, setItems] = useState<TesisListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [estado, setEstado] = useState<Estado>("todas");
  const [q, setQ] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!ready) return;
    let alive = true;
    getCorpusStats()
      .then((s) => alive && setStats(s))
      .catch((e: Error) => alive && setError(e.message));
    return () => {
      alive = false;
    };
  }, [ready]);

  useEffect(() => {
    if (!ready) return;
    let alive = true;
    setLoading(true);
    setError(null);
    const query: TesisListQuery = { limit: PAGE_SIZE };
    if (estado !== "todas") query.estado = estado;
    if (q.trim().length >= 2) query.q = q.trim();
    listTesis(query)
      .then((r) => {
        if (!alive) return;
        setItems(r.items);
        setTotal(r.total);
      })
      .catch((e: Error) => alive && setError(e.message))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [ready, estado, q]);

  if (!ready) return null;

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Corpus de tesis</h1>
          <p className="mt-1 text-sm text-slate-600">
            Universo de tesis conocidas. Etiquétalas para que el modelo las use en el
            próximo entrenamiento.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {stats && stats.pendientes > 0 && (
            <Link
              href="/corpus/etiquetar"
              className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-slate-800"
            >
              Etiquetar pendientes ({stats.pendientes})
            </Link>
          )}
          <Link
            href="/corpus/auditoria"
            className="rounded-md border-2 border-amber-300 bg-amber-50 px-4 py-2 text-sm font-medium text-amber-900 hover:bg-amber-100"
            title="Tesis ya etiquetadas donde el modelo discrepa contigo"
          >
            🔍 Auditoría
          </Link>
          <Link
            href="/corpus/importar"
            className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            + Importar
          </Link>
        </div>
      </header>

      {stats && <StatsBlock stats={stats} />}

      <div className="flex flex-wrap items-center gap-3 rounded-lg border border-slate-200 bg-white p-3 shadow-sm">
        <input
          type="text"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Buscar en rubro o texto…"
          className="flex-1 min-w-[240px] rounded-md border border-slate-300 px-3 py-1.5 text-sm focus:border-indigo-400 focus:outline-none focus:ring-1 focus:ring-indigo-300"
        />
        <div className="flex gap-1 rounded-md border border-slate-200 p-0.5 text-xs">
          {(
            [
              ["todas", "Todas"],
              ["pendiente", "Pendientes"],
              ["lista_train", "Lista p/ train"],
              ["no_aplica", "No aplica"],
              ["etiquetada", "Etiquetadas"],
            ] as [Estado, string][]
          ).map(([k, l]) => (
            <button
              key={k}
              type="button"
              onClick={() => setEstado(k)}
              className={`rounded px-3 py-1 ${
                estado === k ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-100"
              }`}
            >
              {l}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div className="rounded-md border border-rose-300 bg-rose-50 px-3 py-2 text-sm text-rose-800">
          {error}
        </div>
      )}

      <div className="text-xs text-slate-500">
        {loading ? "Cargando…" : `${items.length} de ${total} tesis`}
      </div>

      <ul className="space-y-2">
        {items.map((t) => (
          <TesisRow key={t.id} t={t} />
        ))}
      </ul>
    </div>
  );
}

function StatsBlock({ stats }: { stats: CorpusStats }) {
  const pctEtiq =
    stats.total > 0 ? Math.round((stats.etiquetadas / stats.total) * 100) : 0;
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
        <Stat k="Total" v={stats.total} />
        <Stat k="Pendientes" v={stats.pendientes} accent="amber" />
        <Stat
          k="Etiquetadas"
          v={stats.etiquetadas}
          accent="indigo"
        />
        <Stat
          k="Listas p/ entrenar"
          v={stats.listas_para_entrenar}
          accent="emerald"
        />
        <Stat
          k="Limpias (no obsoletas)"
          v={stats.listas_para_train_limpio}
          accent="emerald"
        />
      </div>
      <div className="mt-4">
        <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
          Reparto por categoría
        </div>
        <div className="mt-2 flex flex-wrap gap-1 text-[11px]">
          {TODAS_LAS_CATEGORIAS.map((c) => {
            const m = labelMeta(c);
            const n = stats.por_categoria[c] ?? 0;
            return (
              <span
                key={c}
                className={`rounded px-2 py-0.5 ${labelBadgeClass(m.color)} ${
                  n === 0 ? "opacity-40" : ""
                }`}
                title={m.explicacion}
              >
                {m.short}: <strong>{n}</strong>
              </span>
            );
          })}
        </div>
      </div>
      <div className="mt-4">
        <div className="flex items-center justify-between text-xs">
          <span className="text-slate-500">Progreso de etiquetado</span>
          <span className="font-mono text-slate-700">
            {stats.etiquetadas} / {stats.total} ({pctEtiq}%)
          </span>
        </div>
        <div className="mt-1 h-2 w-full overflow-hidden rounded-full bg-slate-100">
          <div
            className="h-full bg-slate-900 transition-all"
            style={{ width: `${pctEtiq}%` }}
          />
        </div>
        <p className="mt-2 text-[11px] text-slate-500">
          <strong>{stats.listas_para_entrenar}</strong> tesis listas para entrenar (adj +
          sus). Recomendación mínima: ~80 tesis (40 adj + 40 sus) para que el modelo
          deje de ser un juguete.
        </p>
      </div>
      <div className="mt-3 flex flex-wrap gap-1 text-[10px] text-slate-500">
        {Object.entries(stats.por_fuente).map(([k, v]) => {
          const excluida = stats.fuentes_excluidas.includes(k);
          const esLoteDirigido = k.startsWith("sjf_dirigido");
          return (
            <Link
              key={k}
              href={esLoteDirigido ? `/corpus/etiquetar?fuente=${k}` : "#"}
              onClick={(e) => {
                if (!esLoteDirigido) e.preventDefault();
              }}
              className={`rounded border px-2 py-0.5 ${
                excluida
                  ? "border-rose-300 bg-rose-50 text-rose-700"
                  : esLoteDirigido
                  ? "border-indigo-400 bg-indigo-50 text-indigo-800 hover:bg-indigo-100"
                  : "border-slate-200"
              }`}
              title={
                excluida
                  ? "Fuente excluida del próximo training"
                  : esLoteDirigido
                  ? "Lote dirigido — click para etiquetar enfocado"
                  : undefined
              }
            >
              {k}: <strong>{v}</strong>
              {excluida && <span className="ml-1">⊘</span>}
              {esLoteDirigido && <span className="ml-1">🎯</span>}
            </Link>
          );
        })}
      </div>

      <CleanTrainProgress stats={stats} />
    </div>
  );
}

function CleanTrainProgress({ stats }: { stats: CorpusStats }) {
  const target = stats.threshold_train_limpio;
  const current = stats.listas_para_train_limpio;
  const pct = Math.min(100, Math.round((current / target) * 100));
  const ready = current >= target;
  return (
    <div className="mt-5 rounded-md border border-slate-200 bg-slate-50/60 p-4">
      <div className="flex items-baseline justify-between">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-700">
          Progreso a modelo limpio
        </h3>
        <span
          className={`text-xs font-mono ${
            ready ? "text-emerald-700" : "text-slate-600"
          }`}
        >
          {current} / {target} ({pct}%)
        </span>
      </div>
      <div className="mt-1 h-2 w-full overflow-hidden rounded-full bg-slate-200">
        <div
          className={`h-full transition-all ${
            ready ? "bg-emerald-600" : "bg-indigo-500"
          }`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <p className="mt-2 text-[11px] text-slate-600">
        {ready ? (
          <>
            <strong>Listo.</strong> Cuando reentrenes (
            <code className="font-mono">python -m app.ml.train --version vX.Y.Z</code>),
            el modelo nuevo se construye <strong>solo con tesis curadas</strong>{" "}
            (excluye {stats.fuentes_excluidas.join(", ")}). El modelo activo actual sigue funcionando hasta entonces.
          </>
        ) : (
          <>
            Faltan <strong>{target - current}</strong> tesis adj/sus de fuentes
            confiables (no obsoletas) para que el reentreno limpio sea viable.
            Etiqueta más SJF para llegar.
          </>
        )}
      </p>
      {stats.fuentes_excluidas.length > 0 && (
        <p className="mt-1 text-[10px] text-slate-400">
          Fuentes excluidas del training:{" "}
          {stats.fuentes_excluidas.map((f) => (
            <code key={f} className="font-mono">
              {f}
            </code>
          ))}
        </p>
      )}
    </div>
  );
}

function Stat({
  k,
  v,
  accent = "slate",
}: {
  k: string;
  v: number;
  accent?: "indigo" | "emerald" | "amber" | "slate";
}) {
  const cls = {
    indigo: "text-indigo-700",
    emerald: "text-emerald-700",
    amber: "text-amber-700",
    slate: "text-slate-700",
  }[accent];
  return (
    <div>
      <div className="text-[10px] uppercase tracking-wider text-slate-500">{k}</div>
      <div className={`mt-0.5 text-2xl font-semibold ${cls}`}>{v}</div>
    </div>
  );
}

function TesisRow({ t }: { t: TesisListItem }) {
  return (
    <li>
      <Link
        href={`/corpus/${t.id}`}
        className="block rounded-lg border border-slate-200 bg-white p-4 shadow-sm transition hover:border-slate-400"
      >
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <code className="font-mono text-slate-600">{t.registro_sjf}</code>
              <span className="rounded border border-slate-200 bg-slate-50 px-2 py-0.5 text-slate-600">
                {t.tipo}
              </span>
              <span className="text-slate-500">{t.instancia}</span>
              <EtiquetaBadge etiqueta={t.etiqueta} />
              {t.tipo_jurisprudencial && t.tipo_jurisprudencial !== "regla" && (
                <span
                  className="rounded bg-rose-100 px-2 py-0.5 text-[10px] font-medium text-rose-800"
                  title={`Esta tesis es '${t.tipo_jurisprudencial}' — NO entra al training`}
                >
                  ⊘ {t.tipo_jurisprudencial}
                </span>
              )}
              <span className="rounded bg-slate-100 px-2 py-0.5 text-[10px] text-slate-600">
                {t.fuente}
              </span>
            </div>
            <p className="mt-2 line-clamp-2 text-sm font-medium text-slate-800">
              {t.rubro}
            </p>
            <div className="mt-1 text-[10px] text-slate-400">
              {t.etiquetada_por_email
                ? `Etiquetada por ${t.etiquetada_por_email} · ${
                    t.etiquetada_at
                      ? new Date(t.etiquetada_at).toLocaleString("es-MX")
                      : ""
                  }`
                : t.etiqueta === null
                ? "Sin etiqueta"
                : "Etiquetada (auditoría no registrada)"}
            </div>
          </div>
        </div>
      </Link>
    </li>
  );
}

function EtiquetaBadge({ etiqueta }: { etiqueta: string | null }) {
  const meta = labelMeta(etiqueta as never);
  return (
    <span
      className={`rounded px-2 py-0.5 font-medium ${labelBadgeClass(meta.color)}`}
      title={meta.via}
    >
      {meta.short}
    </span>
  );
}
