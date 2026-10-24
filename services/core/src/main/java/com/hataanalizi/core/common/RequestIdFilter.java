package com.hataanalizi.core.common;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.util.UUID;
import java.util.regex.Pattern;
import org.slf4j.MDC;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

/**
 * Her isteğe bir numara verir: gelen X-Request-Id başlığı güvenliyse korunur, yoksa ya da güvensizse
 * yenisi üretilir. Numara log'a (MDC) ve cevap başlığına yazılır; hata cevabındaki requestId alanı da
 * buradan gelir. Filtre en başta çalışır ki sonraki filtrelerin hataları da numaralı olsun.
 */
@Component
@Order(Ordered.HIGHEST_PRECEDENCE)
public class RequestIdFilter extends OncePerRequestFilter {

    public static final String HEADER_NAME = "X-Request-Id";
    public static final String MDC_KEY = "requestId";

    private static final Pattern SAFE_REQUEST_ID = Pattern.compile("[A-Za-z0-9_-]{1,64}");

    /** Şu anki isteğin numarasını döndürür; istek dışında null verir. */
    public static String currentRequestId() {
        return MDC.get(MDC_KEY);
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain filterChain)
            throws ServletException, IOException {
        String requestId = resolveRequestId(request.getHeader(HEADER_NAME));
        response.setHeader(HEADER_NAME, requestId);
        MDC.put(MDC_KEY, requestId);
        try {
            filterChain.doFilter(request, response);
        } finally {
            MDC.remove(MDC_KEY);
        }
    }

    /** Gelen değer güvenliyse onu, değilse yeni bir UUID döndürür. */
    private String resolveRequestId(String incomingValue) {
        if (incomingValue != null && SAFE_REQUEST_ID.matcher(incomingValue).matches()) {
            return incomingValue;
        }
        return UUID.randomUUID().toString();
    }
}
