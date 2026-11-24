-- ============================================================================
-- 008_full_text_search.sql
--
-- Búsqueda full-text en español sobre el corpus de tesis y los actos
-- clasificados. Postgres ts_vector + GIN index + trigger para mantener
-- la columna materializada al día.
--
-- Configuración de idioma: 'spanish' (stemming castellano, stop words).
-- Si en el futuro entran tesis en inglés, hay que hacer un setup
-- multilingüe (out of scope).
-- ============================================================================

BEGIN;

-- 1. tesis: columna tsv sobre rubro + texto
ALTER TABLE tesis ADD COLUMN IF NOT EXISTS tsv tsvector;

UPDATE tesis SET tsv = to_tsvector(
    'spanish',
    coalesce(rubro, '') || ' ' || coalesce(texto, '')
) WHERE tsv IS NULL;

CREATE INDEX IF NOT EXISTS idx_tesis_tsv ON tesis USING GIN(tsv);

DROP TRIGGER IF EXISTS tesis_tsv_update ON tesis;
CREATE TRIGGER tesis_tsv_update
BEFORE INSERT OR UPDATE OF rubro, texto ON tesis
FOR EACH ROW EXECUTE FUNCTION tsvector_update_trigger(
    tsv, 'pg_catalog.spanish', rubro, texto
);

-- 2. classifications: tsv sobre acto_reclamado.
--    classifications es append-only por trigger; respetamos eso: el tsv
--    se calcula UNA VEZ en el INSERT (mismo trigger built-in), nunca en
--    UPDATE — el trigger no_modify_classifications ya bloquea UPDATE.
ALTER TABLE classifications ADD COLUMN IF NOT EXISTS tsv tsvector;

-- Backfill: hay que deshabilitar el trigger de inmutabilidad UN MOMENTO
-- para poblar la columna nueva. Se vuelve a habilitar de inmediato.
ALTER TABLE classifications DISABLE TRIGGER no_modify_classifications;
UPDATE classifications SET tsv = to_tsvector(
    'spanish', coalesce(acto_reclamado, '')
) WHERE tsv IS NULL;
ALTER TABLE classifications ENABLE TRIGGER no_modify_classifications;

CREATE INDEX IF NOT EXISTS idx_class_tsv ON classifications USING GIN(tsv);

-- Para classifications: el tsv se calcula al insertar via función ad-hoc
-- (no podemos usar `BEFORE UPDATE` porque el trigger de inmutabilidad lo
-- bloquearía). Solo BEFORE INSERT.
CREATE OR REPLACE FUNCTION class_tsv_on_insert() RETURNS TRIGGER AS $$
BEGIN
    NEW.tsv := to_tsvector('spanish', coalesce(NEW.acto_reclamado, ''));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS class_tsv_insert ON classifications;
CREATE TRIGGER class_tsv_insert
BEFORE INSERT ON classifications
FOR EACH ROW EXECUTE FUNCTION class_tsv_on_insert();

COMMIT;
