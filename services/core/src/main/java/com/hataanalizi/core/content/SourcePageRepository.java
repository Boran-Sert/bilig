package com.hataanalizi.core.content;

import java.util.Optional;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.Repository;
import org.springframework.data.repository.query.Param;

/** Kaynak sayfasının görüntü yolunu salt okunur sorgular. */
public interface SourcePageRepository extends Repository<SourcePage, Long> {

    /** Kimliğe göre kaynak sayfasını bulur. */
    @Query("SELECT page FROM SourcePage page WHERE page.id = :id")
    Optional<SourcePage> findById(@Param("id") Long id);
}
