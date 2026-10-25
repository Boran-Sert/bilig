package com.hataanalizi.core.common;

/**
 * Servislerin bilinen bir iş hatasını bildirmek için fırlattığı istisnadır. Hata kodunu ve Türkçe
 * metindeki {0}, {1} gibi yerlere girecek argümanları taşır; cevaba GlobalExceptionHandler çevirir.
 */
public class ApiException extends RuntimeException {

    private final ErrorCode errorCode;
    private final Object[] messageArguments;

    public ApiException(ErrorCode errorCode, Object... messageArguments) {
        super(errorCode.name());
        this.errorCode = errorCode;
        this.messageArguments = messageArguments.clone();
    }

    /** Hatanın kodunu döndürür. */
    public ErrorCode getErrorCode() {
        return errorCode;
    }

    /** Hata metnine girecek argümanların bir kopyasını döndürür. */
    public Object[] getMessageArguments() {
        return messageArguments.clone();
    }
}
