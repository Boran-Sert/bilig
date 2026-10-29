package com.hataanalizi.core;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.context.annotation.Import;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.transaction.annotation.Transactional;

/** İş kuyruğu ve kaynak tablolarının migration sözleşmesini doğrular. */
@ActiveProfiles("test")
@SpringBootTest
@Import(TestcontainersConfiguration.class)
@Transactional
class JobAndSourceTablesIT {

    private final JdbcTemplate jdbcTemplate;

    /** Test veritabanı erişimini hazırlar. */
    @Autowired
    JobAndSourceTablesIT(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    /** Migration'ın tabloları ve kuyruk indekslerini oluşturduğunu doğrular. */
    @Test
    void createsTablesAndBackgroundJobIndexes() {
        List<String> tables = jdbcTemplate.queryForList("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name IN ('background_job', 'source_document', 'source_page')
                ORDER BY table_name
                """, String.class);
        List<String> indexes = jdbcTemplate.queryForList("""
                SELECT indexname
                FROM pg_indexes
                WHERE schemaname = 'public'
                  AND indexname IN (
                    'idx_background_job_status_run_after',
                    'idx_background_job_source_id'
                  )
                """, String.class);

        assertEquals(List.of("background_job", "source_document", "source_page"), tables);
        assertTrue(indexes.containsAll(List.of("idx_background_job_status_run_after", "idx_background_job_source_id")));
    }

    /** Kaynak belgenin tür varsayılanını ve iş yükünün JSONB biçimini doğrular. */
    @Test
    void usesUnknownKindAndAcceptsSourcePayload() {
        Long uploadedBy = insertUser();
        String hash = createHash();
        String kind = jdbcTemplate.queryForObject(
                """
                INSERT INTO source_document (title, sha256, file_path, uploaded_by)
                VALUES (?, ?, ?, ?)
                RETURNING kind
                """, String.class, "Test source", hash, "/data/sources/test.pdf", uploadedBy);
        String payload = jdbcTemplate.queryForObject("""
                INSERT INTO background_job (job_type, payload)
                VALUES ('INGEST_SOURCE', '{"sourceId": 12}'::jsonb)
                RETURNING payload::text
                """, String.class);

        assertEquals("UNKNOWN", kind);
        assertEquals("{\"sourceId\": 12}", payload);
    }

    /** Aynı özete sahip ikinci kaynak belgenin reddedildiğini doğrular. */
    @Test
    void rejectsDuplicateSourceDocumentHash() {
        Long uploadedBy = insertUser();
        String hash = createHash();
        insertSourceDocument(uploadedBy, hash);

        assertThrows(DataIntegrityViolationException.class, () -> insertSourceDocument(uploadedBy, hash));
    }

    /** Kullanıcı tablosuna test kaydı ekler. */
    private Long insertUser() {
        return jdbcTemplate.queryForObject("""
                INSERT INTO app_user (tenant_id, display_name)
                SELECT id, 'Test user'
                FROM tenant
                ORDER BY id
                LIMIT 1
                RETURNING id
                """, Long.class);
    }

    /** Benzersiz bir 64 karakterlik SHA-256 değeri üretir. */
    private String createHash() {
        return UUID.randomUUID().toString().replace("-", "")
                + UUID.randomUUID().toString().replace("-", "");
    }

    /** Kaynak belgesi ekler. */
    private void insertSourceDocument(Long uploadedBy, String hash) {
        jdbcTemplate.update("""
                INSERT INTO source_document (title, sha256, file_path, uploaded_by)
                VALUES (?, ?, ?, ?)
                """, "Test source", hash, "/data/sources/test.pdf", uploadedBy);
    }
}
