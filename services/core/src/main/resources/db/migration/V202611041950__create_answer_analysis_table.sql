-- Yanlış öğrenci cevaplarının AI hata türü analizini kaydeder.
CREATE TABLE answer_analysis (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    student_answer_id bigint NOT NULL UNIQUE REFERENCES student_answer (id) ON DELETE CASCADE,
    error_type text NOT NULL CHECK (
        error_type IN ('KNOWLEDGE', 'MISCONCEPTION', 'ATTENTION', 'READING')
    ),
    needs_review boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now()
);
