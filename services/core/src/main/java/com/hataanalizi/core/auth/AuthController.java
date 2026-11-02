package com.hataanalizi.core.auth;

import com.hataanalizi.core.auth.dto.LoginRequest;
import com.hataanalizi.core.auth.dto.MeResponse;
import com.hataanalizi.core.auth.dto.RegisterOptionsResponse;
import com.hataanalizi.core.auth.dto.RegisterRequest;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.web.authentication.logout.SecurityContextLogoutHandler;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/** Kayıt, giriş, çıkış ve mevcut kullanıcı uç noktalarını sunar. */
@RestController
@RequestMapping("/api")
public class AuthController {

    private final AuthService authService;
    private final AppPersistentTokenRememberMeServices rememberMeServices;
    private final SecurityContextLogoutHandler logoutHandler = new SecurityContextLogoutHandler();

    /** Auth iş kurallarını saklar. */
    public AuthController(AuthService authService, AppPersistentTokenRememberMeServices rememberMeServices) {
        this.authService = authService;
        this.rememberMeServices = rememberMeServices;
    }

    /** Kayıt formunda seçilebilecek sınıfları döndürür. */
    @GetMapping("/auth/register-options")
    public RegisterOptionsResponse registerOptions() {
        return authService.registerOptions();
    }

    /** Yeni öğrenci hesabı oluşturur ve oturumunu açar. */
    @PostMapping("/auth/register")
    public ResponseEntity<MeResponse> register(
            @Valid @RequestBody RegisterRequest request,
            HttpServletRequest servletRequest,
            HttpServletResponse servletResponse) {
        return ResponseEntity.status(HttpStatus.CREATED)
                .body(authService.register(request, servletRequest, servletResponse));
    }

    /** Öğrencinin kimlik bilgilerini doğrulayıp oturum açar. */
    @PostMapping("/auth/login")
    public MeResponse login(
            @Valid @RequestBody LoginRequest request,
            HttpServletRequest servletRequest,
            HttpServletResponse servletResponse) {
        return authService.login(request, servletRequest, servletResponse);
    }

    /** Mevcut sunucu oturumunu kapatır. */
    @PostMapping("/auth/logout")
    public ResponseEntity<Void> logout(HttpServletRequest request, HttpServletResponse response) {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        rememberMeServices.logout(request, response, authentication);
        logoutHandler.logout(request, response, authentication);
        return ResponseEntity.noContent().build();
    }

    /** Giriş yapmış kullanıcının profilini döndürür. */
    @GetMapping("/me")
    public MeResponse me(@AuthenticationPrincipal AuthUser authUser) {
        return authService.findMe(authUser);
    }
}
