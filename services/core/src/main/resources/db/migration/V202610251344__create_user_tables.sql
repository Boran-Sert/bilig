-- Kullanıcı, kurum ve model çağrısı tablolarını oluşturur.
CREATE TABLE tenant (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

INSERT INTO tenant (name) VALUES ('Bilig');

CREATE TABLE app_user (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id bigint NOT NULL REFERENCES tenant (id),
    email text UNIQUE,
    password_hash text,
    display_name text NOT NULL,
    role text NOT NULL DEFAULT 'STUDENT'
        CHECK (role IN ('STUDENT', 'CONTENT_ADMIN', 'ADMIN')),
    grade smallint,
    explain_style text NOT NULL DEFAULT 'SIMPLE'
        CHECK (explain_style IN ('SIMPLE', 'EXAMPLES', 'STEP_BY_STEP')),
    external_user_id text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_app_user_tenant_id_external_user_id UNIQUE (tenant_id, external_user_id)
);

CREATE TABLE persistent_logins (
    series varchar(64) PRIMARY KEY,
    username varchar(254) NOT NULL,
    token varchar(64) NOT NULL,
    last_used timestamp NOT NULL
);

CREATE TABLE llm_call_log (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    task text NOT NULL,
    model text NOT NULL,
    prompt_version smallint NOT NULL,
    input_tokens integer NOT NULL,
    output_tokens integer NOT NULL,
    cache_read_tokens integer NOT NULL DEFAULT 0,
    cost_usd numeric(10, 6) NOT NULL,
    duration_ms integer NOT NULL,
    request_id text NOT NULL,
    user_id bigint REFERENCES app_user (id),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_llm_call_log_created_at ON llm_call_log (created_at);
