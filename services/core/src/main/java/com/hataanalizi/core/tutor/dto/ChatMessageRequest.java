package com.hataanalizi.core.tutor.dto;

import jakarta.validation.constraints.NotBlank;

/** Öğrencinin sohbet iletisini taşır. */
public record ChatMessageRequest(@NotBlank String text) {}
