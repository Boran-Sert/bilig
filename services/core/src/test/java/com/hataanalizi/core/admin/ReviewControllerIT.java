package com.hataanalizi.core.admin;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.testSecurityContext;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.hataanalizi.core.TestcontainersConfiguration;
import com.hataanalizi.core.auth.WithAuthUser;
import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.transaction.annotation.Transactional;

/** İnceleme listeleme ve karar uçlarının HTTP sözleşmesini sınar. */
@ActiveProfiles("test")
@SpringBootTest
@AutoConfigureMockMvc
@Import(TestcontainersConfiguration.class)
@Transactional
class ReviewControllerIT extends ReviewControllerTestSupport {

    /** Yalnız açık kayıtları eskiden yeniye sayfalı ve hedef içeriğiyle döndürür. */
    @Test
    @WithAuthUser(role = "CONTENT_ADMIN", id = 1001)
    void listsOnlyOpenReviewsInCreationOrder() throws Exception {
        mockMvc.perform(get("/api/admin/review?page=0&size=1").with(testSecurityContext()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.items.length()").value(1))
                .andExpect(jsonPath("$.items[0].reason").value("LOW_CONFIDENCE"))
                .andExpect(jsonPath("$.items[0].targetType").value("QUESTION"))
                .andExpect(jsonPath("$.items[0].targetId").value(questionId))
                .andExpect(jsonPath("$.items[0].questionContent.stem[0].md").value("Soru kökü"))
                .andExpect(jsonPath("$.items[0].blockMarkdown").doesNotExist())
                .andExpect(jsonPath("$.items[0].sourceTitle").value("İnceleme kaynağı"))
                .andExpect(jsonPath("$.items[0].pageId").isNumber())
                .andExpect(jsonPath("$.items[0].pageNo").value(3))
                .andExpect(jsonPath("$.items[0].outcomes[0].id").value(firstOutcomeId))
                .andExpect(jsonPath("$.items[0].outcomes[0].mappedBy").value("MODEL"))
                .andExpect(jsonPath("$.items[0].createdAt").value("2026-11-02T10:00:00Z"))
                .andExpect(jsonPath("$.page").value(0))
                .andExpect(jsonPath("$.size").value(1))
                .andExpect(jsonPath("$.total").value(2));

        mockMvc.perform(get("/api/admin/review?page=1&size=1").with(testSecurityContext()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.items[0].targetType").value("BLOCK"))
                .andExpect(jsonPath("$.items[0].targetId").value(blockId))
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
                .andExpect(jsonPath("$[0].id").value(firstOutcomeId))
                .andExpect(jsonPath("$[0].code").value("A.2.6"))
                .andExpect(jsonPath("$[1].id").value(secondOutcomeId))
                .andExpect(jsonPath("$[1].title").value("Zaman ve mekân"));
    }

    /** FIX iki tür hedefin bütün bağlarını HUMAN olarak değiştirip yayına alır. */
    @Test
    @WithAuthUser(role = "CONTENT_ADMIN", id = 1001)
    void fixesOutcomesForQuestionAndBlock() throws Exception {
        postDecision(questionReviewId, "{\"decision\":\"FIX\",\"outcomeIds\":[" + secondOutcomeId + "]}")
                .andExpect(status().isNoContent());
        postDecision(blockReviewId, "{\"decision\":\"FIX\",\"outcomeIds\":[" + firstOutcomeId + "]}")
                .andExpect(status().isNoContent());

        assertThat(jdbcTemplate.queryForList(
                        "SELECT learning_outcome_id FROM question_outcome WHERE question_id = ?",
                        Long.class,
                        questionId))
                .containsExactly(secondOutcomeId);
        assertThat(jdbcTemplate.queryForList(
                        "SELECT mapped_by FROM question_outcome WHERE question_id = ?", String.class, questionId))
                .containsExactly("HUMAN");
        assertThat(jdbcTemplate.queryForList(
                        "SELECT learning_outcome_id FROM content_block_outcome WHERE content_block_id = ?",
                        Long.class,
                        blockId))
                .containsExactly(firstOutcomeId);
        assertThat(jdbcTemplate.queryForList(
                        "SELECT mapped_by FROM content_block_outcome WHERE content_block_id = ?",
                        String.class,
                        blockId))
                .containsExactly("HUMAN");
        assertThat(jdbcTemplate.queryForObject("SELECT status FROM question WHERE id = ?", String.class, questionId))
                .isEqualTo("PUBLISHED");
        assertThat(jdbcTemplate.queryForObject("SELECT status FROM content_block WHERE id = ?", String.class, blockId))
                .isEqualTo("PUBLISHED");
        assertDecision(questionReviewId, "APPROVED");
        assertDecision(blockReviewId, "APPROVED");
    }

    /** APPROVE bağları korur; REJECT hedefi ve inceleme kaydını reddeder. */
    @Test
    @WithAuthUser(role = "CONTENT_ADMIN", id = 1001)
    void appliesApproveAndRejectDecisions() throws Exception {
        postDecision(questionReviewId, "{\"decision\":\"APPROVE\"}").andExpect(status().isNoContent());
        postDecision(blockReviewId, "{\"decision\":\"REJECT\"}").andExpect(status().isNoContent());

        assertThat(jdbcTemplate.queryForList(
                        "SELECT learning_outcome_id FROM question_outcome WHERE question_id = ?",
                        Long.class,
                        questionId))
                .containsExactly(firstOutcomeId);
        assertThat(jdbcTemplate.queryForObject("SELECT status FROM question WHERE id = ?", String.class, questionId))
                .isEqualTo("PUBLISHED");
        assertThat(jdbcTemplate.queryForObject("SELECT status FROM content_block WHERE id = ?", String.class, blockId))
                .isEqualTo("REJECTED");
        assertDecision(questionReviewId, "APPROVED");
        assertDecision(blockReviewId, "REJECTED");
    }

    /** Daha önce karara bağlanan kaydın ikinci kararını 409 ile reddeder. */
    @Test
    @WithAuthUser(role = "CONTENT_ADMIN", id = 1001)
    void rejectsSecondDecision() throws Exception {
        postDecision(decidedReviewId, "{\"decision\":\"APPROVE\"}")
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.code").value("REVIEW_ALREADY_DECIDED"));
    }

    /** Boş veya bulunmayan kazanımlı FIX isteğini 400 ile reddeder. */
    @Test
    @WithAuthUser(role = "CONTENT_ADMIN", id = 1001)
    void rejectsInvalidFixOutcomes() throws Exception {
        postDecision(questionReviewId, "{\"decision\":\"FIX\",\"outcomeIds\":[]}")
                .andExpect(status().isBadRequest());
        postDecision(questionReviewId, "{\"decision\":\"FIX\",\"outcomeIds\":[999999999]}")
                .andExpect(status().isBadRequest());
        assertThat(jdbcTemplate.queryForObject("SELECT status FROM question WHERE id = ?", String.class, questionId))
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
        postDecision(questionReviewId, "{\"decision\":\"APPROVE\"}").andExpect(status().isForbidden());
    }
}
