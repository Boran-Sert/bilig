package com.hataanalizi.core.dashboard;

import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.nullValue;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.authentication;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.hataanalizi.core.TestcontainersConfiguration;
import com.hataanalizi.core.auth.AuthUser;
import java.math.BigDecimal;
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
import org.springframework.test.web.servlet.request.RequestPostProcessor;
import org.springframework.transaction.annotation.Transactional;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

/** Öğrenci panelinin özet, sahiplik ve kazanım kurallarını PostgreSQL üzerinde doğrular. */
@ActiveProfiles("test")
@SpringBootTest
@AutoConfigureMockMvc
@Import(TestcontainersConfiguration.class)
@Transactional
class DashboardControllerIT {

    private final JdbcTemplate jdbcTemplate;
    private final MockMvc mockMvc;
    private final ObjectMapper objectMapper;

    /** Test bağımlılıklarını saklar. */
    @Autowired
    DashboardControllerIT(JdbcTemplate jdbcTemplate, MockMvc mockMvc, ObjectMapper objectMapper) {
        this.jdbcTemplate = jdbcTemplate;
        this.mockMvc = mockMvc;
        this.objectMapper = objectMapper;
    }

    /** Paneli doldurur ve eşikleri aşan kazanımları diğer kullanıcıdan yalıtır. */
    @Test
    void returnsOwnDashboardStatisticsAndFailedOutcomes() throws Exception {
        DashboardFixture fixture = createDashboardFixture();
        Long otherUserId = insertUser();
        Long otherSessionId = insertSession(otherUserId, fixture.examId(), "IN_PROGRESS", null);
        insertAnswer(otherSessionId, fixture.questionIds().get(0), true, null);

        var result = mockMvc.perform(get("/api/me/dashboard").with(student(fixture.userId())))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.summary.answeredQuestionCount").value(16))
                .andExpect(jsonPath("$.summary.accuracyPercent").value(6.25))
                .andExpect(jsonPath("$.summary.latestNet").value(0.25))
                .andExpect(jsonPath("$.summary.latestQuestionCount").value(4))
                .andExpect(jsonPath("$.activeSessions.length()").value(1))
                .andExpect(jsonPath("$.activeSessions[0].examTitle").value("Şiir · Kazanım Testi 1"))
                .andExpect(jsonPath("$.activeSessions[0].questionCount").value(2))
                .andExpect(jsonPath("$.activeSessions[0].answeredCount").value(0))
                .andExpect(jsonPath("$.unitAccuracy.length()").value(1))
                .andExpect(jsonPath("$.unitAccuracy[0].unitTitle").value("Roman"))
                .andExpect(jsonPath("$.unitAccuracy[0].answeredCount").value(16))
                .andExpect(jsonPath("$.unitAccuracy[0].correctCount").value(1))
                .andExpect(jsonPath("$.errorTypeDistribution.length()").value(2))
                .andReturn();

        assertFailedOutcomes(result.getResponse().getContentAsString());
        assertErrorTypeCounts(result.getResponse().getContentAsString());
    }

    /** Hiç cevaplamamış öğrencinin boş panelini sıfırlarla döndürür. */
    @Test
    void returnsEmptyDashboardForNewStudent() throws Exception {
        mockMvc.perform(get("/api/me/dashboard").with(student(insertUser())))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.summary.answeredQuestionCount").value(0))
                .andExpect(jsonPath("$.summary.accuracyPercent").value(0))
                .andExpect(jsonPath("$.summary.latestNet").value(nullValue()))
                .andExpect(jsonPath("$.summary.latestQuestionCount").value(nullValue()))
                .andExpect(jsonPath("$.activeSessions.length()").value(0))
                .andExpect(jsonPath("$.failedOutcomes.length()").value(0))
                .andExpect(jsonPath("$.unitAccuracy.length()").value(0))
                .andExpect(jsonPath("$.errorTypeDistribution.length()").value(0));
    }

    /** Giriş yapmamış kullanıcının paneli okuyamadığını doğrular. */
    @Test
    void requiresAuthentication() throws Exception {
        mockMvc.perform(get("/api/me/dashboard")).andExpect(status().isUnauthorized());
    }

    /** Panel yanıtındaki başarısız kazanım eşiklerini doğrular. */
    private void assertFailedOutcomes(String response) throws Exception {
        Map<String, JsonNode> outcomes = new HashMap<>();
        objectMapper
                .readTree(response)
                .get("failedOutcomes")
                .forEach(outcome -> outcomes.put(outcome.get("code").stringValue(), outcome));
        assertThat(outcomes).containsOnlyKeys("A.2.7", "A.2.8", "A.2.9");
        assertThat(outcomes.get("A.2.7").get("totalWrongCount").longValue()).isEqualTo(9);
        assertThat(outcomes.get("A.2.7").get("testTitle").stringValue()).isEqualTo("Roman · Kazanım Testi 3");
        assertThat(outcomes.get("A.2.7").get("testWrongCount").longValue()).isEqualTo(3);
        assertThat(outcomes.get("A.2.8").get("totalWrongCount").longValue()).isEqualTo(7);
        assertThat(outcomes.get("A.2.8").get("testTitle").isNull()).isTrue();
        assertThat(outcomes.get("A.2.9").get("totalWrongCount").longValue()).isEqualTo(6);
        assertThat(outcomes.get("A.2.9").get("testTitle").isNull()).isTrue();
        assertThat(outcomes.get("A.2.9").get("testWrongCount").isNull()).isTrue();
    }

    /** Paneldeki sınıflandırılmış hata türü toplamlarını doğrular. */
    private void assertErrorTypeCounts(String response) throws Exception {
        Map<String, JsonNode> errorTypes = new HashMap<>();
        objectMapper
                .readTree(response)
                .get("errorTypeDistribution")
                .forEach(errorType -> errorTypes.put(errorType.get("errorType").stringValue(), errorType));
        assertThat(errorTypes).containsOnlyKeys("READING", "KNOWLEDGE");
        assertThat(errorTypes.get("READING").get("answerCount").longValue()).isEqualTo(1);
        assertThat(errorTypes.get("KNOWLEDGE").get("answerCount").longValue()).isEqualTo(1);
    }

    /** Panel istatistikleri ve farklı başarısızlık eşikleri için öğrenci verisi oluşturur. */
    private DashboardFixture createDashboardFixture() {
        Long userId = insertUser();
        Long unitId = insertCurriculumUnit("Roman");
        Long examId = insertExam("Roman · Kazanım Testi 3");
        List<Long> questionIds = insertQuestions(unitId, examId, 4);
        Map<String, Long> outcomeIds = insertOutcomes(unitId);
        insertOutcomeMapping(questionIds.get(0), outcomeIds.get("A.2.7"));
        insertOutcomeMapping(questionIds.get(1), outcomeIds.get("A.2.7"));
        insertOutcomeMapping(questionIds.get(2), outcomeIds.get("A.2.7"));
        insertOutcomeMapping(questionIds.get(0), outcomeIds.get("A.2.8"));
        insertOutcomeMapping(questionIds.get(3), outcomeIds.get("A.2.9"));
        insertAcrossSessionWrongAnswers(userId, examId, questionIds);
        Long completedSessionId = insertSession(userId, examId, "COMPLETED", new BigDecimal("0.25"));
        insertAnswer(completedSessionId, questionIds.get(0), false, "READING");
        insertAnswer(completedSessionId, questionIds.get(1), false, "KNOWLEDGE");
        insertAnswer(completedSessionId, questionIds.get(2), false, null);
        insertAnswer(completedSessionId, questionIds.get(3), true, null);
        Long activeExamId = insertExam("Şiir · Kazanım Testi 1");
        insertQuestions(unitId, activeExamId, 2);
        insertSession(userId, activeExamId, "IN_PROGRESS", null);
        return new DashboardFixture(userId, examId, questionIds);
    }

    /** Altı ayrı oturumda aynı kazanımdan ikişer yanlış cevap ekler. */
    private void insertAcrossSessionWrongAnswers(Long userId, Long examId, List<Long> questionIds) {
        for (int attempt = 0; attempt < 6; attempt++) {
            Long sessionId = insertSession(userId, examId, "COMPLETED", BigDecimal.ZERO);
            insertAnswer(sessionId, questionIds.get(0), false, null);
            insertAnswer(sessionId, questionIds.get(3), false, null);
        }
    }

    /** Belirtilen ünite ve test için sıralı sorular oluşturur. */
    private List<Long> insertQuestions(Long unitId, Long examId, int count) {
        List<Long> questionIds = new java.util.ArrayList<>();
        for (int index = 0; index < count; index++) {
            String content = """
                    {"stem":[{"type":"paragraph","md":"Question"}],
                     "options":[{"label":"A","blocks":[{"type":"paragraph","md":"Option"}]}]}
                    """;
            String contentHash = UUID.randomUUID().toString().replace("-", "")
                    + UUID.randomUUID().toString().replace("-", "");
            Long questionId = jdbcTemplate.queryForObject("""
                    INSERT INTO question (
                        curriculum_unit_id, origin, content, correct_option, content_hash, status
                    ) VALUES (?, 'SOURCE', ?::jsonb, 'A', ?, 'PUBLISHED')
                    RETURNING id
                    """, Long.class, unitId, content, contentHash);
            questionIds.add(questionId);
            jdbcTemplate.update(
                    "INSERT INTO exam_question (exam_id, question_id, position) VALUES (?, ?, ?)",
                    examId,
                    questionId,
                    index + 1);
        }
        return questionIds;
    }

    /** Panel testlerinde kullanılacak üç kazanımı oluşturur. */
    private Map<String, Long> insertOutcomes(Long unitId) {
        String identifier = UUID.randomUUID().toString();
        Long groupId = jdbcTemplate.queryForObject("""
                INSERT INTO learning_outcome_group (curriculum_id, code, name)
                VALUES ((SELECT curriculum_id FROM curriculum_unit WHERE id = ?), ?, ?)
                RETURNING id
                """, Long.class, unitId, identifier, identifier);
        Map<String, Long> outcomeIds = new HashMap<>();
        for (String code : List.of("A.2.7", "A.2.8", "A.2.9")) {
            Long outcomeId =
                    jdbcTemplate.queryForObject("""
                    INSERT INTO learning_outcome (learning_outcome_group_id, code, title, search_text)
                    VALUES (?, ?, ?, ?)
                    RETURNING id
                    """, Long.class, groupId, code, "Outcome " + code, "Outcome " + code);
            outcomeIds.put(code, outcomeId);
        }
        return outcomeIds;
    }

    /** Soruyu belirtilen kazanıma bağlar. */
    private void insertOutcomeMapping(Long questionId, Long outcomeId) {
        jdbcTemplate.update("""
                INSERT INTO question_outcome (question_id, learning_outcome_id, mapped_by)
                VALUES (?, ?, 'SOURCE')
                """, questionId, outcomeId);
    }

    /** Yeni bir öğrenci hesabı oluşturur. */
    private Long insertUser() {
        String identifier = UUID.randomUUID().toString();
        return jdbcTemplate.queryForObject("""
                INSERT INTO app_user (tenant_id, email, display_name, role)
                SELECT id, ?, ?, 'STUDENT' FROM tenant WHERE name = 'Bilig'
                RETURNING id
                """, Long.class, identifier + "@example.test", identifier);
    }

    /** Testte kullanılacak ders programı ve ünitesini oluşturur. */
    private Long insertCurriculumUnit(String title) {
        String identifier = UUID.randomUUID().toString();
        Long subjectId = jdbcTemplate.queryForObject("""
                INSERT INTO subject (code, name) VALUES (?, ?) RETURNING id
                """, Long.class, identifier, identifier);
        Long curriculumId = jdbcTemplate.queryForObject("""
                INSERT INTO curriculum (subject_id, name, model, year) VALUES (?, ?, ?, ?) RETURNING id
                """, Long.class, subjectId, identifier, "LEGACY", 2018);
        return jdbcTemplate.queryForObject("""
                INSERT INTO curriculum_unit (curriculum_id, grade, unit_no, title) VALUES (?, ?, ?, ?)
                RETURNING id
                """, Long.class, curriculumId, 12, 1, title);
    }

    /** Yayındaki test kaydını oluşturur. */
    private Long insertExam(String title) {
        return jdbcTemplate.queryForObject("""
                INSERT INTO exam (title, status) VALUES (?, 'PUBLISHED') RETURNING id
                """, Long.class, title);
    }

    /** Test durumuyla oturum oluşturur ve tamamlanan oturuma net yazar. */
    private Long insertSession(Long userId, Long examId, String status, BigDecimal net) {
        return jdbcTemplate.queryForObject("""
                INSERT INTO study_session (user_id, exam_id, status, net, completed_at)
                VALUES (?, ?, ?, ?, CASE WHEN ? = 'COMPLETED' THEN now() END)
                RETURNING id
                """, Long.class, userId, examId, status, net, status);
    }

    /** Öğrencinin doğru veya yanlış cevabını ve varsa hata türünü kaydeder. */
    private void insertAnswer(Long sessionId, Long questionId, boolean correct, String errorType) {
        jdbcTemplate.update("""
                INSERT INTO student_answer (study_session_id, question_id, selected_option, is_correct, error_type)
                VALUES (?, ?, 'A', ?, ?)
                """, sessionId, questionId, correct, errorType);
    }

    /** İstek için test öğrencisinin kimliğini hazırlar. */
    private RequestPostProcessor student(Long userId) {
        AuthUser authUser = new AuthUser(userId, "student@example.test", "STUDENT");
        var authentication = new UsernamePasswordAuthenticationToken(
                authUser, null, List.of(new SimpleGrantedAuthority("ROLE_STUDENT")));
        return authentication(authentication);
    }

    /** Panel testinin öğrenci, test ve soru kimliklerini taşır. */
    private record DashboardFixture(Long userId, Long examId, List<Long> questionIds) {}
}
