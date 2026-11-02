package com.hataanalizi.core.dashboard.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import java.math.BigDecimal;
import java.util.List;

/** Öğrencinin test, kazanım ve hata türü panelini taşır. */
public record DashboardResponse(
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED) Summary summary,
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED) List<ActiveSession> activeSessions,
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED) List<FailedOutcome> failedOutcomes,
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED) List<UnitAccuracy> unitAccuracy,
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED) List<ErrorTypeCount> errorTypeDistribution) {

    /** Genel cevap başarısını ve son tamamlanan test netini taşır. */
    public record Summary(
            @Schema(requiredMode = Schema.RequiredMode.REQUIRED)
            long answeredQuestionCount,

            @Schema(requiredMode = Schema.RequiredMode.REQUIRED)
            BigDecimal accuracyPercent,

            @Schema(requiredMode = Schema.RequiredMode.REQUIRED, nullable = true)
            BigDecimal latestNet,

            @Schema(requiredMode = Schema.RequiredMode.REQUIRED, nullable = true)
            Long latestQuestionCount) {}

    /** Devam eden testin öğrenci ilerlemesini taşır. */
    public record ActiveSession(
            @Schema(requiredMode = Schema.RequiredMode.REQUIRED)
            Long sessionId,

            @Schema(requiredMode = Schema.RequiredMode.REQUIRED)
            String examTitle,

            @Schema(requiredMode = Schema.RequiredMode.REQUIRED)
            long questionCount,

            @Schema(requiredMode = Schema.RequiredMode.REQUIRED)
            long answeredCount,

            @Schema(requiredMode = Schema.RequiredMode.REQUIRED)
            short currentPosition) {}

    /** Başarısız kazanımın toplam ve son test yanlışlarını taşır. */
    public record FailedOutcome(
            @Schema(requiredMode = Schema.RequiredMode.REQUIRED)
            String code,

            @Schema(requiredMode = Schema.RequiredMode.REQUIRED)
            String title,

            @Schema(requiredMode = Schema.RequiredMode.REQUIRED)
            long totalWrongCount,

            @Schema(requiredMode = Schema.RequiredMode.REQUIRED, nullable = true)
            String testTitle,

            @Schema(requiredMode = Schema.RequiredMode.REQUIRED, nullable = true)
            Long testWrongCount) {}

    /** Ünite bazlı doğru cevap oranını taşır. */
    public record UnitAccuracy(
            @Schema(requiredMode = Schema.RequiredMode.REQUIRED)
            String unitTitle,

            @Schema(requiredMode = Schema.RequiredMode.REQUIRED)
            long answeredCount,

            @Schema(requiredMode = Schema.RequiredMode.REQUIRED)
            long correctCount,

            @Schema(requiredMode = Schema.RequiredMode.REQUIRED)
            BigDecimal accuracyPercent) {}

    /** Sınıflandırılmış hata türü ve cevap sayısını taşır. */
    public record ErrorTypeCount(
            @Schema(requiredMode = Schema.RequiredMode.REQUIRED)
            String errorType,

            @Schema(requiredMode = Schema.RequiredMode.REQUIRED)
            long answerCount) {}
}
