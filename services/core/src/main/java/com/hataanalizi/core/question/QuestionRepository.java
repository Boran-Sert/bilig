package com.hataanalizi.core.question;

import java.util.Collection;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.Repository;
import org.springframework.data.repository.query.Param;
import org.springframework.transaction.annotation.Transactional;

/** Soru içeriğini okur ve ipucunu saklar. */
public interface QuestionRepository extends Repository<Question, Long> {

    /** Kimlik listesine göre soru içeriklerini okur. */
    @Query("SELECT question FROM Question question WHERE question.id IN :questionIds")
    List<Question> findAllByQuestionIds(@Param("questionIds") Collection<Long> questionIds);

    /** Verilen durumdaki soruyu bulur. */
    @Query("SELECT question FROM Question question WHERE question.id = :questionId AND question.status = :status")
    Optional<Question> findByIdAndStatus(@Param("questionId") Long questionId, @Param("status") String status);

    /** İpucu boşsa yazar; başka bir istek önce yazdıysa dokunmaz. */
    @Transactional
    @Modifying
    @Query("""
            UPDATE Question question SET question.hint = :hint
            WHERE question.id = :questionId AND (question.hint IS NULL OR question.hint = '')
            """)
    int saveHintIfAbsent(@Param("questionId") Long questionId, @Param("hint") String hint);

    /** Sorunun kayıtlı ipucunu okur. */
    @Query("SELECT question.hint FROM Question question WHERE question.id = :questionId")
    String findHint(@Param("questionId") Long questionId);

    /**
     * Öğrencinin çözmediği, kazanımı en çok ortak olan, eşitlikte vektörü en yakın yayındaki soruyu
     * bulur.
     */
    @Query(value = """
            SELECT candidate.id, candidate.content, candidate.hint, candidate.status
            FROM question AS source_question
            JOIN question_outcome AS source_outcome ON source_outcome.question_id = source_question.id
            JOIN question_outcome AS candidate_outcome
                ON candidate_outcome.learning_outcome_id = source_outcome.learning_outcome_id
            JOIN question AS candidate ON candidate.id = candidate_outcome.question_id
            WHERE source_question.id = :questionId
                AND candidate.id <> source_question.id
                AND candidate.status = :publishedStatus
                AND NOT EXISTS (
                    SELECT 1
                    FROM student_answer
                    JOIN study_session ON study_session.id = student_answer.study_session_id
                    WHERE study_session.user_id = :userId AND student_answer.question_id = candidate.id)
            GROUP BY candidate.id
            ORDER BY COUNT(*) DESC,
                     MIN(candidate.embedding <=> source_question.embedding) NULLS LAST,
                     candidate.id
            LIMIT 1
            """, nativeQuery = true)
    Optional<Question> findSimilarQuestion(
            @Param("questionId") Long questionId,
            @Param("userId") Long userId,
            @Param("publishedStatus") String publishedStatus);
}
