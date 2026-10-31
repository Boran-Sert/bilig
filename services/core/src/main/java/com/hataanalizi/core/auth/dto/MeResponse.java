package com.hataanalizi.core.auth.dto;

import com.hataanalizi.core.auth.AppUser;
import com.hataanalizi.core.auth.AppUserPrincipal;
import io.swagger.v3.oas.annotations.media.Schema;

/** Giriş yapmış kullanıcının gizli olmayan profil bilgilerini taşır. */
public record MeResponse(
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED) Long id,
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED) String email,
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED) String displayName,
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED) String role,

        @Schema(requiredMode = Schema.RequiredMode.REQUIRED, nullable = true)
        Short grade,

        @Schema(requiredMode = Schema.RequiredMode.REQUIRED) String explainStyle) {

    /** Kullanıcı varlığından parola içermeyen yanıtı üretir. */
    public static MeResponse from(AppUser appUser) {
        return new MeResponse(
                appUser.getId(),
                appUser.getEmail(),
                appUser.getDisplayName(),
                appUser.getRole(),
                appUser.getGrade(),
                appUser.getExplainStyle());
    }

    /** Kimlik doğrulama sırasında yüklenen kullanıcıdan parola içermeyen yanıtı üretir. */
    public static MeResponse from(AppUserPrincipal principal) {
        return new MeResponse(
                principal.id(),
                principal.email(),
                principal.displayName(),
                principal.role(),
                principal.grade(),
                principal.explainStyle());
    }
}
