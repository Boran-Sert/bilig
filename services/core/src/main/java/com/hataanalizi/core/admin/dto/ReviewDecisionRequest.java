package com.hataanalizi.core.admin.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import java.util.List;

/** İnceleme kaydına verilecek kararı ve isteğe bağlı kazanımları taşır. */
public record ReviewDecisionRequest(
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED) Decision decision, List<Long> outcomeIds) {

    /** İnceleme kaydında kullanılabilen kararları tanımlar. */
    public enum Decision {
        APPROVE,
        FIX,
        REJECT
    }
}
