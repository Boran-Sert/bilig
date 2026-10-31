package com.hataanalizi.core.exam;

import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

/** Testleri ve soru sıralarını veritabanından okur. */
public interface ExamRepository extends JpaRepository<Exam, Long> {

    /** Kullanıcının yayınlanmış testlerini ve son oturum ilerlemesini tek sorguda getirir. */
    @Query(value = """
                    SELECT e.id AS id,
                           e.title AS title,
                           COUNT(question.id) AS "questionCount",
                           COUNT(sa.question_id) AS "answeredCount",
                           latest_session.id AS "sessionId",
                           latest_session.status AS status
                    FROM exam e
                    LEFT JOIN LATERAL (
                        SELECT session.id, session.status
                        FROM study_session session
                        WHERE session.exam_id = e.id
                          AND session.user_id = :userId
                        ORDER BY session.started_at DESC, session.id DESC
                        LIMIT 1
                    ) latest_session ON true
                    LEFT JOIN exam_question eq ON eq.exam_id = e.id
                    LEFT JOIN question ON question.id = eq.question_id
                        AND question.status = :publishedQuestionStatus
                    LEFT JOIN student_answer sa
                        ON sa.study_session_id = latest_session.id
                       AND sa.question_id = question.id
                    WHERE e.status = :publishedExamStatus
                    GROUP BY e.id, e.title, latest_session.id, latest_session.status
                    ORDER BY e.id
                    """, nativeQuery = true)
    List<ExamSummaryRow> findPublishedSummariesByUserId(
            @Param("userId") Long userId,
            @Param("publishedExamStatus") String publishedExamStatus,
            @Param("publishedQuestionStatus") String publishedQuestionStatus);

    /** Yayınlanmış test kimliğine göre yükler. */
    Optional<Exam> findByIdAndStatus(Long id, String status);

    /** Testteki yayımlanmış soruları sıralı konumlarıyla döndürür. */
    @Query(value = """
                    SELECT exam_question.question_id AS "questionId", exam_question.position
                    FROM exam_question
                    JOIN question ON question.id = exam_question.question_id
                        AND question.status = :publishedQuestionStatus
                    WHERE exam_question.exam_id = :examId
                    ORDER BY exam_question.position
                    """, nativeQuery = true)
    List<ExamQuestionPosition> findQuestionPositions(
            @Param("examId") Long examId, @Param("publishedQuestionStatus") String publishedQuestionStatus);

    /** Test listesi sorgusunun özet alanlarını temsil eder. */
    interface ExamSummaryRow {

        /** Test kimliğini döndürür. */
        Long getId();

        /** Test başlığını döndürür. */
        String getTitle();

        /** Testteki soru sayısını döndürür. */
        Long getQuestionCount();

        /** Son oturumdaki cevap sayısını döndürür. */
        Long getAnsweredCount();

        /** Son oturum kimliğini veya null değerini döndürür. */
        Long getSessionId();

        /** Son oturum durumunu veya null değerini döndürür. */
        String getStatus();
    }

    /** Test sorusunun kimliğini ve sırasını temsil eder. */
    interface ExamQuestionPosition {

        /** Soru kimliğini döndürür. */
        Long getQuestionId();

        /** Soru sırasını döndürür. */
        Short getPosition();
    }
}
