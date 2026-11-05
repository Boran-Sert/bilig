package com.hataanalizi.core.question;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.hataanalizi.core.auth.AuthUser;
import com.hataanalizi.core.common.ApiException;
import com.hataanalizi.core.common.AppConstants;
import com.hataanalizi.core.common.ErrorCode;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import tools.jackson.databind.ObjectMapper;

/** Benzer soru servisinin yayın kontrolünü ve boş sonucu doğrular. */
class QuestionServiceTest {

    private static final Long QUESTION_ID = 12L;
    private static final AuthUser STUDENT = new AuthUser(7L, "student@example.test", "STUDENT");

    private final QuestionRepository questionRepository = mock(QuestionRepository.class);
    private final QuestionService questionService = new QuestionService(questionRepository, new ObjectMapper());

    /** Kaynak soru yayında değilse benzer soru aranmaz ve QUESTION_NOT_FOUND döner. */
    @Test
    void unpublishedSourceQuestionThrowsNotFound() {
        when(questionRepository.findByIdAndStatus(QUESTION_ID, AppConstants.QUESTION_STATUS_PUBLISHED))
                .thenReturn(Optional.empty());

        assertThatThrownBy(() -> questionService.findSimilar(QUESTION_ID, STUDENT))
                .isInstanceOfSatisfying(
                        ApiException.class,
                        exception -> assertThat(exception.getErrorCode()).isEqualTo(ErrorCode.QUESTION_NOT_FOUND));
        verify(questionRepository, never()).findSimilarQuestion(anyLong(), anyLong(), anyString());
    }

    /** Uygun soru yoksa sonuç boştur ve arama öğrencinin kimliğiyle yapılır. */
    @Test
    void returnsEmptyWhenNoCandidate() {
        when(questionRepository.findByIdAndStatus(QUESTION_ID, AppConstants.QUESTION_STATUS_PUBLISHED))
                .thenReturn(Optional.of(new Question()));
        when(questionRepository.findSimilarQuestion(QUESTION_ID, STUDENT.id(), AppConstants.QUESTION_STATUS_PUBLISHED))
                .thenReturn(Optional.empty());

        assertThat(questionService.findSimilar(QUESTION_ID, STUDENT)).isEmpty();
    }
}
