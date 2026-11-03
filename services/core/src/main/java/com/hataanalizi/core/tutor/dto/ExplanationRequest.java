package com.hataanalizi.core.tutor.dto;

import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;

/** Yanlış cevap anlatımı için oturum ve soru kimliklerini taşır. */
public record ExplanationRequest(
        @NotNull @Positive Long sessionId,
        @NotNull @Positive Long questionId) {}
