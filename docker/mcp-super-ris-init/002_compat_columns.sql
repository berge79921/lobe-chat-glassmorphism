ALTER TABLE IF EXISTS super_ris.rs
  ADD COLUMN IF NOT EXISTS rechtssatz_volltext text,
  ADD COLUMN IF NOT EXISTS fachgebiete text[] DEFAULT ARRAY[]::text[],
  ADD COLUMN IF NOT EXISTS entscheidungsdatum date;

ALTER TABLE IF EXISTS super_ris.te
  ADD COLUMN IF NOT EXISTS normalized_gz text,
  ADD COLUMN IF NOT EXISTS entscheidungsdatum date,
  ADD COLUMN IF NOT EXISTS source_json jsonb,
  ADD COLUMN IF NOT EXISTS original_html text;

CREATE INDEX IF NOT EXISTS idx_super_ris_rs_kurzinformation_fts
  ON super_ris.rs USING gin (to_tsvector('german', COALESCE(rechtssatz_volltext, kurzinformation, '')));

CREATE INDEX IF NOT EXISTS idx_super_ris_te_summary_fts
  ON super_ris.te USING gin (to_tsvector('german', COALESCE(summary, '')));
