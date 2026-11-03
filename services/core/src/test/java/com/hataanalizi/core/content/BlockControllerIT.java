package com.hataanalizi.core.content;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.testSecurityContext;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.hataanalizi.core.TestcontainersConfiguration;
import com.hataanalizi.core.auth.WithAuthUser;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.transaction.annotation.Transactional;

/** Alıntı paragrafı uç noktasının HTTP sözleşmesini PostgreSQL ile doğrular. */
@ActiveProfiles("test")
@SpringBootTest
@AutoConfigureMockMvc
@Import(TestcontainersConfiguration.class)
@Transactional
class BlockControllerIT {

    private final JdbcTemplate jdbcTemplate;
    private final MockMvc mockMvc;

    /** Veritabanı ve HTTP test bağımlılıklarını saklar. */
    @Autowired
    BlockControllerIT(JdbcTemplate jdbcTemplate, MockMvc mockMvc) {
        this.jdbcTemplate = jdbcTemplate;
        this.mockMvc = mockMvc;
    }

    /** Her test için kaynak yükleyen kullanıcıyı ekler. */
    @BeforeEach
    void createUploader() {
        jdbcTemplate.update("""
                INSERT INTO app_user (id, tenant_id, display_name) OVERRIDING SYSTEM VALUE
                SELECT 1001, id, 'Block controller test'
                FROM tenant
                ORDER BY id
                LIMIT 1
                """);
    }

    /** Yayındaki paragrafı sözleşmedeki kaynak alanlarıyla döndürür. */
    @Test
    @WithAuthUser(id = 1001)
    void returnsPublishedBlockDetails() throws Exception {
        long pageId = createSourcePage();
        long blockId = createBlock(pageId, "PUBLISHED");

        mockMvc.perform(get("/api/blocks/{id}", blockId).with(testSecurityContext()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(5))
                .andExpect(jsonPath("$.id").value(blockId))
                .andExpect(jsonPath("$.markdown").value("Özgün paragraf."))
                .andExpect(jsonPath("$.sourceTitle").value("TDE 12 Ders Kitabı"))
                .andExpect(jsonPath("$.pageNo").value(174))
                .andExpect(jsonPath("$.pageId").value(pageId));
    }

    /** Taslak paragrafı 404 ile gizler. */
    @Test
    @WithAuthUser(id = 1001)
    void unpublishedBlockReturnsNotFound() throws Exception {
        long blockId = createBlock(createSourcePage(), "DRAFT");

        mockMvc.perform(get("/api/blocks/{id}", blockId).with(testSecurityContext()))
                .andExpect(status().isNotFound());
    }

    /** Kimliksiz blok isteğini 401 ile reddeder. */
    @Test
    void unauthenticatedRequestReturnsUnauthorized() throws Exception {
        mockMvc.perform(get("/api/blocks/1")).andExpect(status().isUnauthorized());
    }

    /** Test kaynağını ve 174. sayfasını oluşturur. */
    private long createSourcePage() {
        String uniqueValue = UUID.randomUUID().toString().replace("-", "");
        Long sourceId = jdbcTemplate.queryForObject("""
                INSERT INTO source_document (title, sha256, file_path, uploaded_by)
                VALUES ('TDE 12 Ders Kitabı', ?, 'sources/book.pdf', 1001)
                RETURNING id
                """, Long.class, uniqueValue + uniqueValue);
        return jdbcTemplate.queryForObject("""
                INSERT INTO source_page (source_document_id, page_no)
                VALUES (?, 174)
                RETURNING id
                """, Long.class, sourceId);
    }

    /** Sayfaya bağlı paragrafı verilen yayın durumuyla oluşturur. */
    private long createBlock(long pageId, String status) {
        return jdbcTemplate.queryForObject("""
                INSERT INTO content_block (
                    source_page_id, block_type, position, title_path, markdown, status, search_text
                )
                VALUES (?, 'ALINTI', 1, 'Roman', 'Özgün paragraf.', ?, 'Özgün paragraf.')
                RETURNING id
                """, Long.class, pageId, status);
    }
}
