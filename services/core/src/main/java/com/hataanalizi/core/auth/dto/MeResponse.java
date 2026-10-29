package com.hataanalizi.core.auth.dto;

import com.hataanalizi.core.auth.AppUser;

/** Giriş yapmış kullanıcının gizli olmayan profil bilgilerini taşır. */
public record MeResponse(Long id, String email, String displayName, String role, Short grade, String explainStyle) {

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
}
