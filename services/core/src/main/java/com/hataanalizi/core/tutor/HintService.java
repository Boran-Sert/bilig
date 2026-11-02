package com.hataanalizi.core.tutor;

import com.hataanalizi.core.common.ApiException;
import com.hataanalizi.core.common.ErrorCode;
import com.hataanalizi.core.question.Question;
import com.hataanalizi.core.question.QuestionRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/** Soru ipuçlarını üretir ve kalıcı olarak saklar. */
@Service
public class HintService {

    private final QuestionRepository questionRepository;
    private final AiClient aiClient;

    /** İpucu iş kurallarının bağımlılıklarını saklar. */
    public HintService(QuestionRepository questionRepository, AiClient aiClient) {
        this.questionRepository = questionRepository;
        this.aiClient = aiClient;
    }

    /** Kayıtlı ipucunu döndürür veya üretip soruya kaydeder. */
    @Transactional
    public String getHint(Long questionId) {
        Question question = questionRepository
                .findByIdForUpdate(questionId)
                .orElseThrow(() -> new ApiException(ErrorCode.NOT_FOUND));
        if (question.getHint() != null && !question.getHint().isBlank()) {
            return question.getHint();
        }

        String hint = aiClient.hint(questionId);
        question.setHint(hint);
        questionRepository.save(question);
        return hint;
    }
}
