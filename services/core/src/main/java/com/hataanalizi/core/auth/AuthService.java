package com.hataanalizi.core.auth;

import com.hataanalizi.core.auth.dto.LoginRequest;
import com.hataanalizi.core.auth.dto.MeResponse;
import com.hataanalizi.core.auth.dto.RegisterRequest;
import com.hataanalizi.core.common.ApiException;
import com.hataanalizi.core.common.ErrorCode;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.jdbc.core.JdbcTemplate;
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
    private final AppUserDetailsService appUserDetailsService;
    private final AuthenticationManager authenticationManager;
    private final PasswordEncoder passwordEncoder;
    private final JdbcTemplate jdbcTemplate;
    private final SecurityContextRepository securityContextRepository;

    /** Auth işlemlerinin gerekli servislerini ve depolarını saklar. */
    public AuthService(
            AppUserRepository appUserRepository,
            AppUserDetailsService appUserDetailsService,
            AuthenticationConfiguration authenticationConfiguration,
            PasswordEncoder passwordEncoder,
            JdbcTemplate jdbcTemplate)
            throws Exception {
        this.appUserRepository = appUserRepository;
        this.appUserDetailsService = appUserDetailsService;
        this.authenticationManager = authenticationConfiguration.getAuthenticationManager();
        this.passwordEncoder = passwordEncoder;
        this.jdbcTemplate = jdbcTemplate;
        this.securityContextRepository = new HttpSessionSecurityContextRepository();
    }

    /** Yeni öğrenciyi kaydeder ve parola özeti dışında hiçbir parola bilgisi döndürmez. */
    public MeResponse register(RegisterRequest request) {
        String email = appUserDetailsService.normalizeEmail(request.email());
        if (appUserRepository.findByEmail(email).isPresent()) {
            throw new ApiException(ErrorCode.EMAIL_TAKEN);
        }

        AppUser appUser = new AppUser();
        appUser.setTenantId(jdbcTemplate.queryForObject("SELECT id FROM tenant ORDER BY id LIMIT 1", Long.class));
        appUser.setEmail(email);
        appUser.setPasswordHash(passwordEncoder.encode(request.password()));
        appUser.setDisplayName(request.displayName());
        appUser.setRole("STUDENT");
        appUser.setGrade(request.grade());
        if (request.explainStyle() != null) {
            appUser.setExplainStyle(request.explainStyle());
        }

        try {
            return MeResponse.from(appUserRepository.saveAndFlush(appUser));
        } catch (DataIntegrityViolationException exception) {
            if (appUserRepository.findByEmail(email).isPresent()) {
                throw new ApiException(ErrorCode.EMAIL_TAKEN);
            }
            throw exception;
        }
    }

    /** Doğruladığı kullanıcıyı sunucu oturumuna kaydeder. */
    public MeResponse login(
            LoginRequest request, HttpServletRequest servletRequest, HttpServletResponse servletResponse) {
        String email = appUserDetailsService.normalizeEmail(request.email());
        Authentication authentication;
        try {
            authentication = authenticationManager.authenticate(
                    UsernamePasswordAuthenticationToken.unauthenticated(email, request.password()));
        } catch (BadCredentialsException exception) {
            throw new ApiException(ErrorCode.INVALID_CREDENTIALS);
        }

        AuthUser authUser = appUserDetailsService.loadAuthUserByEmail(email);
        SecurityContext context = SecurityContextHolder.createEmptyContext();
        context.setAuthentication(
                UsernamePasswordAuthenticationToken.authenticated(authUser, null, authentication.getAuthorities()));
        servletRequest.getSession(true);
        servletRequest.changeSessionId();
        SecurityContextHolder.setContext(context);
        securityContextRepository.saveContext(context, servletRequest, servletResponse);
        return findMe(authUser);
    }

    /** Giriş yapmış kullanıcının güncel profilini döndürür. */
    public MeResponse findMe(AuthUser authUser) {
        AppUser appUser =
                appUserRepository.findById(authUser.id()).orElseThrow(() -> new ApiException(ErrorCode.AUTH_REQUIRED));
        return MeResponse.from(appUser);
    }
}
