-- Bilgi bağlarını, öğrenci sohbetlerini, inceleme listesini ve bildirimleri oluşturur.
CREATE TABLE knowledge_node_alias (
    knowledge_node_id bigint NOT NULL REFERENCES knowledge_node (id) ON DELETE CASCADE,
    normalized_alias text NOT NULL,
    alias text NOT NULL,
    PRIMARY KEY (knowledge_node_id, normalized_alias)
);

CREATE INDEX idx_knowledge_node_alias_normalized_alias
    ON knowledge_node_alias (normalized_alias);

CREATE TABLE knowledge_edge (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    from_node_id bigint NOT NULL REFERENCES knowledge_node (id),
    to_node_id bigint NOT NULL REFERENCES knowledge_node (id),
    relation text NOT NULL
        CHECK (relation IN ('WROTE', 'HAS_GENRE', 'IN_PERIOD', 'IN_MOVEMENT', 'RELATED')),
    evidence_content_block_id bigint REFERENCES content_block (id),
    status text NOT NULL DEFAULT 'DRAFT'
        CHECK (status IN ('DRAFT', 'PUBLISHED', 'REJECTED')),
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_knowledge_edge_from_to_relation
        UNIQUE (from_node_id, to_node_id, relation),
    CHECK (from_node_id <> to_node_id)
);

CREATE TABLE tutor_conversation (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id bigint NOT NULL REFERENCES app_user (id),
    question_id bigint REFERENCES question (id),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE tutor_message (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tutor_conversation_id bigint NOT NULL REFERENCES tutor_conversation (id) ON DELETE CASCADE,
    role text NOT NULL CHECK (role IN ('USER', 'ASSISTANT')),
    content text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_tutor_message_tutor_conversation_id
    ON tutor_message (tutor_conversation_id);

CREATE TABLE tutor_message_citation (
    tutor_message_id bigint NOT NULL REFERENCES tutor_message (id) ON DELETE CASCADE,
    content_block_id bigint NOT NULL REFERENCES content_block (id),
    PRIMARY KEY (tutor_message_id, content_block_id)
);

CREATE TABLE review_item (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    reason text NOT NULL
        CHECK (reason IN (
            'LOW_CONFIDENCE',
            'NO_ANSWER_KEY',
            'PROFILE_APPROVAL',
            'VALIDATION_FAILED',
            'NEW_LINK',
            'NAME_MERGE'
        )),
    source_document_id bigint REFERENCES source_document (id),
    content_block_id bigint REFERENCES content_block (id),
    question_id bigint REFERENCES question (id),
    knowledge_node_id bigint REFERENCES knowledge_node (id),
    knowledge_edge_id bigint REFERENCES knowledge_edge (id),
    status text NOT NULL DEFAULT 'OPEN'
        CHECK (status IN ('OPEN', 'APPROVED', 'REJECTED')),
    decided_by bigint REFERENCES app_user (id),
    decided_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (num_nonnulls(
        source_document_id, content_block_id, question_id, knowledge_node_id, knowledge_edge_id
    ) = 1)
);

CREATE INDEX idx_review_item_status
    ON review_item (status);

CREATE TABLE content_report (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id bigint NOT NULL REFERENCES app_user (id),
    question_id bigint REFERENCES question (id),
    tutor_message_id bigint REFERENCES tutor_message (id),
    note text,
    status text NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN', 'RESOLVED')),
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (num_nonnulls(question_id, tutor_message_id) = 1)
);
