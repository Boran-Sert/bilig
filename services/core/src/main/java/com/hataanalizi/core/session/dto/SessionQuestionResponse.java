package com.hataanalizi.core.session.dto;

import io.swagger.v3.oas.annotations.media.Schema;

/** Soru içeriğini ve öğrencinin varsa seçimini doğru cevaptan bağımsız taşır. */
public record SessionQuestionResponse(
        Long id,
        short position,
        QuestionContent content,
        @Schema(nullable = true) String selectedOption) {}
