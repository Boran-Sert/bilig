package com.hataanalizi.core.session.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import java.util.List;

/** Devam eden test oturumunu ve sıralı sorularını taşır. */
public record SessionResponse(
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED) Long sessionId,
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED) short currentPosition,
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED) List<SessionQuestionResponse> questions) {}
