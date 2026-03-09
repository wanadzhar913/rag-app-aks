CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS document_extractions (
    id              SERIAL PRIMARY KEY,
    document_name   TEXT NOT NULL,
    page_number     INTEGER,
    raw_text        TEXT,
    tables          JSONB DEFAULT '[]'::jsonb,
    metadata        JSONB DEFAULT '{}'::jsonb,
    embedding       vector(1536),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_doc_extractions_name
    ON document_extractions (document_name);

CREATE INDEX IF NOT EXISTS idx_doc_extractions_metadata
    ON document_extractions USING GIN (metadata);

CREATE INDEX IF NOT EXISTS idx_doc_extractions_embedding
    ON document_extractions USING hnsw (embedding vector_cosine_ops);
