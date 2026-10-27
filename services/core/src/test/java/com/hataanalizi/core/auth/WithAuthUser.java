package com.hataanalizi.core.auth;

import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;
import org.springframework.security.test.context.support.WithSecurityContext;

/** Testte belirtilen role sahip bir kullanıcıyla güvenlik bağlamı kurar. */
@Target({ElementType.METHOD, ElementType.TYPE})
@Retention(RetentionPolicy.RUNTIME)
@WithSecurityContext(factory = WithAuthUserSecurityContextFactory.class)
public @interface WithAuthUser {

    /** Test kullanıcısının rolünü döndürür. */
    String role() default "STUDENT";

    /** Test kullanıcısının kimliğini döndürür. */
    long id() default 1L;

    /** Test kullanıcısının e-posta adresini döndürür. */
    String email() default "student@example.test";
}
