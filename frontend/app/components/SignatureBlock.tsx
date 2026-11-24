"use client";

import { useState } from "react";
import { validate } from "../lib/api";
import {
  VEREDICTO_CATEGORIAS,
  labelButtonClass,
  labelMeta,
} from "../lib/labels";
import type {
  ClassificationDetail,
  PrediccionCategoria,
  VeredictoCategoria,
} from "../lib/types";

// Mapping del binario LEGACY (modelos viejos) a la taxonomía de 7. Para
// modelos multiclase la "equivalente" es la propia categoría predicha.
const LEGACY_TO_TAXONOMY: Record<string, VeredictoCategoria> = {
  adjetivo: "en_juicio_imposible",
  sustantivo: "en_juicio_diferida",
};

function equivalentePredicha(cat: PrediccionCategoria): VeredictoCategoria {
  if (cat in LEGACY_TO_TAXONOMY) return LEGACY_TO_TAXONOMY[cat];
  // Si el modelo predijo una categoría de las 8 (sin no_aplica que nunca
  // se predice), el equivalente es la propia categoría.
  return cat as VeredictoCategoria;
}

export function SignatureBlock({
  classification,
  onSigned,
}: {
  classification: ClassificationDetail;
  onSigned?: () => void;
}) {
  const equivalente = equivalentePredicha(classification.categoria);
  // Default de corrección: una categoría diferente a la predicha.
  const defaultCorregida: VeredictoCategoria =
    equivalente === "en_juicio_imposible"
      ? "en_juicio_diferida"
      : "en_juicio_imposible";

  const [veredicto, setVeredicto] = useState<"acepta" | "rechaza">("acepta");
  const [corregida, setCorregida] = useState<VeredictoCategoria>(defaultCorregida);
  const [comentario, setComentario] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const vigente = classification.vigente;
  const yaFirmadoMismoVeredicto =
    vigente !== null &&
    vigente.veredicto === veredicto &&
    (vigente.clasificacion_corregida ?? null) ===
      (veredicto === "rechaza" ? corregida : null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSending(true);
    try {
      await validate(classification.id, {
        veredicto,
        clasificacion_corregida: veredicto === "rechaza" ? corregida : null,
        comentario: comentario.trim() || null,
        supersedes_id: vigente?.id ?? null,
      });
      setComentario("");
      onSigned?.();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSending(false);
    }
  }

  // Para mostrar qué confirma "Acepto" y deshabilitar ese botón en la
  // rejilla de corrección.
  const equivalenteMeta = labelMeta(equivalente);

  return (
    <div className="rounded-lg border border-slate-300 bg-white p-5 shadow-sm">
      <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-700">
        Veredicto del proyectista
      </h3>
      <p className="mt-1 text-xs text-slate-500">
        Su firma HMAC-SHA256 quedará anclada al payload (SHA del acto, modelo,
        veredicto, timestamp). Al guardar, esta validación supersede la
        anterior si existe.
      </p>
      <p className="mt-1 rounded border border-amber-200 bg-amber-50 px-2 py-1 text-[10px] text-amber-800">
        ⚠ El modelo activo aún es binario; tú puedes corregir a cualquiera de
        las <strong>7 categorías</strong> reales. Esas correcciones alimentan
        el corpus para el reentreno multiclase.
      </p>

      <form onSubmit={onSubmit} className="mt-4 space-y-4">
        <fieldset className="grid grid-cols-2 gap-2">
          <label
            className={`cursor-pointer rounded-md border p-3 text-sm ${
              veredicto === "acepta"
                ? "border-indigo-500 bg-indigo-50 ring-2 ring-indigo-200"
                : "border-slate-200 bg-white"
            }`}
          >
            <input
              type="radio"
              name="veredicto"
              value="acepta"
              checked={veredicto === "acepta"}
              onChange={() => setVeredicto("acepta")}
              className="sr-only"
            />
            <div className="font-medium">Acepto la clasificación</div>
            <div className="text-xs text-slate-500">
              El modelo acertó. Confirmo:{" "}
              <strong>{equivalenteMeta.display}</strong>.
            </div>
          </label>
          <label
            className={`cursor-pointer rounded-md border p-3 text-sm ${
              veredicto === "rechaza"
                ? "border-rose-500 bg-rose-50 ring-2 ring-rose-200"
                : "border-slate-200 bg-white"
            }`}
          >
            <input
              type="radio"
              name="veredicto"
              value="rechaza"
              checked={veredicto === "rechaza"}
              onChange={() => setVeredicto("rechaza")}
              className="sr-only"
            />
            <div className="font-medium">Rechazo y corrijo</div>
            <div className="text-xs text-slate-500">
              El modelo se equivocó. Indico la categoría correcta entre las 7.
            </div>
          </label>
        </fieldset>

        {veredicto === "rechaza" && (
          <div>
            <label className="text-xs font-medium uppercase tracking-wider text-slate-600">
              Clasificación correcta
            </label>
            <div className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-3">
              {VEREDICTO_CATEGORIAS.map((cat) => {
                const m = labelMeta(cat);
                const isEquivalente = cat === equivalente;
                const isSelected = corregida === cat;
                return (
                  <button
                    key={cat}
                    type="button"
                    disabled={isEquivalente}
                    onClick={() => setCorregida(cat)}
                    title={
                      isEquivalente
                        ? `Equivale a la predicción del modelo — usa "Acepto"`
                        : m.explicacion
                    }
                    className={`rounded-md border px-3 py-2 text-left text-xs transition ${
                      isSelected && !isEquivalente
                        ? "border-rose-500 bg-rose-50 ring-2 ring-rose-200"
                        : labelButtonClass(m.color) + " bg-white"
                    } ${isEquivalente ? "cursor-not-allowed opacity-40" : ""}`}
                  >
                    <div className="font-semibold leading-tight">{m.display}</div>
                    <div className="mt-0.5 text-[10px] text-slate-500">
                      {m.via === "ninguna" ? m.inmediatez : `${m.via} · ${m.inmediatez}`}
                    </div>
                  </button>
                );
              })}
            </div>
            <p className="mt-2 text-[10px] text-slate-500">
              <strong>{equivalenteMeta.display}</strong> está deshabilitado: equivale
              a la predicción del modelo, en ese caso usa “Acepto”.
            </p>
            {labelMeta(corregida).alerta && (
              <div className="mt-3 rounded-md border-2 border-rose-300 bg-rose-50 px-3 py-2 text-xs text-rose-900">
                <strong>⚠ Alerta:</strong> {labelMeta(corregida).alerta}
              </div>
            )}
          </div>
        )}

        <div>
          <label className="text-xs font-medium uppercase tracking-wider text-slate-600">
            Comentario (opcional)
          </label>
          <textarea
            value={comentario}
            onChange={(e) => setComentario(e.target.value)}
            rows={3}
            maxLength={4000}
            placeholder="Razonamiento jurídico que sustenta el veredicto…"
            className="mt-1 w-full rounded-md border border-slate-300 p-2 text-sm focus:border-indigo-400 focus:outline-none focus:ring-1 focus:ring-indigo-300"
          />
        </div>

        {vigente && (
          <div className="rounded-md bg-slate-50 px-3 py-2 text-xs text-slate-600">
            Este veredicto supersede el del{" "}
            <strong>
              {new Date(vigente.validated_at).toLocaleString("es-MX")}
            </strong>{" "}
            ({vigente.veredicto}
            {vigente.clasificacion_corregida
              ? ` → ${labelMeta(vigente.clasificacion_corregida).short}`
              : ""}
            ).
          </div>
        )}

        {error && (
          <div className="rounded-md border border-rose-300 bg-rose-50 px-3 py-2 text-sm text-rose-800">
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={sending || yaFirmadoMismoVeredicto}
          className="w-full rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {sending
            ? "Firmando…"
            : yaFirmadoMismoVeredicto
            ? "Veredicto vigente idéntico — sin cambios"
            : "Firmar veredicto"}
        </button>
      </form>
    </div>
  );
}
