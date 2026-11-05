package com.hataanalizi.core.report;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.authentication;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.hataanalizi.core.TestcontainersConfiguration;
import com.hataanalizi.core.auth.AuthUser;
import jakarta.servlet.http.Cookie;
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
import org.springframework.test.web.servlet.request.RequestPostProcessor;

/** Bildirim API'sinin doğrulamasını, yetkisini ve PostgreSQL kaydını sınar. */
@ActiveProfiles("test")
@SpringBootTest
@AutoConfigureMockMvc
@Import(TestcontainersConfiguration.class)
class ReportControllerIT {

    private static final String CSRF_TOKEN = "report-test-csrf";

    private final JdbcTemplate jdbcTemplate;
    private final MockMvc mockMvc;

    /** HTTP istemcisini ve veritabanı bağlantısını saklar. */
    @Autowired
    ReportControllerIT(JdbcTemplate jdbcTemplate, MockMvc mockMvc) {
        this.jdbcTemplate = jdbcTemplate;
        this.mockMvc = mockMvc;
    }

    /** Soru bildiriminin kaydını oluşturur. */
    @Test
    void reportsQuestion() throws Exception {
        Long userId = insertUser();
        Long questionId = insertQuestion("PUBLISHED");

        mockMvc.perform(post("/api/reports")
                        .with(student(userId))
                        .cookie(new Cookie("XSRF-TOKEN", CSRF_TOKEN))
                        .header("X-XSRF-TOKEN", CSRF_TOKEN)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"questionId\":" + questionId + ",\"note\":\"Yanlış cevap anahtarı\"}"))
                .andExpect(status().isCreated());

        assertReport(userId, questionId, null, "Yanlış cevap anahtarı");
    }

    /** Öğrencinin kendi asistan anlatımını bildirmesine izin verir. */
    @Test
    void reportsOwnedAssistantMessage() throws Exception {
        Long userId = insertUser();
        Long messageId = insertAssistantMessage(userId);

        mockMvc.perform(post("/api/reports")
                        .with(student(userId))
                        .cookie(new Cookie("XSRF-TOKEN", CSRF_TOKEN))
                        .header("X-XSRF-TOKEN", CSRF_TOKEN)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"messageId\":" + messageId + "}"))
                .andExpect(status().isCreated());

        assertReport(userId, null, messageId, null);
    }

    /** Yayında olmayan soruyu bildirmeyi reddeder. */
    @Test
    void rejectsUnpublishedQuestion() throws Exception {
        Long userId = insertUser();
        Long questionId = insertQuestion("DRAFT");

        mockMvc.perform(post("/api/reports")
                        .with(student(userId))
                        .cookie(new Cookie("XSRF-TOKEN", CSRF_TOKEN))
                        .header("X-XSRF-TOKEN", CSRF_TOKEN)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"questionId\":" + questionId + "}"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.code").value("QUESTION_NOT_FOUND"));
    }

    /** Başka bir öğrencinin anlatımını bildirmeyi reddeder. */
    @Test
    void rejectsAnotherStudentsMessage() throws Exception {
        Long ownerId = insertUser();
        Long otherUserId = insertUser();
        Long messageId = insertAssistantMessage(ownerId);

        mockMvc.perform(post("/api/reports")
                        .with(student(otherUserId))
                        .cookie(new Cookie("XSRF-TOKEN", CSRF_TOKEN))
                        .header("X-XSRF-TOKEN", CSRF_TOKEN)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"messageId\":" + messageId + "}"))
                .andExpect(status().isNotFound());

        assertThatNoReportExists(otherUserId, messageId);
    }

    /** İki hedef birden verildiğinde isteği reddeder. */
    @Test
    void rejectsBothTargets() throws Exception {
        mockMvc.perform(post("/api/reports")
                        .with(student(insertUser()))
                        .cookie(new Cookie("XSRF-TOKEN", CSRF_TOKEN))
                        .header("X-XSRF-TOKEN", CSRF_TOKEN)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"questionId\":1,\"messageId\":1}"))
                .andExpect(status().isBadRequest());
    }

    /** Hedef verilmediğinde isteği reddeder. */
    @Test
    void rejectsMissingTarget() throws Exception {
        mockMvc.perform(post("/api/reports")
                        .with(student(insertUser()))
                        .cookie(new Cookie("XSRF-TOKEN", CSRF_TOKEN))
                        .header("X-XSRF-TOKEN", CSRF_TOKEN)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"note\":\"Hatalı içerik\"}"))
                .andExpect(status().isBadRequest());
    }

    /** Soru ya da mesaj bildiriminin kullanıcı ve hedef değerlerini doğrular. */
    private void assertReport(Long userId, Long questionId, Long messageId, String note) {
        var report = jdbcTemplate.queryForMap("""
                SELECT user_id, question_id, tutor_message_id, note
                FROM content_report
                WHERE user_id = ?
                """, userId);
        assertThat(report.get("user_id")).isEqualTo(userId);
        assertThat(report.get("question_id")).isEqualTo(questionId);
        assertThat(report.get("tutor_message_id")).isEqualTo(messageId);
        assertThat(report.get("note")).isEqualTo(note);
    }

    /** Bildirim oluşturulmadığını doğrular. */
    private void assertThatNoReportExists(Long userId, Long messageId) {
        assertThat(jdbcTemplate.queryForObject(
                        "SELECT count(*) FROM content_report WHERE user_id = ? AND tutor_message_id = ?",
                        Integer.class,
                        userId,
                        messageId))
                .isZero();
    }

    /** Yeni öğrenci hesabı açar. */
    private Long insertUser() {
        String identifier = UUID.randomUUID().toString();
        return jdbcTemplate.queryForObject("""
                INSERT INTO app_user (tenant_id, email, display_name, role)
                SELECT id, ?, ?, 'STUDENT' FROM tenant WHERE name = 'Bilig'
                RETURNING id
                """, Long.class, identifier + "@example.test", identifier);
    }

    /** Verilen durumda bir soru oluşturur. */
    private Long insertQuestion(String status) {
        String identifier = UUID.randomUUID().toString();
        Long subjectId = jdbcTemplate.queryForObject(
                "INSERT INTO subject (code, name) VALUES (?, ?) RETURNING id", Long.class, identifier, identifier);
        Long curriculumId = jdbcTemplate.queryForObject("""
                INSERT INTO curriculum (subject_id, name, model, year)
                VALUES (?, ?, 'LEGACY', 2018)
                RETURNING id
                """, Long.class, subjectId, identifier);
        Long unitId = jdbcTemplate.queryForObject("""
                INSERT INTO curriculum_unit (curriculum_id, grade, unit_no, title)
                VALUES (?, 12, 1, ?)
                RETURNING id
                """, Long.class, curriculumId, identifier);
        return jdbcTemplate.queryForObject(
                """
                INSERT INTO question (
                    curriculum_unit_id, origin, content, correct_option, content_hash, status
                ) VALUES (?, 'SOURCE', '{"stem":[],"options":[]}'::jsonb, 'A', ?, ?)
                RETURNING id
                """,
                Long.class,
                unitId,
                identifier.replace("-", "") + UUID.randomUUID().toString().replace("-", ""),
                status);
    }

    /** Öğrenciye ait asistan mesajı oluşturur. */
    private Long insertAssistantMessage(Long userId) {
        Long conversationId = jdbcTemplate.queryForObject(
                "INSERT INTO tutor_conversation (user_id) VALUES (?) RETURNING id", Long.class, userId);
        return jdbcTemplate.queryForObject("""
                INSERT INTO tutor_message (tutor_conversation_id, role, content)
                VALUES (?, 'ASSISTANT', 'Anlatım')
                RETURNING id
                """, Long.class, conversationId);
    }

    /** Kullanıcı kimliğiyle öğrenci yetkisi taşır. */
    private RequestPostProcessor student(Long userId) {
        AuthUser authUser = new AuthUser(userId, "student@example.test", "STUDENT");
        return authentication(new UsernamePasswordAuthenticationToken(
                authUser, null, List.of(new SimpleGrantedAuthority("ROLE_STUDENT"))));
    }
}
