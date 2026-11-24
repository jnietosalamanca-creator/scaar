/**
 * Etiqueta del clasificador binario LEGACY (modelos v0.1.x / v0.2.x).
 * Las clasificaciones nuevas usan la taxonomía multiclase
 * (`PrediccionCategoria`). Este tipo se conserva solo para compatibilidad
 * con `ValidationDetail.clasificacion_corregida` heredado.
 */
export type Etiqueta = "adjetivo" | "sustantivo";

export type PrediccionCategoria =
  | "adjetivo"
  | "sustantivo"
  | "fuera_juicio"
  | "en_juicio_imposible"
  | "en_juicio_diferida"
  | "post_juicio_general"
  | "post_juicio_ejecucion"
  | "post_juicio_prematuro"
  | "tercero_extrano"
  | "sentencia_definitiva";

export type ViaAmparo = "indirecto" | "directo" | "ninguna";
export type InmediatezAmparo =
  | "inmediato"
  | "diferido"
  | "esperar_ultima_resolucion";

/**
 * Las 7 categorías que un proyectista puede asignar como corrección de un
 * veredicto. Excluye 'no_aplica' (decisión de etiquetado de corpus, no
 * veredicto de procedencia).
 */
export type VeredictoCategoria =
  | "fuera_juicio"
  | "en_juicio_imposible"
  | "en_juicio_diferida"
  | "post_juicio_general"
  | "post_juicio_ejecucion"
  | "post_juicio_prematuro"
  | "tercero_extrano"
  | "sentencia_definitiva";

export type TopFeature = {
  token: string;
  contribucion: number;
  tfidf: number;
};

export type TopAnaloga = {
  tesis_id: string;
  registro_sjf: string;
  rubro: string;
  etiqueta: string; // categoría del corpus (puede ser cualquiera, incl. legacy)
  similitud: number;
};

export type ClassifyResponse = {
  classification_id: string;
  acto_sha256: string;
  model_version: string;
  categoria: PrediccionCategoria;
  via: ViaAmparo;
  inmediatez: InmediatezAmparo;
  alerta: string | null;
  prob_categoria: number;
  prob_por_clase: Record<string, number>;
  requiere_revision_humana: boolean;
  top_features: TopFeature[];
  top_analogas: TopAnaloga[];
  created_at: string;
};

export type ValidationDetail = {
  id: string;
  validated_by: string;
  validated_by_email: string;
  validated_at: string;
  veredicto: "acepta" | "rechaza";
  // Puede ser una de las 7 categorías nuevas, o (legacy) 'adjetivo'/'sustantivo'
  // de validaciones firmadas antes del refactor — preserva firmas históricas.
  clasificacion_corregida: PrediccionCategoria | null;
  comentario: string | null;
  firma_sha256: string;
  firma_valida: boolean;
  supersedes_id: string | null;
  es_vigente: boolean;
};

export type ClassificationListItem = {
  id: string;
  acto_sha256: string;
  acto_preview: string;
  model_version: string;
  categoria: PrediccionCategoria;
  via: ViaAmparo;
  prob_categoria: number | null;
  requiere_revision_humana: boolean;
  created_at: string;
  created_by_email: string;
  veredicto_vigente: "acepta" | "rechaza" | null;
  clasificacion_final: PrediccionCategoria | null;
  n_validaciones: number;
};

export type ClassificationListResponse = {
  items: ClassificationListItem[];
  total: number;
  limit: number;
  offset: number;
};

export type ListQuery = {
  sha?: string;
  q?: string;
  categoria?: PrediccionCategoria;
  estado?: "pendiente" | "validada";
  limit?: number;
  offset?: number;
};

// ----------------------------- Corpus / Tesis -----------------------------

export type EtiquetaTesis =
  | "fuera_juicio"
  | "en_juicio_imposible"
  | "en_juicio_diferida"
  | "post_juicio_general"
  | "post_juicio_ejecucion"
  | "post_juicio_prematuro"
  | "tercero_extrano"
  | "sentencia_definitiva"
  | "no_aplica";

/**
 * Rol jurisprudencial de la tesis dentro del corpus.
 *   - `regla`: confirma el criterio general — entra al training.
 *   - `excepcion`: caso particular que desafía la regla — NO entra al training.
 *   - `aislada_dudosa`: doctrina no consolidada — NO entra al training.
 *   - `derogada`: criterio superado por jurisprudencia posterior — NO entra.
 */
export type TipoJurisprudencial =
  | "regla"
  | "excepcion"
  | "aislada_dudosa"
  | "derogada";

export type TesisListItem = {
  id: string;
  registro_sjf: string;
  epoca: string;
  instancia: string;
  tipo: "jurisprudencia" | "aislada";
  rubro: string;
  fecha_publ: string | null;
  etiqueta: EtiquetaTesis | null;
  etiquetada_por_email: string | null;
  etiquetada_at: string | null;
  fuente: string;
  created_at: string;
  es_doctrina_canonica?: boolean;
  tipo_jurisprudencial?: TipoJurisprudencial;
};

export type TesisListResponse = {
  items: TesisListItem[];
  total: number;
  limit: number;
  offset: number;
};

export type TesisDetail = {
  id: string;
  registro_sjf: string;
  epoca: string;
  instancia: string;
  tipo: "jurisprudencia" | "aislada";
  rubro: string;
  texto: string;
  etiqueta: EtiquetaTesis | null;
  fecha_publ: string | null;
  fuente: string;
  etiquetada_por_email: string | null;
  etiquetada_at: string | null;
  created_at: string;
  es_doctrina_canonica: boolean;
  tipo_jurisprudencial: TipoJurisprudencial;
  notas_metodologicas: string | null;
};

export type TopProb = { categoria: string; prob: number };

export type TesisInciertaItem = {
  id: string;
  registro_sjf: string;
  instancia: string;
  tipo: "jurisprudencia" | "aislada";
  rubro: string;
  texto: string;
  fecha_publ: string | null;
  fuente: string;
  created_at: string;
  entropia: number;
  top_probs: TopProb[];
};

export type TesisAuditoriaItem = {
  id: string;
  registro_sjf: string;
  rubro: string;
  etiqueta_humana: EtiquetaTesis;
  etiquetada_por_email: string | null;
  categoria_modelo: string;
  prob_categoria_modelo: number;
  prob_de_etiqueta_humana: number;
  discrepa: boolean;
  fuente: string;
};

export type CorpusStats = {
  total: number;
  etiquetadas: number;
  pendientes: number;
  por_categoria: Record<EtiquetaTesis, number>;
  por_fuente: Record<string, number>;
  listas_para_entrenar: number;
  listas_para_train_limpio: number;
  fuentes_excluidas: string[];
  threshold_train_limpio: number;
};

export type TesisListQuery = {
  estado?: "pendiente" | "etiquetada" | "no_aplica" | "lista_train";
  fuente?: string;
  q?: string;
  limit?: number;
  offset?: number;
};

export type ImportTesisItem = {
  registro_sjf: string;
  epoca: string;
  instancia: string;
  tipo: "jurisprudencia" | "aislada";
  rubro: string;
  texto: string;
  etiqueta?: EtiquetaTesis | null;
  fecha_publ?: string | null;
};

export type ImportTesisResponse = {
  insertadas: number;
  duplicadas: number;
  errores: string[];
};

// ----------------------------- Casos -----------------------------

export type CasoListItem = {
  id: string;
  identificador: string;
  descripcion: string | null;
  materia: string | null;
  created_at: string;
  archived_at: string | null;
  n_actos: number;
  n_indirectos: number;
  n_directos: number;
  n_prematuros: number;
};

export type CasoListResponse = {
  items: CasoListItem[];
  total: number;
  limit: number;
  offset: number;
};

export type ActoEnCaso = {
  classification_id: string;
  acto_preview: string;
  categoria: PrediccionCategoria;
  via: ViaAmparo;
  inmediatez: InmediatezAmparo;
  alerta: string | null;
  prob_categoria: number | null;
  requiere_revision_humana: boolean;
  veredicto_vigente: "acepta" | "rechaza" | null;
  clasificacion_final: PrediccionCategoria | null;
  created_at: string;
};

export type DemandaSugerida = {
  via: ViaAmparo;
  titulo: string;
  explicacion: string;
  actos: string[];
  inmediatez: InmediatezAmparo;
  violaciones_acumulables: string[];
  alerta: string | null;
};

export type CasoResumen = {
  caso_id: string;
  n_actos: number;
  demandas: DemandaSugerida[];
  actos_prematuros: string[];
  actos_no_aplica: string[];
};

export type CasoDetail = {
  id: string;
  identificador: string;
  descripcion: string | null;
  materia: string | null;
  created_by: string;
  created_by_email: string;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
  actos: ActoEnCaso[];
  resumen: CasoResumen;
};

export type CasoCreate = {
  identificador: string;
  descripcion?: string | null;
  materia?: string | null;
};

export type CasoUpdate = {
  identificador?: string;
  descripcion?: string | null;
  materia?: string | null;
  archived?: boolean;
};

export type CasoListQuery = {
  archived?: "activos" | "archivados" | "todos";
  q?: string;
  limit?: number;
  offset?: number;
};

export type CasoSinteticoRequest = {
  n_actos?: number;
  categorias_objetivo?: PrediccionCategoria[];
  seed?: number | null;
};

// ----------------------------- Duplicados -----------------------------

export type DuplicadoItem = {
  classification_id: string;
  created_at: string;
  created_by_email: string;
  categoria_predicha: PrediccionCategoria;
  veredicto_vigente: "acepta" | "rechaza" | null;
  clasificacion_final: PrediccionCategoria | null;
  case_id: string | null;
  case_identificador: string | null;
};

export type DuplicadosResponse = {
  acto_sha256: string;
  n_previas: number;
  previas: DuplicadoItem[];
};

// ----------------------------- Modelo (dashboard) -----------------------------

export type CategoriaPair = {
  predicha: string;
  final: string;
  n: number;
};

export type ModeloStats = {
  version: string;
  algoritmo: string;
  n_tesis_train: number;
  fecha_corte: string;
  metricas: Record<string, unknown>;
  activo: boolean;
  total_clasificaciones: number;
  distribucion_predicciones: Record<string, number>;
  n_validadas: number;
  n_aceptadas: number;
  n_corregidas: number;
  tasa_aceptacion: number | null;
  correcciones: CategoriaPair[];
  clases_no_predichas: string[];
};

export type ModelVersionListItem = {
  id: string;
  version: string;
  algoritmo: string;
  n_tesis_train: number;
  fecha_corte: string;
  activo: boolean;
  created_at: string;
  f1_macro: number | null;
};

export type EjecutoriaImportItem = {
  registro_sjf: string;
  tipo_asunto: string;
  rubro: string;
  instancia: string;
  promovente?: string | null;
  fecha_publ?: string | null;
  url_semanario?: string | null;
  acto_reclamado_candidato: string;
  metodo_extraccion: "antecedentes" | "regex_acto" | "fallback_head";
};

export type EjecutoriasImportResponse = {
  creados: number;
  duplicados: number;
  invalidos: number;
  caso_ids: string[];
};

export type ClassificationDetail = {
  id: string;
  acto_reclamado: string;
  acto_sha256: string;
  model_version: string;
  categoria: PrediccionCategoria;
  via: ViaAmparo;
  inmediatez: InmediatezAmparo;
  alerta: string | null;
  prob_categoria: number | null;
  prob_por_clase: Record<string, number> | null;
  requiere_revision_humana: boolean;
  top_features: TopFeature[];
  top_analogas: TopAnaloga[];
  created_at: string;
  created_by: string;
  created_by_email: string;
  historia_validaciones: ValidationDetail[];
  vigente: ValidationDetail | null;
};
