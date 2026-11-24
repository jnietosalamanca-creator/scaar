-- ============================================================================
-- 005_classifications_multiclase.sql
--
-- classifications.prediccion ya no está restringido a ('adjetivo','sustantivo').
-- Acepta cualquier valor de las 8 categorías de la taxonomía + las 2 legacy.
--
-- Logs históricos (firmados con prediccion='adjetivo'/'sustantivo') siguen
-- siendo válidos — el trigger de inmutabilidad NO los toca, y el CHECK nuevo
-- es estrictamente más permisivo.
-- ============================================================================

BEGIN;

-- Soltar el CHECK column-level autogenerado por SQLAlchemy
ALTER TABLE classifications
    DROP CONSTRAINT IF EXISTS classifications_prediccion_check;
ALTER TABLE classifications
    DROP CONSTRAINT IF EXISTS class_pred_check;

-- Nuevo CHECK ampliado
ALTER TABLE classifications ADD CONSTRAINT class_pred_check CHECK (
    prediccion IN (
        -- Legacy (preservado para verificación de logs antiguos)
        'adjetivo',
        'sustantivo',
        -- Las 8 categorías nuevas
        'fuera_juicio',
        'en_juicio_imposible',
        'en_juicio_diferida',
        'post_juicio_general',
        'post_juicio_ejecucion',
        'post_juicio_prematuro',
        'tercero_extrano',
        'sentencia_definitiva'
    )
);

COMMIT;

-- Verificación: los CHECKs deberían ser solo el nuevo + prob_adjetivo
-- SELECT conname FROM pg_constraint
--  WHERE conrelid='classifications'::regclass AND contype='c';
