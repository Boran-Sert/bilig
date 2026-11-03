package com.hataanalizi.core.tutor;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.content;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.header;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.method;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withServerError;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withStatus;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

import ch.qos.logback.classic.Level;
import ch.qos.logback.classic.Logger;
import ch.qos.logback.classic.spi.ILoggingEvent;
import ch.qos.logback.classic.spi.ThrowableProxyUtil;
import ch.qos.logback.core.read.ListAppender;
import com.hataanalizi.core.common.ApiException;
import com.hataanalizi.core.common.ErrorCode;
import com.hataanalizi.core.common.RequestIdFilter;
import com.hataanalizi.core.config.AiClientConfig;
import java.io.IOException;
import java.util.ResourceBundle;
import java.util.UUID;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.slf4j.LoggerFactory;
import org.slf4j.MDC;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestClient;
import org.springframework.web.reactive.function.client.WebClient;

/** AiClient'ın iç başlıklarını, hata çevirisini ve token'ın log'a yazılmadığını sınar. */
class AiClientTest {

    private static final String BASE_URL = "http://ai-test";
    private static final String HEALTH_URL = "http://ai-test/internal/health";
    private static final String HINT_URL = "http://ai-test/internal/hints";
    private static final String TOKEN = "gizli-test-token-123";
    private static final String UUID_PATTERN = "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}";

    private MockRestServiceServer server;
    private AiClient client;
    private Logger rootLogger;
    private Level previousLevel;
    private ListAppender<ILoggingEvent> logAppender;

    /** Gerçek config'ten RestClient kurar, sahte sunucuya bağlar ve log yakalayıcıyı açar. */
    @BeforeEach
    void setUp() {
        RestClient.Builder builder = RestClient.builder()
                .baseUrl(BASE_URL)
                .requestInterceptor((request, body, execution) -> {
                    request.getHeaders().set(AiClientConfig.INTERNAL_TOKEN_HEADER, TOKEN);

                    String requestId = RequestIdFilter.currentRequestId();
                    request.getHeaders()
                            .set(
                                    RequestIdFilter.HEADER_NAME,
                                    requestId != null
                                            ? requestId
                                            : UUID.randomUUID().toString());

                    return execution.execute(request, body);
                });
        server = MockRestServiceServer.bindTo(builder).build();
        RestClient restClient = builder.build();
        client = new AiClient(restClient, restClient, WebClient.builder().build());

        rootLogger = (Logger) LoggerFactory.getLogger(Logger.ROOT_LOGGER_NAME);
        previousLevel = rootLogger.getLevel();
        rootLogger.setLevel(Level.TRACE);
        logAppender = new ListAppender<>();
        logAppender.setContext(rootLogger.getLoggerContext());
        logAppender.start();
        rootLogger.addAppender(logAppender);
    }

    /** MDC'yi temizler ve log ayarlarını eski haline getirir. */
    @AfterEach
    void tearDown() {
        MDC.clear();
        rootLogger.detachAppender(logAppender);
        rootLogger.setLevel(previousLevel);
    }

    /** İstekle birlikte token ve MDC'deki istek numarası başlık olarak gider. */
    @Test
    void sendsBothInternalHeaders() {
        MDC.put(RequestIdFilter.MDC_KEY, "req-123");
        server.expect(requestTo(HEALTH_URL))
                .andExpect(method(HttpMethod.GET))
                .andExpect(header(AiClientConfig.INTERNAL_TOKEN_HEADER, TOKEN))
                .andExpect(header(RequestIdFilter.HEADER_NAME, "req-123"))
                .andRespond(withSuccess());

        client.health();

        server.verify();
    }

    /** İpucu isteğini iç başlıklar ve Python sözleşmesindeki JSON ile gönderir. */
    @Test
    void requestsHintAndReturnsPythonResponse() {
        server.expect(requestTo(HINT_URL))
                .andExpect(method(HttpMethod.POST))
                .andExpect(header(AiClientConfig.INTERNAL_TOKEN_HEADER, TOKEN))
                .andExpect(request -> assertThat(request.getHeaders().getFirst(RequestIdFilter.HEADER_NAME))
                        .matches(UUID_PATTERN))
                .andExpect(content().json("{\"questionId\":12}"))
                .andRespond(withSuccess("{\"hint\":\"Compare the choices.\"}", MediaType.APPLICATION_JSON));

        assertThat(client.hint(12L)).isEqualTo("Compare the choices.");

        server.verify();
    }

    /** Python sorunun yayında olmadığını 404 ile bildirirse QUESTION_NOT_FOUND olur. */
    @Test
    void hintNotFoundBecomesQuestionNotFound() {
        server.expect(requestTo(HINT_URL)).andRespond(withStatus(HttpStatus.NOT_FOUND));

        assertThatThrownBy(() -> client.hint(12L))
                .isInstanceOfSatisfying(
                        ApiException.class,
                        exception -> assertThat(exception.getErrorCode()).isEqualTo(ErrorCode.QUESTION_NOT_FOUND));
    }

    /** İpucu üretiminde 5xx cevabı AI_UNAVAILABLE olur. */
    @Test
    void hintServerErrorBecomesAiUnavailable() {
        server.expect(requestTo(HINT_URL)).andRespond(withServerError());

        assertThatThrownBy(() -> client.hint(12L))
                .isInstanceOfSatisfying(
                        ApiException.class,
                        exception -> assertThat(exception.getErrorCode()).isEqualTo(ErrorCode.AI_UNAVAILABLE));
    }

    /** MDC boşken de X-Request-Id başlığı gider ve UUID biçimindedir. */
    @Test
    void generatesRequestIdWhenMdcIsEmpty() {
        server.expect(requestTo(HEALTH_URL))
                .andExpect(header(AiClientConfig.INTERNAL_TOKEN_HEADER, TOKEN))
                .andExpect(request -> assertThat(request.getHeaders().getFirst(RequestIdFilter.HEADER_NAME))
                        .matches(UUID_PATTERN))
                .andRespond(withSuccess());

        client.health();

        server.verify();
    }

    /** AI servisinin 5xx cevabı AI_UNAVAILABLE olur. */
    @Test
    void serverErrorBecomesAiUnavailable() {
        server.expect(requestTo(HEALTH_URL)).andRespond(withServerError());
        server.expect(requestTo(HEALTH_URL)).andRespond(withStatus(HttpStatus.SERVICE_UNAVAILABLE));

        for (int attempt = 0; attempt < 2; attempt++) {
            assertThatThrownBy(client::health)
                    .isInstanceOfSatisfying(
                            ApiException.class,
                            exception -> assertThat(exception.getErrorCode()).isEqualTo(ErrorCode.AI_UNAVAILABLE));
        }
    }

    /** Bağlantı kurulamazsa AI_UNAVAILABLE olur. */
    @Test
    void connectionErrorBecomesAiUnavailable() {
        server.expect(requestTo(HEALTH_URL)).andRespond(request -> {
            throw new IOException("Connection refused");
        });

        assertThatThrownBy(client::health)
                .isInstanceOfSatisfying(
                        ApiException.class,
                        exception -> assertThat(exception.getErrorCode()).isEqualTo(ErrorCode.AI_UNAVAILABLE));
    }

    /** AI_UNAVAILABLE 503 döner ve Türkçe metni messages_tr.properties'te vardır. */
    @Test
    void aiUnavailableHasStatusAndMessage() {
        assertThat(ErrorCode.AI_UNAVAILABLE.getStatus()).isEqualTo(HttpStatus.SERVICE_UNAVAILABLE);
        assertThat(ResourceBundle.getBundle("messages_tr").getString(ErrorCode.AI_UNAVAILABLE.messageKey()))
                .isNotBlank();
    }

    /** Başarılı, 5xx ve bağlantı hatalı çağrılarda token hiçbir log satırında geçmez. */
    @Test
    void tokenIsNeverLogged() {
        MDC.put(RequestIdFilter.MDC_KEY, "req-log");
        server.expect(requestTo(HEALTH_URL)).andRespond(withSuccess());
        server.expect(requestTo(HEALTH_URL)).andRespond(withServerError());
        server.expect(requestTo(HEALTH_URL)).andRespond(request -> {
            throw new IOException("Connection refused");
        });

        client.health();
        assertThatThrownBy(client::health).isInstanceOf(ApiException.class);
        assertThatThrownBy(client::health).isInstanceOf(ApiException.class);

        assertThat(logAppender.list).isNotEmpty();
        assertThat(logAppender.list)
                .noneMatch(event -> event.getFormattedMessage().contains(TOKEN)
                        || (event.getThrowableProxy() != null
                                && ThrowableProxyUtil.asString(event.getThrowableProxy())
                                        .contains(TOKEN)));
    }
}
