package com.hataanalizi.core.admin;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.testSecurityContext;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.multipart;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.hataanalizi.core.TestcontainersConfiguration;
import com.hataanalizi.core.auth.WithAuthUser;
import jakarta.persistence.EntityManager;
import jakarta.servlet.http.Cookie;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;
import org.springframework.test.web.servlet.ResultActions;
import org.springframework.test.web.servlet.request.MockMultipartHttpServletRequestBuilder;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.unit.DataSize;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

/** Kaynak yükleme ucunun HTTP, veritabanı, dosya ve iş kuyruğu davranışını sınar. */
@ActiveProfiles("test")
@SpringBootTest
@AutoConfigureMockMvc
@Import(TestcontainersConfiguration.class)
@TestPropertySource(properties = "app.job-queue=postgres")
@Transactional
class SourceControllerITTest {

    @TempDir
    private static Path storageDirectory;

    private final MockMvc mockMvc;
    private final JdbcTemplate jdbcTemplate;
    private final ObjectMapper objectMapper;
    private final EntityManager entityManager;

    /** HTTP, veritabanı ve JSON test bileşenlerini saklar. */
    @Autowired
    SourceControllerITTest(
            MockMvc mockMvc, JdbcTemplate jdbcTemplate, ObjectMapper objectMapper, EntityManager entityManager) {
        this.mockMvc = mockMvc;
        this.jdbcTemplate = jdbcTemplate;
        this.objectMapper = objectMapper;
        this.entityManager = entityManager;
    }

    /** Testte kullanılan sabit kimlik için yükleyen kullanıcıyı ekler. */
    @BeforeEach
    void createUploader() {
        jdbcTemplate.update("""
                INSERT INTO app_user (id, tenant_id, display_name) OVERRIDING SYSTEM VALUE
                SELECT 1001, id, 'Source upload test user'
                FROM tenant
                ORDER BY id
                LIMIT 1
                """);
    }

    /** Yerel depolama kökünü ve PostgreSQL iş kuyruğunu test bağlamına bağlar. */
    @DynamicPropertySource
    static void storageProperties(DynamicPropertyRegistry registry) {
        registry.add("STORAGE_TYPE", () -> "local");
        registry.add("STORAGE_DIR", () -> storageDirectory.toString());
    }

    /**
     * PDF yüklemesinin kaynak satırı, dosyası ve iş oluşturduğunu doğrular.
     */
    @Test
    @WithAuthUser(role = "CONTENT_ADMIN", id = 1001)
    void uploadsPdfAndCreatesSourceFileAndJob() throws Exception {
        MockMultipartFile file = pdfFile("tde12-ders-kitabi.pdf", "tiny.pdf");

        MvcResult result = uploadAsAdmin(file)
                .andExpect(status().isAccepted())
                .andExpect(jsonPath("$.files[0].fileName").value("tde12-ders-kitabi.pdf"))
                .andExpect(jsonPath("$.files[0].duplicate").value(false))
                .andReturn();
        long sourceId = sourceIdFrom(result);
        entityManager.flush();

        assertThat(jdbcTemplate.queryForObject(
                        "SELECT file_path FROM source_document WHERE id = ?", String.class, sourceId))
                .isEqualTo("sources/" + sourceId + ".pdf");
        assertThat(jdbcTemplate.queryForObject("SELECT kind FROM source_document WHERE id = ?", String.class, sourceId))
                .isEqualTo("UNKNOWN");
        assertThat(jdbcTemplate.queryForObject(
                        "SELECT status FROM source_document WHERE id = ?", String.class, sourceId))
                .isEqualTo("UPLOADED");
        assertThat(jdbcTemplate.queryForObject(
                        "SELECT uploaded_by FROM source_document WHERE id = ?", Long.class, sourceId))
                .isEqualTo(1001L);
        assertThat(Files.readAllBytes(storageDirectory.resolve("sources").resolve(sourceId + ".pdf")))
                .containsExactly(fixtureBytes("tiny.pdf"));
        String jobQuery = """
                SELECT count(*) FROM background_job
                WHERE job_type = 'INGEST_SOURCE' AND payload->>'sourceId' = ?
                """;
        assertThat(jdbcTemplate.queryForObject(jobQuery, Long.class, Long.toString(sourceId)))
                .isEqualTo(1L);
    }

    /** Yüklenen kaynağın ilk adımını ve sayfalama sözleşmesini doğrular. */
    @Test
    @WithAuthUser(role = "CONTENT_ADMIN", id = 1001)
    void listsNewSourceAtZeroProgress() throws Exception {
        uploadAsAdmin(pdfFile("tde12-ders-kitabi.pdf", "tiny.pdf")).andExpect(status().isAccepted());

        mockMvc.perform(get("/api/admin/sources").with(testSecurityContext()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.items[0].fileName").value("tde12-ders-kitabi.pdf"))
                .andExpect(jsonPath("$.items[0].status").value("UPLOADED"))
                .andExpect(jsonPath("$.items[0].lastCompletedStep").doesNotExist())
                .andExpect(jsonPath("$.items[0].stepIndex").value(0))
                .andExpect(jsonPath("$.items[0].totalSteps").value(6))
                .andExpect(jsonPath("$.page").value(0))
                .andExpect(jsonPath("$.size").value(20))
                .andExpect(jsonPath("$.total").value(1));
    }

    /** Kaydedilmiş iş adımını ve hata metnini kaynak listesine taşır. */
    @Test
    @WithAuthUser(role = "CONTENT_ADMIN", id = 1001)
    void listsLatestCompletedStepAndJobError() throws Exception {
        MvcResult upload = uploadAsAdmin(pdfFile("tde12-ders-kitabi.pdf", "tiny.pdf"))
                .andExpect(status().isAccepted())
                .andReturn();
        long sourceId = sourceIdFrom(upload);
        assertThat(jdbcTemplate.update("""
                UPDATE background_job
                SET last_completed_step = 'EXTRACT', last_error = 'validation failed'
                WHERE job_type = 'INGEST_SOURCE' AND payload->>'sourceId' = ?
                """, Long.toString(sourceId))).isEqualTo(1);
        entityManager.clear();

        mockMvc.perform(get("/api/admin/sources?page=0&size=20").with(testSecurityContext()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.items[0].lastCompletedStep").value("EXTRACT"))
                .andExpect(jsonPath("$.items[0].stepIndex").value(2))
                .andExpect(jsonPath("$.items[0].totalSteps").value(6))
                .andExpect(jsonPath("$.items[0].error").value("validation failed"));
    }

    /** Adım sırasının Python sözleşmesiyle aynı olduğunu doğrular. */
    @Test
    void definesIngestStepsInPythonOrder() {
        assertThat(IngestStep.values())
                .containsExactly(
                        IngestStep.REGISTERED,
                        IngestStep.EXTRACT,
                        IngestStep.VALIDATE,
                        IngestStep.ENTITIES,
                        IngestStep.OUTCOMES,
                        IngestStep.INDEX);
    }

    /** Kaynak listesinin boyut ve toplam kayıt sayısına göre sayfalandığını doğrular. */
    @Test
    @WithAuthUser(role = "CONTENT_ADMIN", id = 1001)
    void paginatesSourceList() throws Exception {
        uploadAsAdmin(pdfFile("ilk.pdf", "tiny.pdf"));
        uploadAsAdmin(new MockMultipartFile(
                "files",
                "ikinci.pdf",
                "application/pdf",
                "%PDF-1.4 second test PDF".getBytes(StandardCharsets.US_ASCII)));

        mockMvc.perform(get("/api/admin/sources?page=0&size=1").with(testSecurityContext()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.items.length()").value(1))
                .andExpect(jsonPath("$.page").value(0))
                .andExpect(jsonPath("$.size").value(1))
                .andExpect(jsonPath("$.total").value(2));
    }

    /**
     * Yinelenen içerikte eski kimliği döndürüp yeni kayıt ve iş açmadığını doğrular.
     */
    @Test
    @WithAuthUser(role = "CONTENT_ADMIN", id = 1001)
    void returnsExistingSourceForDuplicateUpload() throws Exception {
        MvcResult first = uploadAsAdmin(pdfFile("ilk.pdf", "tiny.pdf"))
                .andExpect(status().isAccepted())
                .andReturn();
        long sourceId = sourceIdFrom(first);

        uploadAsAdmin(pdfFile("tekrar.pdf", "tiny.pdf"))
                .andExpect(status().isAccepted())
                .andExpect(jsonPath("$.files[0].sourceId").value(sourceId))
                .andExpect(jsonPath("$.files[0].fileName").value("tekrar.pdf"))
                .andExpect(jsonPath("$.files[0].duplicate").value(true));

        assertThat(jdbcTemplate.queryForObject("SELECT count(*) FROM source_document", Long.class))
                .isEqualTo(1L);
        assertThat(jdbcTemplate.queryForObject("SELECT count(*) FROM background_job", Long.class))
                .isEqualTo(1L);
    }

    /** PDF imzası olmayan dosyanın 400 döndürüp yan etki oluşturmamasını doğrular. */
    @Test
    @WithAuthUser(role = "CONTENT_ADMIN", id = 1001)
    void rejectsNonPdfWithoutCreatingRecords() throws Exception {
        long storedFilesBeforeRequest = storedFileCount();
        uploadAsAdmin(pdfFile("not-a-pdf.pdf", "not-a-pdf.pdf"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("FILE_NOT_PDF"));

        assertThat(jdbcTemplate.queryForObject("SELECT count(*) FROM source_document", Long.class))
                .isZero();
        assertThat(jdbcTemplate.queryForObject("SELECT count(*) FROM background_job", Long.class))
                .isZero();
        assertThat(storedFileCount()).isEqualTo(storedFilesBeforeRequest);
    }

    /** Dosya sınırını aşan yüklemenin 413 döndürüp kayıt açmamasını doğrular. */
    @Test
    @WithAuthUser(role = "CONTENT_ADMIN", id = 1001)
    void rejectsOversizedFileWithoutCreatingRecords() throws Exception {
        long storedFilesBeforeRequest = storedFileCount();
        MockMultipartFile file = oversizedFile();

        uploadAsAdmin(file)
                .andExpect(status().is(413))
                .andExpect(jsonPath("$.code").value("FILE_TOO_LARGE"));

        assertThat(jdbcTemplate.queryForObject("SELECT count(*) FROM source_document", Long.class))
                .isZero();
        assertThat(jdbcTemplate.queryForObject("SELECT count(*) FROM background_job", Long.class))
                .isZero();
        assertThat(storedFileCount()).isEqualTo(storedFilesBeforeRequest);
    }

    /** Girişsiz isteğin ortak kimlik doğrulama hatasıyla reddedildiğini doğrular. */
    @Test
    void requiresAuthenticationForUpload() throws Exception {
        mockMvc.perform(uploadRequest(pdfFile("dosya.pdf", "tiny.pdf")))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.code").value("AUTH_REQUIRED"));
    }

    /** Öğrencinin kaynak yükleme yetkisi olmadığını doğrular. */
    @Test
    @WithAuthUser(role = "STUDENT", id = 1001)
    void deniesStudentUpload() throws Exception {
        mockMvc.perform(uploadRequest(pdfFile("dosya.pdf", "tiny.pdf")).with(testSecurityContext()))
                .andExpect(status().isForbidden())
                .andExpect(jsonPath("$.code").value("ACCESS_DENIED"));
    }

    /** Yönetici rolüyle CSRF doğrulamasını geçen yükleme isteğini gönderir. */
    private ResultActions uploadAsAdmin(MockMultipartFile file) throws Exception {
        return mockMvc.perform(uploadRequest(file).with(testSecurityContext()));
    }

    /** Dosyaları CSRF çerezi ve başlığı bulunan çok parçalı isteğe ekler. */
    private MockMultipartHttpServletRequestBuilder uploadRequest(MockMultipartFile... files) {
        String csrfToken = UUID.randomUUID().toString();
        MockMultipartHttpServletRequestBuilder request = multipart("/api/admin/sources");
        for (MockMultipartFile file : files) {
            request.file(file);
        }
        return request.cookie(new Cookie("XSRF-TOKEN", csrfToken)).header("X-XSRF-TOKEN", csrfToken);
    }

    /** Yükleme yanıtındaki ilk kaynak kimliğini okur. */
    private long sourceIdFrom(MvcResult result) throws Exception {
        JsonNode response = objectMapper.readTree(result.getResponse().getContentAsString());
        return response.path("files").get(0).path("sourceId").asLong();
    }

    /** Kendi test PDF'ini dosya adı ve içerikle yükleme girdisine dönüştürür. */
    private MockMultipartFile pdfFile(String fileName, String fixtureName) throws IOException {
        return new MockMultipartFile("files", fileName, "application/pdf", fixtureBytes(fixtureName));
    }

    /** 100 MB sınırını bildiren küçük gövdeli çok parçalı dosya üretir. */
    private MockMultipartFile oversizedFile() {
        return new MockMultipartFile("files", "too-large.pdf", "application/pdf", new byte[] {'%', 'P', 'D', 'F'}) {

            /** Gerçek yük gövdesini büyütmeden sınır üstü boyutu bildirir. */
            @Override
            public long getSize() {
                return DataSize.ofMegabytes(100).toBytes() + 1;
            }
        };
    }

    /** Depolama kökündeki dosya sayısını döndürür. */
    private long storedFileCount() throws IOException {
        Path sourceDirectory = storageDirectory.resolve("sources");
        if (!Files.exists(sourceDirectory)) {
            return 0;
        }
        try (var files = Files.list(sourceDirectory)) {
            return files.count();
        }
    }

    /** Sınıf yolundaki kendimize ait fikstürün baytlarını okur. */
    private byte[] fixtureBytes(String fixtureName) throws IOException {
        try (InputStream fixture = getClass().getResourceAsStream("/fixtures/" + fixtureName)) {
            if (fixture == null) {
                throw new IllegalStateException("Missing upload test fixture: " + fixtureName);
            }
            return fixture.readAllBytes();
        }
    }
}
