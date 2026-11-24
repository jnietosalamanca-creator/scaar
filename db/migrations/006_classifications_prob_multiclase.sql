-- ============================================================================
-- 006_classifications_prob_multiclase.sql
--
-- classifications.prob_adjetivo era NOT NULL — semántica binaria. En
-- multiclase no aplica. Cambios:
--   • prob_adjetivo nullable (legacy, se llena solo cuando aplique semánti-
--     camente: predicción equivalente a "imposible reparación")
--   • prob_categoria: probabilidad de la categoría dominante predicha
--   • prob_por_clase: JSONB con la distribución completa de probas
--
-- Logs viejos (firmados con prob_adjetivo poblada) siguen verificando.
-- ============================================================================

BEGIN;

ALTER TABLE classifications ALTER COLUMN prob_adjetivo DROP NOT NULL;
ALTER TABLE classifications ADD COLUMN IF NOT EXISTS prob_categoria NUMERIC(6,5);
ALTER TABLE classifications ADD COLUMN IF NOT EXISTS prob_por_clase JSONB;

ALTER TABLE classifications DROP CONSTRAINT IF EXISTS classifications_prob_categoria_check;
ALTER TABLE classifications ADD CONSTRAINT classifications_prob_categoria_check
    CHECK (prob_categoria IS NULL OR (prob_categoria BETWEEN 0 AND 1));

COMMIT;
