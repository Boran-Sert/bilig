-- Bilgi katmanının düğüm tablosunu ve kelime arama indeksini oluşturur.
CREATE TABLE knowledge_node (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    node_type text NOT NULL
        CHECK (node_type IN ('AUTHOR', 'WORK', 'PERIOD', 'MOVEMENT', 'GENRE', 'CONCEPT')),
    name text NOT NULL,
    note_md text,
    status text NOT NULL DEFAULT 'DRAFT' CHECK (status IN ('DRAFT', 'PUBLISHED')),
    search_text text NOT NULL,
    embedding vector(1024),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_knowledge_node_node_type_name UNIQUE (node_type, name)
);

CREATE INDEX idx_knowledge_node_bm25
    ON knowledge_node USING bm25 (search_text) WITH (text_config = 'turkish');
