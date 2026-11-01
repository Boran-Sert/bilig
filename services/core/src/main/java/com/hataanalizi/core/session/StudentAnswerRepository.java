package com.hataanalizi.core.session;

import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

/** Cevapları, oturum sahipliğini ve soru kazanımlarını sorgular. */
public interface StudentAnswerRepository extends JpaRepository<StudentAnswer, Long> {

    /** Oturumu cevap işlemi boyunca kilitler. */
    @Query(value = """
                    SELECT user_id AS "userId", status
                    FROM study_session
                    WHERE id = :sessionId
                    FOR UPDATE
                    """, nativeQuery = true)
    Optional<SessionContext> lockSessionById(@Param("sessionId") Long sessionId);

    /** Yayımlanmış test sorusunun doğru cevabını bulur. */
    @Query(value = """
                    SELECT question.correct_option AS "correctOption"
                    FROM study_session
                    JOIN exam_question ON exam_question.exam_id = study_session.exam_id
                        AND exam_question.question_id = :questionId
                    JOIN question ON question.id = exam_question.question_id
                        AND question.status = :publishedStatus
                    WHERE study_session.id = :sessionId
                    """, nativeQuery = true)
    Optional<QuestionContext> findPublishedQuestionInSession(
            @Param("sessionId") Long sessionId,
            @Param("questionId") Long questionId,
            @Param("publishedStatus") String publishedStatus);

    /** Aynı oturumda soruya daha önce cevap verilip verilmediğini söyler. */
    boolean existsByStudySessionIdAndQuestionId(Long studySessionId, Long questionId);

    /** Sorunun bütün kazanımlarını sıra belirtmeden döndürür. */
    @Query(value = """
                    SELECT learning_outcome.code AS code, learning_outcome.title AS title
                    FROM question_outcome
                    JOIN learning_outcome ON learning_outcome.id = question_outcome.learning_outcome_id
                    WHERE question_outcome.question_id = :questionId
                    """, nativeQuery = true)
    List<LearningOutcome> findLearningOutcomesByQuestionId(@Param("questionId") Long questionId);

    /** Testteki doğru, yanlış ve boş cevap sayılarını döndürür. */
    @Query(value = """
                    SELECT COUNT(student_answer.id)
                               FILTER (WHERE student_answer.is_correct) AS "correctCount",
                           COUNT(student_answer.id)
                               FILTER (WHERE student_answer.id IS NOT NULL AND NOT student_answer.is_correct)
                               AS "wrongCount",
                           COUNT(exam_question.question_id)
                               FILTER (WHERE question.id IS NOT NULL AND student_answer.id IS NULL)
                               AS "blankCount"
                    FROM study_session
                    LEFT JOIN exam_question ON exam_question.exam_id = study_session.exam_id
                    LEFT JOIN question ON question.id = exam_question.question_id
                        AND question.status = :publishedStatus
                    LEFT JOIN student_answer ON student_answer.study_session_id = study_session.id
                        AND student_answer.question_id = exam_question.question_id
                        AND question.id IS NOT NULL
                    WHERE study_session.id = :sessionId
                    """, nativeQuery = true)
    SessionAnswerCounts findSessionAnswerCounts(
            @Param("sessionId") Long sessionId, @Param("publishedStatus") String publishedStatus);

    /** Testte yanlış cevaplanan soruların kazanım bazlı sayılarını döndürür. */
    @Query(value = """
                    SELECT learning_outcome.code AS code, learning_outcome.title AS title,
                           COUNT(student_answer.id)
                               FILTER (WHERE student_answer.is_correct = false) AS "wrongCount"
                    FROM study_session
                    JOIN exam_question ON exam_question.exam_id = study_session.exam_id
                    JOIN question ON question.id = exam_question.question_id
                        AND question.status = :publishedStatus
                    JOIN question_outcome ON question_outcome.question_id = question.id
                    JOIN learning_outcome ON learning_outcome.id = question_outcome.learning_outcome_id
                    LEFT JOIN student_answer ON student_answer.study_session_id = study_session.id
                        AND student_answer.question_id = exam_question.question_id
                    WHERE study_session.id = :sessionId
                    GROUP BY learning_outcome.code, learning_outcome.title
                    """, nativeQuery = true)
    List<OutcomeWrongCount> findOutcomeWrongCountsBySessionId(
            @Param("sessionId") Long sessionId, @Param("publishedStatus") String publishedStatus);

    /** Konumu cevaplanmamış ilk yayımlanmış soruya, hepsi cevaplıysa son sıranın sonrasına taşır. */
    @Modifying(flushAutomatically = true)
    @Query(value = """
                    UPDATE study_session
                    SET current_position = (
                        SELECT COALESCE(
                                   MIN(exam_question.position) FILTER (WHERE student_answer.id IS NULL),
                                   MAX(exam_question.position) + 1)
                        FROM exam_question
                        JOIN question ON question.id = exam_question.question_id
                            AND question.status = :publishedStatus
                        LEFT JOIN student_answer ON student_answer.study_session_id = study_session.id
                            AND student_answer.question_id = exam_question.question_id
                        WHERE exam_question.exam_id = study_session.exam_id)
                    WHERE id = :sessionId
                    """, nativeQuery = true)
    int moveToFirstUnansweredPosition(
            @Param("sessionId") Long sessionId, @Param("publishedStatus") String publishedStatus);

    /** Cevap isteği için oturum bilgisini taşır. */
    interface SessionContext {

        /** Oturum sahibinin kimliğini döndürür. */
        Long getUserId();

        /** Oturum durumunu döndürür. */
        String getStatus();
    }

    /** Testteki sorunun doğru cevabını taşır. */
    interface QuestionContext {

        /** Sorunun doğru şıkkını döndürür. */
        String getCorrectOption();
    }

    /** Oturumun cevap sayımlarını taşır. */
    interface SessionAnswerCounts {

        /** Doğru cevap sayısını döndürür. */
        Long getCorrectCount();

        /** Yanlış cevap sayısını döndürür. */
        Long getWrongCount();

        /** Boş cevap sayısını döndürür. */
        Long getBlankCount();
    }

    /** Kazanımın yanlış cevap sayısını taşır. */
    interface OutcomeWrongCount {

        /** Kazanım kodunu döndürür. */
        String getCode();

        /** Kazanım başlığını döndürür. */
        String getTitle();

        /** Kazanımdaki yanlış cevap sayısını döndürür. */
        Long getWrongCount();
    }

    /** Bir kazanımın API yanıtında gereken alanlarını taşır. */
    interface LearningOutcome {

        /** Kazanım kodunu döndürür. */
        String getCode();

        /** Kazanım başlığını döndürür. */
        String getTitle();
    }
}
