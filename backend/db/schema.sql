CREATE TABLE IF NOT EXISTS regulations (
  node_id TEXT PRIMARY KEY,
  reg_type TEXT NOT NULL,
  number INTEGER NOT NULL,
  year INTEGER NOT NULL,
  title TEXT NOT NULL,
  revoked INTEGER DEFAULT 0,
  revoked_by TEXT
);

CREATE TABLE IF NOT EXISTS provisions (
  node_id TEXT PRIMARY KEY,
  regulation_id TEXT NOT NULL REFERENCES regulations(node_id),
  parent_id TEXT REFERENCES provisions(node_id),
  type TEXT NOT NULL,
  number TEXT,
  title TEXT,
  text TEXT
);
CREATE INDEX IF NOT EXISTS idx_prov_parent ON provisions(parent_id);
CREATE INDEX IF NOT EXISTS idx_prov_reg ON provisions(regulation_id);

CREATE TABLE IF NOT EXISTS provision_edges (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_id TEXT NOT NULL,
  target_id TEXT NOT NULL,
  edge_type TEXT NOT NULL,
  confidence REAL DEFAULT 1.0,
  UNIQUE(source_id, target_id, edge_type)
);
CREATE INDEX IF NOT EXISTS idx_edges_source ON provision_edges(source_id);
CREATE INDEX IF NOT EXISTS idx_edges_target ON provision_edges(target_id);

CREATE TABLE IF NOT EXISTS norms (
  id TEXT PRIMARY KEY,
  provision_id TEXT NOT NULL,
  description TEXT NOT NULL,
  subjects TEXT,
  severity TEXT NOT NULL,
  consequence TEXT,
  obligation_markers TEXT,
  quantities TEXT
);

CREATE TABLE IF NOT EXISTS putusan (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  case_number TEXT NOT NULL UNIQUE,
  court TEXT NOT NULL,
  court_type TEXT,
  year INTEGER NOT NULL,
  province TEXT,
  dispute_type TEXT,
  outcome TEXT,
  facts_summary TEXT,
  pdf_file TEXT
);

CREATE TABLE IF NOT EXISTS putusan_citations (
  putusan_id INTEGER NOT NULL REFERENCES putusan(id),
  provision_id TEXT,
  raw_citation TEXT NOT NULL,
  pasal TEXT
);
CREATE INDEX IF NOT EXISTS idx_pc_provision ON putusan_citations(provision_id);

CREATE VIRTUAL TABLE IF NOT EXISTS provisions_fts USING fts5(node_id, text);
