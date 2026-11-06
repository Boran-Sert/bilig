package com.hataanalizi.core.session.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import java.util.List;

/** Tamamlanmış oturumdaki soruları doğru şık, öğrenci cevabı ve kazanımlarıyla taşır. */
public record SessionReviewResponse(
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED) List<ReviewQuestion> questions) {

    /** Soru içeriğini, öğrencinin cevabını, doğru şıkkı ve kazanımları taşır. */
    public record ReviewQuestion(
            @Schema(requiredMode = Schema.RequiredMode.REQUIRED)
            Long id,

            @Schema(requiredMode = Schema.RequiredMode.REQUIRED)
            short position,

            @Schema(requiredMode = Schema.RequiredMode.REQUIRED)
            QuestionContent content,

            @Schema(requiredMode = Schema.RequiredMode.REQUIRED, nullable = true)
            String selectedOption,

            @Schema(requiredMode = Schema.RequiredMode.REQUIRED)
            String correctOption,

            @Schema(requiredMode = Schema.RequiredMode.REQUIRED, nullable = true)
            Boolean isCorrect,

            @Schema(requiredMode = Schema.RequiredMode.REQUIRED)
            List<AnswerResponse.Outcome> outcomes) {}
}
