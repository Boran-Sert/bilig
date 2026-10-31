package com.hataanalizi.core;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.context.annotation.Import;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.transaction.annotation.Transactional;

/** Öğrenci oturumu ve cevap tablolarının migration sözleşmesini doğrular. */
@ActiveProfiles("test")
@SpringBootTest
@Import(TestcontainersConfiguration.class)
@Transactional
class StudyTablesIT {

    private final JdbcTemplate jdbcTemplate;

    /** Test veritabanı erişimini hazırlar. */
    @Autowired
    StudyTablesIT(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    /** Oturum ve cevap tablolarının beklenen indekslerle oluştuğunu doğrular. */
    @Test
    void createsStudyTablesAndIndexes() {
        List<String> tables = jdbcTemplate.queryForList("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name IN ('study_session', 'student_answer')
                ORDER BY table_name
                """, String.class);
        List<String> indexes = jdbcTemplate.queryForList("""
                SELECT indexname
                FROM pg_indexes
                WHERE schemaname = 'public'
                  AND indexname IN (
                    'uq_study_session_active', 'idx_study_session_user_id',
                    'uq_student_answer_study_session_id_question_id',
                    'idx_student_answer_question_id'
                  )
                """, String.class);

        assertEquals(List.of("student_answer", "study_session"), tables);
        assertTrue(indexes.containsAll(List.of(
                "uq_study_session_active",
                "idx_study_session_user_id",
                "uq_student_answer_study_session_id_question_id",
                "idx_student_answer_question_id")));
    }

    /** Aynı öğrencinin aynı testte ikinci açık oturum açmasını reddeder. */
    @Test
    void rejectsSecondInProgressSessionForSameExamAndUser() {
        Long userId = insertUser();
        Long examId = insertExam();
        insertStudySession(userId, examId, "IN_PROGRESS");

        assertThrows(DataIntegrityViolationException.class, () -> insertStudySession(userId, examId, "IN_PROGRESS"));
    }

    /** Tamamlanan oturumdan sonra aynı test için yeni açık oturuma izin verir. */
    @Test
    void allowsNewInProgressSessionAfterPreviousSessionCompleted() {
        Long userId = insertUser();
        Long examId = insertExam();
        insertStudySession(userId, examId, "COMPLETED");

        insertStudySession(userId, examId, "IN_PROGRESS");

        assertEquals(
                2,
                jdbcTemplate.queryForObject(
                        "SELECT count(*) FROM study_session WHERE user_id = ? AND exam_id = ?",
                        Integer.class,
                        userId,
                        examId));
    }

    /** Aynı oturumda aynı soruya ikinci cevap satırı eklenmesini reddeder. */
    @Test
    void rejectsSecondAnswerForSameQuestionAndSession() {
        Long userId = insertUser();
        Long questionId = insertQuestion();
        Long sessionId = insertStudySession(userId, null, "IN_PROGRESS");
        insertAnswer(sessionId, questionId);

        assertThrows(DataIntegrityViolationException.class, () -> insertAnswer(sessionId, questionId));
    }

    /** Test kullanıcısı için benzersiz öğrenci hesabı oluşturur. */
    private Long insertUser() {
        String identifier = UUID.randomUUID().toString();
        return jdbcTemplate.queryForObject("""
                INSERT INTO app_user (tenant_id, email, display_name)
                SELECT id, ?, ?
                FROM tenant
                WHERE name = 'Bilig'
                RETURNING id
                """, Long.class, identifier + "@example.test", identifier);
    }

    /** Test için yeni bir sınav oluşturur. */
    private Long insertExam() {
        return jdbcTemplate.queryForObject(
                "INSERT INTO exam (title) VALUES (?) RETURNING id",
                Long.class,
                UUID.randomUUID().toString());
    }

    /** Test için gereken ders programı ve üniteyi oluşturup soru ekler. */
    private Long insertQuestion() {
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
        String contentHash = UUID.randomUUID().toString().replace("-", "")
                + UUID.randomUUID().toString().replace("-", "");
        return jdbcTemplate.queryForObject("""
                INSERT INTO question (
                    curriculum_unit_id, origin, content, correct_option, content_hash
                ) VALUES (?, 'SOURCE', '{}'::jsonb, 'A', ?)
                RETURNING id
                """, Long.class, unitId, contentHash);
    }

    /** Yeni oturum kaydı oluşturup kimliğini döndürür. */
    private Long insertStudySession(Long userId, Long examId, String status) {
        return jdbcTemplate.queryForObject("""
                INSERT INTO study_session (user_id, exam_id, status)
                VALUES (?, ?, ?)
                RETURNING id
                """, Long.class, userId, examId, status);
    }

    /** Oturum için soru cevabı oluşturur. */
    private void insertAnswer(Long sessionId, Long questionId) {
        jdbcTemplate.update("""
                INSERT INTO student_answer (study_session_id, question_id, selected_option, is_correct)
                VALUES (?, ?, 'A', true)
                """, sessionId, questionId);
    }
}
