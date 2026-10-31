package com.hataanalizi.core.exam.dto;

import io.swagger.v3.oas.annotations.media.Schema;

/** Öğrenciye gösterilecek test ve son oturum ilerlemesini taşır. */
public record ExamSummaryResponse(
        Long id,
        String title,
        long questionCount,
        long answeredCount,
        @Schema(nullable = true) Long sessionId,
        @Schema(nullable = true) String status) {}
