package com.hataanalizi.core.admin.dto;

import io.swagger.v3.oas.annotations.media.Schema;

/** Kazanım seçicisinde gösterilecek kazanımı taşır. */
public record ReviewOutcomeResponse(
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED) Long id,
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED) String code,
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED) String title) {}
