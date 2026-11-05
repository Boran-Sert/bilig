package com.hataanalizi.core.question;

import com.hataanalizi.core.auth.AuthUser;
import com.hataanalizi.core.common.ApiException;
import com.hataanalizi.core.common.AppConstants;
import com.hataanalizi.core.common.ErrorCode;
import com.hataanalizi.core.question.dto.SimilarQuestionResponse;
import java.util.Optional;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import tools.jackson.databind.ObjectMapper;

/**
 * Yanlış yapılan sorunun kazanımlarından öğrencinin çözmediği yayındaki bir soruyu seçer. Seçim
 * tek SQL ile yapılır; uygun soru yoksa sonuç boştur.
 */
@Service
public class QuestionService {

    private final QuestionRepository questionRepository;
    private final ObjectMapper objectMapper;

    /** Soru sorgularını ve içerik dönüştürücüsünü saklar. */
    public QuestionService(QuestionRepository questionRepository, ObjectMapper objectMapper) {
        this.questionRepository = questionRepository;
        this.objectMapper = objectMapper;
    }

    /** Yayındaki sorunun benzerini döndürür; kaynak soru yayında değilse hata verir. */
    @Transactional(readOnly = true)
    public Optional<SimilarQuestionResponse> findSimilar(Long questionId, AuthUser authUser) {
        questionRepository
                .findByIdAndStatus(questionId, AppConstants.QUESTION_STATUS_PUBLISHED)
                .orElseThrow(() -> new ApiException(ErrorCode.QUESTION_NOT_FOUND));
        return questionRepository
                .findSimilarQuestion(questionId, authUser.id(), AppConstants.QUESTION_STATUS_PUBLISHED)
                .map(question -> SimilarQuestionResponse.from(question, objectMapper));
    }
}
