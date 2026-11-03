package com.hataanalizi.core.tutor;

import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

/** Tutor sohbeti mesajlarını saklar ve en son mesajı bulur. */
public interface TutorMessageRepository extends JpaRepository<TutorMessage, Long> {

    /** Sohbetin en son yazılan mesajını kimlik sırasıyla döndürür. */
    Optional<TutorMessage> findFirstByTutorConversationIdOrderByIdDesc(Long tutorConversationId);
}
