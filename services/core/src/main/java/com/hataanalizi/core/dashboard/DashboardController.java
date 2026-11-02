package com.hataanalizi.core.dashboard;

import com.hataanalizi.core.auth.AuthUser;
import com.hataanalizi.core.dashboard.dto.DashboardResponse;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/** Öğrencinin panel özetini sunar. */
@RestController
@RequestMapping("/api/me")
public class DashboardController {

    private final DashboardService dashboardService;

    /** Panel sorgu bağımlılığını saklar. */
    public DashboardController(DashboardService dashboardService) {
        this.dashboardService = dashboardService;
    }

    /** Giriş yapmış öğrencinin ilerleme ve kazanım özetini döndürür. */
    @GetMapping("/dashboard")
    public DashboardResponse dashboard(@AuthenticationPrincipal AuthUser authUser) {
        return dashboardService.getDashboard(authUser);
    }
}
