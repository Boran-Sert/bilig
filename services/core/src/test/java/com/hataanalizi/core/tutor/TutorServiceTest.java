package com.hataanalizi.core.tutor;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyBoolean;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.hataanalizi.core.common.ApiException;
import com.hataanalizi.core.common.ErrorCode;
import com.hataanalizi.core.session.StudentAnswerRepository;
import com.hataanalizi.core.session.StudySession;
import com.hataanalizi.core.session.StudySessionRepository;
import com.hataanalizi.core.tutor.dto.ChatMessageRequest;
import com.hataanalizi.core.tutor.dto.ExplanationRequest;
import com.hataanalizi.core.tutor.dto.StartChatRequest;
import java.time.Duration;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.context.MessageSource;
import tools.jackson.databind.ObjectMapper;

/** Tutor servisinin erişim, cevap doğrulama ve kayıt sırasını sınar. */
@ExtendWith(MockitoExtension.class)
class TutorServiceTest {

    private static final Long USER_ID = 3L;
    private static final Long SESSION_ID = 5L;
    private static final Long QUESTION_ID = 42L;
    private static final Long CONVERSATION_ID = 9L;

    @Mock
    private StudySessionRepository studySessionRepository;

    @Mock
    private StudentAnswerRepository studentAnswerRepository;

    @Mock
    private TutorConversationRepository conversationRepository;

    @Mock
    private TutorMessageRepository messageRepository;

    @Mock
    private AiClient aiClient;

    @Mock
    private MessageSource messageSource;

    private TutorService tutorService;

    /** Test servisinin gerçek JSON okuyucusunu ve kısa zaman aşımını kurar. */
    @BeforeEach
    void setUp() {
        tutorService = createService();
    }

    /** Başka öğrencinin oturumunu anlatım Python'a gitmeden reddeder. */
    @Test
    void rejectsAnotherUsersSession() {
        when(studySessionRepository.findById(SESSION_ID)).thenReturn(Optional.of(session(4L, "IN_PROGRESS")));

        assertError(ErrorCode.SESSION_NOT_FOUND, () -> tutorService.explain(USER_ID, explanationRequest()));

        verify(aiClient, never()).streamExplanation(any(), any(), any());
        verify(conversationRepository, never()).saveAndFlush(any());
    }

    /** Yayında olmayan veya oturuma ait olmayan soruyu anlatım Python'a gitmeden reddeder. */
    @Test
    void rejectsQuestionNotPublishedInSession() {
        when(studySessionRepository.findById(SESSION_ID)).thenReturn(Optional.of(session(USER_ID, "COMPLETED")));
        when(studentAnswerRepository.findPublishedQuestionInSession(SESSION_ID, QUESTION_ID, "PUBLISHED"))
                .thenReturn(Optional.empty());

        assertError(ErrorCode.QUESTION_NOT_FOUND, () -> tutorService.explain(USER_ID, explanationRequest()));

        verify(aiClient, never()).streamExplanation(any(), any(), any());
    }

    /** Oturumda cevaplanmamış soruya anlatım başlamaz. */
    @Test
    void rejectsUnansweredQuestion() {
        when(studySessionRepository.findById(SESSION_ID)).thenReturn(Optional.of(session(USER_ID, "IN_PROGRESS")));
        when(studentAnswerRepository.findPublishedQuestionInSession(SESSION_ID, QUESTION_ID, "PUBLISHED"))
                .thenReturn(Optional.of(questionContext()));
        when(studentAnswerRepository.existsByStudySessionIdAndQuestionId(SESSION_ID, QUESTION_ID))
                .thenReturn(false);

        assertError(ErrorCode.TUTOR_CONFLICT, () -> tutorService.explain(USER_ID, explanationRequest()));

        verify(aiClient, never()).streamExplanation(any(), any(), any());
    }

    /** Tamamlanmış oturumdaki cevaplanmış soru için anlatım akışına izin verir. */
    @Test
    void allowsExplanationAfterSessionCompletion() {
        when(studySessionRepository.findById(SESSION_ID)).thenReturn(Optional.of(session(USER_ID, "COMPLETED")));
        when(studentAnswerRepository.findPublishedQuestionInSession(SESSION_ID, QUESTION_ID, "PUBLISHED"))
                .thenReturn(Optional.of(questionContext()));
        when(studentAnswerRepository.existsByStudySessionIdAndQuestionId(SESSION_ID, QUESTION_ID))
                .thenReturn(true);
        StudySessionRepository.AnswerSelection answer = answerSelection(QUESTION_ID, "A");
        when(studySessionRepository.findAnswerSelectionsBySessionId(SESSION_ID)).thenReturn(List.of(answer));
        when(conversationRepository.saveAndFlush(any(TutorConversation.class)))
                .thenAnswer(invocation -> conversation(invocation.getArgument(0), CONVERSATION_ID));
        when(aiClient.streamExplanation(USER_ID, QUESTION_ID, "A")).thenReturn(reactor.core.publisher.Flux.never());

        tutorService.explain(USER_ID, explanationRequest()).complete();

        verify(aiClient).streamExplanation(USER_ID, QUESTION_ID, "A");
    }

    /** Başkasının sohbetini kullanıcı iletisi kaydedilmeden reddeder. */
    @Test
    void rejectsAnotherUsersConversation() {
        when(conversationRepository.findByIdAndUserId(CONVERSATION_ID, USER_ID)).thenReturn(Optional.empty());

        assertError(
                ErrorCode.NOT_FOUND, () -> tutorService.chat(USER_ID, CONVERSATION_ID, new ChatMessageRequest("Soru")));

        verify(messageRepository, never()).saveAndFlush(any(TutorMessage.class));
        verify(aiClient, never()).streamChat(any(), any(), anyBoolean());
    }

    /** Python çağrısından önce öğrenci iletisini USER rolüyle saklar. */
    @Test
    void savesUserMessageBeforeStartingChatStream() {
        when(conversationRepository.findByIdAndUserId(CONVERSATION_ID, USER_ID))
                .thenReturn(Optional.of(conversation(null, CONVERSATION_ID)));
        when(messageRepository.saveAndFlush(any(TutorMessage.class)))
                .thenAnswer(invocation -> invocation.getArgument(0));
        when(messageRepository.findFirstByTutorConversationIdOrderByIdDesc(CONVERSATION_ID))
                .thenReturn(Optional.of(message("USER")));
        when(aiClient.streamChat(CONVERSATION_ID, USER_ID, false)).thenReturn(reactor.core.publisher.Flux.never());

        tutorService
                .chat(USER_ID, CONVERSATION_ID, new ChatMessageRequest("Soru"))
                .complete();

        ArgumentCaptor<TutorMessage> messageCaptor = ArgumentCaptor.forClass(TutorMessage.class);
        verify(messageRepository).saveAndFlush(messageCaptor.capture());
        assertThat(messageCaptor.getValue().getRole()).isEqualTo("USER");
        assertThat(messageCaptor.getValue().getContent()).isEqualTo("Soru");
        verify(aiClient).streamChat(CONVERSATION_ID, USER_ID, false);
    }

    /** Son mesajın USER olmaması durumunda Python sohbet çağrısını reddeder. */
    @Test
    void rejectsConversationWhoseLatestMessageIsNotUser() {
        when(conversationRepository.findByIdAndUserId(CONVERSATION_ID, USER_ID))
                .thenReturn(Optional.of(conversation(null, CONVERSATION_ID)));
        when(messageRepository.saveAndFlush(any(TutorMessage.class)))
                .thenAnswer(invocation -> invocation.getArgument(0));
        when(messageRepository.findFirstByTutorConversationIdOrderByIdDesc(CONVERSATION_ID))
                .thenReturn(Optional.of(message("ASSISTANT")));

        assertError(
                ErrorCode.TUTOR_CONFLICT,
                () -> tutorService.chat(USER_ID, CONVERSATION_ID, new ChatMessageRequest("Soru")));

        verify(aiClient, never()).streamChat(any(), any(), anyBoolean());
    }

    /** Açık oturumda cevaplanmamış soruda doğru şık Python'a saklama bayrağıyla gider. */
    @Test
    void hidesAnswerWhenQuestionIsUnansweredInOpenSession() {
        TutorConversation questionConversation = conversation(null, CONVERSATION_ID);
        questionConversation.setQuestionId(QUESTION_ID);
        when(conversationRepository.findByIdAndUserId(CONVERSATION_ID, USER_ID))
                .thenReturn(Optional.of(questionConversation));
        when(messageRepository.saveAndFlush(any(TutorMessage.class)))
                .thenAnswer(invocation -> invocation.getArgument(0));
        when(messageRepository.findFirstByTutorConversationIdOrderByIdDesc(CONVERSATION_ID))
                .thenReturn(Optional.of(message("USER")));
        when(studentAnswerRepository.existsUnansweredInProgressSession(USER_ID, QUESTION_ID, "IN_PROGRESS"))
                .thenReturn(true);
        when(aiClient.streamChat(CONVERSATION_ID, USER_ID, true)).thenReturn(reactor.core.publisher.Flux.never());

        tutorService
                .chat(USER_ID, CONVERSATION_ID, new ChatMessageRequest("Soru"))
                .complete();

        verify(aiClient).streamChat(CONVERSATION_ID, USER_ID, true);
    }

    /** Başkasının oturumu için sohbet açmayı sohbet kaydı oluşmadan reddeder. */
    @Test
    void rejectsStartChatForAnotherUsersSession() {
        when(studySessionRepository.findById(SESSION_ID)).thenReturn(Optional.of(session(4L, "IN_PROGRESS")));

        assertError(ErrorCode.SESSION_NOT_FOUND, () -> tutorService.startChat(USER_ID, startChatRequest()));

        verify(conversationRepository, never()).saveAndFlush(any());
    }

    /** Oturumda olmayan soru için sohbet açmayı reddeder. */
    @Test
    void rejectsStartChatForQuestionNotInSession() {
        when(studySessionRepository.findById(SESSION_ID)).thenReturn(Optional.of(session(USER_ID, "IN_PROGRESS")));
        when(studentAnswerRepository.findPublishedQuestionInSession(SESSION_ID, QUESTION_ID, "PUBLISHED"))
                .thenReturn(Optional.empty());

        assertError(ErrorCode.QUESTION_NOT_FOUND, () -> tutorService.startChat(USER_ID, startChatRequest()));

        verify(conversationRepository, never()).saveAndFlush(any());
    }

    /** Cevaplanmamış soruda sohbeti soruya bağlı açar ve ilk iletiyi saklar. */
    @Test
    void startsChatBoundToQuestion() {
        when(studySessionRepository.findById(SESSION_ID)).thenReturn(Optional.of(session(USER_ID, "IN_PROGRESS")));
        when(studentAnswerRepository.findPublishedQuestionInSession(SESSION_ID, QUESTION_ID, "PUBLISHED"))
                .thenReturn(Optional.of(questionContext()));
        when(conversationRepository.saveAndFlush(any(TutorConversation.class)))
                .thenAnswer(invocation -> conversation(invocation.getArgument(0), CONVERSATION_ID));
        TutorConversation saved = conversation(null, CONVERSATION_ID);
        saved.setQuestionId(QUESTION_ID);
        when(conversationRepository.findByIdAndUserId(CONVERSATION_ID, USER_ID)).thenReturn(Optional.of(saved));
        when(messageRepository.saveAndFlush(any(TutorMessage.class)))
                .thenAnswer(invocation -> invocation.getArgument(0));
        when(messageRepository.findFirstByTutorConversationIdOrderByIdDesc(CONVERSATION_ID))
                .thenReturn(Optional.of(message("USER")));
        when(studentAnswerRepository.existsUnansweredInProgressSession(USER_ID, QUESTION_ID, "IN_PROGRESS"))
                .thenReturn(true);
        when(aiClient.streamChat(CONVERSATION_ID, USER_ID, true)).thenReturn(reactor.core.publisher.Flux.never());

        tutorService.startChat(USER_ID, startChatRequest()).complete();

        ArgumentCaptor<TutorConversation> captor = ArgumentCaptor.forClass(TutorConversation.class);
        verify(conversationRepository).saveAndFlush(captor.capture());
        assertThat(captor.getValue().getQuestionId()).isEqualTo(QUESTION_ID);
        verify(aiClient).streamChat(CONVERSATION_ID, USER_ID, true);
    }

    /** Test sohbet başlatma isteğini üretir. */
    private StartChatRequest startChatRequest() {
        return new StartChatRequest(SESSION_ID, QUESTION_ID, "Bu soruda ne isteniyor?");
    }

    /** Oluşturulan servis bağımlılıklarına gerçek JSON okuyucusunu verir. */
    private TutorService createService() {
        return new TutorService(
                studySessionRepository,
                studentAnswerRepository,
                conversationRepository,
                messageRepository,
                aiClient,
                new ObjectMapper(),
                messageSource,
                Duration.ofSeconds(1));
    }

    /** Belirtilen hata kodunun servis çağrısından geldiğini doğrular. */
    private void assertError(ErrorCode errorCode, org.assertj.core.api.ThrowableAssert.ThrowingCallable call) {
        assertThatThrownBy(call)
                .isInstanceOfSatisfying(
                        ApiException.class,
                        exception -> assertThat(exception.getErrorCode()).isEqualTo(errorCode));
    }

    /** Kimliği ve durumuyla test oturumu oluşturur. */
    private StudySession session(Long userId, String status) {
        StudySession session = new StudySession();
        session.setId(SESSION_ID);
        session.setUserId(userId);
        session.setStatus(status);
        return session;
    }

    /** Yayımlanmış soru bağlamını taklit eder. */
    private StudentAnswerRepository.QuestionContext questionContext() {
        return org.mockito.Mockito.mock(StudentAnswerRepository.QuestionContext.class);
    }

    /** Cevap seçimini test deposu sonucu olarak üretir. */
    private StudySessionRepository.AnswerSelection answerSelection(Long questionId, String option) {
        StudySessionRepository.AnswerSelection answer =
                org.mockito.Mockito.mock(StudySessionRepository.AnswerSelection.class);
        when(answer.getQuestionId()).thenReturn(questionId);
        when(answer.getSelectedOption()).thenReturn(option);
        return answer;
    }

    /** Kayıtlı gibi görünen konuşmayı oluşturur. */
    private TutorConversation conversation(TutorConversation conversation, Long id) {
        TutorConversation result = conversation == null ? new TutorConversation() : conversation;
        result.setId(id);
        result.setUserId(USER_ID);
        return result;
    }

    /** Belirtilen role sahip son mesajı taklit eder. */
    private TutorMessage message(String role) {
        TutorMessage message = new TutorMessage();
        message.setTutorConversationId(CONVERSATION_ID);
        message.setRole(role);
        message.setContent("Yanıt");
        return message;
    }

    /** Test anlatım isteğini üretir. */
    private ExplanationRequest explanationRequest() {
        return new ExplanationRequest(SESSION_ID, QUESTION_ID);
    }
}
