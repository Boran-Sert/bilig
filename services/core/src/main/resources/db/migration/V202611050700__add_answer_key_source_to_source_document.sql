-- Testin cevaplarının okunacağı ayrı cevap anahtarı kaynağını tutar.
ALTER TABLE source_document
    ADD COLUMN answer_key_source_id bigint REFERENCES source_document (id);
