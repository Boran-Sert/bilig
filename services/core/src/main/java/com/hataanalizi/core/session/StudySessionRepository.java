package com.hataanalizi.core.session;

import java.math.BigDecimal;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

/** Öğrenci oturumlarını ve kayıtlı cevap seçimlerini okur. */
public interface StudySessionRepository extends JpaRepository<StudySession, Long> {

    /** Öğrencinin testteki açık oturumunu bulur. */
    Optional<StudySession> findByUserIdAndExamIdAndStatus(Long userId, Long examId, String status);

    /** Açık oturum yoksa atomik olarak yeni oturum oluşturur. */
    @Modifying
    @Query(value = """
                    INSERT INTO study_session (user_id, exam_id)
                    VALUES (:userId, :examId)
                    ON CONFLICT (user_id, exam_id) WHERE status = 'IN_PROGRESS'
                    DO NOTHING
                    """, nativeQuery = true)
    int createInProgressSessionIfAbsent(@Param("userId") Long userId, @Param("examId") Long examId);

    /** Oturumun netini yazar ve tamamlanma zamanını kaydeder. */
    @Modifying
    @Query(value = """
                    UPDATE study_session
                    SET status = :completedStatus, net = :net, completed_at = now()
                    WHERE id = :sessionId AND status = :inProgressStatus
                    """, nativeQuery = true)
    int completeSession(
            @Param("sessionId") Long sessionId,
            @Param("net") BigDecimal net,
            @Param("completedStatus") String completedStatus,
            @Param("inProgressStatus") String inProgressStatus);

    /** Oturumdaki cevaplanan soruların seçimlerini döndürür. */
    @Query(value = """
                    SELECT question_id AS "questionId", selected_option AS "selectedOption"
                    FROM student_answer
                    WHERE study_session_id = :sessionId
                    """, nativeQuery = true)
    List<AnswerSelection> findAnswerSelectionsBySessionId(@Param("sessionId") Long sessionId);

    /** Bir soruya verilen seçimi temsil eder. */
    interface AnswerSelection {

        /** Cevaplanan soru kimliğini döndürür. */
        Long getQuestionId();

        /** Öğrencinin seçtiği şıkkı döndürür. */
        String getSelectedOption();
    }
}
