package com.hataanalizi.core.auth;

import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.contains;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.hataanalizi.core.TestcontainersConfiguration;
import com.hataanalizi.core.common.AppConstants;
import jakarta.servlet.http.Cookie;
import java.time.Duration;
import java.util.Locale;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import org.junit.jupiter.params.provider.ValueSource;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.system.CapturedOutput;
import org.springframework.boot.test.system.OutputCaptureExtension;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.mock.web.MockHttpSession;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.test.annotation.DirtiesContext;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;
import org.springframework.test.web.servlet.request.RequestPostProcessor;

/**
 * Kayıt ve oturum uç noktalarının HTTP sözleşmesini PostgreSQL üzerinde doğrular.
 *
 * <p>Gerçek CSRF çerez akışını sınadığı için temiz bağlamla başlar; başka testlerin csrf()
 * yardımcısı paylaşılan bağlamdaki CSRF deposunu değiştirir.
 */
@ActiveProfiles("test")
@SpringBootTest
@AutoConfigureMockMvc
@Import(TestcontainersConfiguration.class)
@DirtiesContext(classMode = DirtiesContext.ClassMode.BEFORE_CLASS)
@ExtendWith(OutputCaptureExtension.class)
class AuthControllerIT {

    private static final String PASSWORD = "Sufficient-Test-Password-123";

    private final MockMvc mockMvc;
    private final AppUserRepository appUserRepository;
    private final PasswordEncoder passwordEncoder;
    private final JdbcTemplate jdbcTemplate;

    /** Test bağımlılıklarını saklar. */
    @Autowired
    AuthControllerIT(
            MockMvc mockMvc,
            AppUserRepository appUserRepository,
            PasswordEncoder passwordEncoder,
            JdbcTemplate jdbcTemplate) {
        this.mockMvc = mockMvc;
        this.appUserRepository = appUserRepository;
        this.passwordEncoder = passwordEncoder;
        this.jdbcTemplate = jdbcTemplate;
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
                .andExpect(jsonPath("$.role").value(AppConstants.STUDENT_ROLE))
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
        assertThat(rememberMeTokenCount(normalizedEmail)).isZero();
        assertThat(loginResult.getResponse().getCookie(AppConstants.REMEMBER_ME_COOKIE_NAME))
                .isNull();

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
                        .content(registerJson(email, PASSWORD, "SIMPLE")))
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
                        .content(loginJson(email, "Wrong-Test-Password-123", false)))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.code").value("INVALID_CREDENTIALS"));
    }

    /** İçerik yönetimi yetkisinin sunucudaki rol listesinden hesaplandığını doğrular. */
    @ParameterizedTest
    @CsvSource({"STUDENT, false", "CONTENT_ADMIN, true", "ADMIN, true"})
    void meReportsContentManagementPermissionByRole(String role, boolean canManageContent) throws Exception {
        String email = uniqueEmail();
        register(email);
        jdbcTemplate.update("UPDATE app_user SET role = ? WHERE email = ?", role, email);
        MockHttpSession session =
                (MockHttpSession) login(email, false).getRequest().getSession(false);
        assertThat(session).isNotNull();

        mockMvc.perform(get("/api/me").session(session))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.role").value(role))
                .andExpect(jsonPath("$.canManageContent").value(canManageContent));
    }

    /** Kalıcı token'ın oturum olmadan profili açtığını ve kullanımda yenilendiğini doğrular. */
    @Test
    void rememberMeLoginSurvivesSessionExpiryAndRotatesToken() throws Exception {
        String email = uniqueEmail();
        register(email);
        MvcResult loginResult = login(email, true);
        Cookie originalCookie = loginResult.getResponse().getCookie(AppConstants.REMEMBER_ME_COOKIE_NAME);
        assertThat(originalCookie).isNotNull();
        assertThat(originalCookie.isHttpOnly()).isTrue();
        assertThat(originalCookie.getSecure()).isTrue();
        assertThat(originalCookie.getAttribute("SameSite")).isEqualTo("Lax");
        assertThat(originalCookie.getMaxAge())
                .isEqualTo(Math.toIntExact(Duration.ofDays(30).toSeconds()));
        assertThat(rememberMeTokenCount(email)).isEqualTo(1);

        MvcResult profileResult = mockMvc.perform(get("/api/me").cookie(originalCookie))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.email").value(email))
                .andReturn();

        Cookie refreshedCookie = profileResult.getResponse().getCookie(AppConstants.REMEMBER_ME_COOKIE_NAME);
        assertThat(refreshedCookie).isNotNull();
        assertThat(refreshedCookie.getValue()).isNotEqualTo(originalCookie.getValue());
        assertThat(rememberMeTokenCount(email)).isEqualTo(1);
    }

    /** Eski token tekrar kullanıldığında kullanıcının bütün token'larının silindiğini doğrular. */
    @Test
    void replayedRememberMeTokenRevokesAllUserTokens() throws Exception {
        String email = uniqueEmail();
        register(email);
        Cookie originalCookie = login(email, true).getResponse().getCookie(AppConstants.REMEMBER_ME_COOKIE_NAME);
        assertThat(originalCookie).isNotNull();
        mockMvc.perform(get("/api/me").cookie(originalCookie)).andExpect(status().isOk());

        login(email, true);
        assertThat(rememberMeTokenCount(email)).isEqualTo(2);

        mockMvc.perform(get("/api/me").cookie(originalCookie)).andExpect(status().isUnauthorized());
        assertThat(rememberMeTokenCount(email)).isZero();
    }

    /** Çıkışın sunucu oturumuyla birlikte kalıcı token'ı da sildiğini doğrular. */
    @Test
    void logoutRemovesRememberMeToken() throws Exception {
        String email = uniqueEmail();
        register(email);
        MvcResult loginResult = login(email, true);
        MockHttpSession session = (MockHttpSession) loginResult.getRequest().getSession(false);
        assertThat(session).isNotNull();
        assertThat(rememberMeTokenCount(email)).isEqualTo(1);

        mockMvc.perform(post("/api/auth/logout").with(csrfHeaders()).session(session))
                .andExpect(status().isNoContent());

        assertThat(rememberMeTokenCount(email)).isZero();
    }

    /** Geçersiz e-posta adresini 400 olarak reddeder. */
    @Test
    void invalidEmailReturnsBadRequest() throws Exception {
        mockMvc.perform(post("/api/auth/register")
                        .with(csrfHeaders())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(registerJson("invalid-email", PASSWORD, "SIMPLE")))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.errors[0].message").value("Geçerli bir e-posta adresi gir."));
    }

    /** Sekiz karakterden kısa parolayı 400 olarak reddeder. */
    @Test
    void shortPasswordReturnsBadRequest() throws Exception {
        mockMvc.perform(post("/api/auth/register")
                        .with(csrfHeaders())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(registerJson(uniqueEmail(), "short", "SIMPLE")))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.errors[0].message").value("Şifre en az 8, en fazla 72 karakter olmalıdır."));
    }

    /** Tanınmayan anlatım tarzını 400 olarak reddeder. */
    @Test
    void invalidExplainStyleReturnsBadRequest() throws Exception {
        mockMvc.perform(post("/api/auth/register")
                        .with(csrfHeaders())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(registerJson(uniqueEmail(), PASSWORD, "INVALID")))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.errors[0].message").value("Geçerli bir anlatım tarzı seç."));
    }

    /** Kayıt seçeneklerinin girişsiz alındığını ve 9-12 ile mezunu içerdiğini doğrular. */
    @Test
    void registerOptionsArePublic() throws Exception {
        mockMvc.perform(get("/api/auth/register-options"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.grades").value(contains(9, 10, 11, 12, 13)));
    }

    /** Sınıf seçilmeyen ya da listede olmayan kaydı sınıf alanının hatasıyla reddeder. */
    @ParameterizedTest
    @ValueSource(strings = {"", ",\"grade\":8", ",\"grade\":14"})
    void missingOrInvalidGradeReturnsBadRequest(String gradeProperty) throws Exception {
        mockMvc.perform(post("/api/auth/register")
                        .with(csrfHeaders())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"email":"%s","password":"%s","displayName":"Test student",\
                                "privacyNoticeAccepted":true,"consentAccepted":true%s}
                                """.formatted(uniqueEmail(), PASSWORD, gradeProperty)))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.errors.length()").value(1))
                .andExpect(jsonPath("$.errors[0].field").value("grade"))
                .andExpect(jsonPath("$.errors[0].message").value("Listeden sınıfını seç."));
    }

    /** Onaylardan biri eksik ya da hayırsa kaydı yalnız o alanın hatasıyla reddeder. */
    @ParameterizedTest
    @CsvSource(
            nullValues = "null",
            value = {
                "null,  true,  privacyNoticeAccepted, Devam etmek için aydınlatma metnini okuduğunu onaylamalısın.",
                "false, true,  privacyNoticeAccepted, Devam etmek için aydınlatma metnini okuduğunu onaylamalısın.",
                "true,  null,  consentAccepted, Devam etmek için kişisel verilerinin işlenmesine açık rıza vermelisin.",
                "true,  false, consentAccepted, Devam etmek için kişisel verilerinin işlenmesine açık rıza vermelisin."
            })
    void missingApprovalReturnsBadRequest(
            Boolean privacyNoticeAccepted, Boolean consentAccepted, String field, String message) throws Exception {
        String email = uniqueEmail();
        mockMvc.perform(post("/api/auth/register")
                        .with(csrfHeaders())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"email":"%s","password":"%s","displayName":"Test student","grade":12%s%s}
                                """.formatted(
                                        email,
                                        PASSWORD,
                                        approvalJson("privacyNoticeAccepted", privacyNoticeAccepted),
                                        approvalJson("consentAccepted", consentAccepted))))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.errors.length()").value(1))
                .andExpect(jsonPath("$.errors[0].field").value(field))
                .andExpect(jsonPath("$.errors[0].message").value(message));

        assertThat(appUserRepository.findByEmail(email)).isEmpty();
    }

    /** Kaydın oturumu açtığını, iki onayı ayrı sakladığını ve mezun seçimini koruduğunu doğrular. */
    @Test
    void registerStartsSessionAndStoresConsent() throws Exception {
        String email = uniqueEmail();
        MvcResult result = mockMvc.perform(post("/api/auth/register")
                        .with(csrfHeaders())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"email":"%s","password":"%s","displayName":"Test student","grade":13,\
                                "privacyNoticeAccepted":true,"consentAccepted":true}
                                """.formatted(email, PASSWORD)))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.grade").value(AppConstants.GRADUATE_GRADE))
                .andExpect(jsonPath("$.explainStyle").value(AppConstants.DEFAULT_EXPLAIN_STYLE))
                .andReturn();

        MockHttpSession session = (MockHttpSession) result.getRequest().getSession(false);
        assertThat(session).isNotNull();
        mockMvc.perform(get("/api/me").session(session))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.email").value(email));
        AppUser appUser = appUserRepository.findByEmail(email).orElseThrow();
        assertThat(appUser.getPrivacyNoticeVersion()).isEqualTo(AppConstants.PRIVACY_NOTICE_VERSION);
        assertThat(appUser.getPrivacyNoticeAcceptedAt()).isNotNull();
        assertThat(appUser.getConsentVersion()).isEqualTo(AppConstants.CONSENT_VERSION);
        assertThat(appUser.getConsentAcceptedAt()).isNotNull();
    }

    /** BCrypt sınırını aşan UTF-8 parolayı 400 olarak reddeder. */
    @Test
    void oversizedUtf8PasswordReturnsBadRequest() throws Exception {
        String password = "ğ".repeat(37);
        mockMvc.perform(post("/api/auth/register")
                        .with(csrfHeaders())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(registerJson(uniqueEmail(), password, "SIMPLE")))
                .andExpect(status().isBadRequest())
                .andExpect(
                        jsonPath("$.errors[0].message").value("Şifre UTF-8 kodlamasında en fazla 72 bayt olabilir."));
    }

    /** Test için geçerli öğrenci kaydı oluşturur. */
    private void register(String email) throws Exception {
        MvcResult result = mockMvc.perform(post("/api/auth/register")
                        .with(csrfHeaders())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(registerJson(email, PASSWORD, "SIMPLE")))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.email").value(email.toLowerCase(Locale.ROOT)))
                .andExpect(jsonPath("$.role").value(AppConstants.STUDENT_ROLE))
                .andExpect(jsonPath("$.password").doesNotExist())
                .andReturn();
        assertThat(result.getResponse().getContentAsString()).doesNotContain(PASSWORD);
    }

    /** Kayıt isteğinin JSON gövdesini üretir. */
    private String registerJson(String email, String password, String explainStyle) {
        return """
                {"email":"%s","password":"%s","displayName":"Test student","grade":12,"explainStyle":"%s",\
                "privacyNoticeAccepted":true,"consentAccepted":true}
                """.formatted(email, password, explainStyle);
    }

    /** Onay alanını JSON parçası olarak üretir; değer yoksa alanı hiç yazmaz. */
    private String approvalJson(String field, Boolean accepted) {
        return accepted == null ? "" : ",\"%s\":%s".formatted(field, accepted);
    }

    /** Kalıcı oturum alanı olmayan eski giriş gövdesini üretir. */
    private String loginJson(String email, String password) {
        return """
                {"email":"%s","password":"%s"}
                """.formatted(email, password);
    }

    /** Giriş isteğinin JSON gövdesini seçilen kalıcı oturum değeriyle üretir. */
    private String loginJson(String email, String password, boolean rememberMe) {
        return """
                {"email":"%s","password":"%s","rememberMe":%s}
                """.formatted(email, password, rememberMe);
    }

    /** Test kullanıcısı için kalıcı token ile giriş yapar. */
    private MvcResult login(String email, boolean rememberMe) throws Exception {
        return mockMvc.perform(post("/api/auth/login")
                        .with(csrfHeaders())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(loginJson(email, PASSWORD, rememberMe)))
                .andExpect(status().isOk())
                .andReturn();
    }

    /** Kullanıcıya ait kalıcı token satırı sayısını döndürür. */
    private int rememberMeTokenCount(String email) {
        Integer tokenCount = jdbcTemplate.queryForObject(
                "SELECT count(*) FROM persistent_logins WHERE username = ?", Integer.class, email);
        return tokenCount == null ? 0 : tokenCount;
    }

    /** İsteklere CSRF çereziyle eşleşen başlığı ekler. */
    private RequestPostProcessor csrfHeaders() throws Exception {
        MvcResult csrfResult = mockMvc.perform(get("/api/auth/public"))
                .andExpect(status().isNotFound())
                .andReturn();
        Cookie tokenCookie = csrfResult.getResponse().getCookie("XSRF-TOKEN");
        assertThat(tokenCookie).isNotNull();
        return request -> {
            request.setCookies(tokenCookie);
            request.addHeader("X-XSRF-TOKEN", tokenCookie.getValue());
            return request;
        };
    }

    /** Her entegrasyon testinde yeni bir e-posta adresi üretir. */
    private String uniqueEmail() {
        return "student-" + UUID.randomUUID() + "@example.test";
    }
}
