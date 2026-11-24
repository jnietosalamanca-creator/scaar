"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { getCorpusStats, getSiguientePendiente, labelTesis } from "../../lib/api";
import { useRequireAuth } from "../../lib/useRequireAuth";
import {
  TODAS_LAS_CATEGORIAS,
  labelButtonClass,
  labelMeta,
} from "../../lib/labels";
import type { CorpusStats, EtiquetaTesis, TesisDetail } from "../../lib/types";
import { DoctrinaAncla } from "../../components/DoctrinaAncla";

export default function EtiquetarPage() {
  const { ready } = useRequireAuth();
  const params = useSearchParams();
  const fuenteFiltro = params.get("fuente");
  const [tesis, setTesis] = useState<TesisDetail | null>(null);
  const [stats, setStats] = useState<CorpusStats | null>(null);
  const [labeling, setLabeling] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const [lastLabel, setLastLabel] = useState<EtiquetaTesis | null>(null);

  const loadNext = useCallback(async () => {
    setError(null);
    try {
      const [next, s] = await Promise.all([
        getSiguientePendiente(fuenteFiltro),
        getCorpusStats(),
      ]);
      setStats(s);
      if (next === null) {
        setTesis(null);
        setDone(true);
      } else {
        setTesis(next);
        setDone(false);
      }
    } catch (e) {
      setError((e as Error).message);
    }
  }, [fuenteFiltro]);

  useEffect(() => {
    if (!ready) return;
    loadNext();
  }, [ready, loadNext]);

  const submitLabel = useCallback(
    async (etiqueta: EtiquetaTesis) => {
      if (!tesis || labeling) return;
      setLabeling(true);
      setError(null);
      try {
        await labelTesis(tesis.id, etiqueta);
        setLastLabel(etiqueta);
        setTimeout(() => setLastLabel(null), 350);
        await loadNext();
      } catch (e) {
        setError((e as Error).message);
      } finally {
        setLabeling(false);
      }
    },
    [tesis, labeling, loadNext]
  );

  // Shortcuts: 1-8 = categorías, 0 = no_aplica
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (!tesis || labeling) return;
      if (e.target instanceof HTMLTextAreaElement || e.target instanceof HTMLInputElement) {
        return;
      }
      const cat = TODAS_LAS_CATEGORIAS.find((c) => labelMeta(c).shortcut === e.key);
      if (cat) {
        e.preventDefault();
        submitLabel(cat);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [tesis, labeling, submitLabel]);

  if (!ready) return null;

  return (
    <div className="space-y-6">
      <header className="flex items-end justify-between gap-4">
        <div>
          <Link href="/corpus" className="text-xs text-slate-500 hover:text-slate-900">
            ← Corpus
          </Link>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight">Etiquetar tesis</h1>
          <p className="mt-1 text-sm text-slate-600">
            Para cada tesis, identifica su categoría de procedencia (Ley de Amparo
            art. 107). El sistema deriva automáticamente la vía y la inmediatez.
          </p>
          {fuenteFiltro && (
            <p className="mt-2 inline-block rounded bg-indigo-100 px-2 py-1 text-xs text-indigo-800">
              🎯 Lote enfocado: <code className="font-mono">{fuenteFiltro}</code>
              {" · "}
              <Link href="/corpus/etiquetar" className="underline">
                ver todas las pendientes
              </Link>
            </p>
          )}
        </div>
        {stats && <ProgresoMini stats={stats} />}
      </header>

      {error && (
        <div className="rounded-md border border-rose-300 bg-rose-50 px-3 py-2 text-sm text-rose-800">
          {error}
        </div>
      )}

      <DoctrinaAncla variant="compacto" titulo="Criterio aplicable al etiquetar" />

      {done && !tesis ? (
        <DoneBlock />
      ) : tesis === null ? (
        <p className="text-sm text-slate-500">Cargando…</p>
      ) : (
        <TesisCard tesis={tesis} highlight={lastLabel} />
      )}

      {tesis && (
        <BotoneraCategorias
          disabled={labeling}
          onSubmit={submitLabel}
        />
      )}

      <p className="text-center text-[11px] text-slate-400">
        Atajos:{" "}
        {TODAS_LAS_CATEGORIAS.map((c) => {
          const m = labelMeta(c);
          return (
            <span key={c} className="mx-1">
              <kbd className="rounded border border-slate-300 px-1">{m.shortcut}</kbd>{" "}
              {m.short}
            </span>
          );
        })}
      </p>
    </div>
  );
}

function ProgresoMini({ stats }: { stats: CorpusStats }) {
  const pct = stats.total > 0 ? Math.round((stats.etiquetadas / stats.total) * 100) : 0;
  return (
    <div className="text-right text-xs">
      <div className="font-mono text-slate-700">
        {stats.etiquetadas} / {stats.total} ({pct}%)
      </div>
      <div className="mt-1 h-1.5 w-40 overflow-hidden rounded-full bg-slate-100">
        <div className="h-full bg-slate-900" style={{ width: `${pct}%` }} />
      </div>
      <div className="mt-1 text-slate-500">
        Restantes: <strong>{stats.pendientes}</strong>
      </div>
    </div>
  );
}

function TesisCard({
  tesis,
  highlight,
}: {
  tesis: TesisDetail;
  highlight: EtiquetaTesis | null;
}) {
  const meta = highlight ? labelMeta(highlight) : null;
  const ringColor = meta
    ? {
        indigo: "ring-indigo-300",
        emerald: "ring-emerald-300",
        amber: "ring-amber-300",
        rose: "ring-rose-300",
        sky: "ring-sky-300",
        violet: "ring-violet-300",
        slate: "ring-slate-300",
      }[meta.color]
    : "";
  return (
    <article
      className={`rounded-lg border border-slate-200 bg-white p-6 shadow-sm transition ${
        highlight ? `ring-4 ${ringColor}` : ""
      }`}
    >
      <div className="flex flex-wrap items-center gap-2 text-xs text-slate-600">
        <code className="font-mono">{tesis.registro_sjf}</code>
        <span>·</span>
        <span>{tesis.epoca}</span>
        <span>·</span>
        <span>{tesis.instancia}</span>
        <span>·</span>
        <span className="rounded border border-slate-200 bg-slate-50 px-2 py-0.5">
          {tesis.tipo}
        </span>
        <span>·</span>
        <span className="rounded bg-slate-100 px-2 py-0.5">{tesis.fuente}</span>
      </div>
      <h2 className="mt-3 text-lg font-semibold leading-snug text-slate-900">
        {tesis.rubro}
      </h2>
      <p className="mt-4 whitespace-pre-wrap text-sm leading-relaxed text-slate-800">
        {tesis.texto}
      </p>
      {tesis.fecha_publ && (
        <div className="mt-4 text-[11px] text-slate-400">
          Publicación: {tesis.fecha_publ}
        </div>
      )}
    </article>
  );
}

/**
 * Botonera de categorías agrupada por vía: indirecta inmediata, diferida,
 * directa (sentencia), prematuro (alerta), no aplica.
 */
function BotoneraCategorias({
  disabled,
  onSubmit,
}: {
  disabled: boolean;
  onSubmit: (e: EtiquetaTesis) => void;
}) {
  const grupos: { titulo: string; cats: EtiquetaTesis[] }[] = [
    {
      titulo: "Amparo indirecto — inmediato",
      cats: [
        "fuera_juicio",
        "en_juicio_imposible",
        "tercero_extrano",
        "post_juicio_general",
        "post_juicio_ejecucion",
      ],
    },
    {
      titulo: "Amparo directo",
      cats: ["en_juicio_diferida", "sentencia_definitiva"],
    },
    {
      titulo: "Otros",
      cats: ["post_juicio_prematuro", "no_aplica"],
    },
  ];
  return (
    <div className="space-y-4">
      {grupos.map((g) => (
        <div key={g.titulo}>
          <div className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
            {g.titulo}
          </div>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4">
            {g.cats.map((c) => (
              <BotonCategoria
                key={c}
                etiqueta={c}
                disabled={disabled}
                onClick={() => onSubmit(c)}
              />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

function BotonCategoria({
  etiqueta,
  disabled,
  onClick,
}: {
  etiqueta: EtiquetaTesis;
  disabled: boolean;
  onClick: () => void;
}) {
  const m = labelMeta(etiqueta);
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      title={m.explicacion}
      className={`rounded-lg border-2 bg-white p-3 text-left shadow-sm transition disabled:cursor-not-allowed disabled:opacity-50 ${labelButtonClass(
        m.color
      )}`}
    >
      <div className="flex items-center justify-between">
        <div className="text-sm font-semibold leading-tight">{m.display}</div>
        <kbd className="ml-2 rounded border border-slate-300 bg-slate-50 px-1.5 py-0.5 font-mono text-[10px] text-slate-600">
          {m.shortcut}
        </kbd>
      </div>
      <div className="mt-1 text-[10px] text-slate-500">
        {m.via === "ninguna" ? m.inmediatez : `${m.via} · ${m.inmediatez}`}
      </div>
    </button>
  );
}

function DoneBlock() {
  return (
    <div className="rounded-lg border border-emerald-300 bg-emerald-50 p-8 text-center">
      <p className="text-lg font-semibold text-emerald-900">
        ¡No quedan tesis pendientes!
      </p>
      <p className="mt-2 text-sm text-emerald-800">
        Todas las tesis del corpus tienen etiqueta. Si quieres más, importa otro batch
        desde{" "}
        <Link href="/corpus/importar" className="font-medium underline">
          /corpus/importar
        </Link>
        .
      </p>
    </div>
  );
}
