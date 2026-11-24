-- ============================================================================
-- 002_doctrina_canonica.sql
--
-- Marca tesis que son DOCTRINA APLICABLE (no ejemplos de entrenamiento).
-- Una doctrina canónica:
--   • NO entra al training del modelo (etiqueta queda NULL)
--   • NO aparece en "siguiente pendiente" del flujo de etiquetado
--   • SE MUESTRA siempre en pantallas clave como criterio aplicable
--
-- Ancla actual: tesis IV.2o.C. J/2 (10a.), registro 2006338, sobre el
-- alcance de "actos de imposible reparación" tras la Ley de Amparo 2013.
-- ============================================================================

BEGIN;

ALTER TABLE tesis
    ADD COLUMN IF NOT EXISTS es_doctrina_canonica BOOLEAN NOT NULL DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_tesis_doctrina
    ON tesis(created_at DESC) WHERE es_doctrina_canonica = TRUE;

-- Sanity: una doctrina canónica no debería tener etiqueta adj/sus.
-- (No es un constraint duro porque no queremos romper imports legítimos.)
-- Para enforcement, el endpoint de label rechaza si es_doctrina=true.

COMMIT;
