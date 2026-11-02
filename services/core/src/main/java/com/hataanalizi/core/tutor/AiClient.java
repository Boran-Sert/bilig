package com.hataanalizi.core.tutor;

import com.hataanalizi.core.common.ApiException;
import com.hataanalizi.core.common.ErrorCode;
import java.util.function.Supplier;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.http.HttpStatus;
import org.springframework.http.HttpStatusCode;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestClient;

/**
 * Java'dan Python AI servisine giden bütün akışsız isteklerin tek geçiş noktasıdır. İç başlıklar
 * RestClient'te eklenir; bağlantı hatası ve 5xx cevabı burada ApiException(AI_UNAVAILABLE) olur.
 * Akışlı (SSE) çağrılar ayrı bir işte WebClient ile eklenecek.
 */
@Component
public class AiClient {

    private final RestClient restClient;
    private final RestClient generationRestClient;

    /** Kısa istek ve metin üretimi istemcilerini saklar. */
    public AiClient(
            @Qualifier("aiRestClient") RestClient restClient,
            @Qualifier("aiGenerationRestClient") RestClient generationRestClient) {
        this.restClient = restClient;
        this.generationRestClient = generationRestClient;
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
}
