package com.hataanalizi.core.common;

import org.springframework.http.HttpStatus;

/**
 * Bütün API hata kodlarını ve her kodun HTTP durumunu tutar. Herkes kendi kodunu kendi bölümüne
 * ekler; kodun Türkçe metni messages_tr.properties dosyasında aynı bölümde {@code error.<KOD>}
 * anahtarıyla durur.
 */
public enum ErrorCode {

    // genel
    VALIDATION_FAILED(HttpStatus.BAD_REQUEST),
    NOT_FOUND(HttpStatus.NOT_FOUND),
    INTERNAL_ERROR(HttpStatus.INTERNAL_SERVER_ERROR),
    AI_UNAVAILABLE(HttpStatus.SERVICE_UNAVAILABLE),

    // auth
    AUTH_REQUIRED(HttpStatus.UNAUTHORIZED),
    ACCESS_DENIED(HttpStatus.FORBIDDEN),

// sınav

// oturum

// kaynak

// iş

// inceleme

// sohbet
;

    private final HttpStatus status;

    ErrorCode(HttpStatus status) {
        this.status = status;
    }

    /** Bu hata kodunun HTTP durumunu döndürür. */
    public HttpStatus getStatus() {
        return status;
    }

    /** Bu hata kodunun messages_tr.properties içindeki anahtarını döndürür. */
    public String messageKey() {
        return "error." + name();
    }
}
