package com.hataanalizi.core.admin.dto;

import java.time.Instant;
import java.util.List;
import tools.jackson.databind.JsonNode;

/** İnceleme kaydını hedef içerik ve mevcut kazanımlarıyla taşır. */
public record ReviewItemResponse(
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED) Long id,
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED) String reason,
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED) TargetType targetType,
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED) Long targetId,

        @Schema(
                requiredMode = Schema.RequiredMode.REQUIRED,
                implementation = Object.class,
                types = {"object", "null"},
                additionalProperties = Schema.AdditionalPropertiesValue.TRUE)
        JsonNode questionContent,

        @Schema(requiredMode = Schema.RequiredMode.REQUIRED, nullable = true)
        String blockMarkdown,

        @Schema(requiredMode = Schema.RequiredMode.REQUIRED, nullable = true)
        String sourceTitle,

        @Schema(requiredMode = Schema.RequiredMode.REQUIRED, nullable = true)
        Long pageId,

        @Schema(requiredMode = Schema.RequiredMode.REQUIRED, nullable = true)
        Integer pageNo,

        @Schema(requiredMode = Schema.RequiredMode.REQUIRED) List<OutcomeLink> outcomes,
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED) Instant createdAt) {

    /** İncelemenin soru veya paragraf hedefini tanımlar. */
    public enum TargetType {
        QUESTION,
        BLOCK
    }

    /** Hedefe bağlı kazanımı ve eşleştirme kaynağını taşır. */
    public record OutcomeLink(
            @Schema(requiredMode = Schema.RequiredMode.REQUIRED)
            Long id,

            @Schema(requiredMode = Schema.RequiredMode.REQUIRED)
            String code,

            @Schema(requiredMode = Schema.RequiredMode.REQUIRED)
            String title,

            @Schema(requiredMode = Schema.RequiredMode.REQUIRED)
            String mappedBy) {}
}
