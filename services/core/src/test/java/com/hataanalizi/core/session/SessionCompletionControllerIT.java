package com.hataanalizi.core.session;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.authentication;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.csrf;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.hataanalizi.core.TestcontainersConfiguration;
import com.hataanalizi.core.auth.AuthUser;
import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
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
import org.springframework.test.web.servlet.ResultActions;
import org.springframework.test.web.servlet.request.RequestPostProcessor;
import org.springframework.transaction.annotation.Transactional;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

/** Test tamamlanma uç noktasının puan, yetki ve kazanım sonuçlarını doğrular. */
@ActiveProfiles("test")
@SpringBootTest
@AutoConfigureMockMvc
@Import(TestcontainersConfiguration.class)
@Transactional
class SessionCompletionControllerIT {

    private final JdbcTemplate jdbcTemplate;
    private final MockMvc mockMvc;
    private final SessionQuestionFixture questionFixture;
    private final ObjectMapper objectMapper;

    /** Test bağımlılıklarını saklar. */
    @Autowired
    SessionCompletionControllerIT(JdbcTemplate jdbcTemplate, MockMvc mockMvc, ObjectMapper objectMapper) {
        this.jdbcTemplate = jdbcTemplate;
        this.mockMvc = mockMvc;
        this.questionFixture = new SessionQuestionFixture(jdbcTemplate);
        this.objectMapper = objectMapper;
    }

    /** Boşları yanlış saymadan neti hesaplar ve her kazanıma yanlışları dağıtır. */
    @Test
    void completesSessionWithAytScoreAndOutcomeFailures() throws Exception {
        SessionFixture fixture = createScoringSession();
        var result = completeSession(fixture.sessionId(), fixture.userId())
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.correct").value(2))
                .andExpect(jsonPath("$.wrong").value(4))
                .andExpect(jsonPath("$.blank").value(2))
                .andExpect(jsonPath("$.net").value(1.00))
                .andReturn();
        assertOutcomeFailures(result.getResponse().getContentAsString());
        assertPersistedCompletion(fixture.sessionId());
    }

    /**
     * Başka öğrencinin oturumunu bitirmeyi ve aynı oturumu ikinci kez tamamlamayı engeller.
     */
    @Test
    void rejectsAnotherUsersAndAlreadyCompletedSessions() throws Exception {
        SessionFixture fixture = createEmptySession();
        Long otherUserId = insertUser();

        completeSession(fixture.sessionId(), otherUserId)
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.code").value("SESSION_NOT_FOUND"));
        completeSession(fixture.sessionId(), fixture.userId()).andExpect(status().isOk());
        completeSession(fixture.sessionId(), fixture.userId())
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.code").value("SESSION_ALREADY_COMPLETED"));
    }

    /** Tamamlanmış oturumun sonucunu tamamlama cevabıyla aynı değerlerle tekrar döndürür. */
    @Test
    void returnsCompletedSessionResultAgain() throws Exception {
        SessionFixture fixture = createScoringSession();
        completeSession(fixture.sessionId(), fixture.userId()).andExpect(status().isOk());

        var result = sessionResult(fixture.sessionId(), fixture.userId())
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.correct").value(2))
                .andExpect(jsonPath("$.wrong").value(4))
                .andExpect(jsonPath("$.blank").value(2))
                .andExpect(jsonPath("$.net").value(1.00))
                .andReturn();
        assertOutcomeFailures(result.getResponse().getContentAsString());
    }

    /** Başka öğrencinin oturum sonucunu ve bitmemiş oturumun sonucunu vermez. */
    @Test
    void rejectsAnotherUsersAndUnfinishedSessionResults() throws Exception {
        SessionFixture fixture = createEmptySession();

        sessionResult(fixture.sessionId(), fixture.userId())
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.code").value("SESSION_NOT_COMPLETED"));
        completeSession(fixture.sessionId(), fixture.userId()).andExpect(status().isOk());
        sessionResult(fixture.sessionId(), insertUser())
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.code").value("SESSION_NOT_FOUND"));
    }

    /** Tamamlanmış oturumun soruları doğru şık, öğrenci cevabı ve kazanımlarıyla tek istekte gelir. */
    @Test
    void returnsReviewWithCorrectOptionsAfterCompletion() throws Exception {
        SessionFixture fixture = createScoringSession();
        completeSession(fixture.sessionId(), fixture.userId()).andExpect(status().isOk());

        var result = sessionReview(fixture.sessionId(), fixture.userId())
                .andExpect(status().isOk())
                .andReturn();

        JsonNode questions =
                objectMapper.readTree(result.getResponse().getContentAsString()).get("questions");
        int correct = 0;
        int wrong = 0;
        int blank = 0;
        for (JsonNode question : questions) {
            assertThat(question.get("correctOption").asString()).isNotBlank();
            assertThat(question.get("outcomes").isArray()).isTrue();
            JsonNode isCorrect = question.get("isCorrect");
            if (isCorrect.isNull()) {
                assertThat(question.get("selectedOption").isNull()).isTrue();
                blank++;
            } else if (isCorrect.asBoolean()) {
                correct++;
            } else {
                wrong++;
            }
        }
        assertThat(questions.size()).isEqualTo(8);
        assertThat(new int[] {correct, wrong, blank}).containsExactly(2, 4, 2);
    }

    /** Başka öğrencinin oturumunun ve bitmemiş oturumun incelemesini vermez. */
    @Test
    void rejectsAnotherUsersAndUnfinishedSessionReviews() throws Exception {
        SessionFixture fixture = createEmptySession();

        sessionReview(fixture.sessionId(), fixture.userId())
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.code").value("SESSION_NOT_COMPLETED"));
        completeSession(fixture.sessionId(), fixture.userId()).andExpect(status().isOk());
        sessionReview(fixture.sessionId(), insertUser())
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.code").value("SESSION_NOT_FOUND"));
    }

    /** Tamamlanma yanıtındaki kazanım sayımlarını kodlarına göre doğrular. */
    private void assertOutcomeFailures(String response) throws Exception {
        Map<String, JsonNode> outcomes = new HashMap<>();
        objectMapper
                .readTree(response)
                .get("outcomes")
                .forEach(outcome -> outcomes.put(outcome.get("code").stringValue(), outcome));
        assertThat(outcomes).containsOnlyKeys("A.2.7", "A.2.8", "A.2.9");
        assertThat(outcomes.get("A.2.7").get("wrong").longValue()).isEqualTo(3);
        assertThat(outcomes.get("A.2.7").get("failed").booleanValue()).isTrue();
        assertThat(outcomes.get("A.2.8").get("wrong").longValue()).isEqualTo(2);
        assertThat(outcomes.get("A.2.8").get("failed").booleanValue()).isFalse();
        assertThat(outcomes.get("A.2.9").get("wrong").longValue()).isZero();
        assertThat(outcomes.get("A.2.9").get("failed").booleanValue()).isFalse();
    }

    /** Netin, durumun ve tamamlanma zamanının saklandığını doğrular. */
    private void assertPersistedCompletion(Long sessionId) {
        assertThat(jdbcTemplate.queryForObject(
                        "SELECT net FROM study_session WHERE id = ?", BigDecimal.class, sessionId))
                .isEqualByComparingTo("1.00");
        assertThat(jdbcTemplate.queryForObject(
                        "SELECT status FROM study_session WHERE id = ?", String.class, sessionId))
                .isEqualTo("COMPLETED");
        assertThat(jdbcTemplate.queryForObject(
                        "SELECT completed_at IS NOT NULL FROM study_session WHERE id = ?", Boolean.class, sessionId))
                .isTrue();
    }

    /** İki boş, iki doğru ve dört yanlış cevaplı test oturumu oluşturur. */
    private SessionFixture createScoringSession() {
        Long userId = insertUser();
        Long unitId = insertCurriculumUnit();
        Long examId = insertExam();
        List<Long> questionIds = insertExamQuestions(unitId, examId, 8);
        Map<String, Long> outcomeIds = insertOutcomes(unitId, questionIds.get(0));
        insertOutcomeMapping(questionIds.get(1), outcomeIds.get("A.2.7"));
        insertOutcomeMapping(questionIds.get(2), outcomeIds.get("A.2.7"));
        insertOutcomeMapping(questionIds.get(3), outcomeIds.get("A.2.8"));
        insertOutcomeMapping(questionIds.get(4), outcomeIds.get("A.2.9"));
        Long sessionId = insertStudySession(userId, examId);
        for (int index = 0; index < 4; index++) {
            insertAnswer(sessionId, questionIds.get(index), false);
        }
        insertAnswer(sessionId, questionIds.get(4), true);
        insertAnswer(sessionId, questionIds.get(5), true);
        return new SessionFixture(userId, sessionId);
    }

    /** Yayımlanmış ve sorusuz test için bir açık oturum oluşturur. */
    private SessionFixture createEmptySession() {
        Long userId = insertUser();
        Long sessionId = insertStudySession(userId, insertExam());
        return new SessionFixture(userId, sessionId);
    }

    /** Test sorularını sıralı biçimde oluşturur. */
    private List<Long> insertExamQuestions(Long unitId, Long examId, int count) {
        List<Long> questionIds = new ArrayList<>();
        for (int index = 0; index < count; index++) {
            Long questionId = questionFixture.insertQuestion(unitId);
            questionIds.add(questionId);
            jdbcTemplate.update(
                    "INSERT INTO exam_question (exam_id, question_id, position) VALUES (?, ?, ?)",
                    examId,
                    questionId,
                    index + 1);
        }
        return questionIds;
    }

    /** İki kazanım oluşturur ve ikisini ilk soruya bağlar. */
    private Map<String, Long> insertOutcomes(Long unitId, Long questionId) {
        String identifier = UUID.randomUUID().toString();
        jdbcTemplate.update("""
                WITH outcome_group AS (
                    INSERT INTO learning_outcome_group (curriculum_id, code, name)
                    VALUES ((SELECT curriculum_id FROM curriculum_unit WHERE id = ?), ?, ?) RETURNING id),
                outcomes AS (
                    INSERT INTO learning_outcome
                        (learning_outcome_group_id, code, title, search_text)
                    SELECT outcome_group.id, outcome.code, outcome.title, outcome.title
                    FROM outcome_group
                    CROSS JOIN (VALUES ('A.2.7', 'Learning outcome seven'),
                                       ('A.2.8', 'Learning outcome eight'),
                                       ('A.2.9', 'Learning outcome nine'))
                        AS outcome(code, title) RETURNING id, code)
                INSERT INTO question_outcome (question_id, learning_outcome_id, mapped_by)
                SELECT ?, outcomes.id, 'SOURCE' FROM outcomes WHERE outcomes.code != 'A.2.9'
                """, unitId, identifier, identifier, questionId);
        return jdbcTemplate.query(
                """
                SELECT learning_outcome.code, learning_outcome.id
                FROM learning_outcome
                JOIN learning_outcome_group
                    ON learning_outcome_group.id = learning_outcome.learning_outcome_group_id
                WHERE learning_outcome_group.code = ?
                """,
                resultSet -> {
                    Map<String, Long> outcomeIds = new HashMap<>();
                    while (resultSet.next()) {
                        outcomeIds.put(resultSet.getString("code"), resultSet.getLong("id"));
                    }
                    return outcomeIds;
                },
                identifier);
    }

    /** Soruyu belirtilen kazanıma bağlar. */
    private void insertOutcomeMapping(Long questionId, Long outcomeId) {
        jdbcTemplate.update(
                "INSERT INTO question_outcome (question_id, learning_outcome_id, mapped_by) "
                        + "VALUES (?, ?, 'SOURCE')",
                questionId,
                outcomeId);
    }

    /** Oturum sorusuna doğru veya yanlış cevap ekler. */
    private void insertAnswer(Long sessionId, Long questionId, boolean correct) {
        jdbcTemplate.update(
                "INSERT INTO student_answer "
                        + "(study_session_id, question_id, selected_option, is_correct) "
                        + "VALUES (?, ?, 'B', ?)",
                sessionId,
                questionId,
                correct);
    }

    /** Yeni bir öğrenci hesabı oluşturur. */
    private Long insertUser() {
        String identifier = UUID.randomUUID().toString();
        String sql = """
                INSERT INTO app_user (tenant_id, email, display_name, role)
                SELECT id, ?, ?, 'STUDENT' FROM tenant WHERE name = 'Bilig' RETURNING id
                """;
        return jdbcTemplate.queryForObject(sql, Long.class, identifier + "@example.test", identifier);
    }

    /** Testte kullanılacak ders programı ve ünitesini oluşturur. */
    private Long insertCurriculumUnit() {
        String identifier = UUID.randomUUID().toString();
        Long subjectId = jdbcTemplate.queryForObject("""
                INSERT INTO subject (code, name) VALUES (?, ?) RETURNING id
                """, Long.class, identifier, identifier);
        Long curriculumId = jdbcTemplate.queryForObject("""
                INSERT INTO curriculum (subject_id, name, model, year)
                VALUES (?, ?, ?, ?) RETURNING id
                """, Long.class, subjectId, identifier, "LEGACY", 2018);
        return jdbcTemplate.queryForObject("""
                INSERT INTO curriculum_unit (curriculum_id, grade, unit_no, title)
                VALUES (?, ?, ?, ?) RETURNING id
                """, Long.class, curriculumId, 12, 1, identifier);
    }

    /** Yayındaki test kaydını oluşturur. */
    private Long insertExam() {
        String title = "Test " + UUID.randomUUID();
        return jdbcTemplate.queryForObject("""
                INSERT INTO exam (title, status) VALUES (?, 'PUBLISHED') RETURNING id
                """, Long.class, title);
    }

    /** Öğrenciye ait açık test oturumu oluşturur. */
    private Long insertStudySession(Long userId, Long examId) {
        return jdbcTemplate.queryForObject("""
                INSERT INTO study_session (user_id, exam_id) VALUES (?, ?) RETURNING id
                """, Long.class, userId, examId);
    }

    /** Oturumu tamamlamak için istek gönderir. */
    private ResultActions completeSession(Long sessionId, Long userId) throws Exception {
        return mockMvc.perform(post("/api/sessions/{id}/complete", sessionId)
                .with(student(userId))
                .with(csrf()));
    }

    /** Oturum sonucunu okumak için istek gönderir. */
    private ResultActions sessionResult(Long sessionId, Long userId) throws Exception {
        return mockMvc.perform(get("/api/sessions/{id}/result", sessionId).with(student(userId)));
    }

    /** Oturum incelemesini okumak için istek gönderir. */
    private ResultActions sessionReview(Long sessionId, Long userId) throws Exception {
        return mockMvc.perform(get("/api/sessions/{id}/review", sessionId).with(student(userId)));
    }

    /** İstek için test öğrencisinin kimliğini hazırlar. */
    private RequestPostProcessor student(Long userId) {
        AuthUser authUser = new AuthUser(userId, "student@example.test", "STUDENT");
        var authentication = new UsernamePasswordAuthenticationToken(
                authUser, null, List.of(new SimpleGrantedAuthority("ROLE_STUDENT")));
        return authentication(authentication);
    }

    /** Test oturumunun öğrencisini ve kimliğini taşır. */
    private record SessionFixture(Long userId, Long sessionId) {}
}
