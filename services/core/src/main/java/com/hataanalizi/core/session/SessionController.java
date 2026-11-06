package com.hataanalizi.core.session;

import com.hataanalizi.core.auth.AuthUser;
import com.hataanalizi.core.session.dto.AnswerRequest;
import com.hataanalizi.core.session.dto.AnswerResponse;
import com.hataanalizi.core.session.dto.SessionCompletionResponse;
import com.hataanalizi.core.session.dto.SessionResponse;
import com.hataanalizi.core.session.dto.SessionReviewResponse;
import jakarta.validation.Valid;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

/** Öğrencinin test oturumunu başlatır veya kaldığı yerden sürdürür. */
@RestController
public class SessionController {

    private final SessionService sessionService;

    /** Oturum iş kurallarını saklar. */
    public SessionController(SessionService sessionService) {
        this.sessionService = sessionService;
    }

    /** Testin öğrencinin açık oturumunu veya yeni oturumunu döndürür. */
    @PostMapping("/api/tests/{id}/sessions")
    public SessionResponse startOrResume(@PathVariable Long id, @AuthenticationPrincipal AuthUser authUser) {
        return sessionService.startOrResume(id, authUser);
    }

    /** Öğrencinin cevabını kaydeder ve doğru yanıt ile kazanımları döndürür. */
    @PutMapping("/api/sessions/{id}/answers/{questionId}")
    public AnswerResponse submitAnswer(
            @PathVariable Long id,
            @PathVariable Long questionId,
            @AuthenticationPrincipal AuthUser authUser,
            @Valid @RequestBody AnswerRequest request) {
        return sessionService.submitAnswer(id, questionId, authUser, request);
    }

    /** Oturumu tamamlar ve AYT netiyle kazanım özetini döndürür. */
    @PostMapping("/api/sessions/{id}/complete")
    public SessionCompletionResponse completeSession(
            @PathVariable Long id, @AuthenticationPrincipal AuthUser authUser) {
        return sessionService.completeSession(id, authUser);
    }

    /** Tamamlanmış oturumdaki soruları doğru şık ve öğrenci cevabıyla döndürür. */
    @GetMapping("/api/sessions/{id}/review")
    public SessionReviewResponse getReview(@PathVariable Long id, @AuthenticationPrincipal AuthUser authUser) {
        return sessionService.getReview(id, authUser);
    }

    /** Tamamlanmış oturumun AYT netini ve kazanım özetini döndürür. */
    @GetMapping("/api/sessions/{id}/result")
    public SessionCompletionResponse getResult(@PathVariable Long id, @AuthenticationPrincipal AuthUser authUser) {
        return sessionService.getResult(id, authUser);
    }
}
