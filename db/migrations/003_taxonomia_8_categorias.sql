-- ============================================================================
-- 003_taxonomia_8_categorias.sql
--
-- Cambia el universo de etiquetas de tesis de 3 (adjetivo, sustantivo,
-- no_aplica) a 8 categorías que reflejan el árbol completo de procedencia
-- de amparo:
--
--   fuera_juicio | en_juicio_imposible | en_juicio_diferida
--   post_juicio_general | post_juicio_ejecucion | post_juicio_prematuro
--   tercero_extrano | sentencia_definitiva | no_aplica
--
-- Migración de datos:
--   • dummy_v1_obsoleto: auto-map (datos obsoletos, solo para no romper FK):
--       'adjetivo'   → 'en_juicio_imposible'  (semánticamente equivalente
--                                              bajo el criterio derogado)
--       'sustantivo' → 'en_juicio_diferida'
--       'no_aplica'  → 'no_aplica'
--   • sjf_scraping etiquetadas como adj/sus por el usuario: se RESETEAN a
--     NULL para que se re-etiqueten con la taxonomía nueva.
--   • sjf_scraping con 'no_aplica' se mantienen como 'no_aplica'.
-- ============================================================================

BEGIN;

-- 1. Soltar el CHECK viejo PRIMERO (el universo nuevo y el viejo conviven
--    transitoriamente en este script)
ALTER TABLE tesis DROP CONSTRAINT IF EXISTS tesis_etiqueta_check;

-- 2. Auto-map del dummy obsoleto al nuevo vocabulario
UPDATE tesis SET etiqueta = 'en_juicio_imposible'
    WHERE fuente = 'dummy_v1_obsoleto' AND etiqueta = 'adjetivo';
UPDATE tesis SET etiqueta = 'en_juicio_diferida'
    WHERE fuente = 'dummy_v1_obsoleto' AND etiqueta = 'sustantivo';

-- 3. Reset de las SJF que el usuario etiquetó adj/sus — necesitan re-revisión
UPDATE tesis
   SET etiqueta = NULL,
       etiquetada_por = NULL,
       etiquetada_at = NULL
 WHERE fuente <> 'dummy_v1_obsoleto'
   AND etiqueta IN ('adjetivo', 'sustantivo');

-- 4. Poner el CHECK nuevo (NULL sigue siendo 'pendiente')
ALTER TABLE tesis ADD CONSTRAINT tesis_etiqueta_check
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
    ));

COMMIT;

-- Verificación rápida:
-- SELECT fuente, etiqueta, COUNT(*) FROM tesis GROUP BY 1,2 ORDER BY 1,2;
