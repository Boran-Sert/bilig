package com.hataanalizi.core;

import static com.hataanalizi.core.StudentFlowTestData.CORRECT_OPTION;
import static com.hataanalizi.core.StudentFlowTestData.EXAM_TITLE;
import static com.hataanalizi.core.StudentFlowTestData.FAILING_OUTCOME_CODE;
import static com.hataanalizi.core.StudentFlowTestData.PASSING_OUTCOME_CODE;
import static com.hataanalizi.core.StudentFlowTestData.QUESTION_COUNT;
import static com.hataanalizi.core.StudentFlowTestData.UNIT_TITLE;
import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.when;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.csrf;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.hataanalizi.core.StudentFlowTestData.FlowExam;
import com.hataanalizi.core.tutor.AiClient;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.mock.web.MockHttpSession;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;
import org.springframework.test.web.servlet.request.MockHttpServletRequestBuilder;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

/**
 * Öğrencinin kayıttan panele kadar demo akışını gerçek kayıt ve sunucu oturumuyla PostgreSQL
 * üzerinde baştan sona çalıştırır: test listesi, oturum, ipucu, cevap, devam, bitirme ve panel.
 */
@ActiveProfiles("test")
@SpringBootTest
@AutoConfigureMockMvc
@Import(TestcontainersConfiguration.class)
class StudentFlowIT {

    private static final String WRONG_OPTION = "A";
    private static final String HINT = "Türün tanımına bak.";

    private final MockMvc mockMvc;
    private final JdbcTemplate jdbcTemplate;
    private final ObjectMapper objectMapper;
    private final StudentFlowTestData testData;

    @MockitoBean
    private AiClient aiClient;

    /** HTTP, veritabanı ve JSON bağımlılıklarını saklar. */
    @Autowired
    StudentFlowIT(MockMvc mockMvc, JdbcTemplate jdbcTemplate, ObjectMapper objectMapper) {
        this.mockMvc = mockMvc;
        this.jdbcTemplate = jdbcTemplate;
        this.objectMapper = objectMapper;
        this.testData = new StudentFlowTestData(jdbcTemplate);
    }

    /** Öğrenci testi çözer, yarıda bırakıp devam eder, bitirir, paneli görür ve testi yeniden açar. */
    @Test
    void studentSolvesResumesCompletesAndSeesDashboard() throws Exception {
        FlowExam exam = testData.createPublishedExam();
        MockHttpSession student = registerStudent();

        Long sessionId = startTest(student, exam);
        answerFirstQuestionWithHint(student, sessionId, exam);
        resumeAfterSecondAnswer(student, sessionId, exam);
        completeLeavingLastQuestionBlank(student, sessionId, exam);
        assertDashboardAfterCompletion(student);
        assertThat(readJson(perform(post("/api/tests/{id}/sessions", exam.examId()), student)
                                .andExpect(status().isOk())
                                .andExpect(jsonPath("$.currentPosition").value(1))
                                .andExpect(jsonPath("$.questions[0].selectedOption")
                                        .doesNotExist()))
                        .get("sessionId")
                        .asLong())
                .isNotEqualTo(sessionId);
    }

    /** Testi listede görür ve cevapsız sorularla yeni oturum açar. */
    private Long startTest(MockHttpSession student, FlowExam exam) throws Exception {
        String examPath = "$[?(@.id == " + exam.examId() + ")]";
        perform(get("/api/tests"), student)
                .andExpect(status().isOk())
                .andExpect(jsonPath(examPath + ".title").value(EXAM_TITLE))
                .andExpect(jsonPath(examPath + ".questionCount").value(QUESTION_COUNT))
                .andExpect(jsonPath(examPath + ".answeredCount").value(0));
        JsonNode session = readJson(perform(post("/api/tests/{id}/sessions", exam.examId()), student)
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.currentPosition").value(1))
                .andExpect(jsonPath("$.questions.length()").value(QUESTION_COUNT))
                .andExpect(
                        jsonPath("$.questions[0].id").value(exam.questionIds().getFirst()))
                .andExpect(jsonPath("$.questions[0].selectedOption").doesNotExist())
                .andExpect(jsonPath("$.questions[0].correctOption").doesNotExist())
                .andExpect(jsonPath("$.questions[0].outcomes").doesNotExist())
                .andExpect(jsonPath("$.questions[0].content.correctOption").doesNotExist())
                .andExpect(
                        jsonPath("$.questions[0].content.options[1].isCorrect").doesNotExist()));
        return session.get("sessionId").asLong();
    }

    /** İpucunu açar, yanlış cevap verir; ikinci cevap reddedilir ve analiz işi kuyruğa düşer. */
    private void answerFirstQuestionWithHint(MockHttpSession student, Long sessionId, FlowExam exam) throws Exception {
        Long questionId = exam.questionIds().getFirst();
        when(aiClient.hint(questionId)).thenReturn(HINT);
        perform(get("/api/questions/{id}/hint", questionId), student)
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.hint").value(HINT));

        answer(student, sessionId, questionId, WRONG_OPTION, true)
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.isCorrect").value(false))
                .andExpect(jsonPath("$.correctOption").value(CORRECT_OPTION))
                .andExpect(jsonPath("$.outcomes.length()").value(1))
                .andExpect(jsonPath("$.outcomes[0].code").value(FAILING_OUTCOME_CODE));
        answer(student, sessionId, questionId, CORRECT_OPTION, false)
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.code").value("ANSWER_ALREADY_SUBMITTED"));

        assertThat(jdbcTemplate.queryForObject(
                        "SELECT hint_used FROM student_answer WHERE study_session_id = ? AND question_id = ?",
                        Boolean.class,
                        sessionId,
                        questionId))
                .isTrue();
        assertThat(analysisJobCount(sessionId)).isEqualTo(1);
    }

    /** İkinci soruyu cevaplar; oturumu yeniden açınca aynı oturum, seçimler ve kalınan yer gelir. */
    private void resumeAfterSecondAnswer(MockHttpSession student, Long sessionId, FlowExam exam) throws Exception {
        answer(student, sessionId, exam.questionIds().get(1), WRONG_OPTION, false)
                .andExpect(status().isOk());
        assertThat(jdbcTemplate.queryForObject(
                        "SELECT hint_used FROM student_answer WHERE study_session_id = ? AND question_id = ?",
                        Boolean.class,
                        sessionId,
                        exam.questionIds().get(1)))
                .isFalse();

        perform(post("/api/tests/{id}/sessions", exam.examId()), student)
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.sessionId").value(sessionId))
                .andExpect(jsonPath("$.currentPosition").value(3))
                .andExpect(jsonPath("$.questions[0].selectedOption").value(WRONG_OPTION))
                .andExpect(jsonPath("$.questions[1].selectedOption").value(WRONG_OPTION))
                .andExpect(jsonPath("$.questions[2].selectedOption").doesNotExist());
        String examPath = "$[?(@.id == " + exam.examId() + ")]";
        perform(get("/api/tests"), student)
                .andExpect(jsonPath(examPath + ".answeredCount").value(2))
                .andExpect(jsonPath("$[?(@.id == %d && @.sessionId == %d)]", exam.examId(), sessionId)
                        .exists())
                .andExpect(jsonPath(examPath + ".status").value("IN_PROGRESS"));
        perform(get("/api/me/dashboard"), student)
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.activeSessions.length()").value(1))
                .andExpect(jsonPath("$.activeSessions[0].sessionId").value(sessionId))
                .andExpect(jsonPath("$.activeSessions[0].answeredCount").value(2))
                .andExpect(jsonPath("$.activeSessions[0].currentPosition").value(3));
    }

    /** Üçüncü yanlışı verir, son soruyu boş bırakıp bitirir; sonuç AYT netiyle tekrar okunur. */
    private void completeLeavingLastQuestionBlank(MockHttpSession student, Long sessionId, FlowExam exam)
            throws Exception {
        answer(student, sessionId, exam.questionIds().get(2), WRONG_OPTION, false)
                .andExpect(status().isOk());

        expectResult(perform(post("/api/sessions/{id}/complete", sessionId), student));
        expectResult(perform(get("/api/sessions/{id}/result", sessionId), student));
        answer(student, sessionId, exam.questionIds().get(3), CORRECT_OPTION, false)
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.code").value("SESSION_ALREADY_COMPLETED"));
        assertThat(analysisJobCount(sessionId)).isEqualTo(3);
    }

    /** Üç yanlış ve bir boşla AYT netini ve sadece eşiği aşan kazanımın başarısızlığını bekler. */
    private void expectResult(ResultActions result) throws Exception {
        String failing = "$.outcomes[?(@.code == '" + FAILING_OUTCOME_CODE + "')]";
        String passing = "$.outcomes[?(@.code == '" + PASSING_OUTCOME_CODE + "')]";
        result.andExpect(status().isOk())
                .andExpect(jsonPath("$.correct").value(0))
                .andExpect(jsonPath("$.wrong").value(3))
                .andExpect(jsonPath("$.blank").value(1))
                .andExpect(jsonPath("$.net").value(-0.75))
                .andExpect(jsonPath(failing + ".wrong").value(3))
                .andExpect(jsonPath(failing + ".failed").value(true))
                .andExpect(jsonPath(passing + ".wrong").value(0))
                .andExpect(jsonPath(passing + ".failed").value(false));
    }

    /** Panel netini, başarısız kazanımı, ünite doğruluğunu gösterir ve açık oturum kalmaz. */
    private void assertDashboardAfterCompletion(MockHttpSession student) throws Exception {
        perform(get("/api/me/dashboard"), student)
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.summary.answeredQuestionCount").value(3))
                .andExpect(jsonPath("$.summary.accuracyPercent").value(0.0))
                .andExpect(jsonPath("$.summary.latestNet").value(-0.75))
                .andExpect(jsonPath("$.summary.latestQuestionCount").value(QUESTION_COUNT))
                .andExpect(jsonPath("$.activeSessions.length()").value(0))
                .andExpect(jsonPath("$.failedOutcomes.length()").value(1))
                .andExpect(jsonPath("$.failedOutcomes[0].code").value(FAILING_OUTCOME_CODE))
                .andExpect(jsonPath("$.failedOutcomes[0].totalWrongCount").value(3))
                .andExpect(jsonPath("$.failedOutcomes[0].testTitle").value(EXAM_TITLE))
                .andExpect(jsonPath("$.failedOutcomes[0].testWrongCount").value(3))
                .andExpect(jsonPath("$.unitAccuracy.length()").value(1))
                .andExpect(jsonPath("$.unitAccuracy[0].unitTitle").value(UNIT_TITLE))
                .andExpect(jsonPath("$.unitAccuracy[0].answeredCount").value(3))
                .andExpect(jsonPath("$.unitAccuracy[0].correctCount").value(0));
    }

    /** Yeni öğrenci kaydeder ve açılan sunucu oturumunu döndürür. */
    private MockHttpSession registerStudent() throws Exception {
        String body = """
                {"email":"%s@example.test","password":"Sufficient-Test-Password-123","displayName":"Öğrenci",\
                "grade":12,"explainStyle":"SIMPLE","privacyNoticeAccepted":true,"consentAccepted":true}
                """.formatted(UUID.randomUUID());
        MockHttpSession session = (MockHttpSession) perform(
                        post("/api/auth/register")
                                .contentType(MediaType.APPLICATION_JSON)
                                .content(body),
                        null)
                .andExpect(status().isCreated())
                .andReturn()
                .getRequest()
                .getSession(false);
        assertThat(session).isNotNull();
        return session;
    }

    /** Oturuma şık cevabı gönderir; ipucu yoksa arayüz gibi sadece şıkkı yollar. */
    private ResultActions answer(
            MockHttpSession student, Long sessionId, Long questionId, String option, boolean hintUsed)
            throws Exception {
        String body = hintUsed
                ? "{\"selectedOption\":\"%s\",\"durationMs\":1200,\"hintUsed\":true}".formatted(option)
                : "{\"selectedOption\":\"%s\"}".formatted(option);
        return perform(
                put("/api/sessions/{id}/answers/{questionId}", sessionId, questionId)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body),
                student);
    }

    /**
     * İsteği geçerli CSRF token'ı ve varsa sunucu oturumuyla gönderir. Bağlamı paylaşan testler
     * csrf() ile çerez deposunu değiştirdiği için gerçek çerez beklenmez.
     */
    private ResultActions perform(MockHttpServletRequestBuilder request, MockHttpSession session) throws Exception {
        request.with(csrf());
        return mockMvc.perform(session == null ? request : request.session(session));
    }

    /** Oturumun yanlış cevapları için kuyruğa düşen analiz işlerini sayar. */
    private Integer analysisJobCount(Long sessionId) {
        return jdbcTemplate.queryForObject("""
                SELECT COUNT(*)
                FROM background_job
                JOIN student_answer ON student_answer.id = (background_job.payload->>'studentAnswerId')::bigint
                WHERE background_job.job_type = 'ANALYZE_ANSWER' AND student_answer.study_session_id = ?
                """, Integer.class, sessionId);
    }

    /** İsteğin JSON cevabını okur. */
    private JsonNode readJson(ResultActions result) throws Exception {
        return objectMapper.readTree(result.andReturn().getResponse().getContentAsString());
    }
}
