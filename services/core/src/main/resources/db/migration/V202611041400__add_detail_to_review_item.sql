-- İnceleme kaydına kaynak sorunlarının ayrıntısını (sayfa, test, soru numarası) ekler.
ALTER TABLE review_item
    ADD COLUMN detail jsonb;
