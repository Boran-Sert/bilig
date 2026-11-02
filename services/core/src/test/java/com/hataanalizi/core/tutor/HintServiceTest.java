package com.hataanalizi.core.tutor;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.hataanalizi.core.common.ApiException;
import com.hataanalizi.core.common.AppConstants;
import com.hataanalizi.core.common.ErrorCode;
import com.hataanalizi.core.question.Question;
import com.hataanalizi.core.question.QuestionRepository;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

/** İpucu servisinin üretim, saklama ve yayın kontrolü davranışını doğrular. */
@ExtendWith(MockitoExtension.class)
class HintServiceTest {

    private static final Long QUESTION_ID = 12L;

    @Mock
    private QuestionRepository questionRepository;

    @Mock
    private AiClient aiClient;

    @InjectMocks
    private HintService hintService;

    /** İpucu yoksa üretir, koşullu yazar ve saklanan ipucunu döndürür. */
    @Test
    void generatesAndStoresHint() {
        whenPublishedQuestionHas(null);
        when(aiClient.hint(QUESTION_ID)).thenReturn("Seçenekleri karşılaştır.");
        when(questionRepository.findHint(QUESTION_ID)).thenReturn("Seçenekleri karşılaştır.");

        assertThat(hintService.getHint(QUESTION_ID)).isEqualTo("Seçenekleri karşılaştır.");

        verify(questionRepository).saveHintIfAbsent(QUESTION_ID, "Seçenekleri karşılaştır.");
    }

    /** Kayıtlı ipucu varsa AI'ı çağırmadan döndürür. */
    @Test
    void returnsExistingHintWithoutCallingAi() {
        whenPublishedQuestionHas("Kayıtlı ipucu.");

        assertThat(hintService.getHint(QUESTION_ID)).isEqualTo("Kayıtlı ipucu.");

        verify(aiClient, never()).hint(QUESTION_ID);
        verify(questionRepository, never()).saveHintIfAbsent(QUESTION_ID, "Kayıtlı ipucu.");
    }

    /** Başka bir istek önce yazdıysa kendi ürettiğini değil saklananı döndürür. */
    @Test
    void returnsHintStoredByConcurrentRequest() {
        whenPublishedQuestionHas(null);
        when(aiClient.hint(QUESTION_ID)).thenReturn("Bu isteğin ipucu.");
        when(questionRepository.saveHintIfAbsent(QUESTION_ID, "Bu isteğin ipucu."))
                .thenReturn(0);
        when(questionRepository.findHint(QUESTION_ID)).thenReturn("Önce yazılan ipucu.");

        assertThat(hintService.getHint(QUESTION_ID)).isEqualTo("Önce yazılan ipucu.");
    }

    /** Yayında olmayan ya da bulunmayan soruyu AI'a gitmeden reddeder. */
    @Test
    void rejectsQuestionThatIsNotPublished() {
        when(questionRepository.findByIdAndStatus(QUESTION_ID, AppConstants.QUESTION_STATUS_PUBLISHED))
                .thenReturn(Optional.empty());

        assertThatThrownBy(() -> hintService.getHint(QUESTION_ID))
                .isInstanceOfSatisfying(
                        ApiException.class,
                        exception -> assertThat(exception.getErrorCode()).isEqualTo(ErrorCode.QUESTION_NOT_FOUND));

        verify(aiClient, never()).hint(QUESTION_ID);
    }

    /** Yayındaki sorunun verilen ipucuyla bulunmasını taklit eder. */
    private void whenPublishedQuestionHas(String hint) {
        Question question = mock(Question.class);
        when(question.getHint()).thenReturn(hint);
        when(questionRepository.findByIdAndStatus(QUESTION_ID, AppConstants.QUESTION_STATUS_PUBLISHED))
                .thenReturn(Optional.of(question));
    }
}
