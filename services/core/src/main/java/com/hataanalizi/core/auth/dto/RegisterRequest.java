package com.hataanalizi.core.auth.dto;

import com.hataanalizi.core.common.AppConstants;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.AssertTrue;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
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

        @Schema(requiredMode = Schema.RequiredMode.REQUIRED)
        @NotNull(message = "{validation.grade.required}")
        @Min(value = AppConstants.MIN_GRADE, message = "{validation.grade.required}")
        @Max(value = AppConstants.GRADUATE_GRADE, message = "{validation.grade.required}")
        Short grade,

        @Pattern(regexp = AppConstants.EXPLAIN_STYLE_PATTERN, message = "{validation.explainStyle.invalid}")
        String explainStyle,

        @Schema(requiredMode = Schema.RequiredMode.REQUIRED)
        @NotNull(message = "{validation.privacyNotice.required}")
        @AssertTrue(message = "{validation.privacyNotice.required}")
        Boolean privacyNoticeAccepted,

        @Schema(requiredMode = Schema.RequiredMode.REQUIRED)
        @NotNull(message = "{validation.consent.required}")
        @AssertTrue(message = "{validation.consent.required}")
        Boolean consentAccepted) {

    /** BCrypt sınırını aşan UTF-8 parola uzunluğunu reddeder. */
    @AssertTrue(message = "{validation.password.bytes}")
    public boolean isPasswordWithinBcryptLimit() {
        return password == null || password.getBytes(StandardCharsets.UTF_8).length <= AppConstants.MAX_PASSWORD_BYTES;
    }
}
