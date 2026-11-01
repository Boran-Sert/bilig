package com.hataanalizi.core;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.context.annotation.Import;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.transaction.annotation.Transactional;

/** Bilgi, sohbet ve işletim tablolarının migration sözleşmesini doğrular. */
@ActiveProfiles("test")
@SpringBootTest
@Import(TestcontainersConfiguration.class)
@Transactional
class KnowledgeTutorReviewTablesIT {

    private final JdbcTemplate jdbcTemplate;

    /** Test veritabanı erişimini hazırlar. */
    @Autowired
    KnowledgeTutorReviewTablesIT(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    /** Tabloların ve dokümante edilen indekslerin oluştuğunu doğrular. */
    @Test
    void createsKnowledgeTutorAndReviewTables() {
        List<String> tables = jdbcTemplate.queryForList("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name IN (
                    'knowledge_node_alias', 'knowledge_edge', 'tutor_conversation',
                    'tutor_message', 'tutor_message_citation', 'review_item', 'content_report'
                  )
                ORDER BY table_name
                """, String.class);
        List<String> indexes = jdbcTemplate.queryForList("""
                SELECT indexname
                FROM pg_indexes
                WHERE schemaname = 'public'
                  AND indexname IN (
                    'idx_knowledge_node_alias_normalized_alias',
                    'uq_knowledge_edge_from_to_relation',
                    'idx_tutor_message_tutor_conversation_id',
                    'idx_review_item_status'
                  )
                """, String.class);

        assertEquals(
                List.of(
                        "content_report",
                        "knowledge_edge",
                        "knowledge_node_alias",
                        "review_item",
                        "tutor_conversation",
                        "tutor_message",
                        "tutor_message_citation"),
                tables);
        assertTrue(indexes.containsAll(List.of(
                "idx_knowledge_node_alias_normalized_alias",
                "uq_knowledge_edge_from_to_relation",
                "idx_tutor_message_tutor_conversation_id",
                "idx_review_item_status")));
    }

    /** Kolon adlarının ve PostgreSQL tiplerinin şemayla eşleştiğini doğrular. */
    @Test
    void createsDocumentedColumnsWithExpectedTypes() {
        List<String> columns = jdbcTemplate.queryForList("""
                SELECT format('%s.%s:%s', table_name, column_name, udt_name)
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name IN (
                    'knowledge_node_alias', 'knowledge_edge', 'tutor_conversation',
                    'tutor_message', 'tutor_message_citation', 'review_item', 'content_report'
                  )
                ORDER BY table_name, column_name
                """, String.class);

        assertEquals(
                List.of(
                        "content_report.created_at:timestamptz",
                        "content_report.id:int8",
                        "content_report.note:text",
                        "content_report.question_id:int8",
                        "content_report.status:text",
                        "content_report.tutor_message_id:int8",
                        "content_report.user_id:int8",
                        "knowledge_edge.created_at:timestamptz",
                        "knowledge_edge.evidence_content_block_id:int8",
                        "knowledge_edge.from_node_id:int8",
                        "knowledge_edge.id:int8",
                        "knowledge_edge.relation:text",
                        "knowledge_edge.status:text",
                        "knowledge_edge.to_node_id:int8",
                        "knowledge_node_alias.alias:text",
                        "knowledge_node_alias.knowledge_node_id:int8",
                        "knowledge_node_alias.normalized_alias:text",
                        "review_item.content_block_id:int8",
                        "review_item.created_at:timestamptz",
                        "review_item.decided_at:timestamptz",
                        "review_item.decided_by:int8",
                        "review_item.id:int8",
                        "review_item.knowledge_edge_id:int8",
                        "review_item.knowledge_node_id:int8",
                        "review_item.question_id:int8",
                        "review_item.reason:text",
                        "review_item.source_document_id:int8",
                        "review_item.status:text",
                        "tutor_conversation.created_at:timestamptz",
                        "tutor_conversation.id:int8",
                        "tutor_conversation.question_id:int8",
                        "tutor_conversation.user_id:int8",
                        "tutor_message.content:text",
                        "tutor_message.created_at:timestamptz",
                        "tutor_message.id:int8",
                        "tutor_message.role:text",
                        "tutor_message.tutor_conversation_id:int8",
                        "tutor_message_citation.content_block_id:int8",
                        "tutor_message_citation.tutor_message_id:int8"),
                columns);
    }

    /** Bir inceleme kaydında birden fazla hedef bulunmasının reddedildiğini doğrular. */
    @Test
    void rejectsReviewItemWithMultipleTargets() {
        Long firstNodeId = insertKnowledgeNode("AUTHOR", "Tarık Buğra");
        Long secondNodeId = insertKnowledgeNode("WORK", "Küçük Ağa");
        Long edgeId = insertKnowledgeEdge(firstNodeId, secondNodeId);

        assertThrows(DataIntegrityViolationException.class, () -> jdbcTemplate.update("""
                INSERT INTO review_item (reason, knowledge_node_id, knowledge_edge_id)
                VALUES ('NEW_LINK', ?, ?)
                """, firstNodeId, edgeId));
    }

    /** Bir bilgi düğümünün kendisine bağlanmasının reddedildiğini doğrular. */
    @Test
    void rejectsKnowledgeEdgeToSameNode() {
        Long nodeId = insertKnowledgeNode("CONCEPT", "Roman");

        assertThrows(DataIntegrityViolationException.class, () -> insertKnowledgeEdge(nodeId, nodeId));
    }

    /** Test bilgi düğümünü ekler ve kimliğini döndürür. */
    private Long insertKnowledgeNode(String nodeType, String name) {
        return jdbcTemplate.queryForObject("""
                INSERT INTO knowledge_node (node_type, name, search_text)
                VALUES (?, ?, ?)
                RETURNING id
                """, Long.class, nodeType, name, name);
    }

    /** Test bilgi bağını ekler ve kimliğini döndürür. */
    private Long insertKnowledgeEdge(Long fromNodeId, Long toNodeId) {
        return jdbcTemplate.queryForObject("""
                INSERT INTO knowledge_edge (from_node_id, to_node_id, relation)
                VALUES (?, ?, 'RELATED')
                RETURNING id
                """, Long.class, fromNodeId, toNodeId);
    }
}
