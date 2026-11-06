package com.hataanalizi.core.tutor;

import java.util.UUID;
import org.springframework.jdbc.core.JdbcTemplate;

/** Tutor testleri için PostgreSQL kayıtlarını oluşturur. */
final class TutorTestFixture {

    private final JdbcTemplate jdbcTemplate;

    /** Test veritabanı bağlantısını saklar. */
    TutorTestFixture(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    /** Yeni bir öğrenci hesabı oluşturur. */
    Long insertUser() {
        String identifier = UUID.randomUUID().toString();
        return jdbcTemplate.queryForObject("""
                INSERT INTO app_user (tenant_id, email, display_name, role)
                SELECT id, ?, ?, 'STUDENT' FROM tenant WHERE name = 'Bilig'
                RETURNING id
                """, Long.class, identifier + "@example.test", identifier);
    }

    /** Bir sorusu cevaplanmış test oturumunu oluşturur. */
    AnsweredQuestion insertAnsweredQuestion(Long userId) {
        Long unitId = insertCurriculumUnit();
        Long questionId = insertQuestion(unitId);
        Long examId = insertExam();
        jdbcTemplate.update(
                "INSERT INTO exam_question (exam_id, question_id, position) VALUES (?, ?, 1)", examId, questionId);
        Long sessionId = jdbcTemplate.queryForObject("""
                INSERT INTO study_session (user_id, exam_id)
                VALUES (?, ?)
                RETURNING id
                """, Long.class, userId, examId);
        jdbcTemplate.update("""
                INSERT INTO student_answer (study_session_id, question_id, selected_option, is_correct)
                VALUES (?, ?, 'A', false)
                """, sessionId, questionId);
        return new AnsweredQuestion(sessionId, questionId);
    }

    /** Bir sorusu henüz cevaplanmamış açık test oturumunu oluşturur. */
    AnsweredQuestion insertUnansweredQuestion(Long userId) {
        Long unitId = insertCurriculumUnit();
        Long questionId = insertQuestion(unitId);
        Long examId = insertExam();
        jdbcTemplate.update(
                "INSERT INTO exam_question (exam_id, question_id, position) VALUES (?, ?, 1)", examId, questionId);
        Long sessionId = jdbcTemplate.queryForObject("""
                INSERT INTO study_session (user_id, exam_id)
                VALUES (?, ?)
                RETURNING id
                """, Long.class, userId, examId);
        return new AnsweredQuestion(sessionId, questionId);
    }

    /** Öğrenciye ait boş bir sohbet oluşturur. */
    Long insertConversation(Long userId) {
        return jdbcTemplate.queryForObject(
                "INSERT INTO tutor_conversation (user_id) VALUES (?) RETURNING id", Long.class, userId);
    }

    /** Alıntı bağlamak için bir ders kitabı içerik bloğu oluşturur. */
    Long insertContentBlock(Long userId) {
        String identifier = UUID.randomUUID().toString();
        String hash = identifier.replace("-", "") + UUID.randomUUID().toString().replace("-", "");
        Long sourceDocumentId = jdbcTemplate.queryForObject("""
                INSERT INTO source_document (title, sha256, file_path, uploaded_by)
                VALUES (?, ?, ?, ?)
                RETURNING id
                """, Long.class, "Test textbook", hash, "test.pdf", userId);
        Long sourcePageId = jdbcTemplate.queryForObject("""
                INSERT INTO source_page (source_document_id, page_no)
                VALUES (?, 1)
                RETURNING id
                """, Long.class, sourceDocumentId);
        return jdbcTemplate.queryForObject("""
                INSERT INTO content_block (
                    source_page_id, block_type, position, title_path, markdown, search_text, status
                ) VALUES (?, 'ALINTI', 1, 'Test quote', 'Quote content', 'Quote content', 'PUBLISHED')
                RETURNING id
                """, Long.class, sourcePageId);
    }

    /** Sohbetteki kayıtlı mesaj sayısını döndürür. */
    int messageCount(Long conversationId) {
        return jdbcTemplate.queryForObject(
                "SELECT count(*) FROM tutor_message WHERE tutor_conversation_id = ?", Integer.class, conversationId);
    }

    /** Testte kullanılacak ders programı ve ünitesini oluşturur. */
    private Long insertCurriculumUnit() {
        String identifier = UUID.randomUUID().toString();
        Long subjectId = jdbcTemplate.queryForObject(
                "INSERT INTO subject (code, name) VALUES (?, ?) RETURNING id", Long.class, identifier, identifier);
        Long curriculumId = jdbcTemplate.queryForObject("""
                INSERT INTO curriculum (subject_id, name, model, year)
                VALUES (?, ?, 'LEGACY', 2018)
                RETURNING id
                """, Long.class, subjectId, identifier);
        return jdbcTemplate.queryForObject("""
                INSERT INTO curriculum_unit (curriculum_id, grade, unit_no, title)
                VALUES (?, 12, 1, ?)
                RETURNING id
                """, Long.class, curriculumId, identifier);
    }

    /** Yayındaki test sorusunu oluşturur. */
    private Long insertQuestion(Long unitId) {
        String identifier = UUID.randomUUID().toString();
        String hash = identifier.replace("-", "") + UUID.randomUUID().toString().replace("-", "");
        return jdbcTemplate.queryForObject("""
                INSERT INTO question (
                    curriculum_unit_id, origin, content, correct_option, content_hash, status
                ) VALUES (?, 'SOURCE', '{"stem":[],"options":[]}'::jsonb, 'B', ?, 'PUBLISHED')
                RETURNING id
                """, Long.class, unitId, hash);
    }

    /** Yayındaki test kaydını oluşturur. */
    private Long insertExam() {
        return jdbcTemplate.queryForObject("""
                INSERT INTO exam (title, status) VALUES (?, 'PUBLISHED') RETURNING id
                """, Long.class, "Test " + UUID.randomUUID());
    }

    /** Cevaplanmış sorunun ve oturumun kimliklerini taşır. */
    /** Cevaplanmış sorunun ve oturumun kimliklerini taşır. */
    record AnsweredQuestion(Long sessionId, Long questionId) {}
}
