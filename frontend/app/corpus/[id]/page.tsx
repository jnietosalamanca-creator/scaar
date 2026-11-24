"use client";

import { useEffect, useState, use } from "react";
import Link from "next/link";
import {
  cambiarTipoJurisprudencial,
  desmarcarDoctrina,
  getTesis,
  labelTesis,
  marcarDoctrina,
} from "../../lib/api";
import {
  TIPOS_JUR_DISPONIBLES,
  TIPO_JUR_META,
  TODAS_LAS_CATEGORIAS,
  labelBadgeClass,
  labelButtonClass,
  labelMeta,
} from "../../lib/labels";
import { useRequireAuth } from "../../lib/useRequireAuth";
import type {
  EtiquetaTesis,
  TesisDetail,
  TipoJurisprudencial,
} from "../../lib/types";

export default function TesisDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { ready } = useRequireAuth();
  const [tesis, setTesis] = useState<TesisDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!ready) return;
    let alive = true;
    getTesis(id)
      .then((t) => alive && setTesis(t))
      .catch((e: Error) => alive && setError(e.message));
    return () => {
      alive = false;
    };
  }, [ready, id]);

  async function relabel(et: EtiquetaTesis) {
    if (!tesis) return;
    setSaving(true);
    setError(null);
    try {
      const updated = await labelTesis(tesis.id, et);
      setTesis(updated);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  }

  async function setTipoJur(tipo: TipoJurisprudencial, notas?: string | null) {
    if (!tesis) return;
    setSaving(true);
    setError(null);
    try {
      const updated = await cambiarTipoJurisprudencial(tesis.id, tipo, notas);
      setTesis(updated);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  }

  async function toggleDoctrina() {
    if (!tesis) return;
    setSaving(true);
    setError(null);
    try {
      const updated = tesis.es_doctrina_canonica
        ? await desmarcarDoctrina(tesis.id)
        : await marcarDoctrina(tesis.id);
      setTesis(updated);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  }

  if (!ready) return null;
  if (error) {
    return (
      <div className="rounded-md border border-rose-300 bg-rose-50 px-4 py-3 text-sm text-rose-800">
        {error}
      </div>
    );
  }
  if (!tesis) return <p className="text-sm text-slate-500">Cargando…</p>;

  return (
    <div className="space-y-6">
      <Link href="/corpus" className="text-xs text-slate-500 hover:text-slate-900">
        ← Corpus
      </Link>

      <article className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
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
        <h1 className="mt-3 text-xl font-semibold leading-snug text-slate-900">
          {tesis.rubro}
        </h1>
        <p className="mt-4 whitespace-pre-wrap text-sm leading-relaxed text-slate-800">
          {tesis.texto}
        </p>
        {tesis.fecha_publ && (
          <div className="mt-4 text-[11px] text-slate-400">
            Publicación: {tesis.fecha_publ}
          </div>
        )}
      </article>

      <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <div className="text-xs font-semibold uppercase tracking-wider text-slate-700">
          Etiqueta actual
        </div>
        <div className="mt-2 flex items-center gap-3">
          <span
            className={`rounded px-3 py-1 text-sm font-medium ${labelBadgeClass(
              labelMeta(tesis.etiqueta).color
            )}`}
            title={labelMeta(tesis.etiqueta).via}
          >
            {labelMeta(tesis.etiqueta).display}
          </span>
          {tesis.etiquetada_por_email && (
            <span className="text-xs text-slate-500">
              por {tesis.etiquetada_por_email} ·{" "}
              {tesis.etiquetada_at
                ? new Date(tesis.etiquetada_at).toLocaleString("es-MX")
                : ""}
            </span>
          )}
        </div>
        <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-3">
          {TODAS_LAS_CATEGORIAS.map((c) => {
            const m = labelMeta(c);
            return (
              <button
                key={c}
                type="button"
                disabled={saving}
                onClick={() => relabel(c)}
                title={m.explicacion}
                className={`rounded-md border px-3 py-1.5 text-xs ${labelButtonClass(
                  m.color
                )} disabled:opacity-50`}
              >
                {m.display}
              </button>
            );
          })}
        </div>
        <p className="mt-2 text-[10px] text-slate-500">
          Cambiar la etiqueta sobreescribe la anterior y registra al usuario actual como
          etiquetador. No hay historial — esto es opinable, decide cuando quieras
          agregar auditoría como en classifications.
        </p>
      </div>

      <TipoJurisprudencialBlock
        tesis={tesis}
        saving={saving}
        onChange={setTipoJur}
      />

      <div
        className={`rounded-lg border-2 p-5 shadow-sm ${
          tesis.es_doctrina_canonica
            ? "border-amber-400 bg-amber-50"
            : "border-slate-200 bg-white"
        }`}
      >
        <div className="text-xs font-semibold uppercase tracking-wider text-slate-700">
          ⚖ Doctrina canónica
        </div>
        <p className="mt-1 text-xs text-slate-600">
          {tesis.es_doctrina_canonica ? (
            <>
              Esta tesis está marcada como <strong>doctrina aplicable</strong> —
              aparece en <code>&lt;DoctrinaAncla&gt;</code> en /clasificar,
              /corpus/etiquetar y /clasificaciones/[id]. NO entra al training
              del modelo.
            </>
          ) : (
            <>
              Marcar como doctrina canónica significa: esta tesis define el
              criterio jurídico aplicable, se muestra siempre como referencia
              en la UI y NO se usa como ejemplo de entrenamiento. Su etiqueta
              de entrenamiento se borra al marcar.
            </>
          )}
        </p>
        <button
          type="button"
          disabled={saving}
          onClick={toggleDoctrina}
          className={`mt-3 rounded-md px-3 py-1.5 text-sm font-medium disabled:opacity-50 ${
            tesis.es_doctrina_canonica
              ? "border border-slate-300 bg-white text-slate-700 hover:bg-slate-50"
              : "bg-amber-600 text-white hover:bg-amber-700"
          }`}
        >
          {tesis.es_doctrina_canonica
            ? "Desmarcar doctrina canónica"
            : "Marcar como doctrina canónica"}
        </button>
        <p className="mt-2 text-[10px] text-slate-500">
          Solo socios y admins pueden cambiar este flag.
        </p>
      </div>
    </div>
  );
}

function TipoJurisprudencialBlock({
  tesis,
  saving,
  onChange,
}: {
  tesis: TesisDetail;
  saving: boolean;
  onChange: (
    t: TipoJurisprudencial,
    notas?: string | null
  ) => void | Promise<void>;
}) {
  const [notas, setNotas] = useState(tesis.notas_metodologicas ?? "");
  const actual = tesis.tipo_jurisprudencial;
  const actualMeta = TIPO_JUR_META[actual];
  const noEsRegla = actual !== "regla";

  return (
    <div
      className={`rounded-lg border-2 p-5 shadow-sm ${
        noEsRegla ? "border-rose-300 bg-rose-50" : "border-slate-200 bg-white"
      }`}
    >
      <div className="flex items-center gap-2">
        <div className="text-xs font-semibold uppercase tracking-wider text-slate-700">
          📐 Rol jurisprudencial
        </div>
        <span
          className={`rounded px-2 py-0.5 text-xs font-medium ${
            actualMeta.entra_training
              ? "bg-emerald-100 text-emerald-800"
              : "bg-rose-100 text-rose-800"
          }`}
        >
          {actualMeta.display}
        </span>
        <span className="text-[10px] text-slate-500">
          {actualMeta.entra_training ? "Sí entra al training" : "NO entra al training"}
        </span>
      </div>
      <p className="mt-2 text-xs text-slate-600">
        Define cómo esta tesis influye en el aprendizaje del modelo. Solo las
        marcadas como <strong>regla</strong> entran al training; las excepciones
        / derogadas / aisladas dudosas se preservan pero no contaminan el
        clasificador con señal contradictoria.
      </p>
      <div className="mt-3 flex flex-wrap gap-2">
        {TIPOS_JUR_DISPONIBLES.map((t) => {
          const m = TIPO_JUR_META[t];
          const isActual = t === actual;
          return (
            <button
              key={t}
              type="button"
              disabled={saving || isActual}
              onClick={() => onChange(t, notas.trim() || null)}
              title={m.descripcion}
              className={`rounded-md border px-3 py-1.5 text-xs ${
                isActual
                  ? "border-slate-900 bg-slate-900 text-white"
                  : "border-slate-300 bg-white text-slate-700 hover:bg-slate-50"
              } disabled:opacity-50`}
            >
              {m.display}
            </button>
          );
        })}
      </div>
      <div className="mt-3">
        <label className="text-[10px] font-medium uppercase tracking-wider text-slate-600">
          Notas metodológicas (opcional)
        </label>
        <textarea
          value={notas}
          onChange={(e) => setNotas(e.target.value)}
          rows={2}
          placeholder="Ej: 'La regla post-IV.2o.C. J/2 sería diferida, pero esta tesis sostiene imposible por la afectación material que ocasiona en el caso concreto...'"
          className="mt-1 w-full rounded-md border border-slate-300 p-2 text-xs focus:border-rose-400 focus:outline-none focus:ring-1 focus:ring-rose-300"
        />
        <button
          type="button"
          disabled={saving || notas === (tesis.notas_metodologicas ?? "")}
          onClick={() => onChange(actual, notas.trim() || null)}
          className="mt-2 rounded-md border border-slate-300 bg-white px-3 py-1 text-xs hover:bg-slate-50 disabled:opacity-50"
        >
          Guardar notas
        </button>
      </div>
    </div>
  );
}
