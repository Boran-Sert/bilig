package com.hataanalizi.core;

import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import org.springframework.jdbc.core.JdbcTemplate;

/** Uçtan uca öğrenci akışı için yayındaki testi, sorularını ve kazanımlarını oluşturur. */
class StudentFlowTestData {

    static final String UNIT_TITLE = "Roman";
    static final String EXAM_TITLE = "Roman · Kazanım Testi 3";
    static final String FAILING_OUTCOME_CODE = "A.2.15";
    static final String PASSING_OUTCOME_CODE = "A.2.3";
    static final String CORRECT_OPTION = "B";
    static final int QUESTION_COUNT = 4;

    private final JdbcTemplate jdbcTemplate;

    /** Test veritabanı bağlantısını saklar. */
    StudentFlowTestData(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    /** Yayındaki testin ve sıralı sorularının kimliklerini taşır. */
    record FlowExam(Long examId, List<Long> questionIds) {}

    /** İlk üç sorusu bir kazanıma, son sorusu başka kazanıma bağlı yayında bir test oluşturur. */
    FlowExam createPublishedExam() {
        String identifier = UUID.randomUUID().toString();
        Long unitId = jdbcTemplate.queryForObject("""
                WITH new_subject AS (INSERT INTO subject (code, name) VALUES (?, ?) RETURNING id),
                new_curriculum AS (
                    INSERT INTO curriculum (subject_id, name, model, year)
                    SELECT id, ?, 'LEGACY', 2018 FROM new_subject
                    RETURNING id)
                INSERT INTO curriculum_unit (curriculum_id, grade, unit_no, title)
                SELECT id, 12, 1, ? FROM new_curriculum
                RETURNING id
                """, Long.class, identifier, identifier, identifier, UNIT_TITLE);
        Long failingOutcomeId = insertOutcome(unitId, FAILING_OUTCOME_CODE);
        Long passingOutcomeId = insertOutcome(unitId, PASSING_OUTCOME_CODE);
        Long examId = jdbcTemplate.queryForObject(
                "INSERT INTO exam (curriculum_unit_id, title, status) VALUES (?, ?, 'PUBLISHED') RETURNING id",
                Long.class,
                unitId,
                EXAM_TITLE);
        List<Long> questionIds = new ArrayList<>();
        for (int position = 1; position <= QUESTION_COUNT; position++) {
            Long questionId = insertQuestion(unitId, examId, position);
            Long outcomeId = position < QUESTION_COUNT ? failingOutcomeId : passingOutcomeId;
            jdbcTemplate.update(
                    "INSERT INTO question_outcome (question_id, learning_outcome_id, mapped_by) VALUES (?, ?, 'SOURCE')",
                    questionId,
                    outcomeId);
            questionIds.add(questionId);
        }
        return new FlowExam(examId, questionIds);
    }

    /** Ünitenin programında verilen kodla bir kazanım oluşturur. */
    private Long insertOutcome(Long unitId, String code) {
        String identifier = UUID.randomUUID().toString();
        return jdbcTemplate.queryForObject(
                """
                WITH new_group AS (
                    INSERT INTO learning_outcome_group (curriculum_id, code, name)
                    SELECT curriculum_id, ?, ? FROM curriculum_unit WHERE id = ?
                    RETURNING id)
                INSERT INTO learning_outcome (learning_outcome_group_id, code, title, search_text)
                SELECT id, ?, ?, ? FROM new_group
                RETURNING id
                """, Long.class, identifier, identifier, unitId, code, "Outcome " + code, "Outcome " + code);
    }

    /** Gizli cevap alanları da taşıyan bir soruyu testin verilen sırasına ekler. */
    private Long insertQuestion(Long unitId, Long examId, int position) {
        String content = """
                {"stem":[{"type":"paragraph","md":"Soru %d"}],
                 "options":[{"label":"A","blocks":[{"type":"paragraph","md":"Option A"}]},
                            {"label":"B","isCorrect":true,"blocks":[{"type":"paragraph","md":"Option B"}]}],
                 "correctOption":"B"}
                """.formatted(position);
        String contentHash = UUID.randomUUID().toString().replace("-", "")
                + UUID.randomUUID().toString().replace("-", "");
        Long questionId = jdbcTemplate.queryForObject("""
                INSERT INTO question (curriculum_unit_id, origin, content, correct_option, content_hash, status)
                VALUES (?, 'SOURCE', ?::jsonb, ?, ?, 'PUBLISHED')
                RETURNING id
                """, Long.class, unitId, content, CORRECT_OPTION, contentHash);
        jdbcTemplate.update(
                "INSERT INTO exam_question (exam_id, question_id, position) VALUES (?, ?, ?)",
                examId,
                questionId,
                position);
        return questionId;
    }
}
