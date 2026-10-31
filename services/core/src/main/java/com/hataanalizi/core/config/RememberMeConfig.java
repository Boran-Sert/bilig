package com.hataanalizi.core.config;

import com.hataanalizi.core.auth.AppPersistentTokenRememberMeServices;
import com.hataanalizi.core.auth.AppUserDetailsService;
import com.hataanalizi.core.common.AppConstants;
import java.time.Duration;
import javax.sql.DataSource;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.web.authentication.rememberme.JdbcTokenRepositoryImpl;

/** Kalıcı oturum çerezini ve veritabanı token deposunu yapılandırır. */
@Configuration
public class RememberMeConfig {

    /** JDBC deposunu migration ile oluşturulan kalıcı token tablosuna bağlar. */
    @Bean
    public JdbcTokenRepositoryImpl rememberMeTokenRepository(DataSource dataSource) {
        JdbcTokenRepositoryImpl repository = new JdbcTokenRepositoryImpl();
        repository.setDataSource(dataSource);
        repository.setCreateTableOnStartup(false);
        return repository;
    }

    /** Kalıcı oturum token'larının anahtarını, ömrünü ve çerez güvenliğini yapılandırır. */
    @Bean
    public AppPersistentTokenRememberMeServices rememberMeServices(
            @Value("${REMEMBER_ME_KEY}") String key,
            AppUserDetailsService userDetailsService,
            JdbcTokenRepositoryImpl tokenRepository,
            @Value("${app.auth.remember-me-days}") int validityDays) {
        AppPersistentTokenRememberMeServices services =
                new AppPersistentTokenRememberMeServices(key, userDetailsService, tokenRepository);
        services.setCookieName(AppConstants.REMEMBER_ME_COOKIE_NAME);
        services.setTokenValiditySeconds(
                Math.toIntExact(Duration.ofDays(validityDays).toSeconds()));
        services.setUseSecureCookie(true);
        services.setCookieCustomizer(cookie -> {
            cookie.setHttpOnly(true);
            cookie.setAttribute("SameSite", "Lax");
        });
        return services;
    }
}
