package com.hataanalizi.core.auth.dto;

import com.hataanalizi.core.common.AppConstants;
import io.swagger.v3.oas.annotations.media.Schema;
import java.util.List;
import java.util.stream.IntStream;

/** Kayıt formunda seçilebilecek değerleri taşır. */
public record RegisterOptionsResponse(
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED) List<Integer> grades) {

    /** Sabitlerdeki sınıf aralığından seçenekleri üretir. */
    public static RegisterOptionsResponse current() {
        return new RegisterOptionsResponse(IntStream.rangeClosed(AppConstants.MIN_GRADE, AppConstants.GRADUATE_GRADE)
                .boxed()
                .toList());
    }
}
