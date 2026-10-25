package com.hataanalizi.core.common;

import java.net.URI;
import java.util.List;
import java.util.Locale;
import java.util.Optional;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.context.MessageSource;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.HttpStatusCode;
import org.springframework.http.ProblemDetail;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.context.request.WebRequest;
import org.springframework.web.servlet.mvc.method.annotation.ResponseEntityExceptionHandler;

/**
 * Bütün controller hatalarını RFC 9457 ProblemDetail biçimine çevirir; cevaba code ve requestId
 * eklenir, detail metni messages_tr.properties dosyasından gelir. Beklenmeyen hatanın ayrıntısı
 * cevaba değil sadece log'a yazılır.
 */
@RestControllerAdvice
public class GlobalExceptionHandler extends ResponseEntityExceptionHandler {

    private static final Logger log = LoggerFactory.getLogger(GlobalExceptionHandler.class);
    private static final Locale TURKISH = Locale.forLanguageTag("tr");
    private static final String CODE_PROPERTY = "code";
    private static final String REQUEST_ID_PROPERTY = "requestId";
    private static final String ERRORS_PROPERTY = "errors";
    private static final URI PROBLEM_TYPE = URI.create("about:blank");

    private final MessageSource messageSource;

    public GlobalExceptionHandler(MessageSource messageSource) {
        this.messageSource = messageSource;
    }

    /** Doğrulama hatasındaki tek bir alanın adını ve mesajını taşır. */
    public record FieldViolation(String field, String message) {}

    /** Servislerin bilinen hatalarını koduna uygun durum ve Türkçe metinle döndürür. */
    @ExceptionHandler(ApiException.class)
    public ResponseEntity<ProblemDetail> handleApiException(ApiException exception) {
        ErrorCode errorCode = exception.getErrorCode();
        if (errorCode.getStatus().is5xxServerError()) {
            log.error("Api exception with server error code {}", errorCode, exception);
        } else {
            log.info("Api exception with code {}", errorCode);
        }
        ProblemDetail problem = createProblem(errorCode, exception.getMessageArguments());
        return ResponseEntity.status(errorCode.getStatus()).body(problem);
    }

    /** Beklenmeyen hatayı log'a yazar, cevaba sadece genel mesajı koyar. */
    @ExceptionHandler(Exception.class)
    public ResponseEntity<ProblemDetail> handleUnexpected(Exception exception) {
        log.error("Unexpected error occurred", exception);
        ProblemDetail problem = createProblem(ErrorCode.INTERNAL_ERROR);
        return ResponseEntity.status(ErrorCode.INTERNAL_ERROR.getStatus()).body(problem);
    }

    /** Doğrulama hatasını 400 olarak döndürür ve hatalı alanları listeler. */
    @Override
    protected ResponseEntity<Object> handleMethodArgumentNotValid(
            MethodArgumentNotValidException exception, HttpHeaders headers, HttpStatusCode status, WebRequest request) {
        ProblemDetail problem = exception.getBody();
        List<FieldViolation> violations = exception.getBindingResult().getFieldErrors().stream()
                .map(error -> new FieldViolation(error.getField(), error.getDefaultMessage()))
                .toList();
        problem.setProperty(ERRORS_PROPERTY, violations);
        return handleExceptionInternal(exception, problem, headers, status, request);
    }

    /** Spring'in kendi hata cevaplarına da requestId ve mümkünse code ekler. */
    @Override
    protected ResponseEntity<Object> handleExceptionInternal(
            Exception exception, Object body, HttpHeaders headers, HttpStatusCode statusCode, WebRequest request) {
        ResponseEntity<Object> response = super.handleExceptionInternal(exception, body, headers, statusCode, request);
        if (response != null && response.getBody() instanceof ProblemDetail problem) {
            completeProblem(problem, statusCode);
        }
        return response;
    }

    /** Hata koduna göre Türkçe metinli, code ve requestId taşıyan ProblemDetail üretir. */
    private ProblemDetail createProblem(ErrorCode errorCode, Object... arguments) {
        ProblemDetail problem =
                ProblemDetail.forStatusAndDetail(errorCode.getStatus(), resolveMessage(errorCode, arguments));

        problem.setType(PROBLEM_TYPE);
        problem.setProperty(CODE_PROPERTY, errorCode.name());
        problem.setProperty(REQUEST_ID_PROPERTY, RequestIdFilter.currentRequestId());
        return problem;
    }

    /** Spring'in ürettiği ProblemDetail'e requestId ve durumuna uyan code ekler. */
    private void completeProblem(ProblemDetail problem, HttpStatusCode statusCode) {
        problem.setType(PROBLEM_TYPE);

        resolveCode(statusCode).ifPresent(errorCode -> {
            problem.setDetail(resolveMessage(errorCode));
            problem.setProperty(CODE_PROPERTY, errorCode.name());
        });
        problem.setProperty(REQUEST_ID_PROPERTY, RequestIdFilter.currentRequestId());
    }

    /** HTTP durumuna karşılık gelen genel hata kodunu bulur, yoksa boş döner. */
    private Optional<ErrorCode> resolveCode(HttpStatusCode statusCode) {
        if (statusCode.value() == HttpStatus.BAD_REQUEST.value()) {
            return Optional.of(ErrorCode.VALIDATION_FAILED);
        }
        if (statusCode.value() == HttpStatus.NOT_FOUND.value()) {
            return Optional.of(ErrorCode.NOT_FOUND);
        }
        if (statusCode.is5xxServerError()) {
            return Optional.of(ErrorCode.INTERNAL_ERROR);
        }
        return Optional.empty();
    }

    /** Hata kodunun Türkçe metnini argümanlarıyla birlikte döndürür. */
    private String resolveMessage(ErrorCode errorCode, Object... arguments) {
        return messageSource.getMessage(errorCode.messageKey(), arguments, TURKISH);
    }
}
