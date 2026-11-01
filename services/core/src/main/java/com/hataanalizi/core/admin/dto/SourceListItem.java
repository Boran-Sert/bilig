package com.hataanalizi.core.admin.dto;

import com.hataanalizi.core.admin.IngestStep;
import com.hataanalizi.core.admin.SourceKind;
import com.hataanalizi.core.admin.SourceStatus;
import java.time.Instant;

/** Kaynak listesinde dosya bilgisini ve hazırlık ilerlemesini taşır. */
public record SourceListItem(
        Long sourceId,
        String fileName,
        SourceKind kind,
        SourceStatus status,
        IngestStep lastCompletedStep,
        int stepIndex,
        int totalSteps,
        String error,
        Instant createdAt) {}
