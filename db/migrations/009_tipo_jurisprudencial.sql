-- ============================================================================
-- 009_tipo_jurisprudencial.sql
--
-- Distingue el ROL JURISPRUDENCIAL de cada tesis dentro de su categoría.
-- Crítico para evitar que el modelo aprenda señal contradictoria:
--   • `regla`        → confirma el criterio general; SÍ entra al training.
--   • `excepcion`    → caso particular que desafía la regla general; NO al training.
--   • `aislada_dudosa` → tesis aislada cuya doctrina aún no se consolida; NO al training.
--   • `derogada`     → criterio superado por jurisprudencia posterior; NO al training.
--
-- También agregamos `notas_metodologicas` (free text) para que el proyectista
-- escriba por qué clasificó una tesis como excepción / derogada.
--
-- Las doctrinas canónicas (es_doctrina_canonica=TRUE) son ortogonales a este
-- flag — la doctrina ancla puede ser una "regla" cuyo rol es educar al usuario;
-- no entra al training porque tiene su propio mecanismo de exclusión.
-- ============================================================================

BEGIN;

ALTER TABLE tesis ADD COLUMN IF NOT EXISTS tipo_jurisprudencial TEXT
    NOT NULL DEFAULT 'regla'
    CHECK (tipo_jurisprudencial IN (
        'regla',
        'excepcion',
        'aislada_dudosa',
        'derogada'
    ));

ALTER TABLE tesis ADD COLUMN IF NOT EXISTS notas_metodologicas TEXT;

CREATE INDEX IF NOT EXISTS idx_tesis_tipo_jur
    ON tesis(tipo_jurisprudencial) WHERE tipo_jurisprudencial <> 'regla';

COMMIT;
