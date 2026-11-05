package com.hataanalizi.core.question.dto;

import com.hataanalizi.core.question.Question;
import com.hataanalizi.core.session.dto.QuestionContent;
import io.swagger.v3.oas.annotations.media.Schema;
import tools.jackson.databind.ObjectMapper;

/** Benzer soruyu taşır; doğru şık ve kazanımlar bu yanıtta yer almaz. */
public record SimilarQuestionResponse(
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED) Long questionId,
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED) QuestionContent content) {

    /** Sorudan sadece kökü, ortak parçayı ve şıkları taşıyan yanıt oluşturur. */
    public static SimilarQuestionResponse from(Question question, ObjectMapper objectMapper) {
        return new SimilarQuestionResponse(
                question.getId(), objectMapper.convertValue(question.getContent(), QuestionContent.class));
    }
}
