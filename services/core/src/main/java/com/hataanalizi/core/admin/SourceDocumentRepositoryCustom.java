package com.hataanalizi.core.admin;

import java.util.Optional;

/** Kaynak kayıtları üzerinde PostgreSQL'e özel atomik işlemleri tanımlar. */
public interface SourceDocumentRepositoryCustom {

    /**
     * SHA-256 daha önce kaydedilmemişse yeni kaynak ekler.
     * Kayıt eklenirse ID, duplicate ise boş Optional döndürür.
     */
    Optional<Long> insertIfAbsent(String title, String sha256, String filePath, Long uploadedBy);

    /** Kaynağın dosya yolunu günceller. */
    void updateFilePath(long sourceId, String filePath);
}
