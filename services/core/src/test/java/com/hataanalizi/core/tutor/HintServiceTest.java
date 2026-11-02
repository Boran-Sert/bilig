package com.hataanalizi.core.tutor;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.hataanalizi.core.common.ApiException;
import com.hataanalizi.core.common.ErrorCode;
import com.hataanalizi.core.question.Question;
import com.hataanalizi.core.question.QuestionRepository;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

/** İpucu servisinin üretim, saklama ve önbellek davranışını doğrular. */
@ExtendWith(MockitoExtension.class)
class HintServiceTest {

    @Mock
    private QuestionRepository questionRepository;

    @Mock
    private AiClient aiClient;

    @InjectMocks
    private HintService hintService;

    /** Boş ipucunu üretir, saklar ve sonraki istekte AI'ı çağırmaz. */
    @Test
    void generatesAndCachesHint() {
        Question question = new Question();
        when(questionRepository.findByIdForUpdate(12L)).thenReturn(Optional.of(question));
        when(aiClient.hint(12L)).thenReturn("Compare the choices.");

        assertThat(hintService.getHint(12L)).isEqualTo("Compare the choices.");
        assertThat(question.getHint()).isEqualTo("Compare the choices.");
        assertThat(hintService.getHint(12L)).isEqualTo("Compare the choices.");

        verify(aiClient).hint(12L);
        verify(questionRepository).save(question);
    }

    /** Dolu ipucunu AI'ı çağırmadan döndürür. */
    @Test
    void returnsExistingHintWithoutCallingAi() {
        Question question = new Question();
        question.setHint("Saved hint.");
        when(questionRepository.findByIdForUpdate(12L)).thenReturn(Optional.of(question));

        assertThat(hintService.getHint(12L)).isEqualTo("Saved hint.");

        verify(aiClient, never()).hint(12L);
        verify(questionRepository, never()).save(question);
    }

    /** Bulunmayan soru için 404 hata kodu döndürür ve AI'ı çağırmaz. */
    @Test
    void rejectsMissingQuestion() {
        when(questionRepository.findByIdForUpdate(12L)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> hintService.getHint(12L))
                .isInstanceOfSatisfying(
                        ApiException.class,
                        exception -> assertThat(exception.getErrorCode()).isEqualTo(ErrorCode.NOT_FOUND));

        verify(aiClient, never()).hint(12L);
    }
}
