package com.hataanalizi.core.session;

import com.hataanalizi.core.auth.AuthUser;
import com.hataanalizi.core.session.dto.SessionResponse;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/** Öğrencinin test oturumunu başlatır veya kaldığı yerden sürdürür. */
@RestController
@RequestMapping("/api/tests")
public class SessionController {

    private final SessionService sessionService;

    /** Oturum iş kurallarını saklar. */
    public SessionController(SessionService sessionService) {
        this.sessionService = sessionService;
    }

    /** Testin öğrencinin açık oturumunu veya yeni oturumunu döndürür. */
    @PostMapping("/{id}/sessions")
    public SessionResponse startOrResume(@PathVariable Long id, @AuthenticationPrincipal AuthUser authUser) {
        return sessionService.startOrResume(id, authUser);
    }
}
