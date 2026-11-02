package com.hataanalizi.core.dashboard;

import com.hataanalizi.core.auth.AuthUser;
import com.hataanalizi.core.common.AppConstants;
import com.hataanalizi.core.dashboard.dto.DashboardResponse;
import com.hataanalizi.core.dashboard.dto.DashboardResponse.ActiveSession;
import com.hataanalizi.core.dashboard.dto.DashboardResponse.ErrorTypeCount;
import com.hataanalizi.core.dashboard.dto.DashboardResponse.FailedOutcome;
import com.hataanalizi.core.dashboard.dto.DashboardResponse.Summary;
import com.hataanalizi.core.dashboard.dto.DashboardResponse.UnitAccuracy;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.List;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/** Öğrenci panelini salt okunur sorgularla birleştirir. */
@Service
public class DashboardService {

    private static final BigDecimal PERCENT_SCALE = BigDecimal.valueOf(100);

    private final DashboardRepository dashboardRepository;

    /** Panel repository bağımlılığını saklar. */
    public DashboardService(DashboardRepository dashboardRepository) {
        this.dashboardRepository = dashboardRepository;
    }

    /** Öğrencinin kendi test, kazanım ve cevap istatistiklerini döndürür. */
    @Transactional(readOnly = true)
    public DashboardResponse getDashboard(AuthUser authUser) {
        long userId = authUser.id();
        DashboardRepository.SummaryRow summaryRow = dashboardRepository
                .findSummaryByUserId(
                        userId, AppConstants.SESSION_STATUS_COMPLETED, AppConstants.QUESTION_STATUS_PUBLISHED)
                .orElseThrow(() -> new IllegalStateException("Dashboard summary query returned no result."));
        Summary summary = new Summary(
                summaryRow.getAnsweredCount(),
                accuracyPercent(summaryRow.getCorrectCount(), summaryRow.getAnsweredCount()),
                summaryRow.getLatestNet(),
                summaryRow.getLatestQuestionCount());
        List<ActiveSession> activeSessions = dashboardRepository
                .findActiveSessionsByUserId(
                        userId,
                        AppConstants.SESSION_STATUS_IN_PROGRESS,
                        AppConstants.EXAM_STATUS_PUBLISHED,
                        AppConstants.QUESTION_STATUS_PUBLISHED)
                .stream()
                .map(DashboardService::toActiveSession)
                .toList();
        List<FailedOutcome> failedOutcomes = dashboardRepository
                .findFailedOutcomesByUserId(userId, AppConstants.MAX_WRONG_PER_TEST, AppConstants.MAX_WRONG_TOTAL)
                .stream()
                .map(DashboardService::toFailedOutcome)
                .toList();
        List<UnitAccuracy> unitAccuracy = dashboardRepository.findUnitAccuracyByUserId(userId).stream()
                .map(DashboardService::toUnitAccuracy)
                .toList();
        List<ErrorTypeCount> errorTypes = dashboardRepository.findErrorTypeCountsByUserId(userId).stream()
                .map(DashboardService::toErrorTypeCount)
                .toList();
        return new DashboardResponse(summary, activeSessions, failedOutcomes, unitAccuracy, errorTypes);
    }

    /** Doğru cevap oranını yüzde ve iki ondalık basamakla hesaplar. */
    private static BigDecimal accuracyPercent(long correct, long answered) {
        if (answered == 0) {
            return BigDecimal.ZERO.setScale(2);
        }
        return BigDecimal.valueOf(correct)
                .multiply(PERCENT_SCALE)
                .divide(BigDecimal.valueOf(answered), 2, RoundingMode.HALF_UP);
    }

    /** Açık oturum sorgu sonucunu API yanıtına dönüştürür. */
    private static ActiveSession toActiveSession(DashboardRepository.ActiveSessionRow row) {
        return new ActiveSession(
                row.getSessionId(),
                row.getExamTitle(),
                row.getQuestionCount(),
                row.getAnsweredCount(),
                row.getCurrentPosition());
    }

    /** Başarısız kazanım sorgu sonucunu API yanıtına dönüştürür. */
    private static FailedOutcome toFailedOutcome(DashboardRepository.FailedOutcomeRow row) {
        return new FailedOutcome(
                row.getCode(), row.getTitle(), row.getTotalWrongCount(), row.getTestTitle(), row.getTestWrongCount());
    }

    /** Ünite doğruluk sorgu sonucunu yüzdeyle birlikte API yanıtına dönüştürür. */
    private static UnitAccuracy toUnitAccuracy(DashboardRepository.UnitAccuracyRow row) {
        return new UnitAccuracy(
                row.getUnitTitle(),
                row.getAnsweredCount(),
                row.getCorrectCount(),
                accuracyPercent(row.getCorrectCount(), row.getAnsweredCount()));
    }

    /** Hata türü sayımını API yanıtına dönüştürür. */
    private static ErrorTypeCount toErrorTypeCount(DashboardRepository.ErrorTypeCountRow row) {
        return new ErrorTypeCount(row.getErrorType(), row.getAnswerCount());
    }
}
