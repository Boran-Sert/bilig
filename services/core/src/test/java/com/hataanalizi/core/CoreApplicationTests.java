package com.hataanalizi.core;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.util.List;
import java.util.Set;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.web.servlet.MockMvc;

/** Uygulama bağlamının hatasız açıldığını doğrular. */
@SpringBootTest
@AutoConfigureMockMvc
@Import(TestcontainersConfiguration.class)
class CoreApplicationTests {

    private final JdbcTemplate jdbcTemplate;
    private final MockMvc mockMvc;

    /** Test bağımlılıklarını hazırlar. */
    @Autowired
    CoreApplicationTests(JdbcTemplate jdbcTemplate, MockMvc mockMvc) {
        this.jdbcTemplate = jdbcTemplate;
        this.mockMvc = mockMvc;
    }

    /** Spring bağlamı yüklenir. */
    @Test
    void contextLoads() {}

    /** Flyway ile PostgreSQL eklentilerinin açıldığını doğrular. */
    @Test
    void requiredExtensionsAreInstalled() {
        List<String> extensions = jdbcTemplate.queryForList(
                "SELECT extname FROM pg_extension WHERE extname IN (?, ?)", String.class, "vector", "pg_textsearch");

        assertEquals(Set.of("vector", "pg_textsearch"), Set.copyOf(extensions));
    }

    /** OpenAPI belgesinin HTTP üzerinden erişilebilir olduğunu doğrular. */
    @Test
    void apiDocumentationIsAvailable() throws Exception {
        mockMvc.perform(get("/v3/api-docs")).andExpect(status().isOk());
    }
}
