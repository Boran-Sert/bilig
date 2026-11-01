package com.hataanalizi.core.session.dto;

import java.util.List;

/** Devam eden test oturumunu ve sıralı sorularını taşır. */
public record SessionResponse(Long sessionId, short currentPosition, List<SessionQuestionResponse> questions) {}
