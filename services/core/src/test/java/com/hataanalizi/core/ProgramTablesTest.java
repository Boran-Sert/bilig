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

/** Program tablolarının migration ile kurulduğunu doğrular. */
@ActiveProfiles("test")
@SpringBootTest
@Import(TestcontainersConfiguration.class)
@Transactional
class ProgramTablesTest {

    private final JdbcTemplate jdbcTemplate;

    /** Test veritabanı erişimini hazırlar. */
    @Autowired
    ProgramTablesTest(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    /** Program tablolarının ve kazanım arama indekslerinin oluştuğunu doğrular. */
    @Test
    void createsProgramTablesAndOutcomeIndexes() {
        List<String> tables = jdbcTemplate.queryForList("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name IN (
                    'subject', 'curriculum', 'learning_outcome_group',
                    'learning_outcome', 'curriculum_unit', 'curriculum_unit_outcome'
                  )
                ORDER BY table_name
                """, String.class);
        List<String> indexes = jdbcTemplate.queryForList("""
                SELECT indexname
                FROM pg_indexes
                WHERE schemaname = 'public'
                  AND indexname IN ('idx_learning_outcome_embedding', 'idx_learning_outcome_bm25')
                """, String.class);

        assertEquals(
                List.of(
                        "curriculum",
                        "curriculum_unit",
                        "curriculum_unit_outcome",
                        "learning_outcome",
                        "learning_outcome_group",
                        "subject"),
                tables);
        assertTrue(indexes.containsAll(List.of("idx_learning_outcome_embedding", "idx_learning_outcome_bm25")));
    }

    /** Aynı grupta aynı kodla ikinci kazanım eklenmesini engeller. */
    @Test
    void rejectsDuplicateOutcomeCodeInGroup() {
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

        insertOutcome(groupId, identifier);
        assertThrows(DataIntegrityViolationException.class, () -> insertOutcome(groupId, identifier));
    }

    /** Kazanım kaydını ekler. */
    private void insertOutcome(Long groupId, String code) {
        jdbcTemplate.update("""
                INSERT INTO learning_outcome (
                    learning_outcome_group_id, code, title, search_text
                ) VALUES (?, ?, ?, ?)
                """, groupId, code, code, code);
    }
}
