package com.hataanalizi.core;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
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

/** İçerik, soru, kazanım ve test tablolarının migration sözleşmesini doğrular. */
@ActiveProfiles("test")
@SpringBootTest
@Import(TestcontainersConfiguration.class)
@Transactional
class ContentTablesIT {

    private final JdbcTemplate jdbcTemplate;

    /** Test veritabanı erişimini hazırlar. */
    @Autowired
    ContentTablesIT(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    /** İçerik tablolarının ve arama indekslerinin oluştuğunu doğrular. */
    @Test
    void createsContentTablesAndSearchIndexes() {
        List<String> tables = jdbcTemplate.queryForList("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name IN (
                    'content_block', 'content_block_outcome', 'question',
                    'question_outcome', 'exam', 'exam_question'
                  )
                ORDER BY table_name
                """, String.class);
        List<String> indexes = jdbcTemplate.queryForList("""
                SELECT indexname
                FROM pg_indexes
                WHERE schemaname = 'public'
                  AND indexname IN (
                    'idx_content_block_embedding', 'idx_content_block_bm25',
                    'idx_content_block_outcome_learning_outcome_id',
                    'idx_question_curriculum_unit_id_status', 'idx_question_embedding',
                    'idx_question_outcome_learning_outcome_id',
                    'uq_exam_question_exam_id_position'
                  )
                """, String.class);

        assertEquals(
                List.of(
                        "content_block",
                        "content_block_outcome",
                        "exam",
                        "exam_question",
                        "question",
                        "question_outcome"),
                tables);
        assertTrue(indexes.containsAll(List.of(
                "idx_content_block_embedding",
                "idx_content_block_bm25",
                "idx_content_block_outcome_learning_outcome_id",
                "idx_question_curriculum_unit_id_status",
                "idx_question_embedding",
                "idx_question_outcome_learning_outcome_id",
                "uq_exam_question_exam_id_position")));
    }

    /** Aynı içerik özetine sahip ikinci sorunun reddedildiğini doğrular. */
    @Test
    void rejectsDuplicateQuestionContentHash() {
        TestCurriculum curriculum = insertCurriculum();
        String hash = createHash();
        insertQuestion(curriculum.curriculumUnitId(), hash);

        assertThrows(DataIntegrityViolationException.class, () -> insertQuestion(curriculum.curriculumUnitId(), hash));
    }

    /** Bir soruya birden çok kazanım bağlanabildiğini ve sıralama alanı olmadığını doğrular. */
    @Test
    void allowsMultipleQuestionOutcomesWithoutOrderingOrWeightColumns() {
        TestCurriculum curriculum = insertCurriculum();
        Long questionId = insertQuestion(curriculum.curriculumUnitId(), createHash());
        Long firstOutcomeId = insertOutcome(curriculum.outcomeGroupId(), "first");
        Long secondOutcomeId = insertOutcome(curriculum.outcomeGroupId(), "second");

        insertQuestionOutcome(questionId, firstOutcomeId);
        insertQuestionOutcome(questionId, secondOutcomeId);

        Integer outcomeCount = jdbcTemplate.queryForObject(
                "SELECT count(*) FROM question_outcome WHERE question_id = ?", Integer.class, questionId);
        List<String> columns = jdbcTemplate.queryForList("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'question_outcome'
                """, String.class);

        assertEquals(2, outcomeCount);
        assertFalse(columns.contains("position"));
        assertFalse(columns.contains("weight"));
    }

    /** Test için ders programı ve ünite oluşturur. */
    private TestCurriculum insertCurriculum() {
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
        Long groupId = jdbcTemplate.queryForObject(
                "INSERT INTO learning_outcome_group (curriculum_id, code, name) VALUES (?, ?, ?) RETURNING id",
                Long.class,
                curriculumId,
                identifier,
                identifier);
        Long unitId = jdbcTemplate.queryForObject(
                "INSERT INTO curriculum_unit (curriculum_id, grade, unit_no, title) VALUES (?, ?, ?, ?) RETURNING id",
                Long.class,
                curriculumId,
                12,
                1,
                identifier);
        return new TestCurriculum(unitId, groupId);
    }

    /** Test sorusunu ekler ve kimliğini döndürür. */
    private Long insertQuestion(Long curriculumUnitId, String contentHash) {
        return jdbcTemplate.queryForObject("""
                INSERT INTO question (
                    curriculum_unit_id, origin, content, correct_option, content_hash
                ) VALUES (?, 'SOURCE', '{}'::jsonb, 'A', ?)
                RETURNING id
                """, Long.class, curriculumUnitId, contentHash);
    }

    /** Test kazanımını ekler ve kimliğini döndürür. */
    private Long insertOutcome(Long groupId, String suffix) {
        return jdbcTemplate.queryForObject("""
                INSERT INTO learning_outcome (learning_outcome_group_id, code, title, search_text)
                VALUES (?, ?, ?, ?)
                RETURNING id
                """, Long.class, groupId, suffix, suffix, suffix);
    }

    /** Soruyu belirtilen kazanıma bağlar. */
    private void insertQuestionOutcome(Long questionId, Long learningOutcomeId) {
        jdbcTemplate.update("""
                INSERT INTO question_outcome (question_id, learning_outcome_id, mapped_by)
                VALUES (?, ?, 'SOURCE')
                """, questionId, learningOutcomeId);
    }

    /** Benzersiz bir 64 karakterlik SHA-256 değeri üretir. */
    private String createHash() {
        return UUID.randomUUID().toString().replace("-", "")
                + UUID.randomUUID().toString().replace("-", "");
    }

    /** Test programının ünite ve kazanım grubu kimliklerini taşır. */
    private record TestCurriculum(Long curriculumUnitId, Long outcomeGroupId) {}
}
