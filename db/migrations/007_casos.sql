-- ============================================================================
-- 007_casos.sql
--
-- Apartado de "casos": agrupación de actos reclamados que pertenecen a un
-- mismo expediente del despacho. Permite computar la VÍA RECOMENDADA del
-- expediente completo (qué amparos presentar y en qué orden) en lugar de
-- ver cada acto aislado.
--
-- Decisiones:
--   • Un acto puede vivir SIN caso (case_id NULL) — los flujos ad-hoc
--     siguen funcionando.
--   • Un caso puede archivarse (archived_at) sin borrarse — preserva el log.
--   • Sin trigger de inmutabilidad — los casos son mutables (cambia
--     descripción, identificador, archivado). El log de actos asociados
--     SIGUE inmutable por su propio trigger.
-- ============================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS cases (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    -- Identificador interno del despacho (ej. "EXP-2026/0142")
    identificador   TEXT NOT NULL,
    -- Descripción libre: juicio de origen, partes, etapa procesal
    descripcion     TEXT,
    -- Materia para filtrado/análisis (libre por ahora; futuras versiones
    -- podrían acotar a un enum: civil, mercantil, penal, fiscal, ...).
    materia         TEXT,
    created_by      UUID NOT NULL REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    archived_at     TIMESTAMPTZ
);

-- Identificador único POR usuario que lo creó — distintos despachos podrían
-- usar mismas claves; en el MVP solo hay un despacho.
CREATE UNIQUE INDEX IF NOT EXISTS cases_identificador_per_user
    ON cases(created_by, identificador);

CREATE INDEX IF NOT EXISTS idx_cases_archived
    ON cases(archived_at) WHERE archived_at IS NULL;

-- Asociación opcional acto → caso
ALTER TABLE classifications
    ADD COLUMN IF NOT EXISTS case_id UUID REFERENCES cases(id);

CREATE INDEX IF NOT EXISTS idx_class_case ON classifications(case_id);

-- Trigger ligero para mantener updated_at
CREATE OR REPLACE FUNCTION cases_touch_updated_at() RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS cases_updated_at ON cases;
CREATE TRIGGER cases_updated_at
BEFORE UPDATE ON cases
FOR EACH ROW EXECUTE FUNCTION cases_touch_updated_at();

COMMIT;
