"use client";

import { useEffect, useState, use } from "react";
import Link from "next/link";
import { getClassification } from "../../lib/api";
import { useRequireAuth } from "../../lib/useRequireAuth";
import type { ClassificationDetail } from "../../lib/types";
import { DoctrinaAncla } from "../../components/DoctrinaAncla";
import { HistoriaValidaciones } from "../../components/HistoriaValidaciones";
import { MarcoNormativo } from "../../components/MarcoNormativo";
import { PrediccionCard } from "../../components/PrediccionCard";
import { ReasoningLog } from "../../components/ReasoningLog";
import { SignatureBlock } from "../../components/SignatureBlock";

export default function ClasificacionPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { ready } = useRequireAuth();
  const [data, setData] = useState<ClassificationDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    if (!ready) return;
    let alive = true;
    getClassification(id)
      .then((d) => alive && setData(d))
      .catch((e: Error) => alive && setError(e.message));
    return () => {
      alive = false;
    };
  }, [id, tick, ready]);

  if (!ready) return null;

  if (error) {
    return (
      <div className="rounded-md border border-rose-300 bg-rose-50 px-4 py-3 text-sm text-rose-800">
        {error}
      </div>
    );
  }
  if (!data) {
    return <p className="text-sm text-slate-500">Cargando…</p>;
  }

  return (
    <div className="space-y-6">
      <header className="flex items-start justify-between gap-4">
        <div>
          <Link
            href="/clasificar"
            className="text-xs text-slate-500 hover:text-slate-900"
          >
            ← Nueva clasificación
          </Link>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight">
            Clasificación #{data.id.slice(0, 8)}
          </h1>
          <p className="mt-1 text-xs text-slate-500">
            Capturada por {data.created_by_email} ·{" "}
            {new Date(data.created_at).toLocaleString("es-MX")}
          </p>
        </div>
      </header>

      <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-700">
          Acto reclamado
        </h3>
        <p className="mt-2 whitespace-pre-wrap text-sm text-slate-800">
          {data.acto_reclamado}
        </p>
      </div>

      <PrediccionCard
        categoria={data.categoria}
        via={data.via}
        inmediatez={data.inmediatez}
        alerta={data.alerta}
        prob_categoria={data.prob_categoria ?? 0}
        prob_por_clase={data.prob_por_clase ?? {}}
        requiere_revision_humana={data.requiere_revision_humana}
        model_version={data.model_version}
      />

      <ReasoningLog
        features={data.top_features}
        analogas={data.top_analogas}
        acto_sha256={data.acto_sha256}
      />

      <div className="grid gap-4 lg:grid-cols-2">
        <HistoriaValidaciones historia={data.historia_validaciones} />
        <SignatureBlock
          classification={data}
          onSigned={() => setTick((t) => t + 1)}
        />
      </div>

      <MarcoNormativo categoria={data.categoria} variant="compacto" />
      <DoctrinaAncla variant="compacto" titulo="Doctrina aplicable al firmar" />
    </div>
  );
}
