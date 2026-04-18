CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS memory_embeddings (
    id BIGSERIAL PRIMARY KEY,
    session_id TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding vector(384),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS memory_embeddings_session_idx
    ON memory_embeddings (session_id);

CREATE INDEX IF NOT EXISTS memory_embeddings_vector_idx
    ON memory_embeddings USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 10);
