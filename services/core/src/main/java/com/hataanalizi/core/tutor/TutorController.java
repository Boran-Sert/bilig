package com.hataanalizi.core.tutor;

import com.hataanalizi.core.auth.AuthUser;
import com.hataanalizi.core.tutor.dto.ChatMessageRequest;
import com.hataanalizi.core.tutor.dto.ExplanationRequest;
import com.hataanalizi.core.tutor.dto.StartChatRequest;
import jakarta.validation.Valid;
import org.springframework.http.MediaType;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

/** Öğrenciye tutor anlatım ve sohbet akışı uçlarını sunar. */
@RestController
@RequestMapping("/api/tutor")
public class TutorController {

    private final TutorService tutorService;

    /** Tutor iş kurallarını saklar. */
    public TutorController(TutorService tutorService) {
        this.tutorService = tutorService;
    }

    /** Öğrencinin cevaplanmış sorusuna anlatım akışını başlatır. */
    @PostMapping(
            value = "/explanations",
            consumes = MediaType.APPLICATION_JSON_VALUE,
            produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public SseEmitter explain(
            @AuthenticationPrincipal AuthUser principal, @Valid @RequestBody ExplanationRequest request) {
        return tutorService.explain(principal.id(), request);
    }

    /** Sorunun sohbetini ilk iletiyle açar; soru cevaplanmamış olsa da çalışır. */
    @PostMapping(
            value = "/chats",
            consumes = MediaType.APPLICATION_JSON_VALUE,
            produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public SseEmitter startChat(
            @AuthenticationPrincipal AuthUser principal, @Valid @RequestBody StartChatRequest request) {
        return tutorService.startChat(principal.id(), request);
    }

    /** Öğrenci sohbet iletisini kaydeder ve yanıt akışını başlatır. */
    @PostMapping(
            value = "/conversations/{id}/messages",
            consumes = MediaType.APPLICATION_JSON_VALUE,
            produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public SseEmitter chat(
            @AuthenticationPrincipal AuthUser principal,
            @PathVariable Long id,
            @Valid @RequestBody ChatMessageRequest request) {
        return tutorService.chat(principal.id(), id, request);
    }
}
