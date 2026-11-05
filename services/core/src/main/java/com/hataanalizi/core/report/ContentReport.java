package com.hataanalizi.core.report;

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

/** Öğrenci bildirimini content_report tablosuyla eşler. */
@Entity
@Table(name = "content_report")
@Getter
@Setter
@NoArgsConstructor
public class ContentReport {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "user_id", nullable = false)
    private Long userId;

    @Column(name = "question_id")
    private Long questionId;

    @Column(name = "tutor_message_id")
    private Long tutorMessageId;

    @Column(columnDefinition = "text")
    private String note;

    @Column(nullable = false, insertable = false, updatable = false, columnDefinition = "text")
    private String status;

    @Column(name = "created_at", nullable = false, insertable = false, updatable = false)
    private OffsetDateTime createdAt;
}
