package com.hataanalizi.core.session.dto;

import io.swagger.v3.oas.annotations.media.Schema;

/** Soru içeriğini ve öğrencinin varsa seçimini doğru cevaptan bağımsız taşır. */
public record SessionQuestionResponse(
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED) Long id,
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED) short position,
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED) QuestionContent content,

        @Schema(requiredMode = Schema.RequiredMode.REQUIRED, nullable = true)
        String selectedOption) {}
