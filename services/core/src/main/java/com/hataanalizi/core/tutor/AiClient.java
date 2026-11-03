package com.hataanalizi.core.tutor;

import com.hataanalizi.core.common.ApiException;
import com.hataanalizi.core.common.ErrorCode;
import java.util.Objects;
import java.util.function.Supplier;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.HttpStatus;
import org.springframework.http.HttpStatusCode;
import org.springframework.http.MediaType;
import org.springframework.http.codec.ServerSentEvent;
import org.springframework.stereotype.Component;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestClient;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.web.reactive.function.client.WebClientRequestException;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

/**
 * Java'dan Python AI servisine giden bütün isteklerin tek geçiş noktasıdır. Akışsız isteklerde
 * RestClient, SSE isteklerinde WebClient kullanır; iç başlıklar config'te eklenir.
 */
@Component
public class AiClient {

    private final RestClient restClient;
    private final RestClient generationRestClient;
    private final WebClient webClient;

    /** Kısa istek ve metin üretimi istemcilerini saklar. */
    public AiClient(
            @Qualifier("aiRestClient") RestClient restClient,
            @Qualifier("aiGenerationRestClient") RestClient generationRestClient,
            @Qualifier("aiWebClient") WebClient webClient) {
        this.restClient = restClient;
        this.generationRestClient = generationRestClient;
        this.webClient = webClient;
    }

    /** AI servisinin ayakta olduğunu GET /internal/health ile kontrol eder. */
    public void health() {
        execute(() -> restClient
                .get()
                .uri("/internal/health")
                .retrieve()
                .onStatus(HttpStatusCode::isError, (request, response) -> {
                    throw new ApiException(
                            ErrorCode.AI_UNAVAILABLE,
                            new IllegalStateException("AI service returned status "
                                    + response.getStatusCode().value()));
                })
                .toBodilessEntity());
    }

    /** Python'dan soru ipucunu alır; soru Python'da yayında değilse QUESTION_NOT_FOUND olur. */
    public String hint(Long questionId) {
        HintResponse response = execute(() -> generationRestClient
                .post()
                .uri("/internal/hints")
                .contentType(MediaType.APPLICATION_JSON)
                .body(new HintRequest(questionId))
                .retrieve()
                .onStatus(status -> status.isSameCodeAs(HttpStatus.NOT_FOUND), (request, result) -> {
                    throw new ApiException(ErrorCode.QUESTION_NOT_FOUND);
                })
                .onStatus(HttpStatusCode::isError, (request, result) -> {
                    throw new ApiException(
                            ErrorCode.AI_UNAVAILABLE,
                            new IllegalStateException("AI service returned status "
                                    + result.getStatusCode().value()));
                })
                .body(HintResponse.class));
        if (response == null || response.hint() == null || response.hint().isBlank()) {
            throw new ApiException(
                    ErrorCode.AI_UNAVAILABLE, new IllegalStateException("AI service returned an empty hint."));
        }
        return response.hint();
    }

    /** Python'dan yanlış cevap anlatımının olay akışını alır. */
    public Flux<StreamEvent> streamExplanation(Long userId, Long questionId, String selectedOption) {
        return stream("/internal/explanations", new ExplanationRequest(userId, questionId, selectedOption));
    }

    /** Python'dan sohbet yanıtının olay akışını alır. */
    public Flux<StreamEvent> streamChat(Long conversationId, Long userId) {
        return stream("/internal/chat", new ChatRequest(conversationId, userId));
    }

    /** Python'un SSE akışını okur ve servis hatalarını ortak hata kodlarına çevirir. */
    private Flux<StreamEvent> stream(String path, Object request) {
        return webClient
                .post()
                .uri(path)
                .contentType(MediaType.APPLICATION_JSON)
                .accept(MediaType.TEXT_EVENT_STREAM)
                .bodyValue(request)
                .retrieve()
                .onStatus(
                        status -> status.isSameCodeAs(HttpStatus.NOT_FOUND),
                        response -> Mono.error(new ApiException(ErrorCode.NOT_FOUND)))
                .onStatus(HttpStatusCode::isError, response -> Mono.error(new ApiException(ErrorCode.AI_UNAVAILABLE)))
                .bodyToFlux(new ParameterizedTypeReference<ServerSentEvent<String>>() {})
                .map(event -> new StreamEvent(event.event(), Objects.requireNonNullElse(event.data(), "")))
                .onErrorMap(
                        WebClientRequestException.class,
                        exception -> new ApiException(ErrorCode.AI_UNAVAILABLE, exception));
    }

    /** Çağrıyı çalıştırır, bağlantı hatasını AI_UNAVAILABLE'a çevirir. */
    private <T> T execute(Supplier<T> call) {
        try {
            return call.get();
        } catch (ResourceAccessException exception) {
            throw new ApiException(ErrorCode.AI_UNAVAILABLE, exception);
        }
    }

    /** Python ipucu isteğinin gövdesini tanımlar. */
    private record HintRequest(Long questionId) {}

    /** Python ipucu yanıtının gövdesini tanımlar. */
    private record HintResponse(String hint) {}

    /** Python'dan gelen SSE olayının adını ve ham verisini taşır. */
    public record StreamEvent(String event, String data) {}

    /** Python anlatım isteğinin JSON gövdesini tanımlar. */
    private record ExplanationRequest(Long userId, Long questionId, String selectedOption) {}

    /** Python sohbet isteğinin JSON gövdesini tanımlar. */
    private record ChatRequest(Long conversationId, Long userId) {}
}
