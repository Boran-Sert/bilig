package com.hataanalizi.core.auth.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;

/** Oturum açmak için gereken kullanıcı bilgilerini taşır. */
public record LoginRequest(
        @NotBlank @Email String email, @NotBlank String password, boolean rememberMe) {}
