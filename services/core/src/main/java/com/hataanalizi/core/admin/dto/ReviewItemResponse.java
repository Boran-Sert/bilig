package com.hataanalizi.core.admin.dto;

import java.time.Instant;
import java.util.List;
import tools.jackson.databind.JsonNode;

/** İnceleme kaydını hedef içerik ve mevcut kazanımlarıyla taşır. */
public record ReviewItemResponse(
        Long id,
        String reason,
        TargetType targetType,
        Long targetId,
        JsonNode questionContent,
        String blockMarkdown,
        String sourceTitle,
        Long pageId,
        Integer pageNo,
        List<OutcomeLink> outcomes,
        Instant createdAt) {

    /** İncelemenin soru veya paragraf hedefini tanımlar. */
    public enum TargetType {
        QUESTION,
        BLOCK
    }

    /** Hedefe bağlı kazanımı ve eşleştirme kaynağını taşır. */
    public record OutcomeLink(Long id, String code, String title, String mappedBy) {}
}
