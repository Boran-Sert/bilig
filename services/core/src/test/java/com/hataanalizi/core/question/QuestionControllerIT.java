package com.hataanalizi.core.question;

import static com.hataanalizi.core.question.QuestionControllerTestData.vector;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.authentication;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.hataanalizi.core.TestcontainersConfiguration;
import com.hataanalizi.core.auth.AuthUser;
import com.hataanalizi.core.common.AppConstants;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.request.RequestPostProcessor;
import org.springframework.transaction.annotation.Transactional;

/** Benzer soru uç noktasının seçim kurallarını ve HTTP cevabını PostgreSQL ile doğrular. */
@ActiveProfiles("test")
@SpringBootTest
@AutoConfigureMockMvc
@Import(TestcontainersConfiguration.class)
@Transactional
class QuestionControllerIT {

    private static final String PUBLISHED = AppConstants.QUESTION_STATUS_PUBLISHED;
    private static final String SIMILAR_URL = "/api/questions/{id}/similar";

    private final MockMvc mockMvc;
    private final QuestionControllerTestData testData;

    /** HTTP ve veritabanı bağımlılıklarını saklar. */
    @Autowired
    QuestionControllerIT(JdbcTemplate jdbcTemplate, MockMvc mockMvc) {
        this.mockMvc = mockMvc;
        this.testData = new QuestionControllerTestData(jdbcTemplate);
    }

    /** Ortak kazanımı çok olan soru döner; yanıtta doğru şık ve kazanımlar yoktur. */
    @Test
    void returnsQuestionWithMostSharedOutcomesWithoutAnswer() throws Exception {
        List<Long> outcomes = testData.insertOutcomes(2);
        Long sourceId = testData.insertQuestion(PUBLISHED, vector(1, 0), outcomes);
        testData.insertQuestion(PUBLISHED, vector(1, 0), List.of(outcomes.get(0)));
        Long bothOutcomesId = testData.insertQuestion(PUBLISHED, vector(0, 1), outcomes);

        mockMvc.perform(get(SIMILAR_URL, sourceId).with(student(testData.insertUser())))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(2))
                .andExpect(jsonPath("$.questionId").value(bothOutcomesId))
                .andExpect(jsonPath("$.content.stem[0].md").value("Benzer soru"))
                .andExpect(jsonPath("$.content.options.length()").value(2))
                .andExpect(jsonPath("$.content.correctOption").doesNotExist())
                .andExpect(jsonPath("$.content.options[0].isCorrect").doesNotExist())
                .andExpect(jsonPath("$.outcomes").doesNotExist());
    }

    /** Ortak kazanım sayısı eşitse vektörü en yakın soru, vektörü olmayan en son seçilir. */
    @Test
    void breaksTieByNearestVector() throws Exception {
        List<Long> outcomes = testData.insertOutcomes(1);
        Long sourceId = testData.insertQuestion(PUBLISHED, vector(1, 0), outcomes);
        testData.insertQuestion(PUBLISHED, null, outcomes);
        testData.insertQuestion(PUBLISHED, vector(0, 1), outcomes);
        Long nearestId = testData.insertQuestion(PUBLISHED, vector(1, 0.1f), outcomes);

        mockMvc.perform(get(SIMILAR_URL, sourceId).with(student(testData.insertUser())))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.questionId").value(nearestId));
    }

    /** Öğrencinin herhangi bir oturumda çözdüğü soru dönmez; başka öğrencinin cevabı etkilemez. */
    @Test
    void skipsQuestionSolvedByStudent() throws Exception {
        List<Long> outcomes = testData.insertOutcomes(2);
        Long sourceId = testData.insertQuestion(PUBLISHED, vector(1, 0), outcomes);
        Long solvedId = testData.insertQuestion(PUBLISHED, vector(1, 0), outcomes);
        Long unsolvedId = testData.insertQuestion(PUBLISHED, vector(1, 0), List.of(outcomes.get(0)));
        Long userId = testData.insertUser();
        testData.insertAnswer(userId, solvedId);
        testData.insertAnswer(testData.insertUser(), unsolvedId);

        mockMvc.perform(get(SIMILAR_URL, sourceId).with(student(userId)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.questionId").value(unsolvedId));
    }

    /** Yayında olmayan soru aday olmaz; başka aday yoksa 204 döner. */
    @Test
    void skipsUnpublishedQuestionAndReturnsNoContent() throws Exception {
        List<Long> outcomes = testData.insertOutcomes(1);
        Long sourceId = testData.insertQuestion(PUBLISHED, vector(1, 0), outcomes);
        testData.insertQuestion(AppConstants.QUESTION_STATUS_DRAFT, vector(1, 0), outcomes);
        testData.insertQuestion("REVIEW", vector(1, 0), outcomes);
        testData.insertQuestion(PUBLISHED, vector(1, 0), testData.insertOutcomes(1));

        mockMvc.perform(get(SIMILAR_URL, sourceId).with(student(testData.insertUser())))
                .andExpect(status().isNoContent())
                .andExpect(content().string(""));
    }

    /** Kaynak soru yayında değilse 404 döner. */
    @Test
    void unpublishedSourceQuestionReturnsNotFound() throws Exception {
        List<Long> outcomes = testData.insertOutcomes(1);
        Long sourceId = testData.insertQuestion(AppConstants.QUESTION_STATUS_DRAFT, vector(1, 0), outcomes);
        testData.insertQuestion(PUBLISHED, vector(1, 0), outcomes);

        mockMvc.perform(get(SIMILAR_URL, sourceId).with(student(testData.insertUser())))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.code").value("QUESTION_NOT_FOUND"));
    }

    /** Giriş yapmamış istek 401 alır. */
    @Test
    void unauthenticatedRequestReturnsUnauthorized() throws Exception {
        Long sourceId = testData.insertQuestion(PUBLISHED, vector(1, 0), testData.insertOutcomes(1));

        mockMvc.perform(get(SIMILAR_URL, sourceId))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.code").value("AUTH_REQUIRED"));
    }

    /** İstek için test öğrencisinin kimliğini hazırlar. */
    private RequestPostProcessor student(Long userId) {
        AuthUser authUser = new AuthUser(userId, "student@example.test", "STUDENT");
        return authentication(new UsernamePasswordAuthenticationToken(
                authUser, null, List.of(new SimpleGrantedAuthority("ROLE_STUDENT"))));
    }
}
