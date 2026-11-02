-- Kullanıcının kayıtta verdiği açık rızanın sürümünü ve zamanını saklar.
ALTER TABLE app_user
    ADD COLUMN consent_version text,
    ADD COLUMN consent_accepted_at timestamptz;
