package com.hataanalizi.core.session.dto;

import com.hataanalizi.core.common.AppConstants;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.PositiveOrZero;

/** Öğrencinin şık ve cevaplama bilgilerini taşır. */
public record AnswerRequest(
        @NotBlank(message = "{validation.answer.option}")
        @Pattern(regexp = AppConstants.ANSWER_OPTION_PATTERN, message = "{validation.answer.option}")
        String selectedOption,

        @PositiveOrZero(message = "{validation.answer.duration}")
        Integer durationMs,

        boolean hintUsed) {}
