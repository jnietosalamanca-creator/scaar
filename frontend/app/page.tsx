"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { listClassifications } from "./lib/api";
import { labelMeta } from "./lib/labels";
import { useRequireAuth } from "./lib/useRequireAuth";
import type { ClassificationListItem, ListQuery } from "./lib/types";
import { BannerModeloBinario } from "./components/BannerModeloBinario";

const PAGE_SIZE = 20;

type Estado = "todas" | "pendiente" | "validada";

export default function HomePage() {
  const { ready } = useRequireAuth();
  const [sha, setSha] = useState("");
  const [textQuery, setTextQuery] = useState("");
  const [estado, setEstado] = useState<Estado>("todas");
  const [items, setItems] = useState<ClassificationListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // tick fuerza recarga después de cambios
  const [tick, setTick] = useState(0);

  useEffect(() => {
    if (!ready) return;
    let alive = true;
    setLoading(true);
    setError(null);
    const query: ListQuery = { limit: PAGE_SIZE };
    if (sha.trim().length >= 2) query.sha = sha.trim();
    if (textQuery.trim().length >= 2) query.q = textQuery.trim();
    if (estado !== "todas") query.estado = estado;
    listClassifications(query)
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
  }, [ready, sha, textQuery, estado, tick]);

  if (!ready) return null;

  return (
    <div className="space-y-6">
      <BannerModeloBinario />
      <header className="flex items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Clasificaciones</h1>
          <p className="mt-1 text-sm text-slate-600">
            Total: {total} · Filtrando por estado: <strong>{estado}</strong>
            {sha && (
              <>
                {" "}· SHA <code className="font-mono text-xs">{sha}</code>
              </>
            )}
            {textQuery && (
              <>
                {" "}· Texto <code className="font-mono text-xs">“{textQuery}”</code>
              </>
            )}
          </p>
        </div>
        <Link
          href="/clasificar"
          className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-slate-800"
        >
          + Nueva clasificación
        </Link>
      </header>

      <div className="flex flex-wrap items-center gap-3 rounded-lg border border-slate-200 bg-white p-3 shadow-sm">
        <input
          type="text"
          value={textQuery}
          onChange={(e) => setTextQuery(e.target.value)}
          placeholder="Buscar en el texto del acto (full-text, español)…"
          className="flex-1 min-w-[260px] rounded-md border border-slate-300 px-3 py-1.5 text-sm focus:border-indigo-400 focus:outline-none focus:ring-1 focus:ring-indigo-300"
        />
        <input
          type="text"
          value={sha}
          onChange={(e) => setSha(e.target.value.replace(/[^0-9a-f]/gi, "").toLowerCase())}
          placeholder="SHA…"
          className="w-32 rounded-md border border-slate-300 px-3 py-1.5 font-mono text-xs focus:border-indigo-400 focus:outline-none focus:ring-1 focus:ring-indigo-300"
        />
        <div className="flex gap-1 rounded-md border border-slate-200 p-0.5">
          {(["todas", "pendiente", "validada"] as Estado[]).map((e) => (
            <button
              key={e}
              type="button"
              onClick={() => setEstado(e)}
              className={`rounded px-3 py-1 text-xs capitalize ${
                estado === e
                  ? "bg-slate-900 text-white"
                  : "text-slate-600 hover:bg-slate-100"
              }`}
            >
              {e}
            </button>
          ))}
        </div>
        <button
          type="button"
          onClick={() => setTick((t) => t + 1)}
          className="rounded border border-slate-300 px-3 py-1 text-xs text-slate-700 hover:bg-slate-50"
          title="Recargar"
        >
          ↻
        </button>
      </div>

      {error && (
        <div className="rounded-md border border-rose-300 bg-rose-50 px-3 py-2 text-sm text-rose-800">
          {error}
        </div>
      )}

      {loading ? (
        <p className="text-sm text-slate-500">Cargando…</p>
      ) : items.length === 0 ? (
        <EmptyState filtered={sha.length > 0 || estado !== "todas"} />
      ) : (
        <ul className="space-y-2">
          {items.map((it) => (
            <ClassificationRow key={it.id} item={it} query={textQuery} />
          ))}
        </ul>
      )}

      {!loading && items.length > 0 && total > items.length && (
        <p className="text-center text-xs text-slate-500">
          Mostrando {items.length} de {total}. Refina la búsqueda para encontrar más.
        </p>
      )}
    </div>
  );
}

function EmptyState({ filtered }: { filtered: boolean }) {
  return (
    <div className="rounded-lg border border-dashed border-slate-300 bg-white p-10 text-center">
      <p className="text-sm font-medium text-slate-700">
        {filtered ? "Sin resultados con esos filtros." : "No hay clasificaciones todavía."}
      </p>
      <p className="mt-1 text-sm text-slate-500">
        {filtered ? (
          "Cambia los filtros o limpia la búsqueda."
        ) : (
          <>
            Crea la primera desde{" "}
            <Link href="/clasificar" className="font-medium text-indigo-700 underline">
              Nueva clasificación
            </Link>
            .
          </>
        )}
      </p>
    </div>
  );
}

function highlightQuery(text: string, query: string): React.ReactNode {
  if (!query || query.trim().length < 2) return text;
  // Resaltado básico de palabras del query (>= 3 chars). El split con grupo
  // capturador deja los matches en índices impares — más confiable que
  // usar regex.test() que mantiene state con flag /g.
  const palabras = query
    .split(/\s+/)
    .map((p) => p.trim())
    .filter((p) => p.length >= 3);
  if (palabras.length === 0) return text;
  const escaped = palabras.map((p) => p.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  const re = new RegExp(`(${escaped.join("|")})`, "gi");
  const parts = text.split(re);
  return parts.map((part, i) =>
    i % 2 === 1 ? (
      <mark key={i} className="rounded bg-yellow-200 px-0.5">
        {part}
      </mark>
    ) : (
      <span key={i}>{part}</span>
    )
  );
}

function ClassificationRow({
  item,
  query,
}: {
  item: ClassificationListItem;
  query: string;
}) {
  const meta = labelMeta(item.categoria);
  const pct =
    item.prob_categoria !== null
      ? Math.round(item.prob_categoria * 1000) / 10
      : null;
  const finalMeta = item.clasificacion_final ? labelMeta(item.clasificacion_final) : null;
  return (
    <li>
      <Link
        href={`/clasificaciones/${item.id}`}
        className="block rounded-lg border border-slate-200 bg-white p-4 shadow-sm transition hover:border-slate-400"
      >
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <span
                className={`rounded px-2 py-0.5 font-medium ${
                  meta.color === "indigo"
                    ? "bg-indigo-100 text-indigo-700"
                    : meta.color === "emerald"
                    ? "bg-emerald-100 text-emerald-700"
                    : meta.color === "amber"
                    ? "bg-amber-100 text-amber-700"
                    : meta.color === "rose"
                    ? "bg-rose-100 text-rose-700"
                    : meta.color === "sky"
                    ? "bg-sky-100 text-sky-700"
                    : meta.color === "violet"
                    ? "bg-violet-100 text-violet-700"
                    : "bg-slate-200 text-slate-700"
                }`}
                title={meta.via === "ninguna" ? meta.inmediatez : meta.via}
              >
                {meta.short}
              </span>
              {pct !== null && (
                <span className="font-mono text-slate-600">
                  conf. {pct.toFixed(1)}%
                </span>
              )}
              {item.requiere_revision_humana && (
                <span className="rounded bg-amber-100 px-2 py-0.5 text-amber-800">
                  ⚠ revisión humana
                </span>
              )}
              {item.veredicto_vigente === null ? (
                <span className="rounded border border-slate-300 px-2 py-0.5 text-slate-500">
                  pendiente
                </span>
              ) : item.veredicto_vigente === "acepta" ? (
                <span className="rounded bg-emerald-100 px-2 py-0.5 text-emerald-700">
                  ✓ aceptada
                </span>
              ) : (
                <span className="rounded bg-rose-100 px-2 py-0.5 text-rose-700">
                  ✗ corregida → {finalMeta?.short}
                </span>
              )}
              {item.n_validaciones > 1 && (
                <span className="text-[10px] text-slate-400">
                  ({item.n_validaciones} firmas en historia)
                </span>
              )}
            </div>
            <p className="mt-2 line-clamp-2 text-sm text-slate-800">
              {highlightQuery(item.acto_preview, query)}
            </p>
            <div className="mt-2 flex flex-wrap items-center gap-3 text-[10px] text-slate-400">
              <code className="font-mono">SHA {item.acto_sha256.slice(0, 16)}…</code>
              <span>·</span>
              <span>{new Date(item.created_at).toLocaleString("es-MX")}</span>
              <span>·</span>
              <span>{item.created_by_email}</span>
              <span>·</span>
              <span>modelo {item.model_version}</span>
            </div>
          </div>
        </div>
      </Link>
    </li>
  );
}
