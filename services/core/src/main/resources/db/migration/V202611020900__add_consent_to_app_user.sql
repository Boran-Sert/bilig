-- Kayıtta ayrı ayrı onaylanan aydınlatma metnini ve açık rızayı sürümüyle saklar.
ALTER TABLE app_user
    ADD COLUMN privacy_notice_version text,
    ADD COLUMN privacy_notice_accepted_at timestamptz,
    ADD COLUMN consent_version text,
    ADD COLUMN consent_accepted_at timestamptz;
