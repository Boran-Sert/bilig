-- Program katmanının tablolarını ve kazanım arama indekslerini oluşturur.
CREATE TABLE subject (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code text NOT NULL UNIQUE,
    name text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE curriculum (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    subject_id bigint NOT NULL REFERENCES subject (id),
    name text NOT NULL,
    model text NOT NULL CHECK (model IN ('LEGACY', 'MAARIF')),
    year smallint NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_curriculum_subject_id_name UNIQUE (subject_id, name)
);

CREATE TABLE learning_outcome_group (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    curriculum_id bigint NOT NULL REFERENCES curriculum (id),
    code text NOT NULL,
    name text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_learning_outcome_group_curriculum_id_code UNIQUE (curriculum_id, code)
);

CREATE TABLE learning_outcome (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    learning_outcome_group_id bigint NOT NULL REFERENCES learning_outcome_group (id),
    code text NOT NULL,
    title text NOT NULL,
    meb_explanation text,
    search_text text NOT NULL,
    embedding vector(1024),
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_learning_outcome_group_id_code UNIQUE (learning_outcome_group_id, code)
);

CREATE INDEX idx_learning_outcome_embedding
    ON learning_outcome USING hnsw (embedding vector_cosine_ops);
CREATE INDEX idx_learning_outcome_bm25
    ON learning_outcome USING bm25 (search_text) WITH (text_config = 'turkish');

CREATE TABLE curriculum_unit (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    curriculum_id bigint NOT NULL REFERENCES curriculum (id),
    grade smallint NOT NULL CHECK (grade BETWEEN 9 AND 12),
    unit_no smallint NOT NULL,
    title text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_curriculum_unit_curriculum_id_grade_unit_no
        UNIQUE (curriculum_id, grade, unit_no)
);

CREATE TABLE curriculum_unit_outcome (
    curriculum_unit_id bigint NOT NULL REFERENCES curriculum_unit (id),
    learning_outcome_id bigint NOT NULL REFERENCES learning_outcome (id),
    PRIMARY KEY (curriculum_unit_id, learning_outcome_id)
);
