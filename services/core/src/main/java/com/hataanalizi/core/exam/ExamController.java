package com.hataanalizi.core.exam;

import com.hataanalizi.core.auth.AuthUser;
import com.hataanalizi.core.exam.dto.ExamSummaryResponse;
import java.util.List;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/** Öğrencinin test listesini sunar. */
@RestController
@RequestMapping("/api/tests")
public class ExamController {

    private final ExamService examService;

    /** Test iş kurallarını saklar. */
    public ExamController(ExamService examService) {
        this.examService = examService;
    }

    /** Yayındaki testleri mevcut öğrencinin ilerlemesiyle listeler. */
    @GetMapping
    public List<ExamSummaryResponse> listTests(@AuthenticationPrincipal AuthUser authUser) {
        return examService.findPublishedExams(authUser);
    }
}
