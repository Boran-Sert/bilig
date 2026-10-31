package com.hataanalizi.core.auth.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;

/** Oturum açmak için gereken kullanıcı bilgilerini taşır. */
public record LoginRequest(
        @NotBlank(message = "{validation.email.required}") @Email(message = "{validation.email.invalid}")
        String email,

        @NotBlank(message = "{validation.password.required}")
        String password) {}
