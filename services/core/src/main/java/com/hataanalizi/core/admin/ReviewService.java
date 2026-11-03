package com.hataanalizi.core.admin;

import com.hataanalizi.core.admin.dto.ReviewDecisionRequest;
import com.hataanalizi.core.admin.dto.ReviewDecisionRequest.Decision;
import com.hataanalizi.core.admin.dto.ReviewItemResponse;
import com.hataanalizi.core.admin.dto.ReviewItemResponse.OutcomeLink;
import com.hataanalizi.core.admin.dto.ReviewItemResponse.TargetType;
import com.hataanalizi.core.admin.dto.ReviewOutcomeResponse;
import com.hataanalizi.core.common.ApiException;
import com.hataanalizi.core.common.AppConstants;
import com.hataanalizi.core.common.ErrorCode;
import com.hataanalizi.core.common.PageResponse;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import org.springframework.jdbc.core.namedparam.MapSqlParameterSource;
import org.springframework.jdbc.core.namedparam.NamedParameterJdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

/** Açık kazanım incelemelerini listeler ve içerik kararlarını yönetir. */
@Service
public class ReviewService {

    private static final String REVIEW_LIST_QUERY = """
            SELECT review_item.id,
                   review_item.reason,
                   CASE WHEN review_item.question_id IS NOT NULL THEN 'QUESTION' ELSE 'BLOCK' END,
                   COALESCE(review_item.question_id, review_item.content_block_id),
                   question.content::text,
                   content_block.markdown,
                   source_document.title,
                   source_page.id,
                   source_page.page_no,
                   COALESCE(question_outcomes.items, block_outcomes.items, '[]'::jsonb)::text,
                   review_item.created_at
            FROM review_item
            LEFT JOIN question ON question.id = review_item.question_id
            LEFT JOIN content_block ON content_block.id = review_item.content_block_id
            LEFT JOIN source_page
                ON source_page.id = COALESCE(question.source_page_id, content_block.source_page_id)
            LEFT JOIN source_document ON source_document.id = source_page.source_document_id
            LEFT JOIN LATERAL (
                SELECT jsonb_agg(jsonb_build_object(
                    'id', learning_outcome.id,
                    'code', learning_outcome.code,
                    'title', learning_outcome.title,
                    'mappedBy', question_outcome.mapped_by
                ) ORDER BY learning_outcome.code, learning_outcome.id) AS items
                FROM question_outcome
                JOIN learning_outcome ON learning_outcome.id = question_outcome.learning_outcome_id
                WHERE question_outcome.question_id = review_item.question_id
            ) question_outcomes ON true
            LEFT JOIN LATERAL (
                SELECT jsonb_agg(jsonb_build_object(
                    'id', learning_outcome.id,
                    'code', learning_outcome.code,
                    'title', learning_outcome.title,
                    'mappedBy', content_block_outcome.mapped_by
                ) ORDER BY learning_outcome.code, learning_outcome.id) AS items
                FROM content_block_outcome
                JOIN learning_outcome
                    ON learning_outcome.id = content_block_outcome.learning_outcome_id
                WHERE content_block_outcome.content_block_id = review_item.content_block_id
            ) block_outcomes ON true
            WHERE review_item.status = 'OPEN' AND review_item.reason = 'LOW_CONFIDENCE'
            ORDER BY review_item.created_at, review_item.id
            LIMIT :size OFFSET :offset
            """;

    private static final String OUTCOME_LIST_QUERY = """
            SELECT id, code, title
            FROM learning_outcome
            ORDER BY code, id
            """;

    private static final String REVIEW_COUNT_QUERY = """
            SELECT count(*)
            FROM review_item
            WHERE status = 'OPEN' AND reason = 'LOW_CONFIDENCE'
            """;

    private static final String SELECT_OUTCOME_COUNT_QUERY = """
            SELECT count(*)
            FROM learning_outcome
            WHERE id IN (:outcomeIds)
            """;

    private static final String PUBLISH_QUESTION_QUERY = """
            UPDATE question SET status = 'PUBLISHED', updated_at = now()
            WHERE id = :targetId AND status = :draftStatus
            """;

    private static final String PUBLISH_BLOCK_QUERY = """
            UPDATE content_block SET status = 'PUBLISHED', updated_at = now()
            WHERE id = :targetId AND status = :draftStatus
            """;

    private static final String REJECT_QUESTION_QUERY = """
            UPDATE question SET status = 'REJECTED', updated_at = now()
            WHERE id = :targetId
            """;

    private static final String REJECT_BLOCK_QUERY = """
            UPDATE content_block SET status = 'REJECTED', updated_at = now()
            WHERE id = :targetId
            """;

    private static final String DELETE_QUESTION_OUTCOMES_QUERY = """
            DELETE FROM question_outcome WHERE question_id = :targetId
            """;

    private static final String DELETE_BLOCK_OUTCOMES_QUERY = """
            DELETE FROM content_block_outcome WHERE content_block_id = :targetId
            """;

    private static final String INSERT_QUESTION_OUTCOME_QUERY = """
            INSERT INTO question_outcome (question_id, learning_outcome_id, mapped_by)
            VALUES (:targetId, :outcomeId, 'HUMAN')
            """;

    private static final String INSERT_BLOCK_OUTCOME_QUERY = """
            INSERT INTO content_block_outcome (content_block_id, learning_outcome_id, mapped_by)
            VALUES (:targetId, :outcomeId, 'HUMAN')
            """;

    private static final String UPDATE_REVIEW_DECISION_QUERY = """
            UPDATE review_item
            SET status = :status, decided_by = :reviewerId, decided_at = now()
            WHERE id = :reviewId
            """;

    private final NamedParameterJdbcTemplate jdbcTemplate;
    private final ReviewItemRepository reviewItemRepository;
    private final ObjectMapper objectMapper;

    /** İnceleme sorguları ve JSON dönüştürücüsünü saklar. */
    public ReviewService(
            NamedParameterJdbcTemplate jdbcTemplate,
            ReviewItemRepository reviewItemRepository,
            ObjectMapper objectMapper) {
        this.jdbcTemplate = jdbcTemplate;
        this.reviewItemRepository = reviewItemRepository;
        this.objectMapper = objectMapper;
    }

    /** Açık düşük güvenli incelemeleri eskiden yeniye sayfalı döner. */
    @Transactional(readOnly = true)
    public PageResponse<ReviewItemResponse> listReviews(int page, int size) {
        validatePage(page, size);
        MapSqlParameterSource parameters =
                new MapSqlParameterSource().addValue("size", size).addValue("offset", (long) page * size);
        List<ReviewItemResponse> items =
                jdbcTemplate.query(REVIEW_LIST_QUERY, parameters, (result, rowNumber) -> mapReviewItem(result));
        Long total = jdbcTemplate.getJdbcTemplate().queryForObject(REVIEW_COUNT_QUERY, Long.class);
        return new PageResponse<>(items, page, size, total == null ? 0 : total);
    }

    /** Bütün kazanımları seçici için kod sırasıyla döner. */
    @Transactional(readOnly = true)
    public List<ReviewOutcomeResponse> listOutcomes() {
        return jdbcTemplate
                .getJdbcTemplate()
                .query(
                        OUTCOME_LIST_QUERY,
                        (result, rowNumber) -> new ReviewOutcomeResponse(
                                result.getLong("id"), result.getString("code"), result.getString("title")));
    }

    /** İnceleme kararını hedef, kazanım bağları ve kayıtla birlikte yazar. */
    @Transactional
    public void decideReview(long reviewId, long reviewerId, ReviewDecisionRequest request) {
        if (request == null || request.decision() == null) {
            throw new ApiException(ErrorCode.VALIDATION_FAILED);
        }
        ReviewItem reviewItem = reviewItemRepository
                .findByIdForUpdate(reviewId, AppConstants.REVIEW_REASON_LOW_CONFIDENCE)
                .orElseThrow(() -> new ApiException(ErrorCode.NOT_FOUND));
        if (!"OPEN".equals(reviewItem.getStatus())) {
            throw new ApiException(ErrorCode.REVIEW_ALREADY_DECIDED);
        }
        TargetType targetType = targetType(reviewItem);
        long targetId = targetId(reviewItem);
        applyDecision(request, targetType, targetId);
        jdbcTemplate.update(
                UPDATE_REVIEW_DECISION_QUERY,
                Map.of(
                        "status", request.decision() == Decision.REJECT ? "REJECTED" : "APPROVED",
                        "reviewerId", reviewerId,
                        "reviewId", reviewId));
    }

    /** Seçilen kararı kazanım ve hedef tablolarına uygular. */
    private void applyDecision(ReviewDecisionRequest request, TargetType targetType, long targetId) {
        switch (request.decision()) {
            case APPROVE -> publishTarget(targetType, targetId);
            case FIX -> {
                replaceOutcomes(targetType, targetId, request.outcomeIds());
                publishTarget(targetType, targetId);
            }
            case REJECT -> rejectTarget(targetType, targetId);
        }
    }

    /** Hedefin bütün kazanım bağlarını insan seçimiyle değiştirir. */
    private void replaceOutcomes(TargetType targetType, long targetId, List<Long> outcomeIds) {
        if (outcomeIds == null || outcomeIds.isEmpty()) {
            throw new ApiException(ErrorCode.VALIDATION_FAILED);
        }
        List<Long> uniqueOutcomeIds = outcomeIds.stream().distinct().toList();
        Long existingOutcomeCount = jdbcTemplate.queryForObject(
                SELECT_OUTCOME_COUNT_QUERY, Map.of("outcomeIds", uniqueOutcomeIds), Long.class);
        if (!Objects.equals(existingOutcomeCount, (long) uniqueOutcomeIds.size())) {
            throw new ApiException(ErrorCode.VALIDATION_FAILED);
        }
        String deleteQuery =
                targetType == TargetType.QUESTION ? DELETE_QUESTION_OUTCOMES_QUERY : DELETE_BLOCK_OUTCOMES_QUERY;
        jdbcTemplate.update(deleteQuery, Map.of("targetId", targetId));
        String insertQuery =
                targetType == TargetType.QUESTION ? INSERT_QUESTION_OUTCOME_QUERY : INSERT_BLOCK_OUTCOME_QUERY;
        for (Long outcomeId : uniqueOutcomeIds) {
            jdbcTemplate.update(
                    insertQuery,
                    new MapSqlParameterSource().addValue("targetId", targetId).addValue("outcomeId", outcomeId));
        }
    }

    /** Taslak hedef içeriği yayına alır. */
    private void publishTarget(TargetType targetType, long targetId) {
        if (targetType == TargetType.QUESTION) {
            jdbcTemplate.update(
                    PUBLISH_QUESTION_QUERY,
                    Map.of("targetId", targetId, "draftStatus", AppConstants.QUESTION_STATUS_DRAFT));
        } else {
            jdbcTemplate.update(
                    PUBLISH_BLOCK_QUERY,
                    Map.of("targetId", targetId, "draftStatus", AppConstants.CONTENT_BLOCK_STATUS_DRAFT));
        }
    }

    /** Hedef içeriği reddeder. */
    private void rejectTarget(TargetType targetType, long targetId) {
        String query = targetType == TargetType.QUESTION ? REJECT_QUESTION_QUERY : REJECT_BLOCK_QUERY;
        jdbcTemplate.update(query, Map.of("targetId", targetId));
    }

    /** İnceleme kaydının soru veya paragraf hedefini belirler. */
    private TargetType targetType(ReviewItem reviewItem) {
        if (reviewItem.getQuestionId() != null) {
            return TargetType.QUESTION;
        }
        if (reviewItem.getContentBlockId() != null) {
            return TargetType.BLOCK;
        }
        throw new ApiException(ErrorCode.INTERNAL_ERROR);
    }

    /** İnceleme kaydının hedef kimliğini döndürür. */
    private long targetId(ReviewItem reviewItem) {
        Long targetId =
                reviewItem.getQuestionId() != null ? reviewItem.getQuestionId() : reviewItem.getContentBlockId();
        if (targetId == null) {
            throw new ApiException(ErrorCode.INTERNAL_ERROR);
        }
        return targetId;
    }

    /** Sorgu satırını inceleme cevabına dönüştürür. */
    private ReviewItemResponse mapReviewItem(java.sql.ResultSet result) throws java.sql.SQLException {
        String content = result.getString(5);
        JsonNode questionContent = content == null ? null : objectMapper.readTree(content);
        JsonNode outcomeItems = objectMapper.readTree(result.getString(10));
        List<OutcomeLink> outcomes = outcomeItems
                .valueStream()
                .map(item -> new OutcomeLink(
                        item.get("id").asLong(),
                        item.get("code").asString(),
                        item.get("title").asString(),
                        item.get("mappedBy").asString()))
                .toList();
        OffsetDateTime createdAt = result.getObject(11, OffsetDateTime.class);
        return new ReviewItemResponse(
                result.getLong(1),
                result.getString(2),
                TargetType.valueOf(result.getString(3)),
                result.getLong(4),
                questionContent,
                result.getString(6),
                result.getString(7),
                (Long) result.getObject(8),
                (Integer) result.getObject(9),
                outcomes,
                createdAt.toInstant());
    }

    /** Sayfa ve boyut sınırlarını doğrular. */
    private void validatePage(int page, int size) {
        if (page < 0 || size < 1 || size > AppConstants.MAX_SOURCE_PAGE_SIZE) {
            throw new ApiException(ErrorCode.VALIDATION_FAILED);
        }
    }
}
