package com.hataanalizi.core.session;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.authentication;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.csrf;
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
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;
import org.springframework.test.web.servlet.request.RequestPostProcessor;
import org.springframework.transaction.annotation.Transactional;

/** Yanlış cevapların analiz işine kuyruğa eklenmesini doğrular. */
@ActiveProfiles("test")
@SpringBootTest
@AutoConfigureMockMvc
@Import(TestcontainersConfiguration.class)
@TestPropertySource(properties = "app.job-queue=postgres")
@Transactional
class AnswerAnalysisSessionIT {

    private final JdbcTemplate jdbcTemplate;
    private final MockMvc mockMvc;
    private final SessionQuestionFixture questionFixture;

    /** Test veritabanı ve istek bağımlılıklarını hazırlar. */
    @Autowired
    AnswerAnalysisSessionIT(JdbcTemplate jdbcTemplate, MockMvc mockMvc) {
        this.jdbcTemplate = jdbcTemplate;
        this.mockMvc = mockMvc;
        this.questionFixture = new SessionQuestionFixture(jdbcTemplate);
    }

    /** Yanlış cevap için tek iş oluşturur, doğru cevap için iş eklemez. */
    @Test
    void enqueuesAnalysisOnlyForWrongAnswers() throws Exception {
        Long userId = insertUser();
        Long unitId = insertCurriculumUnit();
        Long examId = insertExam();
        Long wrongQuestionId = questionFixture.insertQuestion(unitId);
        Long correctQuestionId = questionFixture.insertQuestion(unitId);
        insertExamQuestion(examId, wrongQuestionId, (short) 1);
        insertExamQuestion(examId, correctQuestionId, (short) 2);
        Long sessionId = insertStudySession(userId, examId);

        submitAnswer(sessionId, wrongQuestionId, userId, "A")
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.isCorrect").value(false));
        assertAnalysisJobPayload(sessionId, wrongQuestionId);

        submitAnswer(sessionId, correctQuestionId, userId, "B")
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.isCorrect").value(true));

        Long jobCount = jdbcTemplate.queryForObject(
                "SELECT count(*) FROM background_job WHERE job_type = 'ANALYZE_ANSWER'", Long.class);
        assertThat(jobCount).isEqualTo(1L);
    }

    /** Yanlış cevabın kimliğinin kuyruk yükünde bulunduğunu doğrular. */
    private void assertAnalysisJobPayload(Long sessionId, Long questionId) {
        Long answerId = jdbcTemplate.queryForObject(
                "SELECT id FROM student_answer WHERE study_session_id = ? AND question_id = ?",
                Long.class,
                sessionId,
                questionId);
        List<String> payloadAnswerIds = jdbcTemplate.queryForList(
                "SELECT payload->>'studentAnswerId' FROM background_job WHERE job_type = 'ANALYZE_ANSWER'",
                String.class);
        assertThat(payloadAnswerIds).containsExactly(answerId.toString());
    }

    /** Veritabanına test öğrencisi ekler. */
    private Long insertUser() {
        String identifier = UUID.randomUUID().toString();
        return jdbcTemplate.queryForObject("""
                INSERT INTO app_user (tenant_id, email, display_name, role)
                SELECT id, ?, ?, 'STUDENT' FROM tenant WHERE name = 'Bilig'
                RETURNING id
                """, Long.class, identifier + "@example.test", identifier);
    }

    /** Test sorusu için ders ünitesi ekler. */
    private Long insertCurriculumUnit() {
        String identifier = UUID.randomUUID().toString();
        Long subjectId = jdbcTemplate.queryForObject(
                "INSERT INTO subject (code, name) VALUES (?, ?) RETURNING id", Long.class, identifier, identifier);
        Long curriculumId = jdbcTemplate.queryForObject("""
                INSERT INTO curriculum (subject_id, name, model, year)
                VALUES (?, ?, 'LEGACY', 2018) RETURNING id
                """, Long.class, subjectId, identifier);
        return jdbcTemplate.queryForObject("""
                INSERT INTO curriculum_unit (curriculum_id, grade, unit_no, title)
                VALUES (?, 12, 1, ?) RETURNING id
                """, Long.class, curriculumId, identifier);
    }

    /** Yayındaki test kaydını ekler. */
    private Long insertExam() {
        return jdbcTemplate.queryForObject(
                "INSERT INTO exam (title, status) VALUES (?, 'PUBLISHED') RETURNING id",
                Long.class,
                "Analysis " + UUID.randomUUID());
    }

    /** Soruyu teste belirtilen sırada ekler. */
    private void insertExamQuestion(Long examId, Long questionId, short position) {
        jdbcTemplate.update(
                "INSERT INTO exam_question (exam_id, question_id, position) VALUES (?, ?, ?)",
                examId,
                questionId,
                position);
    }

    /** Öğrencinin açık oturumunu oluşturur. */
    private Long insertStudySession(Long userId, Long examId) {
        return jdbcTemplate.queryForObject(
                "INSERT INTO study_session (user_id, exam_id) VALUES (?, ?) RETURNING id", Long.class, userId, examId);
    }

    /** İstenen seçeneği öğrenci olarak gönderir. */
    private ResultActions submitAnswer(Long sessionId, Long questionId, Long userId, String option) throws Exception {
        String request = "{\"selectedOption\":\"" + option + "\",\"durationMs\":100,\"hintUsed\":false}";
        return mockMvc.perform(put("/api/sessions/{id}/answers/{questionId}", sessionId, questionId)
                .with(student(userId))
                .with(csrf())
                .contentType(MediaType.APPLICATION_JSON)
                .content(request));
    }

    /** İsteği test öğrencisinin kimliğiyle yetkilendirir. */
    private RequestPostProcessor student(Long userId) {
        AuthUser authUser = new AuthUser(userId, "student@example.test", "STUDENT");
        var authentication = new UsernamePasswordAuthenticationToken(
                authUser, null, List.of(new SimpleGrantedAuthority("ROLE_STUDENT")));
        return authentication(authentication);
    }
}
