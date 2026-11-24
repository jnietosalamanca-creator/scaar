-- ============================================================================
-- 004_veredicto_7_categorias.sql
--
-- Permite que el proyectista corrija el veredicto a cualquiera de las 7
-- categorías de procedencia (no incluye 'no_aplica' — eso es decisión de
-- etiquetado de corpus, no veredicto de clasificación).
--
-- Semántica:
--   • Si el modelo activo (binario v0.2.0) dijo 'adjetivo' y la corrección
--     coincide con 'en_juicio_imposible' → equivalente, usar 'acepta'.
--     Idem 'sustantivo' ↔ 'en_juicio_diferida'.
--   • Cualquier otra categoría es una corrección legítima.
--
-- Las firmas HMAC existentes siguen verificando — la columna
-- firma_payload tiene la corregida grabada, recompute = igual.
-- ============================================================================

BEGIN;

-- También soltar el CHECK columna-level autogenerado del schema.sql original
-- (named 'classification_validations_clasificacion_corregida_check')
ALTER TABLE classification_validations
    DROP CONSTRAINT IF EXISTS classification_validations_clasificacion_corregida_check;
ALTER TABLE classification_validations
    DROP CONSTRAINT IF EXISTS val_corregida_check;

ALTER TABLE classification_validations
    ADD CONSTRAINT val_corregida_check CHECK (
        clasificacion_corregida IS NULL
        OR clasificacion_corregida IN (
            -- Compat con firmas pasadas (las 2 viejas)
            'adjetivo',
            'sustantivo',
            -- Las 7 categorías nuevas (sin no_aplica)
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
