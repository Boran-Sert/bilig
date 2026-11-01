package com.hataanalizi.core.session;

import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.nullValue;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.authentication;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.csrf;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.hataanalizi.core.TestcontainersConfiguration;
import com.hataanalizi.core.auth.AuthUser;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;
import org.springframework.test.web.servlet.request.RequestPostProcessor;
import org.springframework.transaction.annotation.Transactional;

/** Test oturumu uç noktasının sahiplik ve soru güvenliği sözleşmesini doğrular. */
@ActiveProfiles("test")
@SpringBootTest
@AutoConfigureMockMvc
@Import(TestcontainersConfiguration.class)
@Transactional
class SessionControllerIT {

    private final JdbcTemplate jdbcTemplate;
    private final MockMvc mockMvc;
    private final SessionQuestionFixture questionFixture;

    /** Test bağımlılıklarını saklar. */
    @Autowired
    SessionControllerIT(JdbcTemplate jdbcTemplate, MockMvc mockMvc) {
        this.jdbcTemplate = jdbcTemplate;
        this.mockMvc = mockMvc;
        this.questionFixture = new SessionQuestionFixture(jdbcTemplate);
    }

    /** Aynı öğrencinin oturumunu sürdürür ve başkasının oturumunu açığa çıkarmaz. */
    @Test
    void resumesOwnSessionAndCreatesSeparateSessionForAnotherStudent() throws Exception {
        Long ownerId = insertUser();
        Long otherUserId = insertUser();
        Long unitId = insertCurriculumUnit();
        Long examId = insertExam("PUBLISHED");
        Long firstQuestionId = questionFixture.insertQuestion(unitId);
        Long secondQuestionId = questionFixture.insertQuestion(unitId);
        insertExamQuestion(examId, secondQuestionId, (short) 1);
        insertExamQuestion(examId, firstQuestionId, (short) 2);
        Long ownerSessionId = insertStudySession(ownerId, examId, (short) 2);
        jdbcTemplate.update(
                "INSERT INTO student_answer (study_session_id, question_id, selected_option, is_correct) "
                        + "VALUES (?, ?, 'C', false)",
                ownerSessionId,
                secondQuestionId);

        mockMvc.perform(post("/api/tests/{id}/sessions", examId)
                        .with(student(ownerId))
                        .with(csrf()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.sessionId").value(ownerSessionId))
                .andExpect(jsonPath("$.currentPosition").value(2))
                .andExpect(jsonPath("$.questions.length()").value(2))
                .andExpect(jsonPath("$.questions[0].id").value(secondQuestionId))
                .andExpect(jsonPath("$.questions[0].position").value(1))
                .andExpect(jsonPath("$.questions[0].selectedOption").value("C"))
                .andExpect(jsonPath("$.questions[0].content.stem[0].md").value("Question"))
                .andExpect(jsonPath("$.questions[0].correctOption").doesNotExist())
                .andExpect(jsonPath("$.questions[0].learningOutcomes").doesNotExist());

        mockMvc.perform(post("/api/tests/{id}/sessions", examId)
                        .with(student(otherUserId))
                        .with(csrf()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.sessionId").value(org.hamcrest.Matchers.not(ownerSessionId)))
                .andExpect(jsonPath("$.currentPosition").value(1))
                .andExpect(jsonPath("$.questions[0].selectedOption").value(nullValue()));
    }

    /** Bulunmayan veya taslak test için 404 hata kodu döndürür. */
    @Test
    void rejectsMissingAndUnpublishedExams() throws Exception {
        Long userId = insertUser();
        Long draftExamId = insertExam("DRAFT");

        mockMvc.perform(post("/api/tests/{id}/sessions", Long.MAX_VALUE)
                        .with(student(userId))
                        .with(csrf()))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.code").value("EXAM_NOT_FOUND"));
        mockMvc.perform(post("/api/tests/{id}/sessions", draftExamId)
                        .with(student(userId))
                        .with(csrf()))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.code").value("EXAM_NOT_FOUND"));
    }

    /** İlk cevabı kaydeder, kazanımları döndürür ve ikinci cevabı reddeder. */
    @Test
    void savesFirstAnswerWithOutcomesAndRejectsSecondAnswer() throws Exception {
        Long userId = insertUser();
        Long unitId = insertCurriculumUnit();
        Long examId = insertExam("PUBLISHED");
        Long questionId = questionFixture.insertQuestion(unitId);
        insertExamQuestion(examId, questionId, (short) 1);
        insertOutcomes(unitId, questionId);
        Long sessionId = insertStudySession(userId, examId, (short) 1);

        submitAnswer(sessionId, questionId, userId, "{\"selectedOption\":\"B\",\"durationMs\":1200,\"hintUsed\":true}")
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.isCorrect").value(true))
                .andExpect(jsonPath("$.correctOption").value("B"))
                .andExpect(jsonPath("$.outcomes.length()").value(2))
                .andExpect(jsonPath("$.outcomes[0].code").exists())
                .andExpect(jsonPath("$.outcomes[1].title").exists());

        submitAnswer(sessionId, questionId, userId, "{\"selectedOption\":\"A\",\"durationMs\":2400,\"hintUsed\":false}")
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.code").value("ANSWER_ALREADY_SUBMITTED"))
                .andExpect(jsonPath("$.correctOption").doesNotExist());

        assertThatFirstAnswerWasKept(sessionId, questionId);
    }

    /** Taslak soruyu ve sıra boşluğunu atlayarak sonraki soruya ilerler. */
    @Test
    void skipsDraftQuestionsAndPositionGaps() throws Exception {
        Long userId = insertUser();
        Long unitId = insertCurriculumUnit();
        Long examId = insertExam("PUBLISHED");
        Long firstQuestionId = questionFixture.insertQuestion(unitId);
        Long draftQuestionId = questionFixture.insertQuestion(unitId);
        Long lastQuestionId = questionFixture.insertQuestion(unitId);
        jdbcTemplate.update("UPDATE question SET status = 'DRAFT' WHERE id = ?", draftQuestionId);
        insertExamQuestion(examId, firstQuestionId, (short) 1);
        insertExamQuestion(examId, draftQuestionId, (short) 2);
        insertExamQuestion(examId, lastQuestionId, (short) 4);
        Long sessionId = insertStudySession(userId, examId, (short) 1);
        String request = "{\"selectedOption\":\"B\",\"durationMs\":100,\"hintUsed\":false}";

        submitAnswer(sessionId, firstQuestionId, userId, request).andExpect(status().isOk());
        assertThat(currentPosition(sessionId)).isEqualTo(4);

        submitAnswer(sessionId, lastQuestionId, userId, request).andExpect(status().isOk());
        assertThat(currentPosition(sessionId)).isEqualTo(5);
    }

    /** Atlanan soru cevaplanana kadar konumu o soruda tutar. */
    @Test
    void keepsPositionOnSkippedQuestionUntilAnswered() throws Exception {
        Long userId = insertUser();
        Long unitId = insertCurriculumUnit();
        Long examId = insertExam("PUBLISHED");
        Long firstQuestionId = questionFixture.insertQuestion(unitId);
        Long skippedQuestionId = questionFixture.insertQuestion(unitId);
        Long lastQuestionId = questionFixture.insertQuestion(unitId);
        insertExamQuestion(examId, firstQuestionId, (short) 1);
        insertExamQuestion(examId, skippedQuestionId, (short) 2);
        insertExamQuestion(examId, lastQuestionId, (short) 3);
        Long sessionId = insertStudySession(userId, examId, (short) 1);
        String request = "{\"selectedOption\":\"B\",\"durationMs\":100,\"hintUsed\":false}";

        submitAnswer(sessionId, firstQuestionId, userId, request).andExpect(status().isOk());
        submitAnswer(sessionId, lastQuestionId, userId, request).andExpect(status().isOk());
        assertThat(currentPosition(sessionId)).isEqualTo(2);

        submitAnswer(sessionId, skippedQuestionId, userId, request).andExpect(status().isOk());
        assertThat(currentPosition(sessionId)).isEqualTo(4);
    }

    /** Başkasının oturumunu ve tamamlanmış oturumu cevaplamaya kapatır. */
    @Test
    void rejectsAnotherUsersAndCompletedSessions() throws Exception {
        Long ownerId = insertUser();
        Long otherUserId = insertUser();
        Long unitId = insertCurriculumUnit();
        Long examId = insertExam("PUBLISHED");
        Long questionId = questionFixture.insertQuestion(unitId);
        insertExamQuestion(examId, questionId, (short) 1);
        Long sessionId = insertStudySession(ownerId, examId, (short) 1);
        String request = "{\"selectedOption\":\"B\",\"durationMs\":100,\"hintUsed\":false}";

        submitAnswer(sessionId, questionId, otherUserId, request)
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.code").value("SESSION_NOT_FOUND"));

        jdbcTemplate.update("UPDATE study_session SET status = 'COMPLETED' WHERE id = ?", sessionId);
        submitAnswer(sessionId, questionId, ownerId, request)
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.code").value("SESSION_ALREADY_COMPLETED"));
    }

    /** Geçersiz şık ve negatif süre isteğinin doğrulama hatası verdiğini doğrular. */
    @Test
    void validatesAnswerRequest() throws Exception {
        Long userId = insertUser();
        Long unitId = insertCurriculumUnit();
        Long examId = insertExam("PUBLISHED");
        Long questionId = questionFixture.insertQuestion(unitId);
        insertExamQuestion(examId, questionId, (short) 1);
        Long sessionId = insertStudySession(userId, examId, (short) 1);

        submitAnswer(sessionId, questionId, userId, "{\"selectedOption\":\"X\",\"durationMs\":-1,\"hintUsed\":false}")
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("VALIDATION_FAILED"));
    }

    /** Yeni bir öğrenci hesabı oluşturur. */
    private Long insertUser() {
        String identifier = UUID.randomUUID().toString();
        String sql = "INSERT INTO app_user (tenant_id, email, display_name, role) "
                + "SELECT id, ?, ?, 'STUDENT' FROM tenant WHERE name = 'Bilig' RETURNING id";
        return jdbcTemplate.queryForObject(sql, Long.class, identifier + "@example.test", identifier);
    }

    /** Testte kullanılacak ders programı ve ünitesini oluşturur. */
    private Long insertCurriculumUnit() {
        String identifier = UUID.randomUUID().toString();
        Long subjectId = jdbcTemplate.queryForObject(
                "INSERT INTO subject (code, name) VALUES (?, ?) RETURNING id", Long.class, identifier, identifier);
        Long curriculumId = jdbcTemplate.queryForObject(
                "INSERT INTO curriculum (subject_id, name, model, year) VALUES (?, ?, ?, ?) RETURNING id",
                Long.class,
                subjectId,
                identifier,
                "LEGACY",
                2018);
        return jdbcTemplate.queryForObject(
                "INSERT INTO curriculum_unit (curriculum_id, grade, unit_no, title) VALUES (?, ?, ?, ?) RETURNING id",
                Long.class,
                curriculumId,
                12,
                1,
                identifier);
    }

    /** Yayındaki test kaydını oluşturur. */
    private Long insertExam(String examStatus) {
        String title = "Test " + UUID.randomUUID();
        return jdbcTemplate.queryForObject(
                "INSERT INTO exam (title, status) VALUES (?, ?) RETURNING id", Long.class, title, examStatus);
    }

    /** Teste soruyu belirtilen sırada ekler. */
    private void insertExamQuestion(Long examId, Long questionId, short position) {
        jdbcTemplate.update(
                "INSERT INTO exam_question (exam_id, question_id, position) VALUES (?, ?, ?)",
                examId,
                questionId,
                position);
    }

    /** Öğrenciye ait açık test oturumu oluşturur. */
    private Long insertStudySession(Long userId, Long examId, short currentPosition) {
        return jdbcTemplate.queryForObject("""
                INSERT INTO study_session (user_id, exam_id, current_position)
                VALUES (?, ?, ?)
                RETURNING id
                """, Long.class, userId, examId, currentPosition);
    }

    /** Soruya iki kazanım ekler. */
    private void insertOutcomes(Long unitId, Long questionId) {
        String identifier = UUID.randomUUID().toString();
        jdbcTemplate.update("""
                WITH outcome_group AS (INSERT INTO learning_outcome_group (curriculum_id, code, name)
                    VALUES ((SELECT curriculum_id FROM curriculum_unit WHERE id = ?), ?, ?) RETURNING id),
                outcomes AS (INSERT INTO learning_outcome (learning_outcome_group_id, code, title, search_text)
                    SELECT outcome_group.id, outcome.code, outcome.title, outcome.title FROM outcome_group
                    CROSS JOIN (VALUES ('A.2.7', 'Learning outcome seven'),
                                       ('A.2.8', 'Learning outcome eight')) AS outcome(code, title) RETURNING id)
                INSERT INTO question_outcome (question_id, learning_outcome_id, mapped_by)
                SELECT ?, outcomes.id, 'SOURCE' FROM outcomes
                """, unitId, identifier, identifier, questionId);
    }

    /** İlk cevabın değişmeden kaldığını ve ilerlemenin bir kez arttığını doğrular. */
    private void assertThatFirstAnswerWasKept(Long sessionId, Long questionId) {
        var storedAnswer = jdbcTemplate.queryForMap("""
                        SELECT count(*) AS answer_count, max(selected_option::text) AS selected_option,
                               bool_or(is_correct) AS is_correct, max(duration_ms) AS duration_ms,
                               bool_or(hint_used) AS hint_used,
                               (SELECT current_position FROM study_session WHERE id = ?) AS current_position
                        FROM student_answer WHERE study_session_id = ? AND question_id = ?
                        """, sessionId, sessionId, questionId);
        assertThat(storedAnswer)
                .containsEntry("answer_count", 1L)
                .containsEntry("selected_option", "B")
                .containsEntry("is_correct", true)
                .containsEntry("duration_ms", 1200)
                .containsEntry("hint_used", true)
                .containsEntry("current_position", 2);
    }

    /** Oturumun kayıtlı konumunu okur. */
    private Integer currentPosition(Long sessionId) {
        return jdbcTemplate.queryForObject(
                "SELECT current_position FROM study_session WHERE id = ?", Integer.class, sessionId);
    }

    /** Cevap isteğini test öğrencisi olarak gönderir. */
    private ResultActions submitAnswer(Long sessionId, Long questionId, Long userId, String request) throws Exception {
        return mockMvc.perform(put("/api/sessions/{id}/answers/{questionId}", sessionId, questionId)
                .with(student(userId))
                .with(csrf())
                .contentType(MediaType.APPLICATION_JSON)
                .content(request));
    }

    /** İstek için test öğrencisinin kimliğini hazırlar. */
    private RequestPostProcessor student(Long userId) {
        AuthUser authUser = new AuthUser(userId, "student@example.test", "STUDENT");
        var authentication = new UsernamePasswordAuthenticationToken(
                authUser, null, List.of(new SimpleGrantedAuthority("ROLE_STUDENT")));
        return authentication(authentication);
    }
}
