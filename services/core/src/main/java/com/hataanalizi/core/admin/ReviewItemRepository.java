package com.hataanalizi.core.admin;

import jakarta.persistence.LockModeType;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

/** İnceleme kayıtlarını okur ve karar sırasında eşzamanlı değişiklikleri kilitler. */
public interface ReviewItemRepository extends JpaRepository<ReviewItem, Long> {

    /** Karar verilecek inceleme kaydını sebebiyle eşleşirse yazma kilidiyle bulur. */
    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("SELECT reviewItem FROM ReviewItem reviewItem WHERE reviewItem.id = :id AND reviewItem.reason = :reason")
    Optional<ReviewItem> findByIdForUpdate(@Param("id") Long id, @Param("reason") String reason);
}
