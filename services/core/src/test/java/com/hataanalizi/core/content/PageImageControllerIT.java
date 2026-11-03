package com.hataanalizi.core.content;

import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.testSecurityContext;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.hataanalizi.core.TestcontainersConfiguration;
import com.hataanalizi.core.auth.WithAuthUser;
import com.hataanalizi.core.storage.FileStorage;
import java.io.ByteArrayInputStream;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.transaction.annotation.Transactional;

/** Sayfa görüntüsü uç noktasının erişim ve bayt sözleşmesini doğrular. */
@ActiveProfiles("test")
@SpringBootTest
@AutoConfigureMockMvc
@Import(TestcontainersConfiguration.class)
@Transactional
class PageImageControllerIT {

    private final JdbcTemplate jdbcTemplate;
    private final MockMvc mockMvc;

    @MockitoBean
    private FileStorage fileStorage;

    /** Veritabanı ve HTTP test bağımlılıklarını saklar. */
    @Autowired
    PageImageControllerIT(JdbcTemplate jdbcTemplate, MockMvc mockMvc) {
        this.jdbcTemplate = jdbcTemplate;
        this.mockMvc = mockMvc;
    }

    /** Her test için kaynak yükleyen kullanıcıyı ekler. */
    @BeforeEach
    void createUploader() {
        jdbcTemplate.update("""
                INSERT INTO app_user (id, tenant_id, display_name) OVERRIDING SYSTEM VALUE
                SELECT 1001, id, 'Page image controller test'
                FROM tenant
                ORDER BY id
                LIMIT 1
                """);
    }

    /** Sayfa görüntüsünü PNG türünde özgün baytlarıyla döndürür. */
    @Test
    @WithAuthUser(id = 1001)
    void returnsPngImageBytesWithoutPublicationCheck() throws Exception {
        long pageId = createSourcePage("pages/book-174.png");
        createBlock(pageId, "DRAFT");
        byte[] imageBytes = new byte[] {0, 1, 2, 3, -1};
        when(fileStorage.open("pages/book-174.png")).thenReturn(new ByteArrayInputStream(imageBytes));

        mockMvc.perform(get("/api/pages/{id}/image", pageId).with(testSecurityContext()))
                .andExpect(status().isOk())
                .andExpect(content().contentType(MediaType.IMAGE_PNG))
                .andExpect(content().bytes(imageBytes));

        verify(fileStorage).open("pages/book-174.png");
    }

    /** Boş görüntü yolu olan sayfayı 404 ile reddeder. */
    @Test
    @WithAuthUser(id = 1001)
    void pageWithoutImageReturnsNotFound() throws Exception {
        long pageId = createSourcePage(null);

        mockMvc.perform(get("/api/pages/{id}/image", pageId).with(testSecurityContext()))
                .andExpect(status().isNotFound());

        verify(fileStorage, never()).open(org.mockito.ArgumentMatchers.anyString());
    }

    /** Olmayan sayfa ve kimliksiz görüntü isteğini uygun durumlarla reddeder. */
    @Test
    @WithAuthUser(id = 1001)
    void missingPageReturnsNotFound() throws Exception {
        mockMvc.perform(get("/api/pages/999999999/image").with(testSecurityContext()))
                .andExpect(status().isNotFound());
    }

    /** Kimliksiz görüntü isteğini 401 ile reddeder. */
    @Test
    void unauthenticatedRequestReturnsUnauthorized() throws Exception {
        mockMvc.perform(get("/api/pages/1/image")).andExpect(status().isUnauthorized());
    }

    /** Test kaynağına görüntü yolu belirtilen sayfayı ekler. */
    private long createSourcePage(String imagePath) {
        String uniqueValue = UUID.randomUUID().toString().replace("-", "");
        Long sourceId = jdbcTemplate.queryForObject("""
                INSERT INTO source_document (title, sha256, file_path, uploaded_by)
                VALUES ('TDE 12 Ders Kitabı', ?, 'sources/book.pdf', 1001)
                RETURNING id
                """, Long.class, uniqueValue + uniqueValue);
        return jdbcTemplate.queryForObject("""
                INSERT INTO source_page (source_document_id, page_no, image_path)
                VALUES (?, 174, ?)
                RETURNING id
                """, Long.class, sourceId, imagePath);
    }

    /** Test sayfasına taslak paragraf ekler. */
    private void createBlock(long pageId, String status) {
        jdbcTemplate.update("""
                INSERT INTO content_block (
                    source_page_id, block_type, position, title_path, markdown, status, search_text
                )
                VALUES (?, 'ALINTI', 1, 'Roman', 'Taslak paragraf.', ?, 'Taslak paragraf.')
                """, pageId, status);
    }
}
