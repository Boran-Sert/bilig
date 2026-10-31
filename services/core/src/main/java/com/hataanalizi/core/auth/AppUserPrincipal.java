package com.hataanalizi.core.auth;

import com.hataanalizi.core.common.AppConstants;
import java.util.Collection;
import java.util.List;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.userdetails.UserDetails;

/** Kimlik doğrulama sırasında yüklenen kullanıcı verisini taşır. */
public record AppUserPrincipal(
        Long id, String email, String passwordHash, String displayName, String role, Short grade, String explainStyle)
        implements UserDetails {

    /** Kullanıcının rol yetkisini döndürür. */
    @Override
    public Collection<? extends GrantedAuthority> getAuthorities() {
        return List.of(new SimpleGrantedAuthority(AppConstants.ROLE_PREFIX + role));
    }

    /** Doğrulama için saklanan parola özetini döndürür. */
    @Override
    public String getPassword() {
        return passwordHash;
    }

    /** Kimlik doğrulamasında kullanıcı adı olarak e-postayı döndürür. */
    @Override
    public String getUsername() {
        return email;
    }

    /** Hesabın süresinin dolmadığını bildirir. */
    @Override
    public boolean isAccountNonExpired() {
        return true;
    }

    /** Hesabın kilitli olmadığını bildirir. */
    @Override
    public boolean isAccountNonLocked() {
        return true;
    }

    /** Kimlik bilgilerinin süresinin dolmadığını bildirir. */
    @Override
    public boolean isCredentialsNonExpired() {
        return true;
    }

    /** Hesabın etkin olduğunu bildirir. */
    @Override
    public boolean isEnabled() {
        return true;
    }

    /** Parola özetini metinsel gösterime eklemez. */
    @Override
    public String toString() {
        return "AppUserPrincipal";
    }
}
