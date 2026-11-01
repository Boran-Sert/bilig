package com.hataanalizi.core.session.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import java.math.BigDecimal;
import java.util.List;

/** Tamamlanan testin puanını ve kazanım bazlı yanlış özetini taşır. */
public record SessionCompletionResponse(
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED) long correct,
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED) long wrong,
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED) long blank,
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED) BigDecimal net,
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED) List<SessionCompletionOutcome> outcomes) {

    /** Bir kazanımın testteki yanlış sayısını ve başarısızlık durumunu taşır. */
    public record SessionCompletionOutcome(
            @Schema(requiredMode = Schema.RequiredMode.REQUIRED)
            String code,

            @Schema(requiredMode = Schema.RequiredMode.REQUIRED)
            String title,

            @Schema(requiredMode = Schema.RequiredMode.REQUIRED)
            long wrong,

            @Schema(requiredMode = Schema.RequiredMode.REQUIRED)
            boolean failed) {}
}
