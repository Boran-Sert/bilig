package com.hataanalizi.core.tutor;

import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.authentication;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.hataanalizi.core.TestcontainersConfiguration;
import com.hataanalizi.core.auth.AuthUser;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.request.RequestPostProcessor;

/** İpucu uç noktasının HTTP cevabını ve kalıcı önbelleğini PostgreSQL ile doğrular. */
@ActiveProfiles("test")
@SpringBootTest
@AutoConfigureMockMvc
@Import(TestcontainersConfiguration.class)
class HintControllerIT {

    private final JdbcTemplate jdbcTemplate;
    private final MockMvc mockMvc;

    @MockitoBean
    private AiClient aiClient;

    /** HTTP ve veritabanı bağımlılıklarını saklar. */
    @Autowired
    HintControllerIT(JdbcTemplate jdbcTemplate, MockMvc mockMvc) {
        this.jdbcTemplate = jdbcTemplate;
        this.mockMvc = mockMvc;
    }

    /** İlk istekte ipucunu kaydeder, ikinci istekte kayıtlı yanıtı döndürür. */
    @Test
    void generatesAndReturnsCachedHint() throws Exception {
        Long userId = insertUser();
        Long questionId = insertQuestion(insertCurriculumUnit());
        when(aiClient.hint(questionId)).thenReturn("Compare the choices.");

        mockMvc.perform(get("/api/questions/{id}/hint", questionId).with(student(userId)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.hint").value("Compare the choices."));
        mockMvc.perform(get("/api/questions/{id}/hint", questionId).with(student(userId)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.hint").value("Compare the choices."));

        verify(aiClient, times(1)).hint(questionId);
        org.assertj.core.api.Assertions.assertThat(
                        jdbcTemplate.queryForObject("SELECT hint FROM question WHERE id = ?", String.class, questionId))
                .isEqualTo("Compare the choices.");
    }

    /** Yeni bir öğrenci hesabı oluşturur. */
    private Long insertUser() {
        String identifier = UUID.randomUUID().toString();
        return jdbcTemplate.queryForObject("""
                INSERT INTO app_user (tenant_id, email, display_name, role)
                SELECT id, ?, ?, 'STUDENT'
                FROM tenant
                WHERE name = 'Bilig'
                RETURNING id
                """, Long.class, identifier + "@example.test", identifier);
    }

    /** Testte kullanılacak ders programı ve ünitesini oluşturur. */
    private Long insertCurriculumUnit() {
        String identifier = UUID.randomUUID().toString();
        Long subjectId = jdbcTemplate.queryForObject(
                "INSERT INTO subject (code, name) VALUES (?, ?) RETURNING id", Long.class, identifier, identifier);
        Long curriculumId = jdbcTemplate.queryForObject("""
                INSERT INTO curriculum (subject_id, name, model, year)
                VALUES (?, ?, ?, ?)
                RETURNING id
                """, Long.class, subjectId, identifier, "LEGACY", 2018);
        return jdbcTemplate.queryForObject("""
                INSERT INTO curriculum_unit (curriculum_id, grade, unit_no, title)
                VALUES (?, ?, ?, ?)
                RETURNING id
                """, Long.class, curriculumId, 12, 1, identifier);
    }

    /** Testte kullanılacak yayımlanmış soruyu ekler. */
    private Long insertQuestion(Long unitId) {
        String content = """
                {"stem":[{"type":"paragraph","md":"Question"}],
                 "options":[{"label":"A","blocks":[{"type":"paragraph","md":"Option A"}]},
                            {"label":"B","blocks":[{"type":"paragraph","md":"Option B"}]}]}
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

    /** İstek için test öğrencisinin kimliğini hazırlar. */
    private RequestPostProcessor student(Long userId) {
        AuthUser authUser = new AuthUser(userId, "student@example.test", "STUDENT");
        var studentAuthentication = new UsernamePasswordAuthenticationToken(
                authUser, null, List.of(new SimpleGrantedAuthority("ROLE_STUDENT")));
        return authentication(studentAuthentication);
    }
}
