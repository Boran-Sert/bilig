package com.hataanalizi.core.dashboard;

import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.nullValue;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.authentication;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.hataanalizi.core.TestcontainersConfiguration;
import com.hataanalizi.core.auth.AuthUser;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.request.RequestPostProcessor;
import org.springframework.transaction.annotation.Transactional;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

/** Öğrenci panelinin özet, sahiplik ve kazanım kurallarını PostgreSQL üzerinde doğrular. */
@ActiveProfiles("test")
@SpringBootTest
@AutoConfigureMockMvc
@Import(TestcontainersConfiguration.class)
@Transactional
class DashboardControllerIT {

    private final MockMvc mockMvc;
    private final ObjectMapper objectMapper;
    private final DashboardControllerTestData testData;

    /** Test bağımlılıklarını saklar. */
    @Autowired
    DashboardControllerIT(JdbcTemplate jdbcTemplate, MockMvc mockMvc, ObjectMapper objectMapper) {
        this.mockMvc = mockMvc;
        this.objectMapper = objectMapper;
        this.testData = new DashboardControllerTestData(jdbcTemplate);
    }

    /** Paneli doldurur ve eşikleri aşan kazanımları diğer kullanıcıdan yalıtır. */
    @Test
    void returnsOwnDashboardStatisticsAndFailedOutcomes() throws Exception {
        DashboardControllerTestData.DashboardFixture fixture = testData.createDashboardFixture();
        testData.insertOtherStudentAnswer(fixture);

        var result = mockMvc.perform(get("/api/me/dashboard").with(student(fixture.userId())))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.summary.answeredQuestionCount").value(21))
                .andExpect(jsonPath("$.summary.accuracyPercent").value(9.52))
                .andExpect(jsonPath("$.summary.latestNet").value(0.25))
                .andExpect(jsonPath("$.summary.latestQuestionCount").value(8))
                .andExpect(jsonPath("$.activeSessions.length()").value(1))
                .andExpect(jsonPath("$.activeSessions[0].examId").value(fixture.activeExamId()))
                .andExpect(jsonPath("$.activeSessions[0].examTitle").value("Şiir · Kazanım Testi 1"))
                .andExpect(jsonPath("$.activeSessions[0].questionCount").value(2))
                .andExpect(jsonPath("$.activeSessions[0].answeredCount").value(0))
                .andExpect(jsonPath("$.unitAccuracy.length()").value(2))
                .andExpect(jsonPath("$.unitAccuracy[0].unitTitle").value("Roman"))
                .andExpect(jsonPath("$.unitAccuracy[0].answeredCount").value(20))
                .andExpect(jsonPath("$.unitAccuracy[0].correctCount").value(1))
                .andExpect(jsonPath("$.unitAccuracy[1].unitTitle").value("Şiir"))
                .andExpect(jsonPath("$.unitAccuracy[1].answeredCount").value(1))
                .andExpect(jsonPath("$.errorTypeDistribution.length()").value(2))
                .andExpect(jsonPath("$.errorTypeDistribution[0].errorType").value("KNOWLEDGE"))
                .andExpect(jsonPath("$.errorTypeDistribution[1].errorType").value("READING"))
                .andReturn();

        assertFailedOutcomes(result.getResponse().getContentAsString());
    }

    /** Hiç cevaplamamış öğrencinin boş panelini sıfırlarla döndürür. */
    @Test
    void returnsEmptyDashboardForNewStudent() throws Exception {
        mockMvc.perform(get("/api/me/dashboard").with(student(testData.insertUser())))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.summary.answeredQuestionCount").value(0))
                .andExpect(jsonPath("$.summary.accuracyPercent").value(0))
                .andExpect(jsonPath("$.summary.latestNet").value(nullValue()))
                .andExpect(jsonPath("$.summary.latestQuestionCount").value(nullValue()))
                .andExpect(jsonPath("$.activeSessions.length()").value(0))
                .andExpect(jsonPath("$.failedOutcomes.length()").value(0))
                .andExpect(jsonPath("$.unitAccuracy.length()").value(0))
                .andExpect(jsonPath("$.errorTypeDistribution.length()").value(0));
    }

    /** Giriş yapmamış kullanıcının paneli okuyamadığını doğrular. */
    @Test
    void requiresAuthentication() throws Exception {
        mockMvc.perform(get("/api/me/dashboard")).andExpect(status().isUnauthorized());
    }

    /** Panel yanıtındaki başarısız kazanım eşiklerini doğrular. */
    private void assertFailedOutcomes(String response) throws Exception {
        JsonNode outcomes = objectMapper.readTree(response).get("failedOutcomes");
        assertThat(outcomes.size()).isEqualTo(3);
        assertThat(outcomes.get(0).get("code").stringValue()).isEqualTo("A.2.4");
        assertThat(outcomes.get(0).get("totalWrongCount").longValue()).isEqualTo(3);
        assertThat(outcomes.get(0).get("testWrongCount").longValue()).isEqualTo(3);
        assertThat(outcomes.get(1).get("code").stringValue()).isEqualTo("A.2.7");
        assertThat(outcomes.get(1).get("totalWrongCount").longValue()).isEqualTo(11);
        assertThat(outcomes.get(1).get("testTitle").stringValue()).isEqualTo("Roman · Kazanım Testi 3");
        assertThat(outcomes.get(2).get("code").stringValue()).isEqualTo("A.2.8");
        assertThat(outcomes.get(2).get("totalWrongCount").longValue()).isEqualTo(7);
        assertThat(outcomes.get(2).get("testTitle").isNull()).isTrue();
        assertThat(outcomes.get(2).get("testWrongCount").isNull()).isTrue();
    }

    /** İstek için test öğrencisinin kimliğini hazırlar. */
    private RequestPostProcessor student(Long userId) {
        AuthUser authUser = new AuthUser(userId, "student@example.test", "STUDENT");
        var authentication = new UsernamePasswordAuthenticationToken(
                authUser, null, List.of(new SimpleGrantedAuthority("ROLE_STUDENT")));
        return authentication(authentication);
    }
}
