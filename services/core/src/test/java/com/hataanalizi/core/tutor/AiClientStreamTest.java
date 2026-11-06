package com.hataanalizi.core.tutor;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.hataanalizi.core.common.ApiException;
import com.hataanalizi.core.common.ErrorCode;
import com.hataanalizi.core.common.RequestIdFilter;
import com.hataanalizi.core.config.AiClientConfig;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.atomic.AtomicReference;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.web.client.RestClient;
import org.springframework.web.reactive.function.client.ClientRequest;
import org.springframework.web.reactive.function.client.ClientResponse;
import org.springframework.web.reactive.function.client.ExchangeFunction;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Mono;

/** AiClient'ın Python SSE uçlarını, iç başlıklarını ve hata eşlemesini doğrular. */
class AiClientStreamTest {

    private static final String BASE_URL = "http://ai-test";
    private static final String TOKEN = "test-internal-token";

    /** Anlatım olaylarını aynı sırada ve ham JSON verisiyle döndürür. */
    @Test
    void streamsExplanationEventsAndAddsInternalHeaders() {
        AtomicReference<ClientRequest> capturedRequest = new AtomicReference<>();
        List<AiClient.StreamEvent> events = new ArrayList<>();
        AiClient client = clientFor(HttpStatus.OK, """
                event: delta
                data: {"text":"Küçük Ağa "}

                event: citation
                data: {"blockId":102,"sourceTitle":"TDE 12 Ders Kitabı","page":175}

                event: done
                data: {}

                """, capturedRequest);

        events.addAll(client.streamExplanation(3L, 42L, "A").collectList().block(Duration.ofSeconds(2)));

        assertThat(events).extracting(AiClient.StreamEvent::event).containsExactly("delta", "citation", "done");
        assertThat(events)
                .extracting(AiClient.StreamEvent::data)
                .containsExactly(
                        "{\"text\":\"Küçük Ağa \"}",
                        "{\"blockId\":102,\"sourceTitle\":\"TDE 12 Ders Kitabı\",\"page\":175}",
                        "{}");
        assertThat(capturedRequest.get().url().toString()).isEqualTo(BASE_URL + "/internal/explanations");
        assertThat(capturedRequest.get().method()).isEqualTo(HttpMethod.POST);
        assertThat(capturedRequest.get().headers().getFirst(AiClientConfig.INTERNAL_TOKEN_HEADER))
                .isEqualTo(TOKEN);
        assertThat(capturedRequest.get().headers().getFirst(RequestIdFilter.HEADER_NAME))
                .matches("[0-9a-f-]{36}");
        assertThat(capturedRequest.get().headers().getAccept()).contains(MediaType.TEXT_EVENT_STREAM);
    }

    /** Sohbet isteği doğru iç uçtan akar. */
    @Test
    void streamsChat() {
        AtomicReference<ClientRequest> capturedRequest = new AtomicReference<>();
        AiClient client = clientFor(HttpStatus.OK, "event: done\ndata: {}\n\n", capturedRequest);

        assertThat(client.streamChat(9L, 3L, false)
                        .blockFirst(Duration.ofSeconds(2))
                        .event())
                .isEqualTo("done");

        assertThat(capturedRequest.get().url().toString()).isEqualTo(BASE_URL + "/internal/chat");
    }

    /** Python'ın HTTP 404 yanıtını NOT_FOUND olarak çevirir. */
    @Test
    void mapsNotFoundResponse() {
        AiClient client = clientFor(HttpStatus.NOT_FOUND, "", new AtomicReference<>());

        assertThatThrownBy(() -> client.streamChat(9L, 3L, false).collectList().block(Duration.ofSeconds(2)))
                .isInstanceOfSatisfying(
                        ApiException.class,
                        exception -> assertThat(exception.getErrorCode()).isEqualTo(ErrorCode.NOT_FOUND));
    }

    /** Python'ın diğer HTTP hatalarını AI_UNAVAILABLE olarak çevirir. */
    @Test
    void mapsServerErrorResponse() {
        AiClient client = clientFor(HttpStatus.SERVICE_UNAVAILABLE, "", new AtomicReference<>());

        assertThatThrownBy(() -> client.streamChat(9L, 3L, false).collectList().block(Duration.ofSeconds(2)))
                .isInstanceOfSatisfying(
                        ApiException.class,
                        exception -> assertThat(exception.getErrorCode()).isEqualTo(ErrorCode.AI_UNAVAILABLE));
    }

    /** Sahte WebClient yanıtıyla iç başlık ve SSE davranışını test eder. */
    private AiClient clientFor(HttpStatus status, String body, AtomicReference<ClientRequest> capturedRequest) {
        ExchangeFunction exchangeFunction = request -> {
            capturedRequest.set(request);
            return Mono.just(ClientResponse.create(status)
                    .header(HttpHeaders.CONTENT_TYPE, MediaType.TEXT_EVENT_STREAM_VALUE)
                    .body(body)
                    .build());
        };
        WebClient.Builder builder = WebClient.builder().exchangeFunction(exchangeFunction);
        WebClient webClient = new AiClientConfig()
                .aiWebClient(builder, BASE_URL, TOKEN, Duration.ofSeconds(1), Duration.ofSeconds(5));
        return new AiClient(RestClient.builder().build(), RestClient.builder().build(), webClient);
    }
}
