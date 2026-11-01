package com.hataanalizi.core.admin;

import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

/** Yüklenen kaynak kayıtlarına veritabanı üzerinden erişir. */
public interface SourceDocumentRepository extends JpaRepository<SourceDocument, Long>, SourceDocumentRepositoryCustom {

    /** SHA-256 özetiyle daha önce yüklenmiş kaynağı bulur. */
    Optional<SourceDocument> findBySha256(String sha256);
}
