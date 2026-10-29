-- İş kuyruğu, yüklenen dosyalar ve sayfaları için tabloları oluşturur.
CREATE TABLE background_job (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    job_type text NOT NULL
        CHECK (job_type IN (
            'INGEST_SOURCE',
            'BUILD_PROGRAM',
            'EXTRACT_ENTITIES',
            'MATCH_OUTCOMES',
            'EMBED',
            'GENERATE_QUESTIONS',
            'ANALYZE_ANSWER'
        )),
    status text NOT NULL DEFAULT 'QUEUED'
        CHECK (status IN ('QUEUED', 'RUNNING', 'DONE', 'FAILED')),
    last_completed_step text,
    attempts smallint NOT NULL DEFAULT 0,
    payload jsonb NOT NULL,
    last_error text,
    run_after timestamptz NOT NULL DEFAULT now(),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_background_job_status_run_after
    ON background_job (status, run_after);
CREATE INDEX idx_background_job_source_id
    ON background_job ((payload->>'sourceId'));

CREATE TABLE source_document (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    curriculum_id bigint REFERENCES curriculum (id),
    kind text NOT NULL DEFAULT 'UNKNOWN'
        CHECK (kind IN ('UNKNOWN', 'PROGRAM', 'TEXTBOOK', 'TEST', 'QUESTION_BANK', 'ANSWER_KEY')),
    title text NOT NULL,
    publisher text,
    year smallint,
    grade smallint,
    sha256 char(64) NOT NULL UNIQUE,
    file_path text NOT NULL,
    text_layer_valid boolean,
    profile_name text,
    license_status text NOT NULL DEFAULT 'UNKNOWN'
        CHECK (license_status IN ('MEB', 'PERMITTED', 'UNKNOWN')),
    status text NOT NULL DEFAULT 'UPLOADED'
        CHECK (status IN ('UPLOADED', 'PROCESSING', 'REVIEW', 'PUBLISHED', 'FAILED')),
    uploaded_by bigint NOT NULL REFERENCES app_user (id),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE source_page (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_document_id bigint NOT NULL REFERENCES source_document (id) ON DELETE CASCADE,
    page_no integer NOT NULL,
    image_path text,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_source_page_source_document_id_page_no UNIQUE (source_document_id, page_no)
);
