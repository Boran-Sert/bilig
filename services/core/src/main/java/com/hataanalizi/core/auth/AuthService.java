package com.hataanalizi.core.auth;

import com.hataanalizi.core.auth.dto.LoginRequest;
import com.hataanalizi.core.auth.dto.MeResponse;
import com.hataanalizi.core.auth.dto.RegisterRequest;
import com.hataanalizi.core.common.ApiException;
import com.hataanalizi.core.common.AppConstants;
import com.hataanalizi.core.common.ErrorCode;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.util.Locale;
import org.hibernate.exception.ConstraintViolationException;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.BadCredentialsException;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.config.annotation.authentication.configuration.AuthenticationConfiguration;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContext;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.context.HttpSessionSecurityContextRepository;
import org.springframework.security.web.context.SecurityContextRepository;
import org.springframework.stereotype.Service;

/** Öğrenci kaydını, girişini ve oturum principal'ını yönetir. */
@Service
public class AuthService {

    private final AppUserRepository appUserRepository;
    private final TenantRepository tenantRepository;
    private final AuthenticationManager authenticationManager;
    private final PasswordEncoder passwordEncoder;
    private final SecurityContextRepository securityContextRepository;
    private final AppPersistentTokenRememberMeServices rememberMeServices;

    /** Auth işlemlerinin gerekli servislerini ve depolarını saklar. */
    public AuthService(
            AppUserRepository appUserRepository,
            TenantRepository tenantRepository,
            AuthenticationConfiguration authenticationConfiguration,
            PasswordEncoder passwordEncoder,
            AppPersistentTokenRememberMeServices rememberMeServices)
            throws Exception {
        this.appUserRepository = appUserRepository;
        this.tenantRepository = tenantRepository;
        this.authenticationManager = authenticationConfiguration.getAuthenticationManager();
        this.passwordEncoder = passwordEncoder;
        this.securityContextRepository = new HttpSessionSecurityContextRepository();
        this.rememberMeServices = rememberMeServices;
    }

    /** Yeni öğrenciyi kaydeder ve parola özeti dışında hiçbir parola bilgisi döndürmez. */
    public MeResponse register(RegisterRequest request) {
        AppUser appUser = new AppUser();
        appUser.setTenantId(tenantRepository
                .findByName(AppConstants.DEFAULT_TENANT_NAME)
                .orElseThrow(() -> new IllegalStateException("Registration tenant is not configured"))
                .getId());
        appUser.setEmail(normalizeEmail(request.email()));
        appUser.setPasswordHash(passwordEncoder.encode(request.password()));
        appUser.setDisplayName(request.displayName());
        appUser.setRole(AppConstants.STUDENT_ROLE);
        appUser.setGrade(request.grade());
        if (request.explainStyle() != null) {
            appUser.setExplainStyle(request.explainStyle());
        }

        try {
            return MeResponse.from(appUserRepository.saveAndFlush(appUser));
        } catch (DataIntegrityViolationException exception) {
            if (isEmailAlreadyTaken(exception)) {
                throw new ApiException(ErrorCode.EMAIL_TAKEN, exception);
            }
            throw exception;
        }
    }

    /** Doğruladığı kullanıcıyı sunucu oturumuna kaydeder. */
    public MeResponse login(
            LoginRequest request, HttpServletRequest servletRequest, HttpServletResponse servletResponse) {
        String email = normalizeEmail(request.email());
        Authentication authentication;
        try {
            authentication = authenticationManager.authenticate(
                    UsernamePasswordAuthenticationToken.unauthenticated(email, request.password()));
        } catch (BadCredentialsException exception) {
            throw new ApiException(ErrorCode.INVALID_CREDENTIALS);
        }

        if (!(authentication.getPrincipal() instanceof AppUserPrincipal principal)) {
            throw new IllegalStateException("Authentication returned an unexpected principal");
        }
        AuthUser authUser = new AuthUser(principal.id(), principal.email(), principal.role());
        SecurityContext context = SecurityContextHolder.createEmptyContext();
        context.setAuthentication(
                UsernamePasswordAuthenticationToken.authenticated(authUser, null, authentication.getAuthorities()));
        servletRequest.getSession(true);
        servletRequest.changeSessionId();
        SecurityContextHolder.setContext(context);
        securityContextRepository.saveContext(context, servletRequest, servletResponse);
        if (Boolean.TRUE.equals(request.rememberMe())) {
            rememberMeServices.issueRememberMeCookie(authentication, servletRequest, servletResponse);
        }
        return MeResponse.from(principal);
    }

    /** Giriş yapmış kullanıcının güncel profilini döndürür. */
    public MeResponse findMe(AuthUser authUser) {
        AppUser appUser =
                appUserRepository.findById(authUser.id()).orElseThrow(() -> new ApiException(ErrorCode.AUTH_REQUIRED));
        return MeResponse.from(appUser);
    }

    /** E-posta adresini boşluklardan arındırıp kök yerel ayara göre küçültür. */
    private String normalizeEmail(String email) {
        return email.trim().toLowerCase(Locale.ROOT);
    }

    /** E-posta benzersiz kısıtı ihlal edildiyse true döndürür. */
    private boolean isEmailAlreadyTaken(DataIntegrityViolationException exception) {
        for (Throwable cause = exception; cause != null; cause = cause.getCause()) {
            if (cause instanceof ConstraintViolationException violation
                    && AppConstants.APP_USER_EMAIL_UNIQUE_CONSTRAINT.equals(violation.getConstraintName())) {
                return true;
            }
        }
        return false;
    }
}
