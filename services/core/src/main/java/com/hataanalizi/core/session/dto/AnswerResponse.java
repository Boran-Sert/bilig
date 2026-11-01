package com.hataanalizi.core.session.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import java.util.List;

/** Cevap doğruluğunu, doğru şıkkı ve sorunun kazanımlarını taşır. */
public record AnswerResponse(
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED) boolean isCorrect,
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED) String correctOption,
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED) List<Outcome> outcomes) {

    /** Kazanımın kodunu ve başlığını taşır. */
    public record Outcome(
            @Schema(requiredMode = Schema.RequiredMode.REQUIRED)
            String code,

            @Schema(requiredMode = Schema.RequiredMode.REQUIRED)
            String title) {}
}
