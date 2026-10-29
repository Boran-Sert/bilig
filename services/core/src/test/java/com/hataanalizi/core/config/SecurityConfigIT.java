package com.hataanalizi.core.config;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.testSecurityContext;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.hataanalizi.core.auth.WithAuthUser;
import com.hataanalizi.core.common.GlobalExceptionHandler;
import com.hataanalizi.core.common.RequestIdFilter;
import jakarta.servlet.http.Cookie;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.webmvc.test.autoconfigure.WebMvcTest;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

/** Güvenlik yollarının, rollerin ve CSRF başlık sözleşmesinin HTTP davranışını doğrular. */
@WebMvcTest
@Import({SecurityConfig.class, GlobalExceptionHandler.class, RequestIdFilter.class})
class SecurityConfigIT {

    private final MockMvc mockMvc;

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
    @WithAuthUser(role = "CONTENT_ADMIN")
    void contentAdminPassesAdminAuthorization() throws Exception {
        mockMvc.perform(get("/api/admin/private").with(testSecurityContext())).andExpect(status().isNotFound());
    }

    /** Yöneticinin yönetici yolundaki yetki kontrolünü geçtiğini doğrular. */
    @Test
    @WithAuthUser(role = "ADMIN")
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
        String token = UUID.randomUUID().toString();
        mockMvc.perform(post("/api/auth/login")
                        .cookie(new Cookie("XSRF-TOKEN", token))
                        .header("X-XSRF-TOKEN", token)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{}"))
                .andExpect(status().isNotFound());
    }
}
