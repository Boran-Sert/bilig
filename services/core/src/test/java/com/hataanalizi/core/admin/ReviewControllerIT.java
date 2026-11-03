package com.hataanalizi.core.admin;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.testSecurityContext;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.hataanalizi.core.TestcontainersConfiguration;
import com.hataanalizi.core.admin.ReviewControllerTestData.ReviewFixture;
import com.hataanalizi.core.auth.WithAuthUser;
import jakarta.servlet.http.Cookie;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;
import org.springframework.transaction.annotation.Transactional;

/** İnceleme listeleme ve karar uçlarının HTTP sözleşmesini sınar. */
@ActiveProfiles("test")
@SpringBootTest
@AutoConfigureMockMvc
@Import(TestcontainersConfiguration.class)
@Transactional
class ReviewControllerIT {

    private final MockMvc mockMvc;
    private final JdbcTemplate jdbcTemplate;
    private final ReviewControllerTestData testData;
    private ReviewFixture fixture;

    /** Test bağımlılıklarını saklar. */
    @Autowired
    ReviewControllerIT(MockMvc mockMvc, JdbcTemplate jdbcTemplate) {
        this.mockMvc = mockMvc;
        this.jdbcTemplate = jdbcTemplate;
        this.testData = new ReviewControllerTestData(jdbcTemplate);
    }

    /** Her test için inceleme verisini oluşturur. */
    @BeforeEach
    void createReviewData() {
        fixture = testData.createReviewFixture();
    }

    /** Yalnız açık kayıtları eskiden yeniye sayfalı ve hedef içeriğiyle döndürür. */
    @Test
    @WithAuthUser(role = "CONTENT_ADMIN", id = 1001)
    void listsOnlyOpenReviewsInCreationOrder() throws Exception {
        mockMvc.perform(get("/api/admin/review?page=0&size=1").with(testSecurityContext()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.items.length()").value(1))
                .andExpect(jsonPath("$.items[0].reason").value("LOW_CONFIDENCE"))
                .andExpect(jsonPath("$.items[0].targetType").value("QUESTION"))
                .andExpect(jsonPath("$.items[0].targetId").value(fixture.questionId()))
                .andExpect(jsonPath("$.items[0].questionContent.stem[0].md").value("Soru kökü"))
                .andExpect(jsonPath("$.items[0].blockMarkdown").doesNotExist())
                .andExpect(jsonPath("$.items[0].sourceTitle").value("İnceleme kaynağı"))
                .andExpect(jsonPath("$.items[0].pageId").isNumber())
                .andExpect(jsonPath("$.items[0].pageNo").value(3))
                .andExpect(jsonPath("$.items[0].outcomes[0].id").value(fixture.firstOutcomeId()))
                .andExpect(jsonPath("$.items[0].outcomes[0].mappedBy").value("MODEL"))
                .andExpect(jsonPath("$.items[0].createdAt").value("2026-11-02T10:00:00Z"))
                .andExpect(jsonPath("$.page").value(0))
                .andExpect(jsonPath("$.size").value(1))
                .andExpect(jsonPath("$.total").value(2));

        mockMvc.perform(get("/api/admin/review?page=1&size=1").with(testSecurityContext()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.items[0].targetType").value("BLOCK"))
                .andExpect(jsonPath("$.items[0].targetId").value(fixture.blockId()))
                .andExpect(jsonPath("$.items[0].questionContent").doesNotExist())
                .andExpect(jsonPath("$.items[0].blockMarkdown").value("Paragraf metni"))
                .andExpect(jsonPath("$.items[0].outcomes[0].mappedBy").value("MODEL"));
    }

    /** Düzeltme seçicisi için bütün kazanımları kimlikleriyle döndürür. */
    @Test
    @WithAuthUser(role = "CONTENT_ADMIN", id = 1001)
    void listsOutcomesForCorrectionSelector() throws Exception {
        mockMvc.perform(get("/api/admin/outcomes").with(testSecurityContext()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(2))
                .andExpect(jsonPath("$[0].id").value(fixture.firstOutcomeId()))
                .andExpect(jsonPath("$[0].code").value("A.2.6"))
                .andExpect(jsonPath("$[1].id").value(fixture.secondOutcomeId()))
                .andExpect(jsonPath("$[1].title").value("Zaman ve mekân"));
    }

    /** FIX iki tür hedefin bütün bağlarını HUMAN olarak değiştirip yayına alır. */
    @Test
    @WithAuthUser(role = "CONTENT_ADMIN", id = 1001)
    void fixesOutcomesForQuestionAndBlock() throws Exception {
        postDecision(
                        fixture.questionReviewId(),
                        "{\"decision\":\"FIX\",\"outcomeIds\":[" + fixture.secondOutcomeId() + "]}")
                .andExpect(status().isNoContent());
        postDecision(
                        fixture.blockReviewId(),
                        "{\"decision\":\"FIX\",\"outcomeIds\":[" + fixture.firstOutcomeId() + "]}")
                .andExpect(status().isNoContent());

        assertThat(jdbcTemplate.queryForList(
                        "SELECT learning_outcome_id FROM question_outcome WHERE question_id = ?",
                        Long.class,
                        fixture.questionId()))
                .containsExactly(fixture.secondOutcomeId());
        assertThat(jdbcTemplate.queryForList(
                        "SELECT mapped_by FROM question_outcome WHERE question_id = ?",
                        String.class,
                        fixture.questionId()))
                .containsExactly("HUMAN");
        assertThat(jdbcTemplate.queryForList(
                        "SELECT learning_outcome_id FROM content_block_outcome WHERE content_block_id = ?",
                        Long.class,
                        fixture.blockId()))
                .containsExactly(fixture.firstOutcomeId());
        assertThat(jdbcTemplate.queryForList(
                        "SELECT mapped_by FROM content_block_outcome WHERE content_block_id = ?",
                        String.class,
                        fixture.blockId()))
                .containsExactly("HUMAN");
        assertThat(jdbcTemplate.queryForObject(
                        "SELECT status FROM question WHERE id = ?", String.class, fixture.questionId()))
                .isEqualTo("PUBLISHED");
        assertThat(jdbcTemplate.queryForObject(
                        "SELECT status FROM content_block WHERE id = ?", String.class, fixture.blockId()))
                .isEqualTo("PUBLISHED");
        assertDecision(fixture.questionReviewId(), "APPROVED");
        assertDecision(fixture.blockReviewId(), "APPROVED");
    }

    /** APPROVE bağları korur; REJECT hedefi ve inceleme kaydını reddeder. */
    @Test
    @WithAuthUser(role = "CONTENT_ADMIN", id = 1001)
    void appliesApproveAndRejectDecisions() throws Exception {
        postDecision(fixture.questionReviewId(), "{\"decision\":\"APPROVE\"}").andExpect(status().isNoContent());
        postDecision(fixture.blockReviewId(), "{\"decision\":\"REJECT\"}").andExpect(status().isNoContent());

        assertThat(jdbcTemplate.queryForList(
                        "SELECT learning_outcome_id FROM question_outcome WHERE question_id = ?",
                        Long.class,
                        fixture.questionId()))
                .containsExactly(fixture.firstOutcomeId());
        assertThat(jdbcTemplate.queryForObject(
                        "SELECT status FROM question WHERE id = ?", String.class, fixture.questionId()))
                .isEqualTo("PUBLISHED");
        assertThat(jdbcTemplate.queryForObject(
                        "SELECT status FROM content_block WHERE id = ?", String.class, fixture.blockId()))
                .isEqualTo("REJECTED");
        assertDecision(fixture.questionReviewId(), "APPROVED");
        assertDecision(fixture.blockReviewId(), "REJECTED");
    }

    /** Daha önce karara bağlanan kaydın ikinci kararını 409 ile reddeder. */
    @Test
    @WithAuthUser(role = "CONTENT_ADMIN", id = 1001)
    void rejectsSecondDecision() throws Exception {
        postDecision(fixture.decidedReviewId(), "{\"decision\":\"APPROVE\"}")
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.code").value("REVIEW_ALREADY_DECIDED"));
    }

    /** Düşük güven dışındaki açık kaydı 404 ile reddeder ve hedefe dokunmaz. */
    @Test
    @WithAuthUser(role = "CONTENT_ADMIN", id = 1001)
    void rejectsDecisionForOtherReason() throws Exception {
        long reviewId =
                testData.createReview(fixture.questionId(), null, "VALIDATION_FAILED", "OPEN", "2026-11-02T12:00:00Z");

        postDecision(reviewId, "{\"decision\":\"APPROVE\"}").andExpect(status().isNotFound());

        assertThat(jdbcTemplate.queryForObject(
                        "SELECT status FROM question WHERE id = ?", String.class, fixture.questionId()))
                .isEqualTo("DRAFT");
        assertThat(jdbcTemplate.queryForObject("SELECT status FROM review_item WHERE id = ?", String.class, reviewId))
                .isEqualTo("OPEN");
    }

    /** Boş veya bulunmayan kazanımlı FIX isteğini 400 ile reddeder. */
    @Test
    @WithAuthUser(role = "CONTENT_ADMIN", id = 1001)
    void rejectsInvalidFixOutcomes() throws Exception {
        postDecision(fixture.questionReviewId(), "{\"decision\":\"FIX\",\"outcomeIds\":[]}")
                .andExpect(status().isBadRequest());
        postDecision(fixture.questionReviewId(), "{\"decision\":\"FIX\",\"outcomeIds\":[999999999]}")
                .andExpect(status().isBadRequest());
        assertThat(jdbcTemplate.queryForObject(
                        "SELECT status FROM question WHERE id = ?", String.class, fixture.questionId()))
                .isEqualTo("DRAFT");
    }

    /** Öğrencinin inceleme uçlarına erişemediğini doğrular. */
    @Test
    @WithAuthUser(role = "STUDENT", id = 1001)
    void deniesStudentReviewEndpoints() throws Exception {
        mockMvc.perform(get("/api/admin/review").with(testSecurityContext()))
                .andExpect(status().isForbidden())
                .andExpect(jsonPath("$.code").value("ACCESS_DENIED"));
        mockMvc.perform(get("/api/admin/outcomes").with(testSecurityContext())).andExpect(status().isForbidden());
        postDecision(fixture.questionReviewId(), "{\"decision\":\"APPROVE\"}").andExpect(status().isForbidden());
    }

    /** CSRF doğrulamasıyla yönetici karar isteği gönderir. */
    private ResultActions postDecision(long reviewId, String body) throws Exception {
        String csrfToken = UUID.randomUUID().toString();
        return mockMvc.perform(post("/api/admin/review/" + reviewId)
                .with(testSecurityContext())
                .cookie(new Cookie("XSRF-TOKEN", csrfToken))
                .header("X-XSRF-TOKEN", csrfToken)
                .contentType(MediaType.APPLICATION_JSON)
                .content(body));
    }

    /** Karar durumu, karar veren ve zamanı veritabanında kaydedildiğini doğrular. */
    private void assertDecision(long reviewId, String expectedStatus) {
        assertThat(jdbcTemplate.queryForObject("SELECT status FROM review_item WHERE id = ?", String.class, reviewId))
                .isEqualTo(expectedStatus);
        assertThat(jdbcTemplate.queryForObject("SELECT decided_by FROM review_item WHERE id = ?", Long.class, reviewId))
                .isEqualTo(1001L);
        assertThat(jdbcTemplate.queryForObject(
                        "SELECT decided_at FROM review_item WHERE id = ?", Object.class, reviewId))
                .isNotNull();
    }
}
