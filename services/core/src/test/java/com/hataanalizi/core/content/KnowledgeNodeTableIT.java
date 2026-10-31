package com.hataanalizi.core.content;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.hataanalizi.core.TestcontainersConfiguration;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.context.annotation.Import;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.transaction.annotation.Transactional;

/** Bilgi düğümü tablosunun migration sözleşmesini doğrular. */
@ActiveProfiles("test")
@SpringBootTest
@Import(TestcontainersConfiguration.class)
@Transactional
class KnowledgeNodeTableIT {

    private final JdbcTemplate jdbcTemplate;

    /** Test veritabanı erişimini hazırlar. */
    @Autowired
    KnowledgeNodeTableIT(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    /** Tablonun, tekillik kısıtının ve kelime arama indeksinin oluştuğunu doğrular. */
    @Test
    void createsKnowledgeNodeTableAndSearchIndex() {
        List<String> indexes = jdbcTemplate.queryForList("""
                SELECT indexname
                FROM pg_indexes
                WHERE schemaname = 'public' AND tablename = 'knowledge_node'
                """, String.class);

        assertTrue(indexes.containsAll(List.of("uq_knowledge_node_node_type_name", "idx_knowledge_node_bm25")));
    }

    /** Yeni düğümün taslak olarak başladığını doğrular. */
    @Test
    void startsNodeAsDraft() {
        Long nodeId = insertNode("AUTHOR", "Tarık Buğra");

        String status =
                jdbcTemplate.queryForObject("SELECT status FROM knowledge_node WHERE id = ?", String.class, nodeId);

        assertEquals("DRAFT", status);
    }

    /** Aynı tür ve adla ikinci düğümün reddedildiğini doğrular. */
    @Test
    void rejectsDuplicateNodeTypeAndName() {
        insertNode("WORK", "Küçük Ağa");

        assertThrows(DataIntegrityViolationException.class, () -> insertNode("WORK", "Küçük Ağa"));
    }

    /** Tanımlı olmayan düğüm türünün reddedildiğini doğrular. */
    @Test
    void rejectsUnknownNodeType() {
        assertThrows(DataIntegrityViolationException.class, () -> insertNode("CHARACTER", "Kara Davut"));
    }

    /** Test düğümünü ekler ve kimliğini döndürür. */
    private Long insertNode(String nodeType, String name) {
        return jdbcTemplate.queryForObject("""
                INSERT INTO knowledge_node (node_type, name, search_text)
                VALUES (?, ?, ?)
                RETURNING id
                """, Long.class, nodeType, name, name);
    }
}
