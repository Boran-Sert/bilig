package com.hataanalizi.core.tutor.dto;

import io.swagger.v3.oas.annotations.media.Schema;

/** Sorunun ipucunu taşır; doğru şık ve kazanımlar bu yanıtta yer almaz. */
public record HintResponse(
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED) String hint) {}
