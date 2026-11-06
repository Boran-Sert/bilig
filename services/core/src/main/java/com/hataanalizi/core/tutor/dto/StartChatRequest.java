package com.hataanalizi.core.tutor.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;

/** Sorunun sohbetini açan oturum, soru ve ilk iletiyi taşır. */
public record StartChatRequest(
        @NotNull @Positive Long sessionId,
        @NotNull @Positive Long questionId,
        @NotBlank String text) {}
