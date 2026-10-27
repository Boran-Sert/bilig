package com.hataanalizi.core.auth;

import java.util.List;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContext;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.test.context.support.WithSecurityContextFactory;

/** Test annotation'ındaki kullanıcı bilgisinden Spring Security bağlamı üretir. */
public class WithAuthUserSecurityContextFactory implements WithSecurityContextFactory<WithAuthUser> {

    /** Kullanıcıyı belirtilen rol yetkisiyle doğrulanmış hale getirir. */
    @Override
    public SecurityContext createSecurityContext(WithAuthUser annotation) {
        SecurityContext context = SecurityContextHolder.createEmptyContext();
        AuthUser user = new AuthUser(annotation.id(), annotation.email(), annotation.role());
        UsernamePasswordAuthenticationToken authentication = new UsernamePasswordAuthenticationToken(
                user, "test", List.of(new SimpleGrantedAuthority("ROLE_" + annotation.role())));
        context.setAuthentication(authentication);
        return context;
    }
}
