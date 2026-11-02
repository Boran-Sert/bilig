package com.hataanalizi.core.config;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.testSecurityContext;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.hataanalizi.core.auth.AppPersistentTokenRememberMeServices;
import com.hataanalizi.core.auth.AuthController;
import com.hataanalizi.core.auth.AuthService;
import com.hataanalizi.core.auth.WithAuthUser;
import com.hataanalizi.core.common.AppConstants;
import com.hataanalizi.core.common.GlobalExceptionHandler;
import com.hataanalizi.core.common.RequestIdFilter;
import jakarta.servlet.http.Cookie;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.boot.webmvc.test.autoconfigure.WebMvcTest;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.core.userdetails.UsernameNotFoundException;
import org.springframework.security.web.authentication.rememberme.PersistentTokenRepository;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;

/** Güvenlik yollarının, rollerin ve CSRF başlık sözleşmesinin HTTP davranışını doğrular. */
@WebMvcTest(AuthController.class)
@Import({
    SecurityConfig.class,
    GlobalExceptionHandler.class,
    RequestIdFilter.class,
    SecurityConfigIT.RememberMeTestConfiguration.class
})
class SecurityConfigIT {

    private final MockMvc mockMvc;

    @MockitoBean
    private AuthService authService;

    /** HTTP test aracını saklar. */
    @Autowired
    SecurityConfigIT(MockMvc mockMvc) {
        this.mockMvc = mockMvc;
    }

    /** Kimliksiz API isteğinin 401 Problem Details döndürdüğünü doğrular. */
    @Test
    void unauthenticatedApiRequestReturnsProblemDetails() throws Exception {
        mockMvc.perform(get("/api/private"))
                .andExpect(status().isUnauthorized())
                .andExpect(content().contentTypeCompatibleWith(MediaType.APPLICATION_PROBLEM_JSON))
                .andExpect(jsonPath("$.code").value("AUTH_REQUIRED"))
                .andExpect(jsonPath("$.requestId").exists());
    }

    /** Kimlik ve belge yollarının herkese açık olduğunu doğrular. */
    @Test
    void authenticationAndDocumentationPathsArePublic() throws Exception {
        mockMvc.perform(get("/api/auth/public")).andExpect(status().isNotFound());
        mockMvc.perform(get("/v3/api-docs")).andExpect(status().isNotFound());
    }

    /** Öğrencinin yönetici yolundan 403 Problem Details aldığını doğrular. */
    @Test
    @WithAuthUser
    void studentCannotAccessAdminEndpoint() throws Exception {
        mockMvc.perform(get("/api/admin/private").with(testSecurityContext()))
                .andExpect(status().isForbidden())
                .andExpect(content().contentTypeCompatibleWith(MediaType.APPLICATION_PROBLEM_JSON))
                .andExpect(jsonPath("$.code").value("ACCESS_DENIED"))
                .andExpect(jsonPath("$.requestId").exists());
    }

    /** İçerik yöneticisinin yönetici yolundaki yetki kontrolünü geçtiğini doğrular. */
    @Test
    @WithAuthUser(role = AppConstants.CONTENT_ADMIN_ROLE)
    void contentAdminPassesAdminAuthorization() throws Exception {
        mockMvc.perform(get("/api/admin/private").with(testSecurityContext())).andExpect(status().isNotFound());
    }

    /** Yöneticinin yönetici yolundaki yetki kontrolünü geçtiğini doğrular. */
    @Test
    @WithAuthUser(role = AppConstants.ADMIN_ROLE)
    void adminPassesAdminAuthorization() throws Exception {
        mockMvc.perform(get("/api/admin/private").with(testSecurityContext())).andExpect(status().isNotFound());
    }

    /** CSRF başlığı olmayan POST isteğinin reddedildiğini doğrular. */
    @Test
    void postWithoutCsrfHeaderIsRejected() throws Exception {
        mockMvc.perform(post("/api/auth/login")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{}"))
                .andExpect(status().isForbidden())
                .andExpect(content().contentTypeCompatibleWith(MediaType.APPLICATION_PROBLEM_JSON))
                .andExpect(jsonPath("$.code").value("ACCESS_DENIED"))
                .andExpect(jsonPath("$.requestId").exists());
    }

    /** CSRF çereziyle eşleşen özel başlığın isteği CSRF kontrolünden geçirdiğini doğrular. */
    @Test
    void postWithCsrfCookieAndHeaderPassesCsrfCheck() throws Exception {
        MvcResult csrfResult = mockMvc.perform(get("/api/auth/public"))
                .andExpect(status().isNotFound())
                .andReturn();
        Cookie tokenCookie = csrfResult.getResponse().getCookie("XSRF-TOKEN");
        assertThat(tokenCookie).isNotNull();

        mockMvc.perform(post("/api/auth/login")
                        .cookie(tokenCookie)
                        .header("X-XSRF-TOKEN", tokenCookie.getValue())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("VALIDATION_FAILED"));
    }

    /** Test güvenlik zinciri için geçerli kalıcı token servisi sağlar. */
    @TestConfiguration
    static class RememberMeTestConfiguration {

        /** Harici veritabanı olmadan güvenlik filtresinin token servisini oluşturur. */
        @Bean
        AppPersistentTokenRememberMeServices rememberMeServices() {
            UserDetailsService userDetailsService = username -> {
                throw new UsernameNotFoundException("User not found");
            };
            PersistentTokenRepository tokenRepository = mock(PersistentTokenRepository.class);
            return new AppPersistentTokenRememberMeServices(
                    "security-test-remember-me-key", userDetailsService, tokenRepository);
        }
    }
}
