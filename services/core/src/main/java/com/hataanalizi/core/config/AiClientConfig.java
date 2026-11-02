package com.hataanalizi.core.config;

import com.hataanalizi.core.common.RequestIdFilter;
import java.net.http.HttpClient;
import java.time.Duration;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.client.ClientHttpRequestInterceptor;
import org.springframework.http.client.JdkClientHttpRequestFactory;
import org.springframework.web.client.RestClient;

/**
 * Python AI servisini çağıran RestClient'leri kurar: kısa istekler için aiRestClient, Claude'un
 * metin ürettiği istekler için daha uzun okuma süreli aiGenerationRestClient. Adres AI_BASE_URL,
 * token INTERNAL_TOKEN ortam değişkeninden, zaman aşımları application.yml'deki app.ai.* ayarından
 * gelir. Her isteğe X-Internal-Token ve X-Request-Id başlıkları burada eklenir.
 */
@Configuration
public class AiClientConfig {

    public static final String INTERNAL_TOKEN_HEADER = "X-Internal-Token";

    /** Kısa iç istekler için zaman aşımlı RestClient bean'ini üretir. */
    @Bean
    public RestClient aiRestClient(
            RestClient.Builder restClientBuilder,
            @Value("${AI_BASE_URL}") String baseUrl,
            @Value("${INTERNAL_TOKEN}") String internalToken,
            @Value("${app.ai.connect-timeout}") Duration connectTimeout,
            @Value("${app.ai.read-timeout}") Duration readTimeout) {
        return buildClient(restClientBuilder, baseUrl, internalToken, connectTimeout, readTimeout);
    }

    /** Claude'un metin ürettiği iç istekler için uzun okuma süreli RestClient bean'ini üretir. */
    @Bean
    public RestClient aiGenerationRestClient(
            RestClient.Builder restClientBuilder,
            @Value("${AI_BASE_URL}") String baseUrl,
            @Value("${INTERNAL_TOKEN}") String internalToken,
            @Value("${app.ai.connect-timeout}") Duration connectTimeout,
            @Value("${app.ai.generation-read-timeout}") Duration readTimeout) {
        return buildClient(restClientBuilder, baseUrl, internalToken, connectTimeout, readTimeout);
    }

    /** Verilen zaman aşımlarıyla adresi ve iç başlıkları hazır RestClient kurar. */
    private RestClient buildClient(
            RestClient.Builder restClientBuilder,
            String baseUrl,
            String internalToken,
            Duration connectTimeout,
            Duration readTimeout) {
        HttpClient httpClient = HttpClient.newBuilder()
                .version(HttpClient.Version.HTTP_1_1)
                .connectTimeout(connectTimeout)
                .build();
        JdkClientHttpRequestFactory requestFactory = new JdkClientHttpRequestFactory(httpClient);
        requestFactory.setReadTimeout(readTimeout);
        return restClientBuilder
                .baseUrl(baseUrl)
                .requestInterceptor(internalHeaders(internalToken))
                .requestFactory(requestFactory)
                .build();
    }

    /** Her isteğe token'ı ve o anki istek numarasını ekleyen ekleyiciyi döndürür. */
    private ClientHttpRequestInterceptor internalHeaders(String internalToken) {
        return (request, body, execution) -> {
            request.getHeaders().set(INTERNAL_TOKEN_HEADER, internalToken);
            request.getHeaders().set(RequestIdFilter.HEADER_NAME, currentOrNewRequestId());
            return execution.execute(request, body);
        };
    }

    /** İstek numarasını MDC'den alır; istek dışındaysa yeni bir UUID üretir. */
    private String currentOrNewRequestId() {
        String requestId = RequestIdFilter.currentRequestId();
        return requestId != null ? requestId : UUID.randomUUID().toString();
    }
}
