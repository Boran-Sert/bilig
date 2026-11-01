package com.hataanalizi.core.common;

import io.swagger.v3.oas.annotations.media.Schema;
import java.util.List;

/**
 * Sayfalı listelerin ortak cevap biçimidir: {items, page, size, total}. Sayfa numarası 0'dan başlar,
 * total bütün kayıtların sayısıdır.
 */
public record PageResponse<T>(
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED) List<T> items,
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED) int page,
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED) int size,
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED) long total) {}
