package com.hataanalizi.core.auth.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;

/** Öğrenci hesabı oluşturmak için gereken bilgileri taşır. */
public record RegisterRequest(
        @NotBlank @Email String email,
        @NotBlank String password,
        @NotBlank String displayName,
        Short grade,
        @Pattern(regexp = "SIMPLE|EXAMPLES|STEP_BY_STEP") String explainStyle) {}
