package com.hataanalizi.core.dashboard;

import com.hataanalizi.core.session.StudySession;
import java.math.BigDecimal;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.Repository;
import org.springframework.data.repository.query.Param;

/** Öğrenci paneli istatistiklerini parametreli SQL ile okur. */
public interface DashboardRepository extends Repository<StudySession, Long> {

    /** Cevap toplamını ve son tamamlanan test netini döndürür. */
    @Query(value = """
                    WITH answer_summary AS (
                        SELECT COUNT(student_answer.id) AS "answeredCount",
                               COUNT(student_answer.id)
                                   FILTER (WHERE student_answer.is_correct) AS "correctCount"
                        FROM study_session
                        JOIN student_answer
                            ON student_answer.study_session_id = study_session.id
                        WHERE study_session.user_id = :userId
                    ),
                    latest_completed AS (
                        SELECT study_session.id, study_session.net, study_session.exam_id
                        FROM study_session
                        WHERE study_session.user_id = :userId
                          AND study_session.status = :completedStatus
                          AND study_session.exam_id IS NOT NULL
                        ORDER BY study_session.completed_at DESC NULLS LAST, study_session.id DESC
                        LIMIT 1
                    )
                    SELECT answer_summary."answeredCount",
                           answer_summary."correctCount",
                           latest_completed.net AS "latestNet",
                           CASE WHEN latest_completed.id IS NULL THEN NULL ELSE
                               (SELECT COUNT(question.id)
                                FROM exam_question
                                JOIN question ON question.id = exam_question.question_id
                                    AND question.status = :publishedQuestionStatus
                                WHERE exam_question.exam_id = latest_completed.exam_id)
                           END AS "latestQuestionCount"
                    FROM answer_summary
                    LEFT JOIN latest_completed ON true
                    """, nativeQuery = true)
    Optional<SummaryRow> findSummaryByUserId(
            @Param("userId") Long userId,
            @Param("completedStatus") String completedStatus,
            @Param("publishedQuestionStatus") String publishedQuestionStatus);

    /** Öğrencinin yayındaki testlerdeki devam eden oturumlarını döndürür. */
    @Query(value = """
                    SELECT study_session.id AS "sessionId",
                           exam.title AS "examTitle",
                           COUNT(question.id) AS "questionCount",
                           COUNT(student_answer.id) AS "answeredCount",
                           study_session.current_position AS "currentPosition"
                    FROM study_session
                    JOIN exam ON exam.id = study_session.exam_id
                        AND exam.status = :publishedExamStatus
                    JOIN exam_question ON exam_question.exam_id = exam.id
                    JOIN question ON question.id = exam_question.question_id
                        AND question.status = :publishedQuestionStatus
                    LEFT JOIN student_answer
                        ON student_answer.study_session_id = study_session.id
                       AND student_answer.question_id = question.id
                    WHERE study_session.user_id = :userId
                      AND study_session.status = :inProgressStatus
                    GROUP BY study_session.id, exam.title
                    ORDER BY study_session.started_at DESC, study_session.id DESC
                    """, nativeQuery = true)
    List<ActiveSessionRow> findActiveSessionsByUserId(
            @Param("userId") Long userId,
            @Param("inProgressStatus") String inProgressStatus,
            @Param("publishedExamStatus") String publishedExamStatus,
            @Param("publishedQuestionStatus") String publishedQuestionStatus);

    /** Test veya toplam eşiğini aşan kazanımları yanlış sayımlarıyla döndürür. */
    @Query(value = """
                    WITH outcome_session_wrong_counts AS (
                        SELECT question_outcome.learning_outcome_id,
                               study_session.id AS session_id,
                               exam.title AS test_title,
                               study_session.started_at,
                               COUNT(student_answer.id) AS wrong_count
                        FROM study_session
                        JOIN student_answer
                            ON student_answer.study_session_id = study_session.id
                           AND student_answer.is_correct = false
                        JOIN question_outcome ON question_outcome.question_id = student_answer.question_id
                        LEFT JOIN exam ON exam.id = study_session.exam_id
                        WHERE study_session.user_id = :userId
                          AND study_session.exam_id IS NOT NULL
                        GROUP BY question_outcome.learning_outcome_id,
                                 study_session.id,
                                 exam.title,
                                 study_session.started_at
                    ),
                    latest_test_failure AS (
                        SELECT DISTINCT ON (learning_outcome_id)
                               learning_outcome_id,
                               test_title,
                               wrong_count
                        FROM outcome_session_wrong_counts
                        WHERE wrong_count > :maximumWrongPerTest
                        ORDER BY learning_outcome_id, started_at DESC, session_id DESC
                    ),
                    outcome_total_wrong AS (
                        SELECT question_outcome.learning_outcome_id,
                               COUNT(student_answer.id) AS wrong_count
                        FROM study_session
                        JOIN student_answer
                            ON student_answer.study_session_id = study_session.id
                           AND student_answer.is_correct = false
                        JOIN question_outcome ON question_outcome.question_id = student_answer.question_id
                        WHERE study_session.user_id = :userId
                        GROUP BY question_outcome.learning_outcome_id
                    )
                    SELECT learning_outcome.code AS code,
                           learning_outcome.title AS title,
                           outcome_total_wrong.wrong_count AS "totalWrongCount",
                           latest_test_failure.test_title AS "testTitle",
                           latest_test_failure.wrong_count AS "testWrongCount"
                    FROM outcome_total_wrong
                    JOIN learning_outcome
                        ON learning_outcome.id = outcome_total_wrong.learning_outcome_id
                    LEFT JOIN latest_test_failure
                        ON latest_test_failure.learning_outcome_id = learning_outcome.id
                    WHERE outcome_total_wrong.wrong_count > :maximumWrongTotal
                       OR latest_test_failure.learning_outcome_id IS NOT NULL
                    """, nativeQuery = true)
    List<FailedOutcomeRow> findFailedOutcomesByUserId(
            @Param("userId") Long userId,
            @Param("maximumWrongPerTest") int maximumWrongPerTest,
            @Param("maximumWrongTotal") int maximumWrongTotal);

    /** Öğrencinin cevap doğruluğunu ünite başlığına göre toplar. */
    @Query(value = """
                    SELECT curriculum_unit.title AS "unitTitle",
                           COUNT(student_answer.id) AS "answeredCount",
                           COUNT(student_answer.id)
                               FILTER (WHERE student_answer.is_correct) AS "correctCount"
                    FROM study_session
                    JOIN student_answer
                        ON student_answer.study_session_id = study_session.id
                    JOIN question ON question.id = student_answer.question_id
                    JOIN curriculum_unit ON curriculum_unit.id = question.curriculum_unit_id
                    WHERE study_session.user_id = :userId
                    GROUP BY curriculum_unit.id, curriculum_unit.title
                    """, nativeQuery = true)
    List<UnitAccuracyRow> findUnitAccuracyByUserId(@Param("userId") Long userId);

    /** Öğrencinin sınıflandırılmış cevap hata türlerini sayar. */
    @Query(value = """
                    SELECT student_answer.error_type AS "errorType",
                           COUNT(student_answer.id) AS "answerCount"
                    FROM study_session
                    JOIN student_answer
                        ON student_answer.study_session_id = study_session.id
                    WHERE study_session.user_id = :userId
                      AND student_answer.error_type IS NOT NULL
                    GROUP BY student_answer.error_type
                    """, nativeQuery = true)
    List<ErrorTypeCountRow> findErrorTypeCountsByUserId(@Param("userId") Long userId);

    /** Panelin genel cevap ve son test özetini taşır. */
    interface SummaryRow {

        /** Toplam cevaplanan soru sayısını döndürür. */
        Long getAnsweredCount();

        /** Toplam doğru cevap sayısını döndürür. */
        Long getCorrectCount();

        /** Son tamamlanan test netini veya null değerini döndürür. */
        BigDecimal getLatestNet();

        /** Son tamamlanan testteki soru sayısını veya null değerini döndürür. */
        Long getLatestQuestionCount();
    }

    /** Devam eden test oturumunu taşır. */
    interface ActiveSessionRow {

        /** Oturum kimliğini döndürür. */
        Long getSessionId();

        /** Test başlığını döndürür. */
        String getExamTitle();

        /** Testteki yayımlanmış soru sayısını döndürür. */
        Long getQuestionCount();

        /** Cevaplanmış soru sayısını döndürür. */
        Long getAnsweredCount();

        /** Öğrencinin mevcut soru konumunu döndürür. */
        Short getCurrentPosition();
    }

    /** Başarısız kazanımın test ve toplam yanlış sayılarını taşır. */
    interface FailedOutcomeRow {

        /** Kazanım kodunu döndürür. */
        String getCode();

        /** Kazanım başlığını döndürür. */
        String getTitle();

        /** Öğrencinin bütün oturumlardaki yanlış sayısını döndürür. */
        Long getTotalWrongCount();

        /** Eşiğin aşıldığı en son test başlığını veya null değerini döndürür. */
        String getTestTitle();

        /** Eşiğin aşıldığı en son testteki yanlış sayısını veya null değerini döndürür. */
        Long getTestWrongCount();
    }

    /** Ünite başlığı için cevap doğruluğu toplamlarını taşır. */
    interface UnitAccuracyRow {

        /** Ünite başlığını döndürür. */
        String getUnitTitle();

        /** Cevaplanan soru sayısını döndürür. */
        Long getAnsweredCount();

        /** Doğru cevap sayısını döndürür. */
        Long getCorrectCount();
    }

    /** Bir hata türünün cevap sayısını taşır. */
    interface ErrorTypeCountRow {

        /** Hata türü kodunu döndürür. */
        String getErrorType();

        /** Bu hata türündeki cevap sayısını döndürür. */
        Long getAnswerCount();
    }
}
