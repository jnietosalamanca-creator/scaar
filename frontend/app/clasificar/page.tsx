"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { classify, getCaso } from "../lib/api";
import { useRequireAuth } from "../lib/useRequireAuth";
import type { CasoDetail, ClassifyResponse } from "../lib/types";
import { BannerModeloBinario } from "../components/BannerModeloBinario";
import { DetectorDuplicados } from "../components/DetectorDuplicados";
import { DoctrinaAncla } from "../components/DoctrinaAncla";
import { MarcoNormativo } from "../components/MarcoNormativo";
import { PrediccionCard } from "../components/PrediccionCard";
import { ReasoningLog } from "../components/ReasoningLog";

const EJEMPLOS = [
  {
    label: "Negativa de pericial (adj. esperado)",
    texto:
      "El juez negó la admisión de la prueba pericial ofrecida en tiempo y forma, lo que afecta las defensas del quejoso y trasciende al resultado del fallo.",
  },
  {
    label: "Sentencia definitiva (sus. esperado)",
    texto:
      "La sentencia definitiva que condena al pago resuelve el fondo del asunto y debe impugnarse vía amparo directo, donde se hacen valer las violaciones procesales de manera diferida.",
  },
  {
    label: "Caso ambiguo (revisión humana)",
    texto: "La resolución del juez admite la demanda en sus términos.",
  },
];

export default function ClasificarPage() {
  const { ready } = useRequireAuth();
  const params = useSearchParams();
  const caseIdQuery = params.get("case");
  const [texto, setTexto] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ClassifyResponse | null>(null);
  const [caseInfo, setCaseInfo] = useState<CasoDetail | null>(null);

  useEffect(() => {
    if (!ready || !caseIdQuery) return;
    let alive = true;
    getCaso(caseIdQuery)
      .then((c) => alive && setCaseInfo(c))
      .catch(() => {
        // si el caso no existe, simplemente no mostramos el banner
      });
    return () => {
      alive = false;
    };
  }, [ready, caseIdQuery]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    setResult(null);
    try {
      const r = await classify(texto, caseIdQuery);
      setResult(r);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <BannerModeloBinario />
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">
          Clasificar acto reclamado
        </h1>
        <p className="mt-1 text-sm text-slate-600">
          El sistema produce un log inmutable. Puedes firmar tu veredicto en la
          pantalla de detalle de la clasificación.
        </p>
      </header>

      {caseInfo && (
        <div className="rounded-md border-2 border-indigo-200 bg-indigo-50/40 px-4 py-2 text-sm text-indigo-900">
          Este acto se asociará al caso{" "}
          <Link href={`/casos/${caseInfo.id}`} className="font-mono font-semibold underline">
            {caseInfo.identificador}
          </Link>
          {caseInfo.materia && (
            <span className="ml-2 rounded bg-white px-1.5 py-0.5 text-[10px]">
              {caseInfo.materia}
            </span>
          )}
        </div>
      )}

      <form
        onSubmit={onSubmit}
        className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm"
      >
        <label className="text-xs font-medium uppercase tracking-wider text-slate-600">
          Texto del acto reclamado
        </label>
        <textarea
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
          rows={5}
          minLength={10}
          maxLength={20000}
          required
          placeholder="Describe íntegramente el acto reclamado…"
          className="mt-1 w-full rounded-md border border-slate-300 p-3 text-sm focus:border-indigo-400 focus:outline-none focus:ring-1 focus:ring-indigo-300"
        />
        <div className="mt-3 flex flex-wrap items-center gap-2">
          {EJEMPLOS.map((e) => (
            <button
              key={e.label}
              type="button"
              onClick={() => setTexto(e.texto)}
              className="rounded border border-slate-200 bg-slate-50 px-2 py-1 text-xs text-slate-700 hover:bg-slate-100"
            >
              {e.label}
            </button>
          ))}
        </div>
        {error && (
          <div className="mt-3 rounded-md border border-rose-300 bg-rose-50 px-3 py-2 text-sm text-rose-800">
            {error}
          </div>
        )}
        <div className="mt-4 flex justify-end">
          <button
            type="submit"
            disabled={loading || texto.trim().length < 10}
            className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? "Clasificando…" : "Clasificar"}
          </button>
        </div>
      </form>

      <DetectorDuplicados texto={texto} />

      {result && (
        <section className="space-y-4">
          <PrediccionCard
            categoria={result.categoria}
            via={result.via}
            inmediatez={result.inmediatez}
            alerta={result.alerta}
            prob_categoria={result.prob_categoria}
            prob_por_clase={result.prob_por_clase}
            requiere_revision_humana={result.requiere_revision_humana}
            model_version={result.model_version}
          />
          <ReasoningLog
            features={result.top_features}
            analogas={result.top_analogas}
            acto_sha256={result.acto_sha256}
          />
          <MarcoNormativo categoria={result.categoria} variant="compacto" />
          <DoctrinaAncla variant="compacto" titulo="Criterio jurídico aplicable" />
          <div className="flex justify-end gap-2">
            {caseInfo && (
              <Link
                href={`/casos/${caseInfo.id}`}
                className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
              >
                ← Volver al caso
              </Link>
            )}
            <Link
              href={`/clasificaciones/${result.classification_id}`}
              className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              Firmar veredicto del proyectista →
            </Link>
          </div>
        </section>
      )}
    </div>
  );
}
