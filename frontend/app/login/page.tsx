"use client";

import { useState } from "react";
import { useSearchParams } from "next/navigation";
import { loginRequest } from "../lib/api";

export default function LoginPage() {
  const params = useSearchParams();
  const next = params.get("next") ?? "/clasificar";

  const [email, setEmail] = useState("proyectista@scaar.local");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await loginRequest(email, password);
      // Hard nav: garantiza que el layout (UserMenu) se monte fresco con el
      // localStorage recién poblado, sin condiciones de carrera de hidratación.
      window.location.href = next;
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto mt-10 max-w-md">
      <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <h1 className="text-xl font-semibold tracking-tight">Iniciar sesión</h1>
        <p className="mt-1 text-sm text-slate-600">
          SCAAR — Sistema de Clasificación de Actos Reclamados.
        </p>

        <form onSubmit={onSubmit} className="mt-6 space-y-4">
          <div>
            <label className="text-xs font-medium uppercase tracking-wider text-slate-600">
              Correo
            </label>
            <input
              type="email"
              autoComplete="username"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-indigo-400 focus:outline-none focus:ring-1 focus:ring-indigo-300"
            />
          </div>
          <div>
            <label className="text-xs font-medium uppercase tracking-wider text-slate-600">
              Contraseña
            </label>
            <input
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-indigo-400 focus:outline-none focus:ring-1 focus:ring-indigo-300"
            />
          </div>

          {error && (
            <div className="rounded-md border border-rose-300 bg-rose-50 px-3 py-2 text-sm text-rose-800">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading || password.length === 0}
            className="w-full rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? "Entrando…" : "Entrar"}
          </button>
        </form>

        <details className="mt-6 text-xs text-slate-500">
          <summary className="cursor-pointer">Credenciales de prueba</summary>
          <ul className="mt-2 space-y-1 font-mono">
            <li>proyectista@scaar.local · proy_change_me</li>
            <li>system@scaar.local · system_change_me</li>
          </ul>
        </details>
      </div>
    </div>
  );
}
