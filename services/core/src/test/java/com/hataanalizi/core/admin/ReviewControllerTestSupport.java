package com.hataanalizi.core.admin;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.testSecurityContext;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

import jakarta.servlet.http.Cookie;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;

/** İnceleme uçlarının entegrasyon testleri için ortak veritabanı fikstürü sağlar. */
abstract class ReviewControllerTestSupport {

    @Autowired
    protected MockMvc mockMvc;

    @Autowired
    protected JdbcTemplate jdbcTemplate;

    protected long questionId;
    protected long blockId;
    protected long firstOutcomeId;
    protected long secondOutcomeId;
    protected long questionReviewId;
    protected long blockReviewId;
    protected long decidedReviewId;
    private long curriculumUnitId;

    /** Soru, paragraf, kazanım ve açık/karara bağlanmış incelemeleri oluşturur. */
    @BeforeEach
    void createReviewData() {
        createAdmin();
        long sourcePageId = createSourcePage();
        long outcomeGroupId = createOutcomeGroup();
        firstOutcomeId = createOutcome(outcomeGroupId, "A.2.6", "Şahıs kadrosu");
        secondOutcomeId = createOutcome(outcomeGroupId, "A.2.7", "Zaman ve mekân");
        questionId = createQuestion(sourcePageId);
        blockId = createBlock(sourcePageId);
        createLinks();
        questionReviewId = createReview(questionId, null, "OPEN", "2026-11-02T10:00:00Z");
        blockReviewId = createReview(null, blockId, "OPEN", "2026-11-02T11:00:00Z");
        decidedReviewId = createReview(questionId, null, "APPROVED", "2026-11-02T09:00:00Z");
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

    /** Test kazanımları için program ve kazanım grubunu oluşturur. */
    private long createOutcomeGroup() {
        String uniqueValue = UUID.randomUUID().toString();
        Long subjectId = jdbcTemplate.queryForObject(
                "INSERT INTO subject (code, name) VALUES (?, ?) RETURNING id", Long.class, uniqueValue, uniqueValue);
        Long curriculumId = jdbcTemplate.queryForObject(
                "INSERT INTO curriculum (subject_id, name, model, year) VALUES (?, ?, 'LEGACY', 2018) RETURNING id",
                Long.class,
                subjectId,
                uniqueValue);
        curriculumUnitId = jdbcTemplate.queryForObject("""
                INSERT INTO curriculum_unit (curriculum_id, grade, unit_no, title)
                VALUES (?, 12, 1, ?)
                RETURNING id
                """, Long.class, curriculumId, uniqueValue);
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
    private long createQuestion(long sourcePageId) {
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
    private void createLinks() {
        jdbcTemplate.update("""
                INSERT INTO question_outcome (question_id, learning_outcome_id, mapped_by)
                VALUES (?, ?, 'MODEL')
                """, questionId, firstOutcomeId);
        jdbcTemplate.update("""
                INSERT INTO content_block_outcome (content_block_id, learning_outcome_id, mapped_by)
                VALUES (?, ?, 'MODEL')
                """, blockId, secondOutcomeId);
    }

    /** İnceleme kaydını hedefi ve oluşturulma zamanıyla ekler. */
    private long createReview(Long questionId, Long contentBlockId, String status, String createdAt) {
        return jdbcTemplate.queryForObject("""
                INSERT INTO review_item (reason, question_id, content_block_id, status, created_at)
                VALUES ('LOW_CONFIDENCE', ?, ?, ?, ?::timestamptz)
                RETURNING id
                """, Long.class, questionId, contentBlockId, status, createdAt);
    }

    /** CSRF doğrulamasıyla yönetici karar isteği gönderir. */
    protected ResultActions postDecision(long reviewId, String body) throws Exception {
        String csrfToken = UUID.randomUUID().toString();
        return mockMvc.perform(post("/api/admin/review/" + reviewId)
                .with(testSecurityContext())
                .cookie(new Cookie("XSRF-TOKEN", csrfToken))
                .header("X-XSRF-TOKEN", csrfToken)
                .contentType(MediaType.APPLICATION_JSON)
                .content(body));
    }

    /** Karar durumu, karar veren ve zamanı veritabanında kaydedildiğini doğrular. */
    protected void assertDecision(long reviewId, String expectedStatus) {
        org.assertj.core.api.Assertions.assertThat(jdbcTemplate.queryForObject(
                        "SELECT status FROM review_item WHERE id = ?", String.class, reviewId))
                .isEqualTo(expectedStatus);
        org.assertj.core.api.Assertions.assertThat(jdbcTemplate.queryForObject(
                        "SELECT decided_by FROM review_item WHERE id = ?", Long.class, reviewId))
                .isEqualTo(1001L);
        org.assertj.core.api.Assertions.assertThat(jdbcTemplate.queryForObject(
                        "SELECT decided_at FROM review_item WHERE id = ?", Object.class, reviewId))
                .isNotNull();
    }
}
