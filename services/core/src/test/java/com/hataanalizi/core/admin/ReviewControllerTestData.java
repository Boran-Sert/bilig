package com.hataanalizi.core.admin;

import java.util.UUID;
import org.springframework.jdbc.core.JdbcTemplate;

/** İnceleme uçlarının entegrasyon testleri için PostgreSQL verisi oluşturur. */
class ReviewControllerTestData {

    private final JdbcTemplate jdbcTemplate;

    /** Test veritabanı bağlantısını saklar. */
    ReviewControllerTestData(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    /** Soru, paragraf, kazanım ve açık/karara bağlanmış incelemeleri oluşturur. */
    ReviewFixture createReviewFixture() {
        createAdmin();
        long sourcePageId = createSourcePage();
        long curriculumId = createCurriculum();
        long curriculumUnitId = createCurriculumUnit(curriculumId);
        long outcomeGroupId = createOutcomeGroup(curriculumId);
        long firstOutcomeId = createOutcome(outcomeGroupId, "A.2.6", "Şahıs kadrosu");
        long secondOutcomeId = createOutcome(outcomeGroupId, "A.2.7", "Zaman ve mekân");
        long questionId = createQuestion(sourcePageId, curriculumUnitId);
        long blockId = createBlock(sourcePageId);
        createLinks(questionId, firstOutcomeId, blockId, secondOutcomeId);
        long questionReviewId = createReview(questionId, null, "LOW_CONFIDENCE", "OPEN", "2026-11-02T10:00:00Z");
        long blockReviewId = createReview(null, blockId, "LOW_CONFIDENCE", "OPEN", "2026-11-02T11:00:00Z");
        long decidedReviewId = createReview(questionId, null, "LOW_CONFIDENCE", "APPROVED", "2026-11-02T09:00:00Z");
        return new ReviewFixture(
                questionId, blockId, firstOutcomeId, secondOutcomeId, questionReviewId, blockReviewId, decidedReviewId);
    }

    /** İnceleme kaydını hedefi, sebebi ve oluşturulma zamanıyla ekler. */
    long createReview(Long questionId, Long contentBlockId, String reason, String status, String createdAt) {
        return jdbcTemplate.queryForObject("""
                INSERT INTO review_item (reason, question_id, content_block_id, status, created_at)
                VALUES (?, ?, ?, ?, ?::timestamptz)
                RETURNING id
                """, Long.class, reason, questionId, contentBlockId, status, createdAt);
    }

    /** İçerik yöneticisi kullanıcısını test tenant'ına ekler. */
    private void createAdmin() {
        jdbcTemplate.update("""
                INSERT INTO app_user (id, tenant_id, display_name) OVERRIDING SYSTEM VALUE
                SELECT 1001, id, 'Review test admin'
                FROM tenant
                ORDER BY id
                LIMIT 1
                """);
    }

    /** Test kaynağını ve üçüncü sayfasını oluşturur. */
    private long createSourcePage() {
        String uniqueValue = UUID.randomUUID().toString().replace("-", "");
        Long sourceId = jdbcTemplate.queryForObject("""
                INSERT INTO source_document (title, sha256, file_path, uploaded_by)
                VALUES ('İnceleme kaynağı', ?, 'sources/review-test.pdf', 1001)
                RETURNING id
                """, Long.class, uniqueValue + uniqueValue);
        return jdbcTemplate.queryForObject("""
                INSERT INTO source_page (source_document_id, page_no)
                VALUES (?, 3)
                RETURNING id
                """, Long.class, sourceId);
    }

    /** Test kazanımları için ders ve programı oluşturur. */
    private long createCurriculum() {
        String uniqueValue = UUID.randomUUID().toString();
        Long subjectId = jdbcTemplate.queryForObject(
                "INSERT INTO subject (code, name) VALUES (?, ?) RETURNING id", Long.class, uniqueValue, uniqueValue);
        return jdbcTemplate.queryForObject(
                "INSERT INTO curriculum (subject_id, name, model, year) VALUES (?, ?, 'LEGACY', 2018) RETURNING id",
                Long.class,
                subjectId,
                uniqueValue);
    }

    /** Test sorusu için program ünitesini oluşturur. */
    private long createCurriculumUnit(long curriculumId) {
        return jdbcTemplate.queryForObject(
                """
                INSERT INTO curriculum_unit (curriculum_id, grade, unit_no, title)
                VALUES (?, 12, 1, ?)
                RETURNING id
                """, Long.class, curriculumId, UUID.randomUUID().toString());
    }

    /** Test kazanımları için kazanım grubunu oluşturur. */
    private long createOutcomeGroup(long curriculumId) {
        String uniqueValue = UUID.randomUUID().toString();
        return jdbcTemplate.queryForObject("""
                INSERT INTO learning_outcome_group (curriculum_id, code, name)
                VALUES (?, ?, ?)
                RETURNING id
                """, Long.class, curriculumId, uniqueValue, uniqueValue);
    }

    /** Test kazanımını belirtilen gruba ekler. */
    private long createOutcome(long outcomeGroupId, String code, String title) {
        return jdbcTemplate.queryForObject("""
                INSERT INTO learning_outcome (learning_outcome_group_id, code, title, search_text)
                VALUES (?, ?, ?, ?)
                RETURNING id
                """, Long.class, outcomeGroupId, code, title, title);
    }

    /** Test sorusunu sayfaya bağlar. */
    private long createQuestion(long sourcePageId, long curriculumUnitId) {
        String uniqueHash = UUID.randomUUID().toString().replace("-", "")
                + UUID.randomUUID().toString().replace("-", "");
        return jdbcTemplate.queryForObject("""
                INSERT INTO question (
                    source_page_id, curriculum_unit_id, origin, content, correct_option, content_hash
                )
                VALUES (?, ?, 'SOURCE',
                        '{"stem":[{"type":"paragraph","md":"Soru kökü"}],"options":[]}'::jsonb,
                        'A', ?)
                RETURNING id
                """, Long.class, sourcePageId, curriculumUnitId, uniqueHash);
    }

    /** Test paragrafını sayfaya bağlar. */
    private long createBlock(long sourcePageId) {
        return jdbcTemplate.queryForObject("""
                INSERT INTO content_block (
                    source_page_id, block_type, position, title_path, markdown, search_text
                )
                VALUES (?, 'BILGI', 1, 'Roman', 'Paragraf metni', 'Roman Paragraf metni')
                RETURNING id
                """, Long.class, sourcePageId);
    }

    /** Soruya ve paragrafa MODEL eşleştirmelerini ekler. */
    private void createLinks(long questionId, long questionOutcomeId, long blockId, long blockOutcomeId) {
        jdbcTemplate.update("""
                INSERT INTO question_outcome (question_id, learning_outcome_id, mapped_by)
                VALUES (?, ?, 'MODEL')
                """, questionId, questionOutcomeId);
        jdbcTemplate.update("""
                INSERT INTO content_block_outcome (content_block_id, learning_outcome_id, mapped_by)
                VALUES (?, ?, 'MODEL')
                """, blockId, blockOutcomeId);
    }

    /** İnceleme testlerinin kullandığı kayıt kimliklerini taşır. */
    record ReviewFixture(
            long questionId,
            long blockId,
            long firstOutcomeId,
            long secondOutcomeId,
            long questionReviewId,
            long blockReviewId,
            long decidedReviewId) {}
}
