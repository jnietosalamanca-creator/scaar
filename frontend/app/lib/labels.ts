/**
 * Taxonomía de procedencia de amparo — 8 categorías + outputs derivados.
 *
 * Las etiquetas reflejan el árbol de decisión que sigue un proyectista al
 * recibir un acto reclamado (Ley de Amparo, art. 107):
 *
 *   fuera_juicio              → indirecto inmediato
 *   en_juicio_imposible       → indirecto inmediato (IV.2o.C. J/2 — afecta
 *                                materialmente derechos sustantivos)
 *   en_juicio_diferida        → directo diferido (procesal pura)
 *   post_juicio_general       → indirecto (post-concluido, no ejecución)
 *   post_juicio_ejecucion     → indirecto SI es la última resolución
 *   post_juicio_prematuro     → ⚠ NO presentar — esperar última resolución
 *                                (art. 107.IV LA, ref. DOF 13-03-2025)
 *   tercero_extrano           → indirecto inmediato (sin agotar def.)
 *   sentencia_definitiva      → amparo directo
 *   no_aplica                 → fuera del dominio
 *
 * El enum binario interno del clasificador actual (`adjetivo`/`sustantivo`)
 * mapea aquí solo a `en_juicio_imposible`/`en_juicio_diferida` — el modelo
 * activo aún no resuelve las otras categorías. Pendiente de reentrenar
 * multiclase cuando el corpus alcance el threshold.
 */

import type { Etiqueta, EtiquetaTesis } from "./types";

export type Via = "indirecto" | "directo" | "ninguna";
export type Inmediatez = "inmediato" | "diferido" | "esperar_ultima_resolucion";

export type LabelMeta = {
  /** Nombre completo para botones grandes y títulos */
  display: string;
  /** Versión corta para badges */
  short: string;
  /** Vía de amparo derivada (función pura de la categoría) */
  via: Via;
  /** Inmediatez derivada */
  inmediatez: Inmediatez;
  /** Texto de alerta cuando el caso es procesalmente delicado (prematuridad) */
  alerta?: string;
  /** Atajo de teclado en /corpus/etiquetar */
  shortcut: string;
  /** Color tailwind del badge */
  color: "indigo" | "emerald" | "amber" | "rose" | "sky" | "violet" | "slate";
  /** Sub-explicación una línea, para tooltips y UI */
  explicacion: string;
};

const META: Record<string, LabelMeta> = {
  fuera_juicio: {
    display: "Fuera de juicio",
    short: "fuera juicio",
    via: "indirecto",
    inmediatez: "inmediato",
    shortcut: "1",
    color: "sky",
    explicacion:
      "Acto de autoridad emitido sin estar dentro de un procedimiento judicial. Procede amparo indirecto inmediato.",
  },
  en_juicio_imposible: {
    display: "En juicio — imposible reparación",
    short: "imposible rep.",
    via: "indirecto",
    inmediatez: "inmediato",
    shortcut: "2",
    color: "indigo",
    explicacion:
      "Acto dentro de juicio que afecta MATERIALMENTE derechos sustantivos (embargo, multa, alimentos, arresto). IV.2o.C. J/2 (10a.).",
  },
  en_juicio_diferida: {
    display: "En juicio — diferida",
    short: "diferida",
    via: "directo",
    inmediatez: "diferido",
    shortcut: "3",
    color: "emerald",
    explicacion:
      "Violación procesal sin afectación material a sustantivos. Se reclama de manera diferida en amparo directo.",
  },
  post_juicio_general: {
    display: "Post-juicio (general)",
    short: "post-juicio",
    via: "indirecto",
    inmediatez: "inmediato",
    shortcut: "4",
    color: "violet",
    explicacion:
      "Acto después de concluido el juicio, fuera de procedimiento de ejecución/remate. Procede amparo indirecto.",
  },
  post_juicio_ejecucion: {
    display: "Post-juicio (última resolución de ejecución/remate)",
    short: "ejecución (última)",
    via: "indirecto",
    inmediatez: "inmediato",
    shortcut: "5",
    color: "violet",
    explicacion:
      "Última resolución del procedimiento de ejecución (cumplimiento total / imposibilidad / archivo) o remate (escritura adj. / entrega). Procede indirecto. Las violaciones intermedias se acumulan a esta demanda.",
  },
  post_juicio_prematuro: {
    display: "Post-juicio (prematuro — esperar)",
    short: "⚠ prematuro",
    via: "ninguna",
    inmediatez: "esperar_ultima_resolucion",
    alerta:
      "Art. 107.IV LA — acto intermedio de ejecución de sentencia o remate. NO procede amparo todavía. Espera la última resolución del procedimiento; las violaciones cometidas durante éste se acumularán a la demanda contra esa última resolución.",
    shortcut: "6",
    color: "rose",
    explicacion:
      "Acto intermedio dentro de procedimiento de ejecución o remate. Presentar amparo ahora = desechamiento. Esperar última resolución y acumular.",
  },
  tercero_extrano: {
    display: "Tercero extraño",
    short: "tercero extraño",
    via: "indirecto",
    inmediatez: "inmediato",
    shortcut: "7",
    color: "amber",
    explicacion:
      "Persona ajena al juicio que resiente afectación. Procede amparo indirecto inmediato sin agotar el principio de definitividad.",
  },
  sentencia_definitiva: {
    display: "Sentencia definitiva / laudo",
    short: "directo",
    via: "directo",
    inmediatez: "inmediato",
    shortcut: "8",
    color: "emerald",
    explicacion:
      "Sentencia definitiva, laudo o resolución que pone fin al juicio. Procede amparo directo (Tribunal Colegiado).",
  },
  no_aplica: {
    display: "No aplica",
    short: "no aplica",
    via: "ninguna",
    inmediatez: "inmediato",
    shortcut: "0",
    color: "slate",
    explicacion: "Fuera del dominio del clasificador.",
  },
};

const PENDIENTE: LabelMeta = {
  display: "Pendiente",
  short: "pendiente",
  via: "ninguna",
  inmediatez: "inmediato",
  shortcut: "",
  color: "amber",
  explicacion: "Sin etiqueta — el proyectista aún no la revisó.",
};

/** Mapping de etiquetas binarias del modelo activo a las nuevas categorías. */
function fromBinario(et: Etiqueta): LabelMeta {
  return et === "adjetivo" ? META.en_juicio_imposible : META.en_juicio_diferida;
}

export function labelMeta(et: EtiquetaTesis | Etiqueta | null | undefined): LabelMeta {
  if (!et) return PENDIENTE;
  if (et === "adjetivo" || et === "sustantivo") return fromBinario(et);
  return META[et] ?? PENDIENTE;
}

export const TODAS_LAS_CATEGORIAS: EtiquetaTesis[] = [
  "fuera_juicio",
  "en_juicio_imposible",
  "en_juicio_diferida",
  "post_juicio_general",
  "post_juicio_ejecucion",
  "post_juicio_prematuro",
  "tercero_extrano",
  "sentencia_definitiva",
  "no_aplica",
];

/**
 * Las 7 categorías que un proyectista puede asignar como corrección de un
 * veredicto. Excluye 'no_aplica' (no es un veredicto de procedencia).
 */
export const VEREDICTO_CATEGORIAS: Exclude<EtiquetaTesis, "no_aplica">[] = [
  "fuera_juicio",
  "en_juicio_imposible",
  "en_juicio_diferida",
  "post_juicio_general",
  "post_juicio_ejecucion",
  "post_juicio_prematuro",
  "tercero_extrano",
  "sentencia_definitiva",
];

const colorClasses = {
  indigo: "bg-indigo-100 text-indigo-700",
  emerald: "bg-emerald-100 text-emerald-700",
  amber: "bg-amber-100 text-amber-800",
  rose: "bg-rose-100 text-rose-700",
  sky: "bg-sky-100 text-sky-700",
  violet: "bg-violet-100 text-violet-700",
  slate: "bg-slate-200 text-slate-700",
} as const;

export function labelBadgeClass(color: LabelMeta["color"]): string {
  return colorClasses[color];
}

/** Metadata para el rol jurisprudencial (regla / excepcion / ...). */
export const TIPO_JUR_META: Record<
  string,
  { display: string; short: string; descripcion: string; entra_training: boolean }
> = {
  regla: {
    display: "Regla",
    short: "regla",
    descripcion: "Confirma el criterio general — SÍ entra al training del modelo.",
    entra_training: true,
  },
  excepcion: {
    display: "Excepción",
    short: "excepción",
    descripcion:
      "Caso particular que desafía la regla general — NO entra al training (evita señal contradictoria).",
    entra_training: false,
  },
  aislada_dudosa: {
    display: "Aislada dudosa",
    short: "aislada",
    descripcion:
      "Tesis aislada cuya doctrina aún no se consolida — NO entra al training hasta que se confirme.",
    entra_training: false,
  },
  derogada: {
    display: "Derogada",
    short: "derogada",
    descripcion:
      "Criterio superado por jurisprudencia posterior — NO entra al training (ej. P./J. 4/2001 por IV.2o.C. J/2).",
    entra_training: false,
  },
};

export const TIPOS_JUR_DISPONIBLES = ["regla", "excepcion", "aislada_dudosa", "derogada"] as const;

const buttonBorderClasses = {
  indigo: "border-indigo-300 hover:bg-indigo-50 text-indigo-900",
  emerald: "border-emerald-300 hover:bg-emerald-50 text-emerald-900",
  amber: "border-amber-300 hover:bg-amber-50 text-amber-900",
  rose: "border-rose-300 hover:bg-rose-50 text-rose-900",
  sky: "border-sky-300 hover:bg-sky-50 text-sky-900",
  violet: "border-violet-300 hover:bg-violet-50 text-violet-900",
  slate: "border-slate-300 hover:bg-slate-50 text-slate-700",
} as const;

export function labelButtonClass(color: LabelMeta["color"]): string {
  return buttonBorderClasses[color];
}
