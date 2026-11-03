package com.hataanalizi.core.tutor;

import com.hataanalizi.core.common.ApiException;
import com.hataanalizi.core.common.AppConstants;
import com.hataanalizi.core.common.ErrorCode;
import com.hataanalizi.core.common.RequestIdFilter;
import com.hataanalizi.core.session.StudentAnswerRepository;
import com.hataanalizi.core.session.StudySession;
import com.hataanalizi.core.session.StudySessionRepository;
import com.hataanalizi.core.tutor.dto.ChatMessageRequest;
import com.hataanalizi.core.tutor.dto.ExplanationRequest;
import java.io.IOException;
import java.net.URI;
import java.time.Duration;
import java.util.LinkedHashSet;
import java.util.Locale;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicReference;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.MessageSource;
import org.springframework.dao.DataAccessException;
import org.springframework.http.ProblemDetail;
import org.springframework.stereotype.Service;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;
import reactor.core.Disposable;
import reactor.core.publisher.Flux;
import tools.jackson.core.JacksonException;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

/** Öğrenci anlatımını ve sohbetini akıtır, tamamlanan yanıtları kaydeder. */
@Service
public class TutorService {

    private static final Logger log = LoggerFactory.getLogger(TutorService.class);
    private static final Locale TURKISH = Locale.forLanguageTag("tr");
    private static final String USER_ROLE = "USER";
    private static final String ASSISTANT_ROLE = "ASSISTANT";

    private final StudySessionRepository studySessionRepository;
    private final StudentAnswerRepository studentAnswerRepository;
    private final TutorConversationRepository conversationRepository;
    private final TutorMessageRepository messageRepository;
    private final AiClient aiClient;
    private final ObjectMapper objectMapper;
    private final MessageSource messageSource;
    private final Duration streamTimeout;

    /** Tutor uçlarının kurallarını ve bağımlılıklarını saklar. */
    public TutorService(
            StudySessionRepository studySessionRepository,
            StudentAnswerRepository studentAnswerRepository,
            TutorConversationRepository conversationRepository,
            TutorMessageRepository messageRepository,
            AiClient aiClient,
            ObjectMapper objectMapper,
            MessageSource messageSource,
            @Value("${app.ai.stream-timeout}") Duration streamTimeout) {
        this.studySessionRepository = studySessionRepository;
        this.studentAnswerRepository = studentAnswerRepository;
        this.conversationRepository = conversationRepository;
        this.messageRepository = messageRepository;
        this.aiClient = aiClient;
        this.objectMapper = objectMapper;
        this.messageSource = messageSource;
        this.streamTimeout = streamTimeout;
    }

    /** Cevaplanmış, yayındaki sorunun anlatım akışını başlatır. */
    public SseEmitter explain(Long userId, ExplanationRequest request) {
        StudySession session = studySessionRepository
                .findById(request.sessionId())
                .filter(candidate -> candidate.getUserId().equals(userId))
                .orElseThrow(() -> new ApiException(ErrorCode.SESSION_NOT_FOUND));
        String selectedOption = selectedOption(session.getId(), request.questionId());
        TutorConversation conversation = new TutorConversation();
        conversation.setUserId(userId);
        conversation.setQuestionId(request.questionId());
        conversation = conversationRepository.saveAndFlush(conversation);
        Long conversationId = conversation.getId();
        return startStream(conversationId, aiClient.streamExplanation(userId, request.questionId(), selectedOption));
    }

    /** Öğrenci iletisini önce kaydeder, ardından sohbet yanıtını akıtır. */
    public SseEmitter chat(Long userId, Long conversationId, ChatMessageRequest request) {
        TutorConversation conversation = conversationRepository
                .findByIdAndUserId(conversationId, userId)
                .orElseThrow(() -> new ApiException(ErrorCode.NOT_FOUND));
        TutorMessage userMessage = new TutorMessage();
        userMessage.setTutorConversationId(conversationId);
        userMessage.setRole(USER_ROLE);
        userMessage.setContent(request.text());
        messageRepository.saveAndFlush(userMessage);
        TutorMessage latestMessage = messageRepository
                .findFirstByTutorConversationIdOrderByIdDesc(conversationId)
                .orElseThrow(() -> new ApiException(ErrorCode.TUTOR_CONFLICT));
        if (!USER_ROLE.equals(latestMessage.getRole())) {
            throw new ApiException(ErrorCode.TUTOR_CONFLICT);
        }
        return startStream(conversation.getId(), aiClient.streamChat(conversationId, userId));
    }

    /** Python olaylarına abone olup sonucu SseEmitter üzerinden iletir. */
    private SseEmitter startStream(Long conversationId, Flux<AiClient.StreamEvent> stream) {
        SseEmitter emitter = new SseEmitter(streamTimeout.toMillis());
        StreamState state = new StreamState(emitter, conversationId, RequestIdFilter.currentRequestId());
        AtomicReference<Disposable> subscription = new AtomicReference<>();
        emitter.onCompletion(() -> dispose(subscription));
        emitter.onTimeout(() -> {
            dispose(subscription);
            fail(state, ErrorCode.AI_UNAVAILABLE);
        });
        Disposable disposable = stream.subscribe(
                event -> acceptEvent(state, event), exception -> fail(state, errorCode(exception)), () -> {
                    if (!state.done.get()) {
                        fail(state, ErrorCode.AI_UNAVAILABLE);
                    }
                });
        subscription.set(disposable);
        if (state.finished.get()) {
            disposable.dispose();
        }
        return emitter;
    }

    /** Python olayını işler, metin ve alıntı kimliklerini biriktirir. */
    private void acceptEvent(StreamState state, AiClient.StreamEvent event) {
        if (state.finished.get()) {
            return;
        }
        if (event.event() == null) {
            fail(state, ErrorCode.AI_UNAVAILABLE);
            return;
        }
        try {
            switch (event.event()) {
                case "delta" -> acceptDelta(state, event.data());
                case "citation" -> acceptCitation(state, event.data());
                case "done" -> complete(state);
                case "error" -> fail(state, pythonErrorCode(event.data()));
                default -> fail(state, ErrorCode.AI_UNAVAILABLE);
            }
        } catch (IOException exception) {
            log.warn("Tutor stream delivery failed", exception);
            fail(state, ErrorCode.AI_UNAVAILABLE);
        } catch (ApiException exception) {
            fail(state, exception.getErrorCode());
        }
    }

    /** Delta olayını aynen yollar ve mesaj metnine ekler. */
    private void acceptDelta(StreamState state, String data) throws IOException {
        JsonNode payload = readPayload(data);
        JsonNode text = payload.get("text");
        if (text == null || !text.isString()) {
            throw new ApiException(ErrorCode.AI_UNAVAILABLE);
        }
        state.content.append(text.stringValue());
        sendRaw(state.emitter, "delta", data);
    }

    /** Alıntı olayını aynen yollar ve yeni blok kimliğini biriktirir. */
    private void acceptCitation(StreamState state, String data) throws IOException {
        JsonNode payload = readPayload(data);
        JsonNode blockId = payload.get("blockId");
        if (blockId == null || !blockId.isIntegralNumber() || !blockId.canConvertToLong()) {
            throw new ApiException(ErrorCode.AI_UNAVAILABLE);
        }
        state.citationBlockIds.add(blockId.longValue());
        sendRaw(state.emitter, "citation", data);
    }

    /** Tamamlanan asistan yanıtını ve alıntılarını saklayıp done olayı yollar. */
    private void complete(StreamState state) throws IOException {
        if (!state.finished.compareAndSet(false, true)) {
            return;
        }
        TutorMessage assistantMessage = new TutorMessage();
        assistantMessage.setTutorConversationId(state.conversationId);
        assistantMessage.setRole(ASSISTANT_ROLE);
        assistantMessage.setContent(state.content.toString());
        assistantMessage.setCitationBlockIds(state.citationBlockIds);
        try {
            assistantMessage = messageRepository.saveAndFlush(assistantMessage);
        } catch (DataAccessException exception) {
            log.error("Tutor assistant message could not be saved", exception);
            state.finished.set(false);
            fail(state, ErrorCode.INTERNAL_ERROR);
            return;
        }
        DoneEvent doneEvent = new DoneEvent(assistantMessage.getId(), state.conversationId);
        state.emitter.send(SseEmitter.event().name("done").data(doneEvent));
        state.done.set(true);
        state.emitter.complete();
    }

    /** Akışı Problem Details error olayıyla sonlandırır. */
    private void fail(StreamState state, ErrorCode errorCode) {
        if (!state.finished.compareAndSet(false, true)) {
            return;
        }
        try {
            state.emitter.send(SseEmitter.event().name("error").data(problem(errorCode, state.requestId)));
            state.emitter.complete();
        } catch (IOException | IllegalStateException exception) {
            log.warn("Tutor stream error could not be delivered", exception);
            state.emitter.completeWithError(exception);
        }
    }

    /** Ham Python olay verisini belirtilen SSE adıyla gönderir. */
    private void sendRaw(SseEmitter emitter, String eventName, String data) throws IOException {
        emitter.send(SseEmitter.event().name(eventName).data(data));
    }

    /** JSON olay verisini okur; geçersiz veri AI_UNAVAILABLE olur. */
    private JsonNode readPayload(String data) {
        try {
            return objectMapper.readTree(data);
        } catch (JacksonException exception) {
            throw new ApiException(ErrorCode.AI_UNAVAILABLE, exception);
        }
    }

    /** Python error olayının HTTP durumuna uygun hata kodunu seçer. */
    private ErrorCode pythonErrorCode(String data) {
        JsonNode status = readPayload(data).get("status");
        return status != null && status.asInt() == 404 ? ErrorCode.NOT_FOUND : ErrorCode.AI_UNAVAILABLE;
    }

    /** Akış hatasını ortak API koduna çevirir. */
    private ErrorCode errorCode(Throwable exception) {
        return exception instanceof ApiException apiException ? apiException.getErrorCode() : ErrorCode.AI_UNAVAILABLE;
    }

    /** Standart Problem Details gövdesini akış olayı için üretir. */
    private ProblemDetail problem(ErrorCode errorCode, String requestId) {
        ProblemDetail problem = ProblemDetail.forStatusAndDetail(
                errorCode.getStatus(), messageSource.getMessage(errorCode.messageKey(), null, TURKISH));
        problem.setType(URI.create("about:blank"));
        problem.setProperty("code", errorCode.name());
        problem.setProperty("requestId", requestId);
        return problem;
    }

    /** Oturum sorusunun yayın durumunu ve cevap seçimini doğrular. */
    private String selectedOption(Long sessionId, Long questionId) {
        studentAnswerRepository
                .findPublishedQuestionInSession(sessionId, questionId, AppConstants.QUESTION_STATUS_PUBLISHED)
                .orElseThrow(() -> new ApiException(ErrorCode.QUESTION_NOT_FOUND));
        if (!studentAnswerRepository.existsByStudySessionIdAndQuestionId(sessionId, questionId)) {
            throw new ApiException(ErrorCode.TUTOR_CONFLICT);
        }
        return studySessionRepository.findAnswerSelectionsBySessionId(sessionId).stream()
                .filter(answer -> answer.getQuestionId().equals(questionId))
                .map(StudySessionRepository.AnswerSelection::getSelectedOption)
                .findFirst()
                .orElseThrow(() -> new ApiException(ErrorCode.TUTOR_CONFLICT));
    }

    /** Kapatılan akış aboneliğini sonlandırır. */
    private void dispose(AtomicReference<Disposable> subscription) {
        Disposable disposable = subscription.get();
        if (disposable != null) {
            disposable.dispose();
        }
    }

    /** Asistan yanıtı tamamlandığında tarayıcıya gönderilen kimlikleri taşır. */
    private record DoneEvent(Long messageId, Long conversationId) {}

    /** Bir SSE yanıtının toplanan içeriğini ve yaşam durumunu tutar. */
    private static final class StreamState {

        private final SseEmitter emitter;
        private final Long conversationId;
        private final String requestId;
        private final StringBuilder content = new StringBuilder();
        private final LinkedHashSet<Long> citationBlockIds = new LinkedHashSet<>();
        private final AtomicBoolean finished = new AtomicBoolean();
        private final AtomicBoolean done = new AtomicBoolean();

        /** Akış yanıtı için gerekli durumu saklar. */
        private StreamState(SseEmitter emitter, Long conversationId, String requestId) {
            this.emitter = emitter;
            this.conversationId = conversationId;
            this.requestId = requestId;
        }
    }
}
