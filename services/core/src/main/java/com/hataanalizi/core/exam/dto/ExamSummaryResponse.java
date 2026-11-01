package com.hataanalizi.core.exam.dto;

import io.swagger.v3.oas.annotations.media.Schema;

/** Öğrenciye gösterilecek test ve son oturum ilerlemesini taşır. */
public record ExamSummaryResponse(
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED) Long id,
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED) String title,
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED) long questionCount,
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED) long answeredCount,

        @Schema(requiredMode = Schema.RequiredMode.REQUIRED, nullable = true)
        Long sessionId,

        @Schema(requiredMode = Schema.RequiredMode.REQUIRED, nullable = true)
        String status) {}
