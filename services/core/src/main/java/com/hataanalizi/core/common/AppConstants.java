package com.hataanalizi.core.common;

/**
 * Değişmeyen uygulama sabitlerini özellik bölümlerine göre tutar. Ortama göre değişen değerler
 * buraya değil application.yml dosyasına yazılır.
 */
public final class AppConstants {

    // genel

    // auth
    public static final String ROLE_PREFIX = "ROLE_";
    public static final String STUDENT_ROLE = "STUDENT";
    public static final String CONTENT_ADMIN_ROLE = "CONTENT_ADMIN";
    public static final String ADMIN_ROLE = "ADMIN";
    public static final String DEFAULT_TENANT_NAME = "Bilig";
    public static final String DEFAULT_EXPLAIN_STYLE = "SIMPLE";
    public static final String EXPLAIN_STYLE_PATTERN = "SIMPLE|EXAMPLES|STEP_BY_STEP";
    public static final int MIN_PASSWORD_LENGTH = 8;
    public static final int MAX_PASSWORD_LENGTH = 72;
    public static final int MAX_PASSWORD_BYTES = 72;

    // sınav

    // oturum
    public static final int MAX_WRONG_PER_TEST = 2;
    public static final int MAX_WRONG_TOTAL = 5;

    // kaynak

    // iş

    // inceleme

    // sohbet

    private AppConstants() {}
}
