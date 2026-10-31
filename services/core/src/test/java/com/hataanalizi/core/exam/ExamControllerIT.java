package com.hataanalizi.core.exam;

import static org.hamcrest.Matchers.nullValue;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.authentication;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
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

/** Test listesinin yayın ve ilerleme sözleşmesini PostgreSQL üzerinde doğrular. */
@ActiveProfiles("test")
@SpringBootTest
@AutoConfigureMockMvc
@Import(TestcontainersConfiguration.class)
@Transactional
class ExamControllerIT {

    private final JdbcTemplate jdbcTemplate;
    private final MockMvc mockMvc;

    /** Test bağımlılıklarını saklar. */
    @Autowired
    ExamControllerIT(JdbcTemplate jdbcTemplate, MockMvc mockMvc) {
        this.jdbcTemplate = jdbcTemplate;
        this.mockMvc = mockMvc;
    }

    /** Yalnız yayındaki testleri ve öğrencinin en son oturum ilerlemesini döndürür. */
    @Test
    void listsPublishedExamsWithLatestSessionProgress() throws Exception {
        Long userId = insertUser();
        Long unitId = insertCurriculumUnit();
        Long examId = insertExam("Published test", "PUBLISHED");
        Long firstQuestionId = insertQuestion(unitId, "PUBLISHED");
        Long secondQuestionId = insertQuestion(unitId, "PUBLISHED");
        Long draftQuestionId = insertQuestion(unitId, "DRAFT");
        insertExamQuestion(examId, firstQuestionId, (short) 1);
        insertExamQuestion(examId, secondQuestionId, (short) 2);
        insertExamQuestion(examId, draftQuestionId, (short) 3);
        Long sessionId = insertStudySession(userId, examId, "COMPLETED");
        insertAnswer(sessionId, firstQuestionId);
        insertExam("Draft test", "DRAFT");
        insertExam("Published test without session", "PUBLISHED");

        mockMvc.perform(get("/api/tests").with(student(userId)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(2))
                .andExpect(jsonPath("$[0].id").value(examId))
                .andExpect(jsonPath("$[0].title").value("Published test"))
                .andExpect(jsonPath("$[0].questionCount").value(2))
                .andExpect(jsonPath("$[0].answeredCount").value(1))
                .andExpect(jsonPath("$[0].sessionId").value(sessionId))
                .andExpect(jsonPath("$[0].status").value("COMPLETED"))
                .andExpect(jsonPath("$[1].answeredCount").value(0))
                .andExpect(jsonPath("$[1].sessionId").value(nullValue()))
                .andExpect(jsonPath("$[1].status").value(nullValue()));
    }

    /** Giriş yapmamış kullanıcının test listesini alamadığını doğrular. */
    @Test
    void requiresAuthentication() throws Exception {
        mockMvc.perform(get("/api/tests")).andExpect(status().isUnauthorized());
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

    /** Belirtilen durumda test oluşturur. */
    private Long insertExam(String title, String examStatus) {
        return jdbcTemplate.queryForObject(
                "INSERT INTO exam (title, status) VALUES (?, ?) RETURNING id", Long.class, title, examStatus);
    }

    /** İçeriği ve doğru cevabı olan soru oluşturur. */
    private Long insertQuestion(Long unitId, String questionStatus) {
        String content = """
                {"stem":[{"type":"paragraph","md":"Test question"}],
                 "options":[{"label":"A","blocks":[{"type":"paragraph","md":"Option A"}]}]}
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

    /** Test oturumu oluşturur. */
    private Long insertStudySession(Long userId, Long examId, String sessionStatus) {
        return jdbcTemplate.queryForObject("""
                INSERT INTO study_session (user_id, exam_id, status)
                VALUES (?, ?, ?)
                RETURNING id
                """, Long.class, userId, examId, sessionStatus);
    }

    /** Oturuma öğrenci cevabı ekler. */
    private void insertAnswer(Long sessionId, Long questionId) {
        jdbcTemplate.update("""
                INSERT INTO student_answer (study_session_id, question_id, selected_option, is_correct)
                VALUES (?, ?, 'A', false)
                """, sessionId, questionId);
    }

    /** İstek için test öğrencisinin kimliğini hazırlar. */
    private RequestPostProcessor student(Long userId) {
        AuthUser authUser = new AuthUser(userId, "student@example.test", "STUDENT");
        var authentication = new UsernamePasswordAuthenticationToken(
                authUser, null, List.of(new SimpleGrantedAuthority("ROLE_STUDENT")));
        return authentication(authentication);
    }
}
