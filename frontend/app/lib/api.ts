import { getToken, logout, setToken, setUser, type AuthUser } from "./auth";
import type {
  CasoCreate,
  CasoDetail,
  CasoListQuery,
  CasoListResponse,
  CasoSinteticoRequest,
  CasoUpdate,
  ClassificationDetail,
  ClassificationListResponse,
  ClassifyResponse,
  DuplicadosResponse,
  EjecutoriaImportItem,
  EjecutoriasImportResponse,
  ModeloStats,
  ModelVersionListItem,
  CorpusStats,
  EtiquetaTesis,
  ImportTesisItem,
  ImportTesisResponse,
  TesisAuditoriaItem,
  TesisInciertaItem,
  ListQuery,
  TesisDetail,
  TesisListQuery,
  TesisListResponse,
  TipoJurisprudencial,
  VeredictoCategoria,
} from "./types";

const BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export class AuthError extends Error {}

async function call<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getToken();
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init.headers ?? {}),
    },
    cache: "no-store",
  });

  if (res.status === 401) {
    logout();
    if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
      window.location.href = "/login";
    }
    throw new AuthError("Sesión inválida o expirada.");
  }

  if (!res.ok) {
    const text = await res.text();
    let detail = text;
    try {
      detail = JSON.parse(text).detail ?? text;
    } catch {
      // body wasn't JSON
    }
    throw new Error(`HTTP ${res.status}: ${detail}`);
  }
  return res.json() as Promise<T>;
}

// --- Auth ---
type LoginResponse = {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: AuthUser;
};

export async function loginRequest(email: string, password: string): Promise<AuthUser> {
  // Llamada directa (sin Bearer) — resultado se persiste si OK.
  const res = await fetch(`${BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
    cache: "no-store",
  });
  if (!res.ok) {
    let msg = "Error de login.";
    try {
      const body = (await res.json()) as { detail?: string };
      if (body.detail) msg = body.detail;
    } catch {
      // no JSON body
    }
    throw new Error(msg);
  }
  const data = (await res.json()) as LoginResponse;
  setToken(data.access_token);
  setUser(data.user);
  return data.user;
}

// --- Classify ---
export function classify(
  acto_reclamado: string,
  case_id?: string | null
): Promise<ClassifyResponse> {
  return call<ClassifyResponse>("/classify", {
    method: "POST",
    body: JSON.stringify({ acto_reclamado, case_id: case_id ?? null }),
  });
}

export function getClassification(id: string): Promise<ClassificationDetail> {
  return call<ClassificationDetail>(`/classifications/${id}`);
}

export function getDuplicados(texto: string): Promise<DuplicadosResponse> {
  const qs = new URLSearchParams({ texto });
  return call<DuplicadosResponse>(`/classifications/duplicados?${qs.toString()}`);
}

export function listClassifications(
  query: ListQuery = {}
): Promise<ClassificationListResponse> {
  const qs = new URLSearchParams();
  if (query.sha) qs.set("sha", query.sha);
  if (query.q) qs.set("q", query.q);
  if (query.categoria) qs.set("categoria", query.categoria);
  if (query.estado) qs.set("estado", query.estado);
  if (query.limit !== undefined) qs.set("limit", String(query.limit));
  if (query.offset !== undefined) qs.set("offset", String(query.offset));
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  return call<ClassificationListResponse>(`/classifications${suffix}`);
}

export type ValidateBody = {
  veredicto: "acepta" | "rechaza";
  clasificacion_corregida?: VeredictoCategoria | null;
  comentario?: string | null;
  supersedes_id?: string | null;
};

export function validate(classificationId: string, body: ValidateBody) {
  return call<{ id: string; firma_sha256: string }>(
    `/classifications/${classificationId}/validate`,
    { method: "POST", body: JSON.stringify(body) }
  );
}

// --- Corpus / Tesis ---
export function listTesis(query: TesisListQuery = {}): Promise<TesisListResponse> {
  const qs = new URLSearchParams();
  if (query.estado) qs.set("estado", query.estado);
  if (query.fuente) qs.set("fuente", query.fuente);
  if (query.q) qs.set("q", query.q);
  if (query.limit !== undefined) qs.set("limit", String(query.limit));
  if (query.offset !== undefined) qs.set("offset", String(query.offset));
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  return call<TesisListResponse>(`/tesis${suffix}`);
}

export function getCorpusStats(): Promise<CorpusStats> {
  return call<CorpusStats>("/tesis/stats");
}

export function getSiguientePendiente(
  fuente?: string | null
): Promise<TesisDetail | null> {
  const qs = fuente ? `?fuente=${encodeURIComponent(fuente)}` : "";
  return call<TesisDetail | null>(`/tesis/siguiente-pendiente${qs}`);
}

export function listTesisInciertas(
  limit = 20,
  fuente?: string | null
): Promise<TesisInciertaItem[]> {
  const qs = new URLSearchParams({ limit: String(limit) });
  if (fuente) qs.set("fuente", fuente);
  return call<TesisInciertaItem[]>(`/tesis/inciertas?${qs.toString()}`);
}

export function listAuditoriaDiscrepancias(
  limit = 30,
  solo_discrepantes = true
): Promise<TesisAuditoriaItem[]> {
  const qs = new URLSearchParams({
    limit: String(limit),
    solo_discrepantes: String(solo_discrepantes),
  });
  return call<TesisAuditoriaItem[]>(`/tesis/auditoria-discrepancias?${qs.toString()}`);
}

export function getTesis(id: string): Promise<TesisDetail> {
  return call<TesisDetail>(`/tesis/${id}`);
}

export function labelTesis(
  id: string,
  etiqueta: EtiquetaTesis,
  opts: { tipo_jurisprudencial?: TipoJurisprudencial; notas_metodologicas?: string | null } = {}
): Promise<TesisDetail> {
  return call<TesisDetail>(`/tesis/${id}/label`, {
    method: "POST",
    body: JSON.stringify({ etiqueta, ...opts }),
  });
}

export function cambiarTipoJurisprudencial(
  id: string,
  tipo_jurisprudencial: TipoJurisprudencial,
  notas_metodologicas?: string | null
): Promise<TesisDetail> {
  return call<TesisDetail>(`/tesis/${id}/tipo-jurisprudencial`, {
    method: "POST",
    body: JSON.stringify({ tipo_jurisprudencial, notas_metodologicas }),
  });
}

export function importTesis(
  fuente: string,
  items: ImportTesisItem[]
): Promise<ImportTesisResponse> {
  return call<ImportTesisResponse>("/tesis/import", {
    method: "POST",
    body: JSON.stringify({ fuente, items }),
  });
}

export function listDoctrinasCanonicas(): Promise<TesisDetail[]> {
  return call<TesisDetail[]>("/tesis/doctrinas-canonicas");
}

// --- Modelo ---
export function getModeloStats(): Promise<ModeloStats> {
  return call<ModeloStats>("/modelo/stats");
}

export function listModelVersiones(): Promise<ModelVersionListItem[]> {
  return call<ModelVersionListItem[]>("/modelo/versiones");
}

export function reentrenarModelo(
  version: string,
  user_email?: string
): Promise<{ status: string; version: string; log_path: string; nota: string }> {
  return call("/modelo/reentrenar", {
    method: "POST",
    body: JSON.stringify({ version, user_email: user_email ?? "system@scaar.local" }),
  });
}

export function marcarDoctrina(tesisId: string): Promise<TesisDetail> {
  return call<TesisDetail>(`/tesis/${tesisId}/marcar-doctrina`, { method: "POST" });
}

export function desmarcarDoctrina(tesisId: string): Promise<TesisDetail> {
  return call<TesisDetail>(`/tesis/${tesisId}/desmarcar-doctrina`, { method: "POST" });
}

// --- Casos ---
export function listCasos(query: CasoListQuery = {}): Promise<CasoListResponse> {
  const qs = new URLSearchParams();
  if (query.archived) qs.set("archived", query.archived);
  if (query.q) qs.set("q", query.q);
  if (query.limit !== undefined) qs.set("limit", String(query.limit));
  if (query.offset !== undefined) qs.set("offset", String(query.offset));
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  return call<CasoListResponse>(`/casos${suffix}`);
}

export function getCaso(id: string): Promise<CasoDetail> {
  return call<CasoDetail>(`/casos/${id}`);
}

export function createCaso(body: CasoCreate): Promise<CasoDetail> {
  return call<CasoDetail>("/casos", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function updateCaso(id: string, body: CasoUpdate): Promise<CasoDetail> {
  return call<CasoDetail>(`/casos/${id}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export function generarCasoSintetico(
  body: CasoSinteticoRequest = {}
): Promise<CasoDetail> {
  return call<CasoDetail>("/casos/sintetico-aleatorio", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

/**
 * Importa una lista de ejecutorias del SJF como casos.
 *
 * El JSONL viene del script `python -m app.scripts.fetch_ejecutorias` y cada
 * línea corresponde a una sentencia de amparo (no a una tesis). El backend
 * crea un `Caso` por entrada con `materia='sjf_ejecutoria'` e
 * `identificador='SJF-EXEC-{ius}'`. Es idempotente: re-importar suma a
 * `duplicados`, no a `creados`.
 */
export function importEjecutorias(
  items: EjecutoriaImportItem[]
): Promise<EjecutoriasImportResponse> {
  return call<EjecutoriasImportResponse>("/casos/import-ejecutorias", {
    method: "POST",
    body: JSON.stringify({ items }),
  });
}
