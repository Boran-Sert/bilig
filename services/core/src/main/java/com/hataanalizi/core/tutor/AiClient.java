package com.hataanalizi.core.tutor;

import com.hataanalizi.core.common.ApiException;
import com.hataanalizi.core.common.ErrorCode;
import java.util.function.Supplier;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.http.HttpStatusCode;
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

    public AiClient(@Qualifier("aiRestClient") RestClient restClient) {
        this.restClient = restClient;
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

    /** Çağrıyı çalıştırır, bağlantı hatasını AI_UNAVAILABLE'a çevirir. */
    private <T> T execute(Supplier<T> call) {
        try {
            return call.get();
        } catch (ResourceAccessException exception) {
            throw new ApiException(ErrorCode.AI_UNAVAILABLE, exception);
        }
    }
}
