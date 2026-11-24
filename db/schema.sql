-- ============================================================================
-- SCAAR — Sistema de Clasificación Automatizada de Actos Reclamados
-- Esquema PostgreSQL CONSOLIDADO (master, incluye todas las migraciones 001-008)
--
-- Principios rectores:
--   1. classifications es INMUTABLE (trigger bloquea UPDATE/DELETE).
--      → El log de Riesgo 9 es evidencia, no estado mutable.
--   2. Veredictos del proyectista viven en classification_validations,
--      append-only con supersedes_id → permite reconstruir línea temporal.
--   3. top_features y top_analogas se denormalizan (JSONB) en la fila de
--      classification → el log se reproduce aunque mañana cambie el corpus
--      o se renombre una feature.
--   4. Sólo un model_version activo a la vez (partial unique index).
--   5. Doctrinas canónicas viven en `tesis` con `es_doctrina_canonica=TRUE`
--      — son el criterio jurídico aplicable, NO ejemplos de entrenamiento.
--   6. Búsqueda full-text en español sobre rubro+texto de tesis y sobre
--      acto_reclamado de classifications (tsv materializado por triggers).
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";  -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS "citext";    -- email case-insensitive

-- ----------------------------------------------------------------------------
-- USUARIOS
-- ----------------------------------------------------------------------------
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           CITEXT UNIQUE NOT NULL,
    nombre_completo TEXT NOT NULL,
    rol             TEXT NOT NULL
                    CHECK (rol IN ('proyectista','socio','admin')),
    cedula_prof     TEXT,
    password_hash   TEXT NOT NULL,
    activo          BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ----------------------------------------------------------------------------
-- CORPUS DE TESIS DE LA SJF
-- ----------------------------------------------------------------------------
CREATE TABLE tesis (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    registro_sjf    TEXT UNIQUE NOT NULL,
    epoca           TEXT NOT NULL,
    instancia       TEXT NOT NULL,
    tipo            TEXT NOT NULL CHECK (tipo IN ('jurisprudencia','aislada')),
    rubro           TEXT NOT NULL,
    texto           TEXT NOT NULL,
    -- NULL = pendiente. 8 categorías post-IV.2o.C. J/2 + no_aplica.
    etiqueta        TEXT
                    CHECK (etiqueta IS NULL OR etiqueta IN (
                        'fuera_juicio',
                        'en_juicio_imposible',
                        'en_juicio_diferida',
                        'post_juicio_general',
                        'post_juicio_ejecucion',
                        'post_juicio_prematuro',
                        'tercero_extrano',
                        'sentencia_definitiva',
                        'no_aplica'
                    )),
    fecha_publ      DATE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    etiquetada_por  UUID REFERENCES users(id),
    etiquetada_at   TIMESTAMPTZ,
    fuente          TEXT NOT NULL DEFAULT 'manual',
    es_doctrina_canonica BOOLEAN NOT NULL DEFAULT FALSE,
    tsv             tsvector
);
CREATE INDEX idx_tesis_etiqueta   ON tesis(etiqueta);
CREATE INDEX idx_tesis_fuente     ON tesis(fuente);
CREATE INDEX idx_tesis_pendientes ON tesis(created_at DESC) WHERE etiqueta IS NULL;
CREATE INDEX idx_tesis_doctrina   ON tesis(created_at DESC) WHERE es_doctrina_canonica = TRUE;
CREATE INDEX idx_tesis_tsv        ON tesis USING GIN(tsv);

-- Mantener tsv al día con stemming español
CREATE TRIGGER tesis_tsv_update
BEFORE INSERT OR UPDATE OF rubro, texto ON tesis
FOR EACH ROW EXECUTE FUNCTION tsvector_update_trigger(
    tsv, 'pg_catalog.spanish', rubro, texto
);

-- ----------------------------------------------------------------------------
-- VERSIONES DEL MODELO
-- ----------------------------------------------------------------------------
CREATE TABLE model_versions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version         TEXT UNIQUE NOT NULL,
    algoritmo       TEXT NOT NULL,
    fecha_corte     DATE NOT NULL,
    n_tesis_train   INT NOT NULL,
    metricas        JSONB NOT NULL,
    artifact_path   TEXT NOT NULL,
    artifact_sha256 CHAR(64) NOT NULL,
    activo          BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      UUID NOT NULL REFERENCES users(id)
);
CREATE UNIQUE INDEX one_active_model
    ON model_versions(activo) WHERE activo = TRUE;

-- ----------------------------------------------------------------------------
-- CASOS (expedientes del despacho — agrupación de actos)
-- ----------------------------------------------------------------------------
CREATE TABLE cases (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    identificador   TEXT NOT NULL,
    descripcion     TEXT,
    materia         TEXT,
    created_by      UUID NOT NULL REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    archived_at     TIMESTAMPTZ
);
CREATE UNIQUE INDEX cases_identificador_per_user
    ON cases(created_by, identificador);
CREATE INDEX idx_cases_archived
    ON cases(archived_at) WHERE archived_at IS NULL;

CREATE OR REPLACE FUNCTION cases_touch_updated_at() RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER cases_updated_at
BEFORE UPDATE ON cases
FOR EACH ROW EXECUTE FUNCTION cases_touch_updated_at();

-- ----------------------------------------------------------------------------
-- CLASIFICACIONES — APPEND-ONLY (núcleo del Log de Riesgo 9)
-- ----------------------------------------------------------------------------
CREATE TABLE classifications (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    acto_reclamado      TEXT NOT NULL,
    acto_sha256         CHAR(64) NOT NULL,
    model_version_id    UUID NOT NULL REFERENCES model_versions(id),
    -- Predicción: una de las 8 categorías nuevas o legacy adj/sus.
    prediccion          TEXT NOT NULL
                        CHECK (prediccion IN (
                            'adjetivo','sustantivo',  -- legacy
                            'fuera_juicio',
                            'en_juicio_imposible',
                            'en_juicio_diferida',
                            'post_juicio_general',
                            'post_juicio_ejecucion',
                            'post_juicio_prematuro',
                            'tercero_extrano',
                            'sentencia_definitiva'
                        )),
    -- Probabilidad legacy del binario (NULL en modelos multiclase)
    prob_adjetivo       NUMERIC(6,5)
                        CHECK (prob_adjetivo IS NULL
                               OR prob_adjetivo BETWEEN 0 AND 1),
    -- Probabilidad de la categoría predicha (multiclase)
    prob_categoria      NUMERIC(6,5)
                        CHECK (prob_categoria IS NULL
                               OR prob_categoria BETWEEN 0 AND 1),
    -- Mapa categoría → probabilidad de todas las clases conocidas por el modelo
    prob_por_clase      JSONB,
    top_features        JSONB NOT NULL,
    top_analogas        JSONB NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by          UUID NOT NULL REFERENCES users(id),
    case_id             UUID REFERENCES cases(id),
    tsv                 tsvector
);
CREATE INDEX idx_class_sha            ON classifications(acto_sha256);
CREATE INDEX idx_class_user_date      ON classifications(created_by, created_at DESC);
CREATE INDEX idx_class_model          ON classifications(model_version_id);
CREATE INDEX idx_class_case           ON classifications(case_id);
CREATE INDEX idx_class_tsv            ON classifications USING GIN(tsv);

-- Trigger BEFORE INSERT: calcular tsv. Después del INSERT, el trigger de
-- inmutabilidad bloquea cualquier modificación posterior.
CREATE OR REPLACE FUNCTION class_tsv_on_insert() RETURNS TRIGGER AS $$
BEGIN
    NEW.tsv := to_tsvector('spanish', coalesce(NEW.acto_reclamado, ''));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER class_tsv_insert
BEFORE INSERT ON classifications
FOR EACH ROW EXECUTE FUNCTION class_tsv_on_insert();

CREATE OR REPLACE FUNCTION classifications_immutable() RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'classifications es append-only (Riesgo 9 / log inmutable)';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER no_modify_classifications
BEFORE UPDATE OR DELETE ON classifications
FOR EACH ROW EXECUTE FUNCTION classifications_immutable();

-- ----------------------------------------------------------------------------
-- VALIDACIONES DEL PROYECTISTA — APPEND-ONLY con cadena de supersede
-- ----------------------------------------------------------------------------
CREATE TABLE classification_validations (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    classification_id       UUID NOT NULL REFERENCES classifications(id),
    validated_by            UUID NOT NULL REFERENCES users(id),
    validated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),

    veredicto               TEXT NOT NULL
                            CHECK (veredicto IN ('acepta','rechaza')),
    -- 7 categorías (sin no_aplica) + 2 legacy para firmas históricas
    clasificacion_corregida TEXT
                            CHECK (clasificacion_corregida IS NULL OR
                                   clasificacion_corregida IN (
                                       'adjetivo','sustantivo',  -- legacy
                                       'fuera_juicio',
                                       'en_juicio_imposible',
                                       'en_juicio_diferida',
                                       'post_juicio_general',
                                       'post_juicio_ejecucion',
                                       'post_juicio_prematuro',
                                       'tercero_extrano',
                                       'sentencia_definitiva'
                                   )),
    comentario              TEXT,

    aprobado_para_corpus    BOOLEAN NOT NULL DEFAULT FALSE,
    aprobado_por            UUID REFERENCES users(id),
    aprobado_at             TIMESTAMPTZ,

    firma_sha256            CHAR(64) NOT NULL,
    firma_payload           JSONB NOT NULL,

    supersedes_id           UUID UNIQUE REFERENCES classification_validations(id),

    CONSTRAINT veredicto_corregida_coherente CHECK (
        (veredicto = 'rechaza' AND clasificacion_corregida IS NOT NULL)
        OR
        (veredicto = 'acepta'  AND clasificacion_corregida IS NULL)
    ),
    CONSTRAINT aprobacion_completa CHECK (
        (aprobado_para_corpus = FALSE)
        OR
        (aprobado_para_corpus = TRUE AND aprobado_por IS NOT NULL AND aprobado_at IS NOT NULL)
    )
);
CREATE INDEX idx_val_classification ON classification_validations(classification_id);
CREATE INDEX idx_val_user_date      ON classification_validations(validated_by, validated_at DESC);

CREATE OR REPLACE FUNCTION validations_immutable() RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'classification_validations es append-only';
    END IF;
    IF (NEW.id, NEW.classification_id, NEW.validated_by, NEW.validated_at,
        NEW.veredicto, NEW.clasificacion_corregida, NEW.comentario,
        NEW.firma_sha256, NEW.firma_payload, NEW.supersedes_id)
       IS DISTINCT FROM
       (OLD.id, OLD.classification_id, OLD.validated_by, OLD.validated_at,
        OLD.veredicto, OLD.clasificacion_corregida, OLD.comentario,
        OLD.firma_sha256, OLD.firma_payload, OLD.supersedes_id) THEN
        RAISE EXCEPTION 'sólo aprobado_para_corpus/aprobado_por/aprobado_at son modificables';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER no_modify_validations
BEFORE UPDATE OR DELETE ON classification_validations
FOR EACH ROW EXECUTE FUNCTION validations_immutable();

-- ----------------------------------------------------------------------------
-- VISTAS
-- ----------------------------------------------------------------------------
CREATE VIEW v_validacion_vigente AS
SELECT v.*
FROM classification_validations v
WHERE NOT EXISTS (
    SELECT 1 FROM classification_validations v2
    WHERE v2.supersedes_id = v.id
);

CREATE VIEW v_corpus_reentreno AS
SELECT
    c.id              AS classification_id,
    c.acto_reclamado  AS texto,
    COALESCE(v.clasificacion_corregida, c.prediccion) AS etiqueta,
    v.aprobado_at,
    v.aprobado_por
FROM classifications c
JOIN v_validacion_vigente v ON v.classification_id = c.id
WHERE v.aprobado_para_corpus = TRUE;
