package com.hataanalizi.core.session;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.hataanalizi.core.auth.AuthUser;
import com.hataanalizi.core.common.AppConstants;
import com.hataanalizi.core.exam.Exam;
import com.hataanalizi.core.exam.ExamRepository;
import com.hataanalizi.core.question.QuestionRepository;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

/** Oturum servisinin devam etme ve yeni oturum açma kurallarını doğrular. */
@ExtendWith(MockitoExtension.class)
class SessionServiceTest {

    @Mock
    private ExamRepository examRepository;

    @Mock
    private StudySessionRepository studySessionRepository;

    @Mock
    private QuestionRepository questionRepository;

    @InjectMocks
    private SessionService sessionService;

    /** Öğrencinin açık oturumu varsa aynı oturumu döndürür. */
    @Test
    void resumesExistingInProgressSession() {
        Exam exam = exam(24L);
        StudySession session = session(31L, 7L, 24L);
        when(examRepository.findByIdAndStatus(24L, AppConstants.EXAM_STATUS_PUBLISHED))
                .thenReturn(Optional.of(exam));
        when(studySessionRepository.findByUserIdAndExamIdAndStatus(7L, 24L, AppConstants.SESSION_STATUS_IN_PROGRESS))
                .thenReturn(Optional.of(session));
        when(examRepository.findQuestionPositions(24L, AppConstants.QUESTION_STATUS_PUBLISHED))
                .thenReturn(List.of());
        when(studySessionRepository.findAnswerSelectionsBySessionId(31L)).thenReturn(List.of());

        var response = sessionService.startOrResume(24L, new AuthUser(7L, "student@example.test", "STUDENT"));

        assertThat(response.sessionId()).isEqualTo(31L);
        assertThat(response.currentPosition()).isEqualTo((short) 2);
        verify(studySessionRepository, never()).save(any());
    }

    /** Açık oturum yoksa yeni oturum kaydeder. */
    @Test
    void createsSessionWhenNoInProgressSessionExists() {
        Exam exam = exam(24L);
        StudySession session = session(32L, 7L, 24L);
        session.setCurrentPosition((short) 1);
        when(examRepository.findByIdAndStatus(24L, AppConstants.EXAM_STATUS_PUBLISHED))
                .thenReturn(Optional.of(exam));
        when(studySessionRepository.findByUserIdAndExamIdAndStatus(7L, 24L, AppConstants.SESSION_STATUS_IN_PROGRESS))
                .thenReturn(Optional.empty(), Optional.of(session));
        when(examRepository.findQuestionPositions(24L, AppConstants.QUESTION_STATUS_PUBLISHED))
                .thenReturn(List.of());
        when(studySessionRepository.findAnswerSelectionsBySessionId(32L)).thenReturn(List.of());

        var response = sessionService.startOrResume(24L, new AuthUser(7L, "student@example.test", "STUDENT"));

        assertThat(response.sessionId()).isEqualTo(32L);
        assertThat(response.currentPosition()).isEqualTo((short) 1);
        verify(studySessionRepository).createInProgressSessionIfAbsent(7L, 24L);
    }

    /** Test nesnesini belirtilen kimlikle oluşturur. */
    private Exam exam(Long id) {
        Exam exam = new Exam();
        exam.setId(id);
        exam.setStatus(AppConstants.EXAM_STATUS_PUBLISHED);
        return exam;
    }

    /** Oturum nesnesini belirtilen kimlik ve konumla oluşturur. */
    private StudySession session(Long id, Long userId, Long examId) {
        StudySession session = new StudySession();
        session.setId(id);
        session.setUserId(userId);
        session.setExamId(examId);
        session.setCurrentPosition((short) 2);
        return session;
    }
}
