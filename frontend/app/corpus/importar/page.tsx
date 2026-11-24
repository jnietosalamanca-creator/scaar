"use client";

import { useState } from "react";
import Link from "next/link";
import { importTesis } from "../../lib/api";
import { useRequireAuth } from "../../lib/useRequireAuth";
import type { ImportTesisItem, ImportTesisResponse } from "../../lib/types";

const EJEMPLO = JSON.stringify(
  {
    registro_sjf: "2024999001",
    epoca: "Undécima",
    instancia: "Tribunales Colegiados de Circuito",
    tipo: "aislada",
    rubro: "RUBRO DE LA TESIS EN MAYÚSCULAS.",
    texto:
      "Texto íntegro de la tesis. Aquí va la fundamentación jurídica completa que será procesada por el modelo TF-IDF.",
    fecha_publ: "2024-09-15",
  },
  null,
  2
);

export default function ImportarPage() {
  const { ready } = useRequireAuth();
  const [fuente, setFuente] = useState("import_jsonl");
  const [raw, setRaw] = useState("");
  const [parseError, setParseError] = useState<string | null>(null);
  const [parsed, setParsed] = useState<ImportTesisItem[] | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);
  const [result, setResult] = useState<ImportTesisResponse | null>(null);

  function tryParse() {
    setParseError(null);
    setParsed(null);
    setResult(null);
    const lines = raw.split("\n").filter((l) => l.trim().length > 0);
    if (lines.length === 0) {
      setParseError("Pega al menos una línea JSON.");
      return;
    }
    const items: ImportTesisItem[] = [];
    for (let i = 0; i < lines.length; i++) {
      try {
        const obj = JSON.parse(lines[i]);
        if (!obj.registro_sjf || !obj.texto || !obj.rubro) {
          throw new Error("falta registro_sjf, rubro o texto");
        }
        items.push(obj as ImportTesisItem);
      } catch (e) {
        setParseError(`Línea ${i + 1}: ${(e as Error).message}`);
        return;
      }
    }
    setParsed(items);
  }

  async function submit() {
    if (!parsed) return;
    setSubmitting(true);
    setServerError(null);
    try {
      const r = await importTesis(fuente, parsed);
      setResult(r);
      setRaw("");
      setParsed(null);
    } catch (e) {
      setServerError((e as Error).message);
    } finally {
      setSubmitting(false);
    }
  }

  if (!ready) return null;

  return (
    <div className="space-y-6">
      <header>
        <Link href="/corpus" className="text-xs text-slate-500 hover:text-slate-900">
          ← Corpus
        </Link>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight">Importar tesis</h1>
        <p className="mt-1 text-sm text-slate-600">
          Pega un <strong>JSONL</strong> (un objeto por línea) con los campos:{" "}
          <code className="font-mono">registro_sjf, epoca, instancia, tipo, rubro, texto</code>
          {" "}(y opcional <code className="font-mono">fecha_publ</code>,{" "}
          <code className="font-mono">etiqueta</code>). Las tesis se importan{" "}
          <strong>sin etiqueta</strong> por defecto.
        </p>
      </header>

      <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <div className="grid gap-3 sm:grid-cols-3">
          <div className="sm:col-span-2">
            <label className="text-xs font-medium uppercase tracking-wider text-slate-600">
              JSONL
            </label>
            <textarea
              value={raw}
              onChange={(e) => setRaw(e.target.value)}
              rows={14}
              placeholder={EJEMPLO}
              className="mt-1 w-full rounded-md border border-slate-300 p-3 font-mono text-xs focus:border-indigo-400 focus:outline-none focus:ring-1 focus:ring-indigo-300"
            />
          </div>
          <div className="space-y-3">
            <div>
              <label className="text-xs font-medium uppercase tracking-wider text-slate-600">
                Fuente
              </label>
              <input
                type="text"
                value={fuente}
                onChange={(e) => setFuente(e.target.value)}
                className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1 font-mono text-xs"
              />
              <p className="mt-1 text-[10px] text-slate-500">
                Etiqueta de origen (ej. <code>sjf_scraping</code>, <code>manual</code>).
              </p>
            </div>
            <button
              type="button"
              onClick={tryParse}
              disabled={raw.trim().length === 0}
              className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm hover:bg-slate-50 disabled:opacity-50"
            >
              Validar JSONL
            </button>
            {parsed && (
              <button
                type="button"
                onClick={submit}
                disabled={submitting}
                className="w-full rounded-md bg-slate-900 px-3 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50"
              >
                {submitting ? "Importando…" : `Importar ${parsed.length} tesis`}
              </button>
            )}
          </div>
        </div>
        {parseError && (
          <div className="mt-3 rounded-md border border-rose-300 bg-rose-50 px-3 py-2 text-sm text-rose-800">
            {parseError}
          </div>
        )}
        {parsed && !result && (
          <div className="mt-3 rounded-md border border-emerald-300 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
            JSONL válido — {parsed.length} tesis listas para importar.
          </div>
        )}
        {serverError && (
          <div className="mt-3 rounded-md border border-rose-300 bg-rose-50 px-3 py-2 text-sm text-rose-800">
            {serverError}
          </div>
        )}
        {result && (
          <div className="mt-3 rounded-md border border-slate-200 bg-slate-50 p-3 text-sm">
            <p className="font-medium text-slate-800">Importación completada</p>
            <ul className="mt-2 space-y-0.5 text-xs text-slate-700">
              <li>
                Insertadas: <strong>{result.insertadas}</strong>
              </li>
              <li>
                Duplicadas (ya existían): <strong>{result.duplicadas}</strong>
              </li>
              {result.errores.length > 0 && (
                <li className="text-rose-700">
                  Errores: {result.errores.length}
                  <ul className="ml-4 mt-1 list-disc">
                    {result.errores.map((e, i) => (
                      <li key={i}>{e}</li>
                    ))}
                  </ul>
                </li>
              )}
            </ul>
            <div className="mt-3 flex gap-2">
              <Link
                href="/corpus"
                className="rounded border border-slate-300 px-3 py-1 text-xs hover:bg-white"
              >
                Ver corpus
              </Link>
              <Link
                href="/corpus/etiquetar"
                className="rounded bg-slate-900 px-3 py-1 text-xs text-white hover:bg-slate-800"
              >
                Etiquetar
              </Link>
            </div>
          </div>
        )}
      </div>

      <details className="rounded border border-slate-200 bg-white p-3 text-xs">
        <summary className="cursor-pointer font-medium">Formato de ejemplo</summary>
        <pre className="mt-2 overflow-auto rounded bg-slate-900 p-3 text-[11px] text-slate-100">
{EJEMPLO}
        </pre>
      </details>
    </div>
  );
}
