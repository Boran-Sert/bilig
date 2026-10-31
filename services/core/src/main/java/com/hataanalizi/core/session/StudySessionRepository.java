package com.hataanalizi.core.session;

import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

/** Öğrenci oturumlarını ve kayıtlı cevap seçimlerini okur. */
public interface StudySessionRepository extends JpaRepository<StudySession, Long> {

    /** Öğrencinin testteki açık oturumunu bulur. */
    Optional<StudySession> findByUserIdAndExamIdAndStatus(Long userId, Long examId, String status);

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
