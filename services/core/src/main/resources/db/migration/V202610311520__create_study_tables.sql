-- Test çözme oturumlarını ve öğrenci cevaplarını oluşturur.
CREATE TABLE study_session (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id bigint NOT NULL REFERENCES app_user (id),
    exam_id bigint REFERENCES exam (id),
    status text NOT NULL DEFAULT 'IN_PROGRESS'
        CHECK (status IN ('IN_PROGRESS', 'COMPLETED')),
    current_position smallint NOT NULL DEFAULT 1,
    net numeric(5, 2),
    started_at timestamptz NOT NULL DEFAULT now(),
    completed_at timestamptz
);

CREATE UNIQUE INDEX uq_study_session_active
    ON study_session (user_id, exam_id)
    WHERE status = 'IN_PROGRESS';
CREATE INDEX idx_study_session_user_id
    ON study_session (user_id);

CREATE TABLE student_answer (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    study_session_id bigint NOT NULL REFERENCES study_session (id) ON DELETE CASCADE,
    question_id bigint NOT NULL REFERENCES question (id),
    selected_option char(1) NOT NULL CHECK (selected_option IN ('A', 'B', 'C', 'D', 'E')),
    is_correct boolean NOT NULL,
    duration_ms integer,
    hint_used boolean NOT NULL DEFAULT false,
    explanation_opened boolean NOT NULL DEFAULT false,
    error_type text CHECK (error_type IN ('KNOWLEDGE', 'MISCONCEPTION', 'ATTENTION', 'READING')),
    answered_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_student_answer_study_session_id_question_id
        UNIQUE (study_session_id, question_id)
);

CREATE INDEX idx_student_answer_question_id
    ON student_answer (question_id);
