package com.hataanalizi.core.session;

import static org.hamcrest.Matchers.nullValue;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.authentication;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.csrf;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
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
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;
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

    /** Test bağımlılıklarını saklar. */
    @Autowired
    SessionControllerIT(JdbcTemplate jdbcTemplate, MockMvc mockMvc) {
        this.jdbcTemplate = jdbcTemplate;
        this.mockMvc = mockMvc;
    }

    /** Aynı öğrencinin oturumunu sürdürür ve başkasının oturumunu açığa çıkarmaz. */
    @Test
    void resumesOwnSessionAndCreatesSeparateSessionForAnotherStudent() throws Exception {
        Long ownerId = insertUser();
        Long otherUserId = insertUser();
        Long unitId = insertCurriculumUnit();
        Long examId = insertExam("PUBLISHED");
        Long firstQuestionId = insertQuestion(unitId, "PUBLISHED");
        Long secondQuestionId = insertQuestion(unitId, "PUBLISHED");
        Long draftQuestionId = insertQuestion(unitId, "DRAFT");
        insertExamQuestion(examId, secondQuestionId, (short) 1);
        insertExamQuestion(examId, firstQuestionId, (short) 2);
        insertExamQuestion(examId, draftQuestionId, (short) 3);
        Long ownerSessionId = insertStudySession(ownerId, examId, (short) 2);
        insertAnswer(ownerSessionId, secondQuestionId, "C");

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

    /** Yeni bir öğrenci hesabı oluşturur. */
    private Long insertUser() {
        String identifier = UUID.randomUUID().toString();
        return jdbcTemplate.queryForObject("""
                INSERT INTO app_user (tenant_id, email, display_name, role)
                SELECT id, ?, ?, 'STUDENT'
                FROM tenant
                WHERE name = 'Bilig'
                RETURNING id
                """, Long.class, identifier + "@example.test", identifier);
    }

    /** Testte kullanılacak ders programı ve ünitesini oluşturur. */
    private Long insertCurriculumUnit() {
        String identifier = UUID.randomUUID().toString();
        Long subjectId = jdbcTemplate.queryForObject(
                "INSERT INTO subject (code, name) VALUES (?, ?) RETURNING id", Long.class, identifier, identifier);
        Long curriculumId = jdbcTemplate.queryForObject("""
                INSERT INTO curriculum (subject_id, name, model, year)
                VALUES (?, ?, ?, ?)
                RETURNING id
                """, Long.class, subjectId, identifier, "LEGACY", 2018);
        return jdbcTemplate.queryForObject("""
                INSERT INTO curriculum_unit (curriculum_id, grade, unit_no, title)
                VALUES (?, ?, ?, ?)
                RETURNING id
                """, Long.class, curriculumId, 12, 1, identifier);
    }

    /** Yayındaki test kaydını oluşturur. */
    private Long insertExam(String examStatus) {
        return jdbcTemplate.queryForObject(
                "INSERT INTO exam (title, status) VALUES (?, ?) RETURNING id",
                Long.class,
                "Test " + UUID.randomUUID(),
                examStatus);
    }

    /** İçerik ve doğru şık içeren yayınlanmış bir soru oluşturur. */
    private Long insertQuestion(Long unitId, String questionStatus) {
        String content = """
                {"stem":[{"type":"paragraph","md":"Question"}],
                 "options":[
                   {"label":"A","blocks":[{"type":"paragraph","md":"Option A"}]},
                   {"label":"B","blocks":[{"type":"paragraph","md":"Option B"}]},
                   {"label":"C","blocks":[{"type":"paragraph","md":"Option C"}]},
                   {"label":"D","blocks":[{"type":"paragraph","md":"Option D"}]},
                   {"label":"E","blocks":[{"type":"paragraph","md":"Option E"}]}
                 ]}
                """;
        String contentHash = UUID.randomUUID().toString().replace("-", "")
                + UUID.randomUUID().toString().replace("-", "");
        return jdbcTemplate.queryForObject("""
                INSERT INTO question (
                    curriculum_unit_id, origin, content, correct_option, content_hash, status
                ) VALUES (?, 'SOURCE', ?::jsonb, 'B', ?, ?)
                RETURNING id
                """, Long.class, unitId, content, contentHash, questionStatus);
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

    /** Oturumdaki bir sorunun cevabını kaydeder. */
    private void insertAnswer(Long sessionId, Long questionId, String selectedOption) {
        jdbcTemplate.update("""
                INSERT INTO student_answer (study_session_id, question_id, selected_option, is_correct)
                VALUES (?, ?, ?, false)
                """, sessionId, questionId, selectedOption);
    }

    /** İstek için test öğrencisinin kimliğini hazırlar. */
    private RequestPostProcessor student(Long userId) {
        AuthUser authUser = new AuthUser(userId, "student@example.test", "STUDENT");
        var authentication = new UsernamePasswordAuthenticationToken(
                authUser, null, List.of(new SimpleGrantedAuthority("ROLE_STUDENT")));
        return authentication(authentication);
    }
}
