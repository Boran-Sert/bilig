package com.hataanalizi.core.session;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.authentication;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.csrf;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

import com.hataanalizi.core.TestcontainersConfiguration;
import com.hataanalizi.core.auth.AuthUser;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import org.junit.jupiter.api.AfterEach;
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
import org.springframework.test.web.servlet.MvcResult;
import org.springframework.test.web.servlet.request.RequestPostProcessor;
import tools.jackson.databind.ObjectMapper;

/** Oturum başlatma güvenliğini ve eşzamanlı istekleri doğrular. */
@ActiveProfiles("test")
@SpringBootTest
@AutoConfigureMockMvc
@Import(TestcontainersConfiguration.class)
class SessionApiSafetyIT {

    private final JdbcTemplate jdbcTemplate;
    private final MockMvc mockMvc;
    private final ObjectMapper objectMapper;
    private final SessionQuestionFixture questionFixture;
    private Long createdExamId;

    /** Test bağımlılıklarını ve soru fixture'ını saklar. */
    @Autowired
    SessionApiSafetyIT(JdbcTemplate jdbcTemplate, MockMvc mockMvc, ObjectMapper objectMapper) {
        this.jdbcTemplate = jdbcTemplate;
        this.mockMvc = mockMvc;
        this.objectMapper = objectMapper;
        this.questionFixture = new SessionQuestionFixture(jdbcTemplate);
    }

    /** Commit edilen yayındaki testi siler; başka testlerin listesine sızmaz. */
    @AfterEach
    void deleteCreatedExam() {
        if (createdExamId == null) {
            return;
        }
        jdbcTemplate.update("DELETE FROM study_session WHERE exam_id = ?", createdExamId);
        jdbcTemplate.update("DELETE FROM exam WHERE id = ?", createdExamId);
    }

    /** Eşzamanlı başlatmaların tek oturumu paylaşmasını ve yanıtı filtrelemesini doğrular. */
    @Test
    void concurrentStartsReuseSessionAndHidePrivateQuestionFields() throws Exception {
        Long userId = insertUser();
        Long examId = insertExamWithQuestion();
        ExecutorService executor = Executors.newFixedThreadPool(2);
        CountDownLatch startSignal = new CountDownLatch(1);
        try {
            Future<MvcResult> firstRequest =
                    executor.submit(() -> startSessionWhenReleased(startSignal, userId, examId));
            Future<MvcResult> secondRequest =
                    executor.submit(() -> startSessionWhenReleased(startSignal, userId, examId));
            startSignal.countDown();
            MvcResult firstResult = firstRequest.get(20, TimeUnit.SECONDS);
            MvcResult secondResult = secondRequest.get(20, TimeUnit.SECONDS);

            assertThat(firstResult.getResponse().getStatus()).isEqualTo(200);
            assertThat(secondResult.getResponse().getStatus()).isEqualTo(200);
            String firstBody = firstResult.getResponse().getContentAsString();
            String secondBody = secondResult.getResponse().getContentAsString();
            long firstSessionId =
                    objectMapper.readTree(firstBody).get("sessionId").longValue();
            long secondSessionId =
                    objectMapper.readTree(secondBody).get("sessionId").longValue();
            assertThat(secondSessionId).isEqualTo(firstSessionId);
            assertThat(activeSessionCount(userId, examId)).isEqualTo(1L);
            assertThat(firstBody)
                    .contains("Question")
                    .doesNotContain("correctOption", "explanation", "isCorrect", "Private answer");
            assertThat(secondBody)
                    .contains("Question")
                    .doesNotContain("correctOption", "explanation", "isCorrect", "Private answer");
        } finally {
            executor.shutdownNow();
        }
    }

    /** Eşzamanlı çağrı serbest bırakılana kadar bekler. */
    private MvcResult startSessionWhenReleased(CountDownLatch startSignal, Long userId, Long examId) throws Exception {
        startSignal.await();
        return mockMvc.perform(post("/api/tests/{id}/sessions", examId)
                        .with(student(userId))
                        .with(csrf()))
                .andReturn();
    }

    /** Yeni bir öğrenci hesabı oluşturur. */
    private Long insertUser() {
        String identifier = UUID.randomUUID().toString();
        return jdbcTemplate.queryForObject(
                "INSERT INTO app_user (tenant_id, email, display_name, role) "
                        + "SELECT id, ?, ?, 'STUDENT' FROM tenant WHERE name = 'Bilig' RETURNING id",
                Long.class,
                identifier + "@example.test",
                identifier);
    }

    /** Bir sorulu yayımlanmış test oluşturur. */
    private Long insertExamWithQuestion() {
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
        Long unitId = jdbcTemplate.queryForObject(
                "INSERT INTO curriculum_unit (curriculum_id, grade, unit_no, title) VALUES (?, ?, ?, ?) RETURNING id",
                Long.class,
                curriculumId,
                12,
                1,
                identifier);
        Long examId = jdbcTemplate.queryForObject(
                "INSERT INTO exam (title, status) VALUES (?, 'PUBLISHED') RETURNING id", Long.class, identifier);
        Long questionId = questionFixture.insertQuestion(unitId);
        jdbcTemplate.update(
                "INSERT INTO exam_question (exam_id, question_id, position) VALUES (?, ?, 1)", examId, questionId);
        createdExamId = examId;
        return examId;
    }

    /** Öğrencinin testteki açık oturum sayısını döndürür. */
    private Long activeSessionCount(Long userId, Long examId) {
        return jdbcTemplate.queryForObject(
                "SELECT count(*) FROM study_session WHERE user_id = ? AND exam_id = ? " + "AND status = 'IN_PROGRESS'",
                Long.class,
                userId,
                examId);
    }

    /** İstek için test öğrencisinin kimliğini hazırlar. */
    private RequestPostProcessor student(Long userId) {
        AuthUser authUser = new AuthUser(userId, "student@example.test", "STUDENT");
        var authentication = new UsernamePasswordAuthenticationToken(
                authUser, null, List.of(new SimpleGrantedAuthority("ROLE_STUDENT")));
        return authentication(authentication);
    }
}
