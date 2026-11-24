-- ============================================================================
-- 001_corpus_labeling.sql
--
-- Habilita el flujo de etiquetado del corpus:
--   • etiqueta puede quedar pendiente (NULL) hasta que un proyectista la revise
--   • nueva etiqueta 'no_aplica' para tesis fuera del dominio del clasificador
--     (no son sobre amparo adj/sus — ej. tesis sobre derecho fiscal)
--   • auditoría: quién etiquetó y cuándo
--   • fuente: de dónde vino la tesis (dummy, sjf, manual, import)
--
-- Idempotente: usa IF EXISTS / IF NOT EXISTS donde aplica.
-- ============================================================================

BEGIN;

-- 1. Soltar el CHECK viejo y permitir NULL en etiqueta
ALTER TABLE tesis DROP CONSTRAINT IF EXISTS tesis_etiqueta_check;
ALTER TABLE tesis ALTER COLUMN etiqueta DROP NOT NULL;

-- 2. Nuevo CHECK que admite NULL (pendiente) y la etiqueta 'no_aplica'
ALTER TABLE tesis ADD CONSTRAINT tesis_etiqueta_check
    CHECK (etiqueta IS NULL OR etiqueta IN ('adjetivo','sustantivo','no_aplica'));

-- 3. Auditoría de etiquetado
ALTER TABLE tesis ADD COLUMN IF NOT EXISTS etiquetada_por UUID REFERENCES users(id);
ALTER TABLE tesis ADD COLUMN IF NOT EXISTS etiquetada_at  TIMESTAMPTZ;
ALTER TABLE tesis ADD COLUMN IF NOT EXISTS fuente         TEXT NOT NULL DEFAULT 'manual';

-- 4. Marcar las 20 tesis dummy ya cargadas como tales (idempotente)
UPDATE tesis SET fuente = 'dummy'
WHERE registro_sjf LIKE '20245000%' AND fuente = 'manual';

-- 5. Índices útiles para los nuevos flujos
CREATE INDEX IF NOT EXISTS idx_tesis_pendientes
    ON tesis(created_at DESC) WHERE etiqueta IS NULL;
CREATE INDEX IF NOT EXISTS idx_tesis_fuente ON tesis(fuente);

COMMIT;

-- Verificación rápida (opcional):
-- \d tesis
-- SELECT fuente, etiqueta, COUNT(*) FROM tesis GROUP BY 1,2 ORDER BY 1,2;
