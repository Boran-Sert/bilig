package com.hataanalizi.core.tutor;

import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

/** Öğrenciye ait tutor sohbetlerini sorgular. */
public interface TutorConversationRepository extends JpaRepository<TutorConversation, Long> {

    /** Sohbeti yalnızca sahibiyle eşleştiğinde döndürür. */
    Optional<TutorConversation> findByIdAndUserId(Long id, Long userId);
}
