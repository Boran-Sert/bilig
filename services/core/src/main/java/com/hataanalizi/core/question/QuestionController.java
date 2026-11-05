package com.hataanalizi.core.question;

import com.hataanalizi.core.auth.AuthUser;
import com.hataanalizi.core.question.dto.SimilarQuestionResponse;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RestController;

/** Öğrenciye benzer soru uç noktasını sunar. */
@RestController
public class QuestionController {

    private final QuestionService questionService;

    /** Soru iş kurallarını saklar. */
    public QuestionController(QuestionService questionService) {
        this.questionService = questionService;
    }

    /** Benzer soruyu döndürür; uygun soru yoksa 204 döner. */
    @GetMapping("/api/questions/{id}/similar")
    public ResponseEntity<SimilarQuestionResponse> getSimilar(
            @PathVariable Long id, @AuthenticationPrincipal AuthUser authUser) {
        return questionService
                .findSimilar(id, authUser)
                .map(ResponseEntity::ok)
                .orElseGet(() -> ResponseEntity.noContent().build());
    }
}
