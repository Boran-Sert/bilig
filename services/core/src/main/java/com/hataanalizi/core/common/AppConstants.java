package com.hataanalizi.core.common;

import java.util.List;

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
    public static final List<String> CONTENT_MANAGER_ROLES = List.of(CONTENT_ADMIN_ROLE, ADMIN_ROLE);
    public static final String DEFAULT_TENANT_NAME = "Bilig";
    public static final String DEFAULT_EXPLAIN_STYLE = "SIMPLE";
    public static final int MIN_GRADE = 9;
    public static final int GRADUATE_GRADE = 13;
    public static final String PRIVACY_NOTICE_VERSION = "2026-11-02";
    public static final String CONSENT_VERSION = "2026-11-02";
    public static final String EXPLAIN_STYLE_PATTERN = "SIMPLE|EXAMPLES|STEP_BY_STEP";
    public static final String REMEMBER_ME_COOKIE_NAME = "remember-me";
    public static final String APP_USER_EMAIL_UNIQUE_CONSTRAINT = "app_user_email_key";
    public static final int MIN_PASSWORD_LENGTH = 8;
    public static final int MAX_PASSWORD_LENGTH = 72;
    public static final int MAX_PASSWORD_BYTES = 72;

    // sınav
    public static final String EXAM_STATUS_PUBLISHED = "PUBLISHED";

    // soru
    public static final String QUESTION_STATUS_PUBLISHED = "PUBLISHED";
    public static final String QUESTION_STATUS_DRAFT = "DRAFT";
    public static final String QUESTION_STATUS_REJECTED = "REJECTED";

    // oturum
    public static final String SESSION_STATUS_IN_PROGRESS = "IN_PROGRESS";
    public static final String SESSION_STATUS_COMPLETED = "COMPLETED";
    public static final String ANSWER_OPTION_PATTERN = "A|B|C|D|E";
    public static final int MAX_WRONG_PER_TEST = 2;
    public static final int MAX_WRONG_TOTAL = 5;

    // kaynak
    public static final String DEFAULT_SOURCE_PAGE_SIZE = "20";
    public static final int MAX_SOURCE_PAGE_SIZE = 100;

    // iş

    // inceleme
    public static final String REVIEW_REASON_LOW_CONFIDENCE = "LOW_CONFIDENCE";
    public static final String REVIEW_STATUS_OPEN = "OPEN";
    public static final String REVIEW_STATUS_APPROVED = "APPROVED";
    public static final String REVIEW_STATUS_REJECTED = "REJECTED";
    public static final String CONTENT_BLOCK_STATUS_DRAFT = "DRAFT";
    public static final String CONTENT_BLOCK_STATUS_PUBLISHED = "PUBLISHED";
    public static final String CONTENT_BLOCK_STATUS_REJECTED = "REJECTED";
    public static final String OUTCOME_MAPPED_BY_HUMAN = "HUMAN";

    // sohbet

    private AppConstants() {}
}
