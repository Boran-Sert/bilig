package com.hataanalizi.core.session.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import tools.jackson.databind.JsonNode;

/** Soru içeriğini ve öğrencinin varsa seçimini doğru cevaptan bağımsız taşır. */
public record SessionQuestionResponse(
        Long id,
        short position,
        @Schema(implementation = QuestionContent.class) JsonNode content,
        @Schema(nullable = true) String selectedOption) {}
