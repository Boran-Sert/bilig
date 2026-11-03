package com.hataanalizi.core.content;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import lombok.Getter;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.Immutable;

/** Kaynak paragrafının yalnızca okuma uçlarında kullanılan kolonlarını eşler. */
@Entity
@Immutable
@Table(name = "content_block")
@Getter
@NoArgsConstructor
public class ContentBlock {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "source_page_id", nullable = false)
    private Long sourcePageId;

    @Column(nullable = false, columnDefinition = "text")
    private String markdown;

    @Column(nullable = false, columnDefinition = "text")
    private String status;
}
