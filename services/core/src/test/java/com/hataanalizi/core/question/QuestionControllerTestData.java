package com.hataanalizi.core.question;

import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import org.springframework.jdbc.core.JdbcTemplate;

/** Benzer soru entegrasyon testleri için soru, kazanım ve cevap kayıtları oluşturur. */
class QuestionControllerTestData {

    private static final int EMBEDDING_DIMENSIONS = 1024;

    private final JdbcTemplate jdbcTemplate;

    /** Test veritabanı bağlantısını saklar. */
    QuestionControllerTestData(JdbcTemplate jdbcTemplate) {
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

    /** Yeni bir programda verilen sayıda kazanım oluşturur. */
    List<Long> insertOutcomes(int count) {
        String identifier = UUID.randomUUID().toString();
        Long groupId = jdbcTemplate.queryForObject(
                """
                WITH new_subject AS (INSERT INTO subject (code, name) VALUES (?, ?) RETURNING id),
                new_curriculum AS (
                    INSERT INTO curriculum (subject_id, name, model, year)
                    SELECT id, ?, 'LEGACY', 2018 FROM new_subject
                    RETURNING id)
                INSERT INTO learning_outcome_group (curriculum_id, code, name)
                SELECT id, ?, ? FROM new_curriculum
                RETURNING id
                """, Long.class, identifier, identifier, identifier, identifier, identifier);
        List<Long> outcomeIds = new ArrayList<>();
        for (int index = 1; index <= count; index++) {
            outcomeIds.add(jdbcTemplate.queryForObject(
                    """
                    INSERT INTO learning_outcome (learning_outcome_group_id, code, title, search_text)
                    VALUES (?, ?, ?, ?)
                    RETURNING id
                    """, Long.class, groupId, "A.2." + index, "Outcome " + index, "Outcome " + index));
        }
        return outcomeIds;
    }

    /** Verilen durum, vektör ve kazanımlarla soru ekler; vektör boşsa kolon boş kalır. */
    Long insertQuestion(String status, String embedding, List<Long> outcomeIds) {
        String content = """
                {"stem":[{"type":"paragraph","md":"Benzer soru"}],
                 "options":[{"label":"A","isCorrect":true,"blocks":[{"type":"paragraph","md":"Option A"}]},
                            {"label":"B","blocks":[{"type":"paragraph","md":"Option B"}]}],
                 "correctOption":"A"}
                """;
        String contentHash = UUID.randomUUID().toString().replace("-", "")
                + UUID.randomUUID().toString().replace("-", "");
        Long questionId = jdbcTemplate.queryForObject("""
                INSERT INTO question (origin, content, correct_option, content_hash, status, embedding)
                VALUES ('SOURCE', ?::jsonb, 'A', ?, ?, ?::vector)
                RETURNING id
                """, Long.class, content, contentHash, status, embedding);
        outcomeIds.forEach(outcomeId -> jdbcTemplate.update(
                "INSERT INTO question_outcome (question_id, learning_outcome_id, mapped_by) VALUES (?, ?, 'SOURCE')",
                questionId,
                outcomeId));
        return questionId;
    }

    /** Öğrencinin testsiz bir oturumda soruyu cevapladığını kaydeder. */
    void insertAnswer(Long userId, Long questionId) {
        Long sessionId = jdbcTemplate.queryForObject(
                "INSERT INTO study_session (user_id, status) VALUES (?, 'COMPLETED') RETURNING id", Long.class, userId);
        jdbcTemplate.update("""
                INSERT INTO student_answer (study_session_id, question_id, selected_option, is_correct)
                VALUES (?, ?, 'B', false)
                """, sessionId, questionId);
    }

    /** İlk iki boyutu verilen, kalanı sıfır olan vektörü pgvector metni olarak oluşturur. */
    static String vector(float first, float second) {
        return "[" + first + "," + second + ",0".repeat(EMBEDDING_DIMENSIONS - 2) + "]";
    }
}
