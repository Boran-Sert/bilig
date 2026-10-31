package com.hataanalizi.core.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;

/** Kullanıcı parolaları için BCrypt kodlayıcısını yapılandırır. */
@Configuration
public class PasswordEncoderConfig {

    /** BCrypt parola kodlayıcısını Spring'e sağlar. */
    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }
}
