package com.hataanalizi.core;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.hataanalizi.core.auth.AppUserRepository;
import jakarta.servlet.http.Cookie;
import java.util.Locale;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.system.CapturedOutput;
import org.springframework.boot.test.system.OutputCaptureExtension;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.mock.web.MockHttpSession;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;
import org.springframework.test.web.servlet.request.RequestPostProcessor;

/** Kayıt ve oturum uç noktalarının HTTP sözleşmesini PostgreSQL üzerinde doğrular. */
@ActiveProfiles("test")
@SpringBootTest
@AutoConfigureMockMvc
@Import(TestcontainersConfiguration.class)
@ExtendWith(OutputCaptureExtension.class)
class AuthControllerIT {

    private static final String PASSWORD = "Sufficient-Test-Password-123";

    private final MockMvc mockMvc;
    private final AppUserRepository appUserRepository;
    private final PasswordEncoder passwordEncoder;

    /** Test bağımlılıklarını saklar. */
    @Autowired
    AuthControllerIT(MockMvc mockMvc, AppUserRepository appUserRepository, PasswordEncoder passwordEncoder) {
        this.mockMvc = mockMvc;
        this.appUserRepository = appUserRepository;
        this.passwordEncoder = passwordEncoder;
    }

    /** Kayıt, oturum açma, profil görüntüleme ve çıkış akışını doğrular. */
    @Test
    void registersLogsInLoadsProfileAndLogsOut(CapturedOutput output) throws Exception {
        String email = uniqueEmail().toUpperCase(Locale.ROOT);
        String normalizedEmail = email.toLowerCase(Locale.ROOT);
        register(email);
        MvcResult loginResult = mockMvc.perform(post("/api/auth/login")
                        .with(csrfHeaders())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(loginJson(normalizedEmail, PASSWORD)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.role").value("STUDENT"))
                .andReturn();

        assertThat(loginResult.getResponse().getContentAsString()).doesNotContain(PASSWORD);
        assertThat(passwordEncoder.matches(
                        PASSWORD,
                        appUserRepository
                                .findByEmail(normalizedEmail)
                                .orElseThrow()
                                .getPasswordHash()))
                .isTrue();
        assertThat(output).doesNotContain(PASSWORD);

        MockHttpSession session = (MockHttpSession) loginResult.getRequest().getSession(false);
        assertThat(session).isNotNull();
        mockMvc.perform(get("/api/me").session(session))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.email").value(normalizedEmail));
        mockMvc.perform(post("/api/auth/logout").with(csrfHeaders()).session(session))
                .andExpect(status().isNoContent());
        mockMvc.perform(get("/api/me")).andExpect(status().isUnauthorized());
    }

    /** Yinelenen e-posta kaydının 409 hata kodu döndürdüğünü doğrular. */
    @Test
    void duplicateEmailReturnsConflict() throws Exception {
        String email = uniqueEmail();
        register(email);

        mockMvc.perform(post("/api/auth/register")
                        .with(csrfHeaders())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(registerJson(email)))
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.code").value("EMAIL_TAKEN"));
    }

    /** Yanlış parolanın 401 hata kodu döndürdüğünü doğrular. */
    @Test
    void invalidPasswordReturnsUnauthorized() throws Exception {
        String email = uniqueEmail();
        register(email);

        mockMvc.perform(post("/api/auth/login")
                        .with(csrfHeaders())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(loginJson(email, "Wrong-Test-Password-123")))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.code").value("INVALID_CREDENTIALS"));
    }

    /** Test için geçerli öğrenci kaydı oluşturur. */
    private void register(String email) throws Exception {
        MvcResult result = mockMvc.perform(post("/api/auth/register")
                        .with(csrfHeaders())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(registerJson(email)))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.email").value(email.toLowerCase(Locale.ROOT)))
                .andExpect(jsonPath("$.role").value("STUDENT"))
                .andExpect(jsonPath("$.password").doesNotExist())
                .andReturn();
        assertThat(result.getResponse().getContentAsString()).doesNotContain(PASSWORD);
    }

    /** Kayıt isteğinin JSON gövdesini üretir. */
    private String registerJson(String email) {
        return """
                {"email":"%s","password":"%s","displayName":"Test student","grade":12,"explainStyle":"SIMPLE"}
                """.formatted(email, PASSWORD);
    }

    /** Giriş isteğinin JSON gövdesini üretir. */
    private String loginJson(String email, String password) {
        return """
                {"email":"%s","password":"%s","rememberMe":false}
                """.formatted(email, password);
    }

    /** İsteklere CSRF çereziyle eşleşen başlığı ekler. */
    private RequestPostProcessor csrfHeaders() {
        String token = UUID.randomUUID().toString();
        return request -> {
            request.setCookies(new Cookie("XSRF-TOKEN", token));
            request.addHeader("X-XSRF-TOKEN", token);
            return request;
        };
    }

    /** Her entegrasyon testinde yeni bir e-posta adresi üretir. */
    private String uniqueEmail() {
        return "student-" + UUID.randomUUID() + "@example.test";
    }
}
