package com.hataanalizi.core.session.dto;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import io.swagger.v3.oas.annotations.media.Schema;
import java.util.List;

/** Soru kökünü, ortak parçayı ve seçenekleri API şemasıyla tanımlar. */
@JsonIgnoreProperties(ignoreUnknown = true)
public record QuestionContent(
        @Schema(nullable = true) List<Block> passage, List<Block> stem, List<QuestionOption> options) {

    /** Soru içeriğindeki biçimlendirilmiş metin parçasını tanımlar. */
    @JsonIgnoreProperties(ignoreUnknown = true)
    public record Block(
            @Schema(allowableValues = {"paragraph", "table", "list", "numbered_items"})
            String type,

            String md) {}

    /** Soru seçeneğinin etiketini ve metin parçalarını tanımlar. */
    @JsonIgnoreProperties(ignoreUnknown = true)
    public record QuestionOption(
            @Schema(allowableValues = {"A", "B", "C", "D", "E"})
            String label,

            List<Block> blocks) {}
}
