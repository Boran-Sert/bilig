package com.hataanalizi.core.admin;

import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import com.hataanalizi.core.admin.dto.ReviewDecisionRequest;
import com.hataanalizi.core.admin.dto.ReviewDecisionRequest.Decision;
import com.hataanalizi.core.common.ApiException;
import com.hataanalizi.core.common.AppConstants;
import com.hataanalizi.core.common.ErrorCode;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.jdbc.core.namedparam.NamedParameterJdbcTemplate;
import tools.jackson.databind.ObjectMapper;

/** İnceleme servisinin karar öncesi doğrulamalarını sınar. */
@ExtendWith(MockitoExtension.class)
class ReviewServiceTest {

    @Mock
    private NamedParameterJdbcTemplate jdbcTemplate;

    @Mock
    private ReviewItemRepository reviewItemRepository;

    private ReviewService reviewService;

    /** İnceleme servisini bağımlılık taklitleriyle hazırlar. */
    @BeforeEach
    void setUp() {
        reviewService = new ReviewService(jdbcTemplate, reviewItemRepository, new ObjectMapper());
    }

    /** Karar verilmiş kaydın güncellenmesini engeller. */
    @Test
    void rejectsAlreadyDecidedReview() {
        ReviewItem reviewItem = reviewItem("APPROVED");
        when(reviewItemRepository.findByIdForUpdate(7L, AppConstants.REVIEW_REASON_LOW_CONFIDENCE))
                .thenReturn(Optional.of(reviewItem));

        assertThatThrownBy(() -> reviewService.decideReview(7L, 10L, new ReviewDecisionRequest(Decision.APPROVE, null)))
                .isInstanceOfSatisfying(
                        ApiException.class,
                        exception -> org.assertj.core.api.Assertions.assertThat(exception.getErrorCode())
                                .isEqualTo(ErrorCode.REVIEW_ALREADY_DECIDED));

        verify(reviewItemRepository).findByIdForUpdate(7L, AppConstants.REVIEW_REASON_LOW_CONFIDENCE);
        verifyNoInteractions(jdbcTemplate);
    }

    /** Boş FIX listesinin hedefe veya kazanım bağlarına dokunmadan reddedildiğini doğrular. */
    @Test
    void rejectsEmptyFixBeforeChangingData() {
        ReviewItem reviewItem = reviewItem("OPEN");
        when(reviewItemRepository.findByIdForUpdate(7L, AppConstants.REVIEW_REASON_LOW_CONFIDENCE))
                .thenReturn(Optional.of(reviewItem));

        assertThatThrownBy(
                        () -> reviewService.decideReview(7L, 10L, new ReviewDecisionRequest(Decision.FIX, List.of())))
                .isInstanceOfSatisfying(
                        ApiException.class,
                        exception -> org.assertj.core.api.Assertions.assertThat(exception.getErrorCode())
                                .isEqualTo(ErrorCode.VALIDATION_FAILED));

        verifyNoInteractions(jdbcTemplate);
    }

    /** Geçersiz sayfa değerini sorgu çalıştırmadan reddeder. */
    @Test
    void rejectsNegativePage() {
        assertThatThrownBy(() -> reviewService.listReviews(-1, 20))
                .isInstanceOfSatisfying(
                        ApiException.class,
                        exception -> org.assertj.core.api.Assertions.assertThat(exception.getErrorCode())
                                .isEqualTo(ErrorCode.VALIDATION_FAILED));

        verifyNoInteractions(jdbcTemplate, reviewItemRepository);
    }

    /** Hedef soru kimliğine sahip inceleme kaydı döndürür. */
    private ReviewItem reviewItem(String status) {
        ReviewItem reviewItem = new ReviewItem();
        reviewItem.setId(7L);
        reviewItem.setReason("LOW_CONFIDENCE");
        reviewItem.setQuestionId(42L);
        reviewItem.setStatus(status);
        return reviewItem;
    }
}
