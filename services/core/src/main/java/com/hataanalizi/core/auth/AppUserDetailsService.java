package com.hataanalizi.core.auth;

import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.core.userdetails.UsernameNotFoundException;
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
        AppUser appUser =
                appUserRepository.findByEmail(email).orElseThrow(() -> new UsernameNotFoundException("User not found"));
        return new AppUserPrincipal(
                appUser.getId(),
                appUser.getEmail(),
                appUser.getPasswordHash() == null ? "" : appUser.getPasswordHash(),
                appUser.getDisplayName(),
                appUser.getRole(),
                appUser.getGrade(),
                appUser.getExplainStyle());
    }
}
