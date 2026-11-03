package com.hataanalizi.core.admin.dto;

import java.util.List;

/** İnceleme kaydına verilecek kararı ve isteğe bağlı kazanımları taşır. */
public record ReviewDecisionRequest(Decision decision, List<Long> outcomeIds) {

    /** İnceleme kaydında kullanılabilen kararları tanımlar. */
    public enum Decision {
        APPROVE,
        FIX,
        REJECT
    }
}
