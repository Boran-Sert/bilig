package com.hataanalizi.core.question;

import java.util.Collection;
import java.util.List;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.Repository;
import org.springframework.data.repository.query.Param;

/** Soru içeriğini yalnızca okumak için sorgular. */
public interface QuestionRepository extends Repository<Question, Long> {

    /** Kimlik listesine göre soru içeriklerini okur. */
    @Query("SELECT question FROM Question question WHERE question.id IN :questionIds")
    List<Question> findAllByQuestionIds(@Param("questionIds") Collection<Long> questionIds);
}
