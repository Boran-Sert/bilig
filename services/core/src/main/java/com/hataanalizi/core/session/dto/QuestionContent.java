package com.hataanalizi.core.session.dto;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import io.swagger.v3.oas.annotations.media.Schema;
import java.util.List;

/** Soru kökünü, ortak parçayı ve seçenekleri API şemasıyla tanımlar. */
@JsonIgnoreProperties(ignoreUnknown = true)
public record QuestionContent(
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED, nullable = true)
        List<Block> passage,

        @Schema(requiredMode = Schema.RequiredMode.REQUIRED) List<Block> stem,
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED) List<QuestionOption> options) {

    /** Soru içeriğindeki biçimlendirilmiş metin parçasını tanımlar. */
    @JsonIgnoreProperties(ignoreUnknown = true)
    public record Block(
            @Schema(
                    requiredMode = Schema.RequiredMode.REQUIRED,
                    allowableValues = {"paragraph", "table", "list", "numbered_items"})
            String type,

            @Schema(requiredMode = Schema.RequiredMode.REQUIRED)
            String md) {}

    /** Soru seçeneğinin etiketini ve metin parçalarını tanımlar. */
    @JsonIgnoreProperties(ignoreUnknown = true)
    public record QuestionOption(
            @Schema(
                    requiredMode = Schema.RequiredMode.REQUIRED,
                    allowableValues = {"A", "B", "C", "D", "E"})
            String label,

            @Schema(requiredMode = Schema.RequiredMode.REQUIRED)
            List<Block> blocks) {}
}
