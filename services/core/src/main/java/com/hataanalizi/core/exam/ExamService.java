package com.hataanalizi.core.exam;

import com.hataanalizi.core.auth.AuthUser;
import com.hataanalizi.core.common.AppConstants;
import com.hataanalizi.core.exam.dto.ExamSummaryResponse;
import java.util.List;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/** Öğrenciye yayınlanmış testleri ve ilerlemesini sunar. */
@Service
public class ExamService {

    private final ExamRepository examRepository;

    /** Test repository bağımlılığını saklar. */
    public ExamService(ExamRepository examRepository) {
        this.examRepository = examRepository;
    }

    /** Yayındaki testleri öğrencinin en son oturumuyla birlikte listeler. */
    @Transactional(readOnly = true)
    public List<ExamSummaryResponse> findPublishedExams(AuthUser authUser) {
        return examRepository
                .findPublishedSummariesByUserId(
                        authUser.id(), AppConstants.EXAM_STATUS_PUBLISHED, AppConstants.QUESTION_STATUS_PUBLISHED)
                .stream()
                .map(ExamService::toResponse)
                .toList();
    }

    /** Veritabanı özetini API yanıtına dönüştürür. */
    private static ExamSummaryResponse toResponse(ExamRepository.ExamSummaryRow row) {
        return new ExamSummaryResponse(
                row.getId(),
                row.getTitle(),
                row.getQuestionCount(),
                row.getAnsweredCount(),
                row.getSessionId(),
                row.getStatus());
    }
}
