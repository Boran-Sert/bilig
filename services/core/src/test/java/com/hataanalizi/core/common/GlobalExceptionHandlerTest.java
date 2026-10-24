package com.hataanalizi.core.common;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import ch.qos.logback.classic.Level;
import ch.qos.logback.classic.Logger;
import ch.qos.logback.classic.spi.ILoggingEvent;
import ch.qos.logback.core.read.ListAppender;
import com.jayway.jsonpath.JsonPath;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import java.nio.charset.StandardCharsets;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.slf4j.LoggerFactory;
import org.springframework.context.support.ResourceBundleMessageSource;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

/** GlobalExceptionHandler'ın ortak hata biçimini küçük bir controller ile sınar. */
class GlobalExceptionHandlerTest {

    private static final String SECRET_DETAIL = "veritabani-sifresi-ayrintisi";

    private MockMvc mockMvc;
    private Logger handlerLogger;
    private ListAppender<ILoggingEvent> logAppender;

    /** Gerçek mesaj dosyasıyla handler'ı, filtreyi ve log yakalayıcıyı kurar. */
    @BeforeEach
    void setUp() {
        ResourceBundleMessageSource messageSource = new ResourceBundleMessageSource();
        messageSource.setBasename("messages_tr");
        messageSource.setDefaultEncoding("UTF-8");
        mockMvc =
                MockMvcBuilders.standaloneSetup(new ProbeController())
                        .setControllerAdvice(new GlobalExceptionHandler(messageSource))
                        .addFilters(new RequestIdFilter())
                        .build();

        handlerLogger = (Logger) LoggerFactory.getLogger(GlobalExceptionHandler.class);
        logAppender = new ListAppender<>();
        logAppender.start();
        handlerLogger.addAppender(logAppender);
    }

    /** Log yakalayıcıyı kaldırır. */
    @AfterEach
    void tearDown() {
        handlerLogger.detachAppender(logAppender);
    }

    /** ApiException doğru durum, Türkçe detail, code ve başlıkla aynı requestId ile döner. */
    @Test
    void apiExceptionReturnsStatusAndTurkishDetail() throws Exception {
        MvcResult result =
                mockMvc.perform(get("/probe/not-found"))
                        .andExpect(status().isNotFound())
                        .andExpect(jsonPath("$.type").value("about:blank"))
                        .andExpect(jsonPath("$.title").value("Not Found"))
                        .andExpect(jsonPath("$.status").value(404))
                        .andExpect(jsonPath("$.detail").value("İstenen kaynak bulunamadı."))
                        .andExpect(jsonPath("$.code").value("NOT_FOUND"))
                        .andReturn();

        String headerValue = result.getResponse().getHeader(RequestIdFilter.HEADER_NAME);
        String bodyValue =
                JsonPath.read(
                        result.getResponse().getContentAsString(StandardCharsets.UTF_8),
                        "$.requestId");
        assertThat(bodyValue).isNotBlank().isEqualTo(headerValue);
    }

    /** ApiException mesaj argümanlarını olduğu gibi taşır. */
    @Test
    void apiExceptionCarriesMessageArguments() {
        ApiException exception = new ApiException(ErrorCode.NOT_FOUND, "oturum", 42);

        assertThat(exception.getErrorCode()).isEqualTo(ErrorCode.NOT_FOUND);
        assertThat(exception.getMessageArguments()).containsExactly("oturum", 42);
    }

    /** Doğrulama hatası 400 VALIDATION_FAILED döner ve hatalı alanlar listelenir. */
    @Test
    void validationErrorReturnsBadRequestWithFieldErrors() throws Exception {
        mockMvc.perform(
                        post("/probe/validate")
                                .contentType(MediaType.APPLICATION_JSON)
                                .content("{\"title\":\"\",\"size\":0}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.status").value(400))
                .andExpect(jsonPath("$.code").value("VALIDATION_FAILED"))
                .andExpect(jsonPath("$.detail").value("Gönderilen bilgilerde hata var."))
                .andExpect(jsonPath("$.requestId").isNotEmpty())
                .andExpect(jsonPath("$.errors.length()").value(2))
                .andExpect(jsonPath("$.errors[?(@.field=='title')]").exists())
                .andExpect(jsonPath("$.errors[?(@.field=='size')]").exists());
    }

    /** Beklenmeyen hata 500 döner, ayrıntı cevaba değil log'a yazılır. */
    @Test
    void unexpectedErrorHidesDetailFromResponseAndLogsIt() throws Exception {
        MvcResult result =
                mockMvc.perform(get("/probe/boom"))
                        .andExpect(status().isInternalServerError())
                        .andExpect(jsonPath("$.code").value("INTERNAL_ERROR"))
                        .andExpect(
                                jsonPath("$.detail")
                                        .value(
                                                "Beklenmeyen bir hata oluştu. Lütfen daha sonra"
                                                        + " tekrar dene."))
                        .andExpect(jsonPath("$.requestId").isNotEmpty())
                        .andReturn();

        assertThat(result.getResponse().getContentAsString(StandardCharsets.UTF_8))
                .doesNotContain(SECRET_DETAIL);
        assertThat(logAppender.list)
                .anyMatch(
                        event ->
                                event.getLevel() == Level.ERROR
                                        && event.getThrowableProxy() != null
                                        && event.getThrowableProxy()
                                        .getMessage()
                                        .contains(SECRET_DETAIL));
    }

    /** Eşleşmeyen yol Spring'den gelse bile ortak biçimde 404 NOT_FOUND döner. */
    @Test
    void unmatchedPathUsesSharedFormat() throws Exception {
        mockMvc.perform(get("/probe/yok"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.code").value("NOT_FOUND"))
                .andExpect(jsonPath("$.requestId").isNotEmpty())
                .andExpect(header().exists(RequestIdFilter.HEADER_NAME));
    }

    /** Desteklenmeyen yöntem 405 olarak döner ve requestId taşır. */
    @Test
    void unsupportedMethodKeepsStatusAndRequestId() throws Exception {
        mockMvc.perform(post("/probe/not-found"))
                .andExpect(status().isMethodNotAllowed())
                .andExpect(jsonPath("$.requestId").isNotEmpty())
                .andExpect(header().exists(RequestIdFilter.HEADER_NAME));
    }

    /** Hata biçimini denemek için kullanılan küçük controller. */
    @RestController
    static class ProbeController {

        /** Doğrulanacak örnek istek gövdesi. */
        record CreateRequest(@NotBlank String title, @Min(1) int size) {}

        /** Her zaman NOT_FOUND kodlu ApiException fırlatır. */
        @GetMapping("/probe/not-found")
        void notFound() {
            throw new ApiException(ErrorCode.NOT_FOUND);
        }

        /** Her zaman ayrıntı taşıyan beklenmeyen bir hata fırlatır. */
        @GetMapping("/probe/boom")
        void boom() {
            throw new IllegalStateException(SECRET_DETAIL);
        }

        /** İstek gövdesini doğrular. */
        @PostMapping("/probe/validate")
        void validate(@Valid @RequestBody CreateRequest request) {}
    }
}
