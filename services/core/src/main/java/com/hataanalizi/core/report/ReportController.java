package com.hataanalizi.core.report;

import com.hataanalizi.core.auth.AuthUser;
import jakarta.validation.Valid;
import jakarta.validation.constraints.AssertTrue;
import jakarta.validation.constraints.Positive;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/** Öğrenci bildirimlerini alır. */
@RestController
@RequestMapping("/api/reports")
public class ReportController {

    private final ReportService reportService;

    /** Bildirim iş kurallarını saklar. */
    public ReportController(ReportService reportService) {
        this.reportService = reportService;
    }

    /** Soru ya da anlatım için öğrenci bildirimi oluşturur. */
    @PostMapping
    public ResponseEntity<Void> createReport(
            @AuthenticationPrincipal AuthUser principal, @Valid @RequestBody ReportRequest request) {
        reportService.createReport(principal.id(), request.questionId(), request.messageId(), request.note());
        return ResponseEntity.status(HttpStatus.CREATED).build();
    }

    /** Bildirim hedeflerinden tam birini taşıyan isteği tanımlar. */
    public record ReportRequest(
            @Positive Long questionId, @Positive Long messageId, String note) {

        /** Soru ya da mesaj hedeflerinden yalnızca birinin seçildiğini doğrular. */
        @AssertTrue
        public boolean hasExactlyOneTarget() {
            return (questionId == null) != (messageId == null);
        }
    }
}
