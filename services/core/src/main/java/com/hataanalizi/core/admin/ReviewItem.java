package com.hataanalizi.core.admin;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.OffsetDateTime;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

/** İnceleme kuyruğundaki bir hedefi ve karar bilgisini eşler. */
@Entity
@Table(name = "review_item")
@Getter
@Setter
@NoArgsConstructor
public class ReviewItem {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, columnDefinition = "text")
    private String reason;

    @Column(name = "content_block_id")
    private Long contentBlockId;

    @Column(name = "question_id")
    private Long questionId;

    @Column(nullable = false, columnDefinition = "text")
    private String status;

    @Column(name = "decided_by")
    private Long decidedBy;

    @Column(name = "decided_at")
    private OffsetDateTime decidedAt;

    @Column(name = "created_at", nullable = false, insertable = false, updatable = false)
    private OffsetDateTime createdAt;
}
