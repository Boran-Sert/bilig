package com.hataanalizi.core.admin.dto;

import com.hataanalizi.core.admin.IngestStep;
import com.hataanalizi.core.admin.SourceKind;
import com.hataanalizi.core.admin.SourceStatus;
import io.swagger.v3.oas.annotations.media.Schema;
import java.time.Instant;

/** Kaynak listesinde dosya bilgisini ve hazırlık ilerlemesini taşır. */
public record SourceListItem(
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED) Long sourceId,
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED) String fileName,
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED) SourceKind kind,
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED) SourceStatus status,

        @Schema(requiredMode = Schema.RequiredMode.REQUIRED, nullable = true)
        IngestStep lastCompletedStep,

        @Schema(requiredMode = Schema.RequiredMode.REQUIRED) int stepIndex,
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED) int totalSteps,

        @Schema(requiredMode = Schema.RequiredMode.REQUIRED, nullable = true)
        String error,

        @Schema(requiredMode = Schema.RequiredMode.REQUIRED) Instant createdAt) {}
