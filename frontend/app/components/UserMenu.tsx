"use client";

import { useEffect, useState } from "react";
import { getUser, logout, type AuthUser } from "../lib/auth";

export function UserMenu() {
  const [user, setUser] = useState<AuthUser | null>(null);

  useEffect(() => {
    setUser(getUser());
  }, []);

  function onLogout() {
    logout();
    // Hard nav: limpia cualquier estado React que dependa del usuario.
    window.location.href = "/login";
  }

  if (!user) {
    return null;
  }

  return (
    <div className="flex items-center gap-3 text-xs">
      <div className="text-right">
        <div className="font-medium text-slate-900">{user.nombre_completo}</div>
        <div className="font-mono text-[10px] text-slate-500">
          {user.email} · {user.rol}
        </div>
      </div>
      <button
        type="button"
        onClick={onLogout}
        className="rounded border border-slate-300 bg-white px-2 py-1 text-slate-700 hover:bg-slate-50"
      >
        Salir
      </button>
    </div>
  );
}
