/**
 * Marco normativo: fracciones aplicables del artículo 107 de la Ley de
 * Amparo (texto vigente, ref. DOF 13-03-2025) para cada categoría de
 * procedencia. Se muestra como referencia normativa en la UI cuando
 * aplica.
 *
 * Fuente: Ley de Amparo, Reglamentaria de los Artículos 103 y 107 de la
 * Constitución Política de los Estados Unidos Mexicanos. DOF 02-04-2013;
 * última reforma DOF 13-03-2025.
 */

import type { PrediccionCategoria } from "../lib/types";

export type FraccionLA = {
  cita: string; // ej. "Art. 107.IV LA"
  titulo: string; // descripción corta
  texto: string; // texto literal de la fracción/párrafo
  notas?: string; // notas operativas (ej. "modifica criterio P./J. 4/2001")
};

const F_107_III: FraccionLA = {
  cita: "Art. 107.III LA",
  titulo:
    "Procedencia del amparo indirecto contra actos en juicio de imposible reparación",
  texto:
    "El amparo indirecto procede contra actos, omisiones o resoluciones provenientes de un procedimiento seguido en forma de juicio que: a) sean dictados por tribunales judiciales, administrativos, agrarios o del trabajo, siempre que se trate de la sentencia definitiva o la resolución que ponga fin al juicio (…); b) en los casos a que se refiere el inciso a), procede el amparo indirecto contra actos en juicio cuyos efectos sean de imposible reparación, entendiéndose por ellos los que afecten materialmente derechos sustantivos tutelados en la Constitución Política de los Estados Unidos Mexicanos y en los tratados internacionales de los que el Estado Mexicano sea parte.",
  notas:
    "La definición de 'imposible reparación' como 'afectación material a derechos sustantivos' deroga el criterio anterior de 'grado predominante o superior' (P./J. 4/2001). Confirmado por tesis IV.2o.C. J/2 (10a.), registro 2006338.",
};

const F_107_IV: FraccionLA = {
  cita: "Art. 107.IV LA",
  titulo:
    "Procedencia contra actos fuera de juicio o después de concluido — regla de la última resolución",
  texto:
    "Contra actos de tribunales judiciales, administrativos, agrarios o del trabajo realizados fuera de juicio o después de concluido. Si se trata de actos de ejecución de sentencia sólo podrá promoverse el amparo contra la última resolución dictada en el procedimiento respectivo, entendida como aquélla que aprueba o reconoce el cumplimiento total de lo sentenciado o declara la imposibilidad material o jurídica para darle cumplimiento, o las que ordenan el archivo definitivo del expediente, pudiendo reclamarse en la misma demanda las violaciones cometidas durante ese procedimiento que hubieren dejado sin defensa a la persona quejosa y trascendido al resultado de la resolución. En los procedimientos de remate la última resolución es aquélla que en forma definitiva ordena el otorgamiento de la escritura de adjudicación y la entrega de los bienes rematados, en cuyo caso se harán valer las violaciones cometidas durante ese procedimiento en los términos del párrafo anterior.",
  notas:
    "Reforma vigente DOF 13-03-2025. Los actos intermedios del procedimiento de ejecución NO son impugnables aisladamente — se acumulan a la demanda contra la última resolución.",
};

const F_107_V: FraccionLA = {
  cita: "Art. 107.V LA",
  titulo: "Tercero extraño al juicio",
  texto:
    "Contra actos en juicio que afecten a personas extrañas al mismo, cuando la afectación se produzca por sí o por sus representantes, sin que hubieran sido debidamente emplazadas a juicio.",
  notas:
    "El tercero extraño accede al amparo indirecto inmediato sin necesidad de agotar el principio de definitividad.",
};

const F_107_VI: FraccionLA = {
  cita: "Art. 107.VI LA",
  titulo: "Procedencia contra leyes y normas generales",
  texto:
    "Contra leyes federales, locales, tratados internacionales, reglamentos federales o locales o cualquier otra norma de carácter general (…) por su sola entrada en vigor o con motivo del primer acto de aplicación.",
};

const FUERA_JUICIO: FraccionLA = {
  cita: "Art. 107.II LA",
  titulo: "Procedencia contra actos fuera de juicio",
  texto:
    "Contra actos que no provengan de tribunales judiciales, administrativos, agrarios o del trabajo. Procede el amparo indirecto inmediato sin la regla de definitividad cuando se trate de actos de autoridades distintas de tribunales.",
};

/**
 * Marco normativo aplicable a cada categoría predicha (o etiqueta del
 * proyectista). Devuelve `null` si la categoría no tiene marco específico.
 */
const MARCO_POR_CATEGORIA: Partial<Record<PrediccionCategoria, FraccionLA[]>> = {
  fuera_juicio: [FUERA_JUICIO],
  en_juicio_imposible: [F_107_III],
  en_juicio_diferida: [F_107_III],
  post_juicio_general: [F_107_IV],
  post_juicio_ejecucion: [F_107_IV],
  post_juicio_prematuro: [F_107_IV],
  tercero_extrano: [F_107_V],
  sentencia_definitiva: [F_107_III],
  // legacy
  adjetivo: [F_107_III],
  sustantivo: [F_107_III],
};

export function marcoPara(cat: PrediccionCategoria | null | undefined): FraccionLA[] {
  if (!cat) return [];
  return MARCO_POR_CATEGORIA[cat] ?? [];
}
