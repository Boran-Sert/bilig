package com.hataanalizi.core.session;

import java.util.UUID;
import org.springframework.jdbc.core.JdbcTemplate;

/** Oturum API testi için soru verisi oluşturur. */
class SessionQuestionFixture {

    private final JdbcTemplate jdbcTemplate;

    /** Test veritabanı bağlantısını saklar. */
    SessionQuestionFixture(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    /** Gizli yanıt alanları içeren bir soru oluşturur. */
    Long insertQuestion(Long unitId) {
        String content = """
                {"stem":[{"type":"paragraph","md":"Question"}],
                 "options":[
                   {"label":"A","isCorrect":true,
                    "blocks":[{"type":"paragraph","md":"Option A"}]},
                   {"label":"B","blocks":[{"type":"paragraph","md":"Option B"}]},
                   {"label":"C","blocks":[{"type":"paragraph","md":"Option C"}]},
                   {"label":"D","blocks":[{"type":"paragraph","md":"Option D"}]},
                   {"label":"E","blocks":[{"type":"paragraph","md":"Option E"}]}
                 ],
                 "correctOption":"B","explanation":"Private answer explanation"}
                """;
        String contentHash = UUID.randomUUID().toString().replace("-", "")
                + UUID.randomUUID().toString().replace("-", "");
        return jdbcTemplate.queryForObject("""
                INSERT INTO question (
                    curriculum_unit_id, origin, content, correct_option, content_hash, status
                ) VALUES (?, 'SOURCE', ?::jsonb, 'B', ?, 'PUBLISHED')
                RETURNING id
                """, Long.class, unitId, content, contentHash);
    }
}
