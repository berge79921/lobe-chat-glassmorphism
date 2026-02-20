-- Rebuild FTS indexes with expressions matching production MCP queries.
-- Safe to run repeatedly.

DROP INDEX IF EXISTS super_ris.idx_super_ris_rs_kurzinformation_fts;
CREATE INDEX IF NOT EXISTS idx_super_ris_rs_kurzinformation_fts
  ON super_ris.rs USING gin (to_tsvector('german', COALESCE(rechtssatz_volltext, kurzinformation, '')));

DROP INDEX IF EXISTS super_ris.idx_super_ris_te_summary_fts;
CREATE INDEX IF NOT EXISTS idx_super_ris_te_summary_fts
  ON super_ris.te USING gin (to_tsvector('german', COALESCE(summary, '')));
