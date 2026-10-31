package com.hataanalizi.core.auth.dto;

import com.hataanalizi.core.common.AppConstants;
import jakarta.validation.constraints.AssertTrue;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import java.nio.charset.StandardCharsets;

/** Öğrenci hesabı oluşturmak için gereken bilgileri taşır. */
public record RegisterRequest(
        @NotBlank(message = "{validation.email.required}") @Email(message = "{validation.email.invalid}")
        String email,

        @NotBlank(message = "{validation.password.required}")
        @Size(
                min = AppConstants.MIN_PASSWORD_LENGTH,
                max = AppConstants.MAX_PASSWORD_LENGTH,
                message = "{validation.password.length}")
        String password,

        @NotBlank(message = "{validation.displayName.required}")
        String displayName,

        Short grade,

        @Pattern(regexp = AppConstants.EXPLAIN_STYLE_PATTERN, message = "{validation.explainStyle.invalid}")
        String explainStyle) {

    /** BCrypt sınırını aşan UTF-8 parola uzunluğunu reddeder. */
    @AssertTrue(message = "{validation.password.bytes}")
    public boolean isPasswordWithinBcryptLimit() {
        return password == null || password.getBytes(StandardCharsets.UTF_8).length <= AppConstants.MAX_PASSWORD_BYTES;
    }
}
