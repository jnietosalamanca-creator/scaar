"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  createCaso,
  generarCasoSintetico,
  importEjecutorias,
  listCasos,
} from "../lib/api";
import { TODAS_LAS_CATEGORIAS, labelMeta } from "../lib/labels";
import { useRequireAuth } from "../lib/useRequireAuth";
import type {
  CasoListItem,
  CasoListQuery,
  EjecutoriaImportItem,
  EjecutoriasImportResponse,
  EtiquetaTesis,
  PrediccionCategoria,
} from "../lib/types";

const PAGE_SIZE = 50;
type Filtro = "activos" | "archivados" | "todos";

export default function CasosPage() {
  const { ready } = useRequireAuth();
  const [items, setItems] = useState<CasoListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [filtro, setFiltro] = useState<Filtro>("activos");
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  // Modal de creación inline
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [newId, setNewId] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [newMateria, setNewMateria] = useState("");

  // Modal de caso sintético
  const [showSint, setShowSint] = useState(false);
  const [sintGenerating, setSintGenerating] = useState(false);
  const [sintError, setSintError] = useState<string | null>(null);
  const [sintNActos, setSintNActos] = useState(4);
  const [sintCategorias, setSintCategorias] = useState<PrediccionCategoria[]>([]);

  // Import de ejecutorias SJF (JSONL)
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [importing, setImporting] = useState(false);
  const [importError, setImportError] = useState<string | null>(null);
  const [importResult, setImportResult] = useState<EjecutoriasImportResponse | null>(
    null
  );

  useEffect(() => {
    if (!ready) return;
    let alive = true;
    setLoading(true);
    setError(null);
    const query: CasoListQuery = { limit: PAGE_SIZE, archived: filtro };
    if (q.trim().length >= 2) query.q = q.trim();
    listCasos(query)
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
  }, [ready, filtro, q, tick]);

  async function onGenerarSintetico() {
    setSintError(null);
    setSintGenerating(true);
    try {
      const caso = await generarCasoSintetico({
        n_actos: sintNActos,
        categorias_objetivo: sintCategorias.length > 0 ? sintCategorias : undefined,
      });
      setShowSint(false);
      window.location.href = `/casos/${caso.id}`;
    } catch (err) {
      setSintError((err as Error).message);
    } finally {
      setSintGenerating(false);
    }
  }

  function toggleSintCategoria(c: PrediccionCategoria) {
    setSintCategorias((prev) =>
      prev.includes(c) ? prev.filter((x) => x !== c) : [...prev, c]
    );
  }

  async function onImportFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setImportError(null);
    setImportResult(null);
    setImporting(true);
    try {
      const text = await file.text();
      // JSONL: una línea = un item. Ignora líneas vacías.
      const lines = text.split(/\r?\n/).filter((l) => l.trim().length > 0);
      const items: EjecutoriaImportItem[] = [];
      for (let i = 0; i < lines.length; i++) {
        try {
          items.push(JSON.parse(lines[i]) as EjecutoriaImportItem);
        } catch {
          throw new Error(`Línea ${i + 1} no es JSON válido.`);
        }
      }
      if (items.length === 0) throw new Error("El archivo está vacío.");
      if (items.length > 500)
        throw new Error(`El servidor acepta máximo 500 por lote (recibí ${items.length}).`);

      const res = await importEjecutorias(items);
      setImportResult(res);
      // Refresca la lista para que aparezcan los nuevos
      setTick((t) => t + 1);
    } catch (err) {
      setImportError((err as Error).message);
    } finally {
      setImporting(false);
      // Reset del input para permitir re-subir el mismo archivo
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  async function onCreate(e: React.FormEvent) {
    e.preventDefault();
    setCreateError(null);
    setCreating(true);
    try {
      const caso = await createCaso({
        identificador: newId.trim(),
        descripcion: newDesc.trim() || null,
        materia: newMateria.trim() || null,
      });
      setShowCreate(false);
      setNewId("");
      setNewDesc("");
      setNewMateria("");
      window.location.href = `/casos/${caso.id}`;
    } catch (err) {
      setCreateError((err as Error).message);
    } finally {
      setCreating(false);
    }
  }

  if (!ready) return null;

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Casos</h1>
          <p className="mt-1 text-sm text-slate-600">
            Expedientes del despacho. Cada caso agrupa los actos reclamados que
            forman un mismo asunto y muestra qué demandas presentar.
          </p>
        </div>
        <div className="flex gap-2">
          <input
            ref={fileInputRef}
            type="file"
            accept=".jsonl,application/jsonlines,application/x-ndjson,application/json,text/plain"
            onChange={onImportFile}
            className="hidden"
          />
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={importing}
            className="rounded-md border border-sky-300 bg-sky-50 px-4 py-2 text-sm font-medium text-sky-900 hover:bg-sky-100 disabled:opacity-50"
            title="Carga un JSONL generado por fetch_ejecutorias.py — crea un caso por sentencia de amparo del SJF"
          >
            {importing ? "Importando…" : "📥 Importar SJF (JSONL)"}
          </button>
          <button
            type="button"
            onClick={() => setShowSint(true)}
            className="rounded-md border border-violet-300 bg-violet-50 px-4 py-2 text-sm font-medium text-violet-900 hover:bg-violet-100"
            title="Genera un caso de práctica con N actos sintéticos clasificados por el modelo"
          >
            🎲 Caso al azar
          </button>
          <button
            type="button"
            onClick={() => setShowCreate(true)}
            className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-slate-800"
          >
            + Nuevo caso
          </button>
        </div>
      </header>

      {(importError || importResult) && (
        <div
          className={`rounded-md border px-3 py-2 text-sm ${
            importError
              ? "border-rose-300 bg-rose-50 text-rose-800"
              : "border-sky-300 bg-sky-50 text-sky-900"
          }`}
        >
          {importError ? (
            <>
              <strong>Error al importar:</strong> {importError}
            </>
          ) : (
            importResult && (
              <>
                <strong>Importación OK.</strong>{" "}
                Creados: {importResult.creados} · Duplicados:{" "}
                {importResult.duplicados} · Inválidos: {importResult.invalidos}
                {importResult.duplicados > 0 && (
                  <span className="ml-2 text-sky-700">
                    (los duplicados ya existían en tu lista de casos —
                    se ignoraron sin reemplazar).
                  </span>
                )}
                <button
                  type="button"
                  onClick={() => setImportResult(null)}
                  className="ml-3 underline hover:text-sky-700"
                >
                  cerrar
                </button>
              </>
            )
          )}
        </div>
      )}

      {showSint && (
        <div className="rounded-lg border-2 border-violet-300 bg-violet-50/50 p-5 shadow-sm">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-violet-900">
            🎲 Generar caso al azar (práctica)
          </h2>
          <p className="mt-1 text-xs text-violet-800">
            Crea un caso sintético con N actos generados de plantillas
            paramétricas. El modelo activo los clasifica y tú firmas
            (acepta/corrige) — útil para practicar el flujo sin esperar
            a un expediente real. Marcado{" "}
            <code className="font-mono">materia=sintetico</code>; no
            contamina el corpus de reentreno.
          </p>
          <div className="mt-3 flex flex-wrap items-end gap-3">
            <div>
              <label className="text-[10px] font-medium uppercase tracking-wider text-slate-600">
                # de actos
              </label>
              <input
                type="number"
                min={1}
                max={12}
                value={sintNActos}
                onChange={(e) => setSintNActos(Number(e.target.value))}
                className="mt-1 w-20 rounded-md border border-slate-300 px-2 py-1 text-sm focus:border-violet-400 focus:outline-none"
              />
            </div>
            <div className="flex-1">
              <label className="text-[10px] font-medium uppercase tracking-wider text-slate-600">
                Categorías objetivo (opcional — si vacío, al azar)
              </label>
              <div className="mt-1 flex flex-wrap gap-1">
                {TODAS_LAS_CATEGORIAS.filter((c) => c !== "no_aplica").map((c) => {
                  const m = labelMeta(c as EtiquetaTesis);
                  const active = sintCategorias.includes(c as PrediccionCategoria);
                  return (
                    <button
                      key={c}
                      type="button"
                      onClick={() => toggleSintCategoria(c as PrediccionCategoria)}
                      className={`rounded px-2 py-0.5 text-[10px] ${
                        active
                          ? "bg-violet-700 text-white"
                          : "border border-slate-300 bg-white text-slate-700 hover:bg-slate-50"
                      }`}
                      title={m.explicacion}
                    >
                      {m.short}
                    </button>
                  );
                })}
              </div>
              {sintCategorias.length > 0 && (
                <p className="mt-1 text-[10px] text-slate-500">
                  {sintCategorias.length} categoría(s) seleccionada(s); cada acto
                  saldrá al azar de esta lista (puede repetirse).
                </p>
              )}
            </div>
          </div>
          {sintError && (
            <div className="mt-3 rounded-md border border-rose-300 bg-rose-50 px-3 py-2 text-sm text-rose-800">
              {sintError}
            </div>
          )}
          <div className="mt-4 flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setShowSint(false)}
              className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm hover:bg-slate-50"
            >
              Cancelar
            </button>
            <button
              type="button"
              onClick={onGenerarSintetico}
              disabled={sintGenerating}
              className="rounded-md bg-violet-700 px-4 py-1.5 text-sm font-medium text-white hover:bg-violet-800 disabled:opacity-50"
            >
              {sintGenerating ? "Generando…" : "Generar caso"}
            </button>
          </div>
        </div>
      )}

      {showCreate && (
        <form
          onSubmit={onCreate}
          className="rounded-lg border-2 border-slate-300 bg-white p-5 shadow-sm"
        >
          <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-700">
            Nuevo caso
          </h2>
          <div className="mt-3 grid gap-3 sm:grid-cols-3">
            <div className="sm:col-span-1">
              <label className="text-xs font-medium uppercase tracking-wider text-slate-600">
                Identificador
              </label>
              <input
                type="text"
                required
                value={newId}
                onChange={(e) => setNewId(e.target.value)}
                placeholder="EXP-2026/0142"
                className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1.5 font-mono text-sm focus:border-indigo-400 focus:outline-none focus:ring-1 focus:ring-indigo-300"
              />
            </div>
            <div className="sm:col-span-1">
              <label className="text-xs font-medium uppercase tracking-wider text-slate-600">
                Materia
              </label>
              <input
                type="text"
                value={newMateria}
                onChange={(e) => setNewMateria(e.target.value)}
                placeholder="mercantil / civil / fiscal …"
                className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm focus:border-indigo-400 focus:outline-none focus:ring-1 focus:ring-indigo-300"
              />
            </div>
            <div className="sm:col-span-3">
              <label className="text-xs font-medium uppercase tracking-wider text-slate-600">
                Descripción
              </label>
              <textarea
                rows={2}
                value={newDesc}
                onChange={(e) => setNewDesc(e.target.value)}
                placeholder="Juicio de origen, partes, etapa procesal…"
                className="mt-1 w-full rounded-md border border-slate-300 p-2 text-sm focus:border-indigo-400 focus:outline-none focus:ring-1 focus:ring-indigo-300"
              />
            </div>
          </div>
          {createError && (
            <div className="mt-3 rounded-md border border-rose-300 bg-rose-50 px-3 py-2 text-sm text-rose-800">
              {createError}
            </div>
          )}
          <div className="mt-4 flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setShowCreate(false)}
              className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm hover:bg-slate-50"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={creating || newId.trim().length === 0}
              className="rounded-md bg-slate-900 px-4 py-1.5 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50"
            >
              {creating ? "Creando…" : "Crear caso"}
            </button>
          </div>
        </form>
      )}

      <div className="flex flex-wrap items-center gap-3 rounded-lg border border-slate-200 bg-white p-3 shadow-sm">
        <input
          type="text"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Buscar por identificador o descripción…"
          className="flex-1 min-w-[240px] rounded-md border border-slate-300 px-3 py-1.5 text-sm focus:border-indigo-400 focus:outline-none focus:ring-1 focus:ring-indigo-300"
        />
        <div className="flex gap-1 rounded-md border border-slate-200 p-0.5 text-xs">
          {(["activos", "archivados", "todos"] as Filtro[]).map((f) => (
            <button
              key={f}
              type="button"
              onClick={() => setFiltro(f)}
              className={`rounded px-3 py-1 capitalize ${
                filtro === f
                  ? "bg-slate-900 text-white"
                  : "text-slate-600 hover:bg-slate-100"
              }`}
            >
              {f}
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
        <div className="rounded-lg border border-dashed border-slate-300 bg-white p-10 text-center">
          <p className="text-sm font-medium text-slate-700">
            {filtro === "archivados"
              ? "Sin casos archivados."
              : "No hay casos todavía."}
          </p>
          <p className="mt-1 text-sm text-slate-500">
            {filtro !== "archivados" && (
              <>Crea el primero con el botón <strong>+ Nuevo caso</strong>.</>
            )}
          </p>
        </div>
      ) : (
        <ul className="space-y-2">
          {items.map((c) => (
            <CasoRow key={c.id} c={c} />
          ))}
        </ul>
      )}

      {!loading && items.length > 0 && (
        <p className="text-center text-xs text-slate-500">
          {items.length} de {total} casos · filtro: {filtro}
        </p>
      )}
    </div>
  );
}

function CasoRow({ c }: { c: CasoListItem }) {
  return (
    <li>
      <Link
        href={`/casos/${c.id}`}
        className="block rounded-lg border border-slate-200 bg-white p-4 shadow-sm transition hover:border-slate-400"
      >
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <code className="font-mono font-semibold text-slate-800">
                {c.identificador}
              </code>
              {c.materia && (
                <span className="rounded bg-slate-100 px-2 py-0.5 text-slate-600">
                  {c.materia}
                </span>
              )}
              {c.archived_at && (
                <span className="rounded border border-slate-300 px-2 py-0.5 text-slate-500">
                  archivado
                </span>
              )}
              <span className="text-slate-500">{c.n_actos} actos</span>
              {c.n_indirectos > 0 && (
                <span className="rounded bg-indigo-100 px-2 py-0.5 text-indigo-700">
                  {c.n_indirectos} indirecto
                </span>
              )}
              {c.n_directos > 0 && (
                <span className="rounded bg-emerald-100 px-2 py-0.5 text-emerald-700">
                  {c.n_directos} directo
                </span>
              )}
              {c.n_prematuros > 0 && (
                <span className="rounded bg-rose-100 px-2 py-0.5 text-rose-700">
                  ⚠ {c.n_prematuros} prematuro
                </span>
              )}
            </div>
            {c.descripcion && (
              <p className="mt-2 line-clamp-2 text-sm text-slate-700">
                {c.descripcion}
              </p>
            )}
            <div className="mt-2 text-[10px] text-slate-400">
              creado {new Date(c.created_at).toLocaleString("es-MX")}
            </div>
          </div>
        </div>
      </Link>
    </li>
  );
}
