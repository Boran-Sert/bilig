package com.hataanalizi.core.tutor;

import com.hataanalizi.core.common.ApiException;
import com.hataanalizi.core.common.AppConstants;
import com.hataanalizi.core.common.ErrorCode;
import com.hataanalizi.core.question.Question;
import com.hataanalizi.core.question.QuestionRepository;
import org.springframework.stereotype.Service;

/**
 * Yayındaki sorunun ipucunu bir kez üretip saklar. Python çağrısı sırasında veritabanı kilidi ve
 * bağlantısı tutulmaz; aynı anda iki istek üretirse ilk yazılan ipucu ikisine de döner.
 */
@Service
public class HintService {

    private final QuestionRepository questionRepository;
    private final AiClient aiClient;

    /** İpucu iş kurallarının bağımlılıklarını saklar. */
    public HintService(QuestionRepository questionRepository, AiClient aiClient) {
        this.questionRepository = questionRepository;
        this.aiClient = aiClient;
    }

    /** Kayıtlı ipucunu döndürür; yoksa üretir ve saklanan ipucunu döndürür. */
    public String getHint(Long questionId) {
        Question question = questionRepository
                .findByIdAndStatus(questionId, AppConstants.QUESTION_STATUS_PUBLISHED)
                .orElseThrow(() -> new ApiException(ErrorCode.QUESTION_NOT_FOUND));
        if (question.getHint() != null && !question.getHint().isBlank()) {
            return question.getHint();
        }

        String hint = aiClient.hint(questionId);
        questionRepository.saveHintIfAbsent(questionId, hint);
        return questionRepository.findHint(questionId);
    }
}
