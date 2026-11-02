-- Sınıfı 9-12 ve mezun (13) değerleriyle sınırlar.
ALTER TABLE app_user
    ADD CONSTRAINT ck_app_user_grade CHECK (grade BETWEEN 9 AND 13);
