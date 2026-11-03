package com.hataanalizi.core.admin;

import com.hataanalizi.core.admin.dto.ReviewDecisionRequest;
import com.hataanalizi.core.admin.dto.ReviewItemResponse;
import com.hataanalizi.core.admin.dto.ReviewOutcomeResponse;
import com.hataanalizi.core.auth.AuthUser;
import com.hataanalizi.core.common.AppConstants;
import com.hataanalizi.core.common.PageResponse;
import java.util.List;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/** İçerik yöneticilerinin inceleme ve kazanım uçlarını sunar. */
@RestController
@RequestMapping("/api/admin")
public class ReviewController {

    private final ReviewService reviewService;

    /** İnceleme işlemlerini yöneten servisi saklar. */
    public ReviewController(ReviewService reviewService) {
        this.reviewService = reviewService;
    }

    /** Açık inceleme kayıtlarını sayfalı döner. */
    @GetMapping("/review")
    public PageResponse<ReviewItemResponse> listReviews(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = AppConstants.DEFAULT_REVIEW_PAGE_SIZE) int size) {
        return reviewService.listReviews(page, size);
    }

    /** İnceleme kararını kaydeder ve gövdesiz başarılı cevap döner. */
    @PostMapping("/review/{id}")
    public ResponseEntity<Void> decideReview(
            @PathVariable long id,
            @RequestBody ReviewDecisionRequest request,
            @AuthenticationPrincipal AuthUser authUser) {
        reviewService.decideReview(id, authUser.id(), request);
        return ResponseEntity.noContent().build();
    }

    /** Düzeltme seçicisi için bütün kazanımları döner. */
    @GetMapping("/outcomes")
    public List<ReviewOutcomeResponse> listOutcomes() {
        return reviewService.listOutcomes();
    }
}
