package com.hataanalizi.core.auth;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.web.authentication.rememberme.CookieTheftException;
import org.springframework.security.web.authentication.rememberme.PersistentTokenBasedRememberMeServices;
import org.springframework.security.web.authentication.rememberme.PersistentTokenRepository;

/** JSON giriş isteği için Spring Security kalıcı oturum token'larını yönetir. */
public class AppPersistentTokenRememberMeServices extends PersistentTokenBasedRememberMeServices {

    private static final Logger LOGGER = LoggerFactory.getLogger(AppPersistentTokenRememberMeServices.class);

    /** Kalıcı token servisini kullanıcı yükleyici ve token deposuyla oluşturur. */
    public AppPersistentTokenRememberMeServices(
            String key, UserDetailsService userDetailsService, PersistentTokenRepository tokenRepository) {
        super(key, userDetailsService, tokenRepository);
    }

    /** Başarılı JSON girişinde kalıcı oturum çerezini oluşturur. */
    public void issueRememberMeCookie(
            Authentication authentication, HttpServletRequest request, HttpServletResponse response) {
        onLoginSuccess(request, response, authentication);
    }

    /** Tekrar kullanılan token'ı reddedip isteği kimliksiz olarak sürdürür. */
    @Override
    public Authentication autoLogin(HttpServletRequest request, HttpServletResponse response) {
        try {
            return super.autoLogin(request, response);
        } catch (CookieTheftException exception) {
            LOGGER.warn("Rejected a replayed remember-me token", exception);
            return null;
        }
    }
}
