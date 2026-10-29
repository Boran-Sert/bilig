package com.hataanalizi.core.auth;

import java.util.Locale;
import org.springframework.context.annotation.Bean;
import org.springframework.security.core.userdetails.User;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.core.userdetails.UsernameNotFoundException;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;

/** E-posta adresine göre giriş bilgilerini ve kullanıcı principal'ını yükler. */
@Service
public class AppUserDetailsService implements UserDetailsService {

    private final AppUserRepository appUserRepository;

    /** Kullanıcı kayıt deposunu saklar. */
    public AppUserDetailsService(AppUserRepository appUserRepository) {
        this.appUserRepository = appUserRepository;
    }

    /** Spring Security için e-posta adresinden kullanıcı bilgilerini döndürür. */
    @Override
    public UserDetails loadUserByUsername(String email) throws UsernameNotFoundException {
        AppUser appUser = appUserRepository
                .findByEmail(normalizeEmail(email))
                .orElseThrow(() -> new UsernameNotFoundException("User not found"));
        String passwordHash = appUser.getPasswordHash() == null ? "" : appUser.getPasswordHash();
        return User.withUsername(appUser.getEmail())
                .password(passwordHash)
                .authorities("ROLE_" + appUser.getRole())
                .build();
    }

    /** Giriş yapmış kullanıcıyı oturumlarda kullanılacak principal'a dönüştürür. */
    public AuthUser loadAuthUserByEmail(String email) {
        AppUser appUser = appUserRepository
                .findByEmail(normalizeEmail(email))
                .orElseThrow(() -> new UsernameNotFoundException("User not found"));
        return new AuthUser(appUser.getId(), appUser.getEmail(), appUser.getRole());
    }

    /** BCrypt parola doğrulayıcısını Spring'e sağlar. */
    @Bean
    public static PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }

    /** E-posta adresini kök yerel ayara göre normalize eder. */
    public String normalizeEmail(String email) {
        return email.toLowerCase(Locale.ROOT);
    }
}
