package com.hataanalizi.core.config;

import com.hataanalizi.core.auth.AppPersistentTokenRememberMeServices;
import com.hataanalizi.core.common.AppConstants;
import com.hataanalizi.core.common.ErrorCode;
import com.hataanalizi.core.common.RequestIdFilter;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.net.URI;
import java.util.Locale;
import org.springframework.context.MessageSource;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ProblemDetail;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.csrf.CookieCsrfTokenRepository;
import org.springframework.security.web.csrf.CsrfFilter;
import org.springframework.security.web.csrf.CsrfTokenRequestAttributeHandler;
import tools.jackson.databind.ObjectMapper;

/** API yollarına göre kimlik doğrulamayı, rolleri ve CSRF korumasını yapılandırır. */
@Configuration
@EnableWebSecurity
public class SecurityConfig {

    private static final Locale TURKISH = Locale.forLanguageTag("tr");

    private final MessageSource messageSource;
    private final ObjectMapper objectMapper;

    /** Güvenlik hata cevapları için gereken bileşenleri saklar. */
    public SecurityConfig(MessageSource messageSource, ObjectMapper objectMapper) {
        this.messageSource = messageSource;
        this.objectMapper = objectMapper;
    }

    /** API erişimini sınırlar ve CSRF token'ını çerez ile başlık üzerinden doğrular. */
    @Bean
    public SecurityFilterChain securityFilterChain(
            HttpSecurity http, AppPersistentTokenRememberMeServices rememberMeServices) throws Exception {
        http.authorizeHttpRequests(authorize -> authorize
                        .requestMatchers("/api/auth/**", "/v3/api-docs/**", "/swagger-ui/**", "/swagger-ui.html")
                        .permitAll()
                        .requestMatchers("/api/admin/**")
                        .hasAnyRole(AppConstants.CONTENT_ADMIN_ROLE, AppConstants.ADMIN_ROLE)
                        .requestMatchers("/api/**")
                        .authenticated()
                        .anyRequest()
                        .permitAll())
                .csrf(csrf -> csrf.csrfTokenRepository(csrfTokenRepository())
                        .csrfTokenRequestHandler(new CsrfTokenRequestAttributeHandler()))
                .rememberMe(rememberMe -> rememberMe.rememberMeServices(rememberMeServices))
                .addFilterAfter(new CsrfCookieFilter(), CsrfFilter.class)
                .exceptionHandling(exceptionHandling -> exceptionHandling
                        .authenticationEntryPoint(
                                (request, response, exception) -> writeSecurityError(response, ErrorCode.AUTH_REQUIRED))
                        .accessDeniedHandler((request, response, exception) ->
                                writeSecurityError(response, ErrorCode.ACCESS_DENIED)));
        return http.build();
    }

    /** CSRF token'ını tarayıcının okuyabildiği XSRF-TOKEN çerezinde tutar. */
    private CookieCsrfTokenRepository csrfTokenRepository() {
        CookieCsrfTokenRepository repository = CookieCsrfTokenRepository.withHttpOnlyFalse();
        repository.setCookieName("XSRF-TOKEN");
        repository.setHeaderName("X-XSRF-TOKEN");
        return repository;
    }

    /** Güvenlik hatasını ortak Problem Details sözleşmesiyle yazar. */
    private void writeSecurityError(HttpServletResponse response, ErrorCode errorCode) throws IOException {
        HttpStatus status = errorCode.getStatus();
        ProblemDetail problem = ProblemDetail.forStatusAndDetail(
                status, messageSource.getMessage(errorCode.messageKey(), null, TURKISH));
        problem.setType(URI.create("about:blank"));
        problem.setProperty("code", errorCode.name());
        problem.setProperty("requestId", RequestIdFilter.currentRequestId());
        response.setStatus(status.value());
        response.setContentType(MediaType.APPLICATION_PROBLEM_JSON_VALUE);
        objectMapper.writeValue(response.getOutputStream(), problem);
    }
}
