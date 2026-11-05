package com.hataanalizi.core.admin;

import jakarta.persistence.EntityManager;
import jakarta.persistence.PersistenceContext;
import java.util.List;
import java.util.Optional;
import org.springframework.stereotype.Repository;

/** Kaynak kayıtları için PostgreSQL'e özel atomik sorguları uygular. */
@Repository
public class SourceDocumentRepositoryCustomImpl implements SourceDocumentRepositoryCustom {

    @PersistenceContext
    private EntityManager entityManager;

    /** SHA-256 çakışmasını hata üretmeden atomik olarak yönetir. */
    @Override
    public Optional<Long> insertIfAbsent(
            String title, String sha256, String filePath, String kind, Long uploadedBy, Long answerKeySourceId) {

        @SuppressWarnings("unchecked")
        List<Number> results = entityManager
                .createNativeQuery("""
                INSERT INTO source_document (
                    title,
                    sha256,
                    file_path,
                    kind,
                    uploaded_by,
                    answer_key_source_id
                )
                VALUES (
                    :title,
                    :sha256,
                    :filePath,
                    :kind,
                    :uploadedBy,
                    :answerKeySourceId
                )
                ON CONFLICT (sha256) DO NOTHING
                RETURNING id
                """)
                .setParameter("title", title)
                .setParameter("sha256", sha256)
                .setParameter("filePath", filePath)
                .setParameter("kind", kind)
                .setParameter("uploadedBy", uploadedBy)
                .setParameter("answerKeySourceId", answerKeySourceId)
                .getResultList();

        if (results.isEmpty()) {
            return Optional.empty();
        }

        return Optional.of(results.get(0).longValue());
    }

    /** Kaydın dosya yolunu günceller. */
    @Override
    public void updateFilePath(long sourceId, String filePath) {
        entityManager
                .createNativeQuery("""
                UPDATE source_document
                SET file_path = :filePath
                WHERE id = :sourceId
                """)
                .setParameter("filePath", filePath)
                .setParameter("sourceId", sourceId)
                .executeUpdate();
    }
}
