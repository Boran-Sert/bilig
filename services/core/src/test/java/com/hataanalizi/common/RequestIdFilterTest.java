package com.hataanalizi.common;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;

import com.hataanalizi.core.common.RequestIdFilter;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.slf4j.MDC;
import org.springframework.http.ResponseEntity;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

/** RequestIdFilter'ın numara üretme, koruma ve MDC davranışını küçük bir controller ile sınar. */
class RequestIdFilterTest {

    private static final String UUID_PATTERN = "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}";

    private MockMvc mockMvc;

    /** Denemelik controller ve filtreyle MockMvc kurar. */
    @BeforeEach
    void setUp() {
        mockMvc = MockMvcBuilders.standaloneSetup(new ProbeController())
                .addFilters(new RequestIdFilter())
                .build();
    }

    /** Başlık gelmediğinde cevaba yeni bir UUID konur. */
    @Test
    void generatesRequestIdWhenHeaderIsMissing() throws Exception {
        MvcResult result = mockMvc.perform(get("/probe/mdc")).andReturn();

        assertThat(result.getResponse().getHeader(RequestIdFilter.HEADER_NAME)).matches(UUID_PATTERN);
    }

    /** Gelen güvenli değer cevapta ve MDC'de aynen korunur. */
    @Test
    void keepsSafeIncomingRequestId() throws Exception {
        MvcResult result = mockMvc.perform(get("/probe/mdc").header(RequestIdFilter.HEADER_NAME, "abc-123_X"))
                .andReturn();

        assertThat(result.getResponse().getHeader(RequestIdFilter.HEADER_NAME)).isEqualTo("abc-123_X");
        assertThat(result.getResponse().getContentAsString()).isEqualTo("abc-123_X");
    }

    /** Boşluklu ya da çok uzun gelen değer yerine yeni numara üretilir. */
    @Test
    void replacesUnsafeIncomingRequestId() throws Exception {
        String tooLong = "a".repeat(65);

        for (String unsafeValue : new String[] {"bad id with spaces", tooLong}) {
            MvcResult result = mockMvc.perform(get("/probe/mdc").header(RequestIdFilter.HEADER_NAME, unsafeValue))
                    .andReturn();

            assertThat(result.getResponse().getHeader(RequestIdFilter.HEADER_NAME))
                    .isNotEqualTo(unsafeValue)
                    .matches(UUID_PATTERN);
        }
    }

    /** Hata durumundaki cevapta da başlık bulunur. */
    @Test
    void addsHeaderToErrorResponses() throws Exception {
        MvcResult result = mockMvc.perform(get("/probe/missing")).andReturn();

        assertThat(result.getResponse().getStatus()).isEqualTo(404);
        assertThat(result.getResponse().getHeader(RequestIdFilter.HEADER_NAME)).isNotBlank();
    }

    /** İstek bittikten sonra MDC temizlenir. */
    @Test
    void clearsMdcAfterRequest() throws Exception {
        mockMvc.perform(get("/probe/mdc")).andReturn();

        assertThat(MDC.get(RequestIdFilter.MDC_KEY)).isNull();
    }

    /** Filtreyi denemek için kullanılan küçük controller. */
    @RestController
    static class ProbeController {

        /** İstek sırasındaki MDC numarasını metin olarak döndürür. */
        @GetMapping("/probe/mdc")
        String mdc() {
            return MDC.get(RequestIdFilter.MDC_KEY);
        }

        /** Her zaman 404 döndürür. */
        @GetMapping("/probe/missing")
        ResponseEntity<Void> missing() {
            return ResponseEntity.notFound().build();
        }
    }
}
