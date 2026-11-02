package com.hataanalizi.core.question;

import jakarta.persistence.LockModeType;
import java.util.Collection;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.Repository;
import org.springframework.data.repository.query.Param;

/** Soru içeriğini okur ve ipucunu saklar. */
public interface QuestionRepository extends Repository<Question, Long> {

    /** Kimlik listesine göre soru içeriklerini okur. */
    @Query("SELECT question FROM Question question WHERE question.id IN :questionIds")
    List<Question> findAllByQuestionIds(@Param("questionIds") Collection<Long> questionIds);

    /** İpucu oluşturulurken eşzamanlı üretimi önlemek için soruyu kilitleyerek bulur. */
    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("SELECT question FROM Question question WHERE question.id = :questionId")
    Optional<Question> findByIdForUpdate(@Param("questionId") Long questionId);

    /** Değişen soru kaydını saklar. */
    Question save(Question question);
}
