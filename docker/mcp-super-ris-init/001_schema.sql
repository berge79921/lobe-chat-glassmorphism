CREATE SCHEMA IF NOT EXISTS super_ris;

CREATE TABLE IF NOT EXISTS super_ris.rs (
  rs_number text PRIMARY KEY,
  rechtssatz_volltext text,
  kurzinformation text,
  rechtsgebiet_primary text,
  schlagworte text[] DEFAULT ARRAY[]::text[],
  fachgebiete text[] DEFAULT ARRAY[]::text[],
  entscheidungsdatum date
);

CREATE TABLE IF NOT EXISTS super_ris.te (
  stable_key text PRIMARY KEY,
  normalized_gz text,
  geschaeftszahl text,
  datum date,
  entscheidungsdatum date,
  summary text,
  source_json jsonb,
  original_html text
);

CREATE INDEX IF NOT EXISTS idx_super_ris_rs_kurzinformation_fts
  ON super_ris.rs USING gin (to_tsvector('german', COALESCE(rechtssatz_volltext, kurzinformation, '')));

CREATE INDEX IF NOT EXISTS idx_super_ris_te_summary_fts
  ON super_ris.te USING gin (to_tsvector('german', COALESCE(summary, '')));
