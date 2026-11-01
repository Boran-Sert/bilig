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

    /** Yayımlanmış test sorusunun doğru cevabını ve sırasını bulur. */
    @Query(value = """
                    SELECT exam_question.position AS position,
                           question.correct_option AS "correctOption"
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

    /** Yanıtlanan soru mevcut konumsa sonraki konuma ilerletir. */
    @Modifying
    @Query(value = """
                    UPDATE study_session
                    SET current_position = current_position + 1
                    WHERE id = :sessionId AND current_position = :questionPosition
                    """, nativeQuery = true)
    int advanceCurrentPosition(@Param("sessionId") Long sessionId, @Param("questionPosition") Short questionPosition);

    /** Cevap isteği için oturum bilgisini taşır. */
    interface SessionContext {

        /** Oturum sahibinin kimliğini döndürür. */
        Long getUserId();

        /** Oturum durumunu döndürür. */
        String getStatus();
    }

    /** Testteki sorunun sırasını ve doğru cevabını taşır. */
    interface QuestionContext {

        /** Sorunun test içindeki konumunu döndürür. */
        Short getPosition();

        /** Sorunun doğru şıkkını döndürür. */
        String getCorrectOption();
    }

    /** Bir kazanımın API yanıtında gereken alanlarını taşır. */
    interface LearningOutcome {

        /** Kazanım kodunu döndürür. */
        String getCode();

        /** Kazanım başlığını döndürür. */
        String getTitle();
    }
}
