package com.hataanalizi.core.auth;

import java.security.Principal;

/** Giriş yapmış kullanıcıyı güvenlik bağlamında temsil eder. */
public record AuthUser(Long id, String email, String role) implements Principal {

    /** E-posta adresini güvenlik principal adı olarak döndürür. */
    @Override
    public String getName() {
        return email;
    }
}
