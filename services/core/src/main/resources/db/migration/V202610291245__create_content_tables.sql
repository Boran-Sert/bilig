-- İçerik bloklarını, soruları, kazanım bağlarını ve testleri oluşturur.
CREATE TABLE content_block (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_page_id bigint NOT NULL REFERENCES source_page (id) ON DELETE CASCADE,
    curriculum_unit_id bigint REFERENCES curriculum_unit (id),
    block_type text NOT NULL
        CHECK (block_type IN ('BILGI', 'ALINTI', 'ETKINLIK', 'METIN', 'BASLIK')),
    position integer NOT NULL,
    title_path text NOT NULL,
    markdown text NOT NULL,
    confidence real,
    status text NOT NULL DEFAULT 'DRAFT'
        CHECK (status IN ('DRAFT', 'REVIEW', 'PUBLISHED', 'REJECTED')),
    search_text text NOT NULL,
    embedding vector(1024),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_content_block_source_page_id_position UNIQUE (source_page_id, position)
);

CREATE INDEX idx_content_block_embedding
    ON content_block USING hnsw (embedding vector_cosine_ops);
CREATE INDEX idx_content_block_bm25
    ON content_block USING bm25 (search_text) WITH (text_config = 'turkish');

CREATE TABLE content_block_outcome (
    content_block_id bigint NOT NULL REFERENCES content_block (id) ON DELETE CASCADE,
    learning_outcome_id bigint NOT NULL REFERENCES learning_outcome (id),
    mapped_by text NOT NULL CHECK (mapped_by IN ('MODEL', 'HUMAN', 'SOURCE')),
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (content_block_id, learning_outcome_id)
);

CREATE INDEX idx_content_block_outcome_learning_outcome_id
    ON content_block_outcome (learning_outcome_id);

CREATE TABLE question (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_page_id bigint REFERENCES source_page (id),
    curriculum_unit_id bigint NOT NULL REFERENCES curriculum_unit (id),
    origin text NOT NULL CHECK (origin IN ('SOURCE', 'GENERATED')),
    content jsonb NOT NULL,
    correct_option char(1) NOT NULL CHECK (correct_option IN ('A', 'B', 'C', 'D', 'E')),
    hint text,
    difficulty smallint CHECK (difficulty BETWEEN 1 AND 5),
    status text NOT NULL DEFAULT 'DRAFT'
        CHECK (status IN ('DRAFT', 'REVIEW', 'PUBLISHED', 'REJECTED')),
    content_hash char(64) NOT NULL UNIQUE,
    embedding vector(1024),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_question_curriculum_unit_id_status
    ON question (curriculum_unit_id, status);
CREATE INDEX idx_question_embedding
    ON question USING hnsw (embedding vector_cosine_ops);

CREATE TABLE question_outcome (
    question_id bigint NOT NULL REFERENCES question (id) ON DELETE CASCADE,
    learning_outcome_id bigint NOT NULL REFERENCES learning_outcome (id),
    mapped_by text NOT NULL CHECK (mapped_by IN ('MODEL', 'HUMAN', 'SOURCE')),
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (question_id, learning_outcome_id)
);

CREATE INDEX idx_question_outcome_learning_outcome_id
    ON question_outcome (learning_outcome_id);

CREATE TABLE exam (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    curriculum_unit_id bigint REFERENCES curriculum_unit (id),
    source_document_id bigint REFERENCES source_document (id),
    title text NOT NULL,
    exam_type text NOT NULL DEFAULT 'AYT' CHECK (exam_type IN ('AYT')),
    status text NOT NULL DEFAULT 'DRAFT' CHECK (status IN ('DRAFT', 'PUBLISHED')),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE exam_question (
    exam_id bigint NOT NULL REFERENCES exam (id) ON DELETE CASCADE,
    question_id bigint NOT NULL REFERENCES question (id),
    position smallint NOT NULL,
    PRIMARY KEY (exam_id, question_id),
    CONSTRAINT uq_exam_question_exam_id_position UNIQUE (exam_id, position)
);
