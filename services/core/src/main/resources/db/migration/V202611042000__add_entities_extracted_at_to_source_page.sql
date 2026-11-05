-- Bilgi katmanı adımının işlediği sayfayı işaretler; işaretli sayfa tekrar modele gitmez.
ALTER TABLE source_page
    ADD COLUMN entities_extracted_at timestamptz;
