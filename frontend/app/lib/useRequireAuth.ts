"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { isLoggedIn } from "./auth";

/**
 * Hook que protege páginas — si no hay token, redirige a /login.
 * Devuelve `ready=true` una vez que la verificación pasó (renderizar contenido).
 */
export function useRequireAuth(): { ready: boolean } {
  const router = useRouter();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!isLoggedIn()) {
      router.replace("/login");
      return;
    }
    setReady(true);
  }, [router]);

  return { ready };
}
