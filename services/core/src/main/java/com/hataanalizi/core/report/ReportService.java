package com.hataanalizi.core.report;

import com.hataanalizi.core.common.ApiException;
import com.hataanalizi.core.common.ErrorCode;
import jakarta.persistence.EntityManager;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/** Bildirim hedefini ve sahipliğini doğrulayarak kaydeder. */
@Service
public class ReportService {

    private final EntityManager entityManager;
    private final JdbcTemplate jdbcTemplate;

    /** Bildirim kaydı ve hedef sorgularını saklar. */
    public ReportService(EntityManager entityManager, JdbcTemplate jdbcTemplate) {
        this.entityManager = entityManager;
        this.jdbcTemplate = jdbcTemplate;
    }

    /** Öğrencinin soru ya da kendi anlatım mesajı için bildirimini kaydeder. */
    @Transactional
    public void createReport(Long userId, Long questionId, Long messageId, String note) {
        if (questionId != null && !questionExists(questionId)) {
            throw new ApiException(ErrorCode.QUESTION_NOT_FOUND);
        }
        if (messageId != null && !isOwnedAssistantMessage(userId, messageId)) {
            throw new ApiException(ErrorCode.NOT_FOUND);
        }
        ContentReport report = new ContentReport();
        report.setUserId(userId);
        report.setQuestionId(questionId);
        report.setTutorMessageId(messageId);
        report.setNote(note);
        entityManager.persist(report);
    }

    /** Bildirilecek sorunun varlığını sorgular. */
    private boolean questionExists(Long questionId) {
        Boolean exists = jdbcTemplate.queryForObject(
                "SELECT EXISTS (SELECT 1 FROM question WHERE id = ?)", Boolean.class, questionId);
        return Boolean.TRUE.equals(exists);
    }

    /** Mesajın asistan yanıtı olduğunu ve öğrenci sohbetine ait olduğunu doğrular. */
    private boolean isOwnedAssistantMessage(Long userId, Long messageId) {
        Boolean owned = jdbcTemplate.queryForObject("""
                SELECT EXISTS (
                    SELECT 1
                    FROM tutor_message
                    JOIN tutor_conversation
                        ON tutor_conversation.id = tutor_message.tutor_conversation_id
                    WHERE tutor_message.id = ?
                        AND tutor_message.role = 'ASSISTANT'
                        AND tutor_conversation.user_id = ?
                )
                """, Boolean.class, messageId, userId);
        return Boolean.TRUE.equals(owned);
    }
}
