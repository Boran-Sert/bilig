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
}
